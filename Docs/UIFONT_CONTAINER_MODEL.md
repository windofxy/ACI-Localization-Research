# UIFONT Minimal Container Model

This document defines the current `v1` minimal reconstructable container model
for Ace Combat Infinity `.uifont` files.

Current exporter:

- [export_uifont_container_model.py](/e:/Games/Emulator/ACI-Reverse-Engineering/Ulysses/Ulysses.DPLUnpack/bin/Debug/net10.0/output/export_uifont_container_model.py:1)

Current writer:

- [build_uifont_from_container_model.py](/e:/Games/Emulator/ACI-Reverse-Engineering/Ulysses/Ulysses.DPLUnpack/bin/Debug/net10.0/output/build_uifont_from_container_model.py:1)

Block model dependency:

- [UIFONT_REBUILD_MODEL.md](/e:/Games/Emulator/ACI-Reverse-Engineering/Ulysses/Ulysses.DPLUnpack/bin/Debug/net10.0/output/UIFONT_REBUILD_MODEL.md:1)

Schema name:

- `aci_uifont_min_container_model_v1`

## Scope

This model is for rebuilding a full `.uifont` container from an ordered list of
minimal block models.

It still does not define:

- how to generate brand-new container signature bytes at `0x04..0x0E`
- package/archive reinsertion into the game
- full sibling atlas resource policy outside the `.uifont` byte container

## Proven Container Layout

Current local evidence supports:

- magic at `0x00..0x03` is `ACF\0`
- container values are big-endian
- block count is stored at `0x0F`
- offset table starts at `0x10`
- offset table entry size is 4 bytes
- first block offset is always `0x10 + block_count * 4`
- blocks are tightly packed with no observed padding between them

Important boundary:

- the `.uifont` byte container itself only stores block headers, page tables, and glyph records
- sibling atlas resources such as `1/0.uitx` and `1/1/<page>/{0,1}.nut` live beside the
  `.uifont` file in the resource tree, not inside the `.uifont` byte stream
- glyph record field `+0x00 .. +0x01` links the container-side glyph data to one of those
  sibling atlas pages

Observed first-block offsets:

- `1` block  -> `0x14`
- `2` blocks -> `0x18`
- `6` blocks -> `0x28`
- `10` blocks -> `0x38`

## Preserve As-Is

The current model preserves:

- raw container header bytes `0x04..0x0E`
- block order
- each block through its referenced block rebuild model

Why preserve `0x04..0x0E`:

- `0x0C..0x0E` is `01 01 01` in all current original samples
- `0x04..0x0B` varies between resource families, but repeats within the same
  family
- no safe derivation rule is proven yet

So the current writer treats `0x04..0x0E` as container-level preserved metadata.

## Recompute

These fields can now be recomputed:

- `block_count`
- container header size
- offset table
- container byte size
- each block's absolute `glyph_data_offset`

These related items are outside the byte-container model, but are now known to
participate in a practical rebuild:

- sibling `1/0.uitx`
- one or more atlas-page siblings under `1/1/<page>/`
- per-glyph atlas page index inside each glyph record

Current rebuild rules:

1. `block_count = len(blocks)`
2. `container_header_size = 0x10 + block_count * 4`
3. `offset[0] = container_header_size`
4. `offset[n+1] = offset[n] + block_size[n]`
5. `container_size = container_header_size + sum(block_size[n])`
6. each block is rebuilt using its block model at the recomputed absolute block
   offset

## Required Invariants

The current model assumes:

- block order stays intentional and preserved
- blocks remain tightly packed
- each block is rebuildable from `aci_uifont_min_block_model_v1`
- glyph-to-atlas-page linkage is handled by the block/glyph model rather than by any
  separate container-level texture table

If a future writer changes block order, it must rebuild:

- the offset table
- every embedded block's absolute `glyph_data_offset`

## Current Confidence

High confidence:

- block count at `0x0F`
- offset table at `0x10`
- first-block offset formula
- tight-pack container layout
- container rebuild by preserving `0x04..0x0E`

Medium confidence:

- `0x0C..0x0E = 01 01 01` is likely a format/version triplet, but that meaning
  is not yet proven

Low confidence:

- exact semantics of `0x04..0x0B`

High confidence outside the byte container:

- the sibling resource tree may contain more than one atlas page
- page selection is carried by glyph record `+0x00 .. +0x01`, not by the sibling `.uitx`

## Round-Trip Status

Two representative containers now rebuild to exact original bytes:

- `DATA00/DPL_UI_COMMON/0/0/0.uifont` (10 blocks)
- `DATA01/DPL_MICW24B_RES/12/0.uifont` (2 blocks, including a reference-only block)

Additional whole-set survey results:

- all sampled original containers matched the first-block offset formula
- all sampled original containers were tightly packed
- observed block-count histogram:
  - `1` block: 21 files
  - `2` blocks: 58 files
  - `6` blocks: 1 file
  - `10` blocks: 1 file

## Practical Implication

For existing `.uifont` files, the current evidence supports a practical rebuild
pipeline:

1. preserve container header bytes `0x04..0x0E`
2. preserve block order
3. rebuild each block from the minimal block model
4. recompute the offset table
5. write a new `.uifont` container

In the full font resource chain now used locally, that container rebuild then
fits into a sibling resource layout like:

- `0.uifont`
- `1/0.uitx`
- `1/1/0/0.nut`
- `1/1/0/1.nut`
- optionally additional atlas pages such as `1/1/1/0.nut`, `1/1/1/1.nut`, etc.

That means the remaining technical gap is no longer `.uifont` structure itself.
The next unknown is how to insert rebuilt `.uifont` files back into the game's
package/archive flow.
