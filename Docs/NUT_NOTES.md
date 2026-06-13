# NUT Notes

These notes are based on local `NTP3` / `.nut` samples in this workspace and the
`Tools/Ulysses` source code.

## Scope

- This document is about the inner texture resource format itself.
- It does not try to solve outer `FHM` repacking.
- Current goal is a strict, reconstruction-friendly path from atlas image data back
  into a valid `.nut`.

## Verified Header

At file offset `0x00`:

- `0x00 .. 0x03`: ASCII magic `NTP3`
- `0x04`: version
- `0x05`: platform
- `0x06 .. 0x07`: big-endian `u16` surface count
- `0x08 .. 0x0F`: two reserved big-endian `u32`, zero in local samples

All numeric fields observed here are big-endian.

## Three Layouts Seen In Ulysses

`Tools/Ulysses/Ulysses/Resources/NuTexture.cs` explicitly handles three layouts:

1. type 1:
   normal self-contained NUT where surface headers and pixel data are in the same file
2. type 2:
   "fast load" FHM layout where item `0` contains copied headers and another item
   contains the full normal NUT payload
3. type 3:
   split layout where item `0` contains only the main NUT header, surface headers are
   separate items, and pixel data is in later items

The exported `Game Data Dumps/.../1/1/0/0.nut` files for fonts are not complete
type 1 files. They are header-only shells from a split/export context.

## Important Font Finding

For the 76 local `.uifont` resources checked so far:

- the atlas `0.nut` is always header-only in the dump
- pixel format is always `BC3`
- mip count is always `1`

Example:

- `Game Data Dumps/DATA00/DPL_UI_COMMON/0/0/1/1/0/0.nut`
  - size: `96`
  - surface count: `1`
  - `HeaderSize = 0x50`
  - `PixelOffset = 0x70`
  - no pixel payload is present in that exported file

After enabling raw export of internally consumed items, the matching full file is now
available too:

- `Game Data Dumps/DATA00/DPL_UI_COMMON/0/0/1/1/0/1.nut`
  - size: `8388736`
  - same first `96` bytes as `0.nut`
  - `0x20` zero bytes at `0x60 .. 0x7F`
  - BC3 pixel payload starts at absolute file offset `0x80`

So for these single-surface single-mip samples, `PixelOffset = 0x70` is not just a
header-only shell quirk. It is also the real value used by the full `1.nut`.

## How Ulysses Exports These

The local exported tree can be misleading unless `Ulysses`'s control flow is kept in mind.

Relevant code paths:

- `Tools/Ulysses/Ulysses.DPLUnpack/Program.cs`
- `Tools/Ulysses/Ulysses/Resources/NuTexture.cs`

What happens for a texture FHM:

1. `DPLUnpack` iterates FHM items in order.
2. For each normal item, it first saves the raw file as-is.
3. It then tries to construct a typed resource from that same item.
4. If the resource reports `IsFullyUtilized = true`, `DPLUnpack` stops iterating later
   sibling items in that FHM.

For `NuTexture`, this matters a lot:

- `NuTexture` sets `IsFullyUtilized = true` when:
  - `fhmIndex == 0`
  - and `fhm.Count == 2`
  - or `fhm.Count == 1 + 2 * surfaceCount`
- The source comments label these as:
  - type 2: header copy in item `0`, full normal NUT in item `1`
  - type 3: split virtual FHM

So in a type 2 texture FHM:

- item `0` is saved raw as `0.nut`
- `NuTexture` then reads item `1` internally as the actual pixel-bearing NUT payload
- the decoded surface is exported as `*.png` or `*.dds`
- because `IsFullyUtilized` is true, `DPLUnpack` breaks out and never separately saves
  item `1` as raw `1.nut`

This explains the local font atlas export shape:

- `.../1/1/0/0.nut`
- `.../1/1/0/08000000@0.png`

and the absence of a sibling raw `1.nut` in the exported tree.

So the missing `1.nut` in `Game Data Dumps` does not mean the original texture FHM lacked
that full payload item. It means `Ulysses` consumed it while exporting the resource.

## Surface Header Core

Each surface begins with a 0x30-byte core:

- `+0x00`: `i32` size
- `+0x04`: `i32` palette size
- `+0x08`: `i32` pixel size
- `+0x0C`: `u16` header size
- `+0x0E`: `u16` palette count
- `+0x10`: `u8` surface type
- `+0x11`: `u8` mip count
- `+0x12`: `u8` palette format
- `+0x13`: `u8` pixel format
- `+0x14`: `u16` width
- `+0x16`: `u16` height
- `+0x18`: `u32` caps1
- `+0x1C`: `u32` caps2
- `+0x20`: `i32` pixel offset
- `+0x24`: reserved
- `+0x28`: reserved
- `+0x2C`: reserved

All of these are big-endian on disk.

## Extra Header Area

