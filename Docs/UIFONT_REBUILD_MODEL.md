# UIFONT Minimal Rebuild Model

This document defines the current `v1` minimal reconstructable block model for Ace Combat
Infinity `.uifont` font blocks.

Current exporter:

- [export_uifont_rebuild_model.py](/e:/Games/Emulator/ACI-Reverse-Engineering/Ulysses/Ulysses.DPLUnpack/bin/Debug/net10.0/output/export_uifont_rebuild_model.py:1)

Current single-block writer prototype:

- [build_uifont_from_rebuild_model.py](/e:/Games/Emulator/ACI-Reverse-Engineering/Ulysses/Ulysses.DPLUnpack/bin/Debug/net10.0/output/build_uifont_from_rebuild_model.py:1)

Schema name:

- `aci_uifont_min_block_model_v1`

## Scope

This model is for rebuilding a single font block.

It does not yet define:

- full container rebuild ordering
- package reinsertion into the game archive format

Current local tooling now does more than the original single-block prototype:

- rebuilds full multi-block `.uifont` containers from a template
- repacks atlas content into one or more atlas pages
- rewrites glyph-record atlas page indices when repacking changes page placement
- rebuilds sibling `.uitx`, `0.nut`, and `1.nut` outputs for each atlas page

## Rebuild Goal

The model is designed so a future writer can rebuild a block header and glyph section without
having to preserve the original page table, original block offsets, or original atlas-page
assignment.

## Preserve As-Is

These fields should currently be preserved from the source block rather than recomputed:

- block name at `+0x00 .. +0x1F`
- the four block metrics at `+0x20 .. +0x27`
- `unk_2a` at `+0x2A`
- `unk_2c` at `+0x2C`
- every preserved per-glyph field inside the 24-byte record

Preserve here means:

- keep the source value when the writer is doing a format-faithful rebuild
- or choose a deliberate replacement rule when atlas repacking or new-codepoint insertion
  requires recomputation

For each glyph record, the current model preserves:

- `atlas_page_index_u16_be`
- `atlas_x_u16_be`
- `atlas_y_u16_be`
- `offset_x_s16_be_26_6`
- `ascent_s16_be_26_6`
- `advance_x_u16_be_26_6`
- `ink_width_u8`
- `ink_height_u8`
- `codepoint_u16_be`
- `reserved_10_13_hex`
- `class_u8`
- `reserved_15_17_hex`

Reason:

- some glyphs have empty ink bbox but still carry meaningful advance / category data
- some currently-unknown bytes are zero in local samples, but should still be preserved until
  wider samples prove they are always derivable
- atlas repacking can move glyphs between pages and coordinates, but does not by itself justify
  inventing new values for the still-unknown reserved bytes

Current evidence for the reserved glyph-byte ranges:

- Official `DATA00` and `DATA94` UI font samples use:
  - `reserved_10_13_hex = 00000000`
  - `reserved_15_17_hex = 000000`
- This remains true for official glyphs newly added in `DATA94` relative to `DATA00`.
- Current local synthetic-glyph samples also write these fields as zero, including custom
  `U+9ECE` insertion tests.

So the current writer rule is:

- preserve these bytes exactly when rebuilding an existing glyph record
- when synthesizing a brand-new glyph record with no template source record, initialize them to
  zero unless wider sample evidence later proves a better rule

## Recompute

These fields can now be recomputed from the preserved glyph list and block kind:

- `glyph_count`
- `glyph_data_offset`
- `unk34`
- page table
- block byte size
- atlas page assignment
- atlas-local `x/y` placement

Current rebuild rules:

1. `glyph_count = len(glyph_records)`
2. `glyph_data_offset = block_offset + 0x434` for embedded blocks
3. `glyph_data_offset = 0` for reference-only blocks
4. `unk34 = count(codepoint where (codepoint & 0xFF) == 0)`
5. page table has 255 entries for low bytes `0x01 .. 0xFF`
6. each page entry stores:
   - `start = first glyph index in that low-byte bucket`
   - `count = number of glyphs in that low-byte bucket`
7. glyph record `+0x00 .. +0x01` is the atlas page index and must be preserved or
   deliberately reassigned if atlas repacking changes page placement
8. if atlas repacking changes glyph order, rebuild the page table from the new order and keep
   each low-byte bucket contiguous
9. current local font-builder behavior uses shelf packing only
10. if a page fills, open a new atlas page and continue packing remaining glyphs there
11. glyphs inserted for codepoints not present in the template may synthesize their preserved
    per-glyph metadata from a block-local prototype glyph when no original record exists
12. fallback glyph reuse is only valid when the template already has that codepoint
13. if a codepoint exists in neither the source font nor the template glyph list, the writer
    must fail rather than inventing bitmap data