### Single-mip surfaces

When `mip_count == 1`, the local samples use:

- `HeaderSize = 0x50`
- no explicit mip-size table
- only two 16-byte records after the 0x30-byte core:
  - `eXt\0`
  - `GIDX`

So:

- `0x30 + 0x20 = 0x50`

### Multi-mip surfaces

In the one local self-contained sample with inline pixels
`Game Data Dumps/DATA00/DPL_POSTPROCESS/0.nut`, surfaces with more than one mip level
use this pattern:

1. write one big-endian `u32` mip-size entry per mip
2. pad that table to a 16-byte boundary
3. append the same `eXt\0` and `GIDX` 16-byte records

This matches local examples such as:

- mip 6:
  - `0x18` bytes mip table
  - `0x08` bytes pad
  - `0x20` bytes `eXt/GIDX`
  - total extra = `0x40`
  - `HeaderSize = 0x30 + 0x40 = 0x70`
- mip 9:
  - `0x24` bytes mip table
  - `0x0C` bytes pad
  - `0x20` bytes `eXt/GIDX`
  - total extra = `0x50`
  - `HeaderSize = 0x30 + 0x50 = 0x80`

Best current formula:

- if `mip_count == 1`:
  - `header_size = 0x50`
- if `mip_count > 1`:
  - `header_size = 0x30 + align(mip_count * 4, 0x10) + 0x20`

## `eXt` and `GIDX`

The trailing 32 bytes of the single-mip header are:

- `65 58 74 00 00 00 00 20 00 00 00 10 00 00 00 00`
- `47 49 44 58 00 00 00 10 ?? ?? ?? ?? 00 00 00 00`

Best current read:

- `eXt\0`
  - size `0x20`
  - nested header size `0x10`
  - reserved `0`
- `GIDX`
  - size `0x10`
  - surface global index as big-endian `u32`
  - trailing reserved `0`

`Tools/Ulysses/Ulysses/Resources/NuTexture.cs` scans this area to recover the global index.

## Type 1 Pixel Offset

The most important rebuild rule from the full inline sample is:

- in a self-contained type 1 file, `PixelOffset` is relative to the start of the
  current surface header
- it points to the absolute location of that surface's pixel payload inside the
  complete file image

For a multi-surface file:

`pixel_offset(surface_n) = total_header_size - surface_start + sum(previous_pixel_sizes)`

Where:

- `total_header_size = file_header_size + sum(surface_header_size)`
- `surface_start` is the absolute file offset where that surface header begins

This exactly matches the local full sample `DPL_POSTPROCESS/0.nut`.

## Consequence For Single-surface Rebuilds

The new full `1.nut` samples change the earlier working assumption.

For the common single-surface single-mip files now visible locally:

- `HeaderSize = 0x50`
- `PixelOffset = 0x70`
- the `0.nut` header copy is byte-identical to the first `0x60` bytes of the full file
- the full file then inserts `0x20` zero bytes before pixel data
- pixel data starts at absolute file offset `0x80`

This pattern is widespread across local full `1.nut` samples, including:

- BC1 atlas-like files such as `DPL_2DIMAGE_AC_*`
- A8R8G8B8 files such as `DPL_2DIMAGE_EMBL_001`
- BC3 files such as `DPL_UI_COMMON` font atlases

Best current single-surface single-mip rebuild rule:

- preserve `PixelOffset = 0x70`
- preserve or synthesize the `0x20` zero gap after the `0x50` surface header

So the safest writer strategy is now:

1. prefer a real full `1.nut` template when available
2. preserve all bytes before the pixel payload
3. replace only the pixel payload

That is stricter and better supported than re-synthesizing the whole prefix from scratch.

## Current Writer Status

Local prototype writer:

- `Scripts/build_nut_from_png.py`
- `Scripts/build_nut_from_dds.py`

Current support:

- `build_nut_from_png.py`
  - version 2
  - single surface
  - single mip
  - PNG input
  - uncompressed `A8R8G8B8` output
  - uncompressed `A8` output
  - prefers full `1.nut` templates and otherwise synthesizes the observed `0x20` gap
- `build_nut_from_dds.py`
  - version 2
  - single surface
  - single mip
  - DDS input whose pixel payload is already in the final compressed form
  - strict template-driven payload replacement
  - especially useful for BC3 font atlases once the replacement image is compressed
    externally to DDS

Not supported yet:

- BC3 encoding from PNG
- multi-surface packing
- palette formats
- split/type 2/type 3 reconstruction

## Why This Still Helps Font Work

Even though font atlases use `BC3`, this work narrows the remaining gap a lot:

1. the container/header layout for the common full `1.nut` path is now pinned down much
   more reliably
2. we now have an exact template-driven route for replacing NUT payload bytes
3. the remaining missing piece for direct `PNG -> font NUT` is mainly BC3 encoding,
   not the surrounding NUT structure