14. reference-only blocks rebuild with:
   - `glyph_count = 0`
   - `glyph_data_offset = 0`
   - `unk34 = 0`
   - zeroed page table
15. `block_size = 0x434 + glyph_count * 24` for embedded blocks
16. `block_size = 0x434` for reference-only blocks

## Required Invariants

The current model assumes:

- each non-zero low-byte bucket occupies a contiguous slice of the glyph list
- every glyph's `atlas_x` / `atlas_y` is relative to its own `atlas_page_index`

Local samples satisfy this.

If a future custom writer changes glyph ordering, it must rebuild the page table from the new
order and keep each bucket contiguous. This is now relevant to atlas-repacking workflows that
may reorder glyphs while also reassigning atlas page indices.

## Current Confidence

High confidence:

- block fixed header size is `0x434`
- glyph record size is `24`
- `glyph_count`
- `glyph_data_offset`
- `unk34`
- page table low-byte meaning
- atlas page index at glyph `+0x00 .. +0x01`
- codepoint field at glyph `+0x0E`
- class byte stability per codepoint

Medium confidence:

- block metrics correspond to face-level font metrics
- metric 2 behaves like a `tmMaxCharWidth`-style value

Lower confidence:

- exact semantics of `unk_2a`
- exact semantics of `unk_2c`
- exact runtime meaning of each class byte value

## Writer Implication

A future writer can probably succeed if it:

- preserves the face-level metrics block
- preserves glyph order unless deliberately rebuilding bucket layout
- preserves every glyph record field not yet proven derivable
- recomputes `glyph_count`, `glyph_data_offset`, `unk34`, and the page table
- preserves or deliberately reassigns `atlas_page_index_u16_be` to match the rebuilt atlas pages
- keeps atlas coordinates page-local after atlas repacking
- opens additional atlas pages instead of forcing a single oversubscribed page
- synthesizes new glyph records carefully when a codepoint is new to the template but present
  in the source font

This is the smallest practical model currently supported by local evidence.

## Current Writer Scope

The current writer prototype can rebuild a **single block** from
`aci_uifont_min_block_model_v1` into a synthetic one-block `.uifont` container.

Current behavior:

- writes a synthetic container header with one block
- writes the block at offset `0x14`
- recomputes the block's absolute `glyph_data_offset` from that new block offset
- rebuilds the page table from glyph order
- rebuilds glyph records strictly from preserved JSON fields

Current local GUI builder behavior goes further than that prototype:

- starts from a multi-block template `.uifont`
- rasterizes glyphs from selected source fonts
- allows codepoints not present in the template, as long as the source font contains them
- falls back to template atlas slices only for codepoints that already exist in the template
- repacks glyphs with shelf layout only
- opens additional atlas pages when one page fills
- rewrites glyph-record atlas page indices and atlas-local coordinates to match the rebuilt atlas set

It does **not** yet define:

- preservation or recomputation of container-level unknown bytes at `0x04..0x0E`
- reinsertion into the game's archive/package format

So the remaining gap is no longer block rebuild itself, but packaging / archive reinsertion and
full formalization of all container-level unknowns.

## Round-Trip Status

Local round-trip validation is now strong enough to say the block model is
structurally reconstructable.

Validated sample models:

- `DATA00/DPL_UI_COMMON/0/0/0.uifont` block 0 `Futura_MdCn_BT62`
- `DATA00/DPL_UI_COMMON/0/0/0.uifont` block 4 `A_OTF_Shin_Go_Pr5_R20`
- `DATA00/DPL_UI_COMMON/0/0/0.uifont` block 9 `A_OTF_Shin_Go_Pr5_R20_radio`
- `DATA01/DPL_MICW24B_RES/12/0.uifont` block 0 `A_OTF_Shin_Go_Pr5_R20_radio`
- `DATA01/DPL_MICW24B_RES/12/0.uifont` block 1 `Futura_MdCn_BT28`

Observed result:

- every rebuilt sample parses correctly as a one-block `.uifont`
- `glyph_count`, `glyph_data_offset`, `unk34`, and page table all match recomputed expectations
- reference-only blocks can byte-match the original block directly
- embedded blocks byte-match the original block **after normalizing** header field `+0x30`
  (`glyph_data_offset`)

Why normalization is needed:

- `+0x30` stores an **absolute container offset**, not a block-relative offset
- the original source blocks lived at larger offsets inside multi-block containers
- the synthetic writer places the rebuilt block at `0x14`, so the absolute glyph-data
  pointer changes even when the block-internal structure is otherwise identical

Practical consequence:

- the current `v1` block model is sufficient to reconstruct original block content
  modulo container rebasing
- the next missing piece is a container-level model/writer for package reinsertion, not more
  basic block-level glyph fields
