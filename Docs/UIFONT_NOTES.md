# UIFONT Notes

These notes are based on the local `ACF` / `.uifont` samples in this workspace.

## Verified Structure

- Container magic: `41 43 46 00` (`ACF\0`)
- Container numbers are big-endian.
- Text encoding used by the game is UTF-16BE.
- Bytes `0x04 .. 0x07` are constant `77 BF 87 3D` across all current local official samples checked so far.
- Byte `0x0D` matches the number of atlas/NUT page folders under `1/1/<page>/`.
  - Full-game scan result in the current workspace: `120 / 120` `.uifont` samples matched this rule.
  - Example:
    - `01 02 01 0B` in `0xdec73b58/0/0/0.uifont` means atlas page count `0x02`, block count `0x0B`.
- Bytes `0x0C` and `0x0E` are currently constant `0x01` across all `120 / 120` official local samples
  checked so far.
- `IdRegistry.Hash(...)` in Ulysses uses CRC-32/BZip2 over the UTF-8 resource name.
  - Verified examples:
    - `DPL_UI_COMMON -> 0xDEC73B58`
    - `DPL_SFX -> 0xE1A4891D`
    - `DPL_UI_COMMON_TEXT_US -> 0xAA54D953`
    - `DPL_UI_COMMON_TEXT_JP -> 0x0AC159B1`
- Byte `0x0F` changes with the number of font blocks and matches local samples:
  - `0x01` in single-block files
  - `0x02` in mission/resource text fonts
  - `0x0A` in `DATA00/DPL_UI_COMMON/0/0/0.uifont`
  - `0x0B` in `DATA94/DPL_UI_COMMON/0/0/0.uifont`
- Starting at `0x10`, the container stores one big-endian `u32` offset per block.
- For single-block files, the first block starts at `0x14`.
- For `N` blocks, the first block starts at `0x10 + N * 4`.

Current strongest read for the first `0x10` bytes is therefore:

- `0x00 .. 0x03`: magic `ACF\0`
- `0x04 .. 0x07`: unknown constant, currently always `77 BF 87 3D`
- `0x08 .. 0x0B`: unknown file-level field(s)
- `0x0C`: currently always `0x01` in checked official samples
- `0x0D`: atlas page count
- `0x0E`: currently always `0x01` in checked official samples
- `0x0F`: block count

Current strongest read for `0x08 .. 0x0B`:

- It does not behave like a block count, atlas count, file size, or simple per-file unique ID.
- In the current full-game scan, `120` official `.uifont` files collapse to only `12` unique values here.
- The same value can cover both a full shared font package and a small subset package:
  - `0x5F8E00D8` appears in:
    - `DPL_UI_COMMON` (`0xDEC73B58`), the 11-block shared UI font with 2 atlas pages
    - `DPL_SFX` (`0xE1A4891D`), a 7-block tiny subset with 1 atlas page
- The value also groups language-family text resources in a stable way:
  - `0x5F8E0144` appears in `DPL_UI_COMMON_TEXT_JP` and `DPL_UI_COMMON_TEXT_US`
  - `0x5F8E0145` appears in `DPL_UI_COMMON_TEXT`

So the best current hypothesis is:

- `0x08 .. 0x0B` is a file-level font-resource family / template / category ID.
- It appears to classify related UIFont packages, not describe the concrete glyph count or atlas layout
  of the current file.
- A fuller value-by-value matrix is in `Docs/uifont_header_08_0B_matrix.md`.

## Font Block Layout

At each block offset:

- `+0x00 .. +0x1F`: ASCII font name, null-padded to 0x20 bytes
- `+0x20 .. +0x27`: four `u16` values
  - These are layout metrics in 26.6 fixed-point (`value / 64`).
  - Strongest current reading is:
    - metric 0: font ascent above baseline
    - metric 1: font descent below baseline
    - metric 2: likely face-level nominal max character width / horizontal limit metric
    - metric 3: line height
  - In every local sample, `metric3 == metric0 + metric1`.
  - These values are face-global metrics, not recomputed from the embedded glyph subset.
    Evidence:
    - reference-only blocks still preserve them
    - narrow subset blocks such as `A_OTF_Shin_Go_Pr5_R20_radio` keep the same values as their full-font counterparts
  - Best current structural analogy: this 4-value group likely mirrors a subset of Windows/GDI
    `TEXTMETRIC`, especially:
    - ascent
    - descent
    - max character width
    - height
- `+0x28`: `u16` glyph count
- `+0x2A`: unknown `u16`
- `+0x2C`: unknown `u32`
- `+0x30`: glyph record offset
- `+0x34`: unknown `u32`
  - Strong support: this is the count of glyphs whose UTF-16BE codepoint has low byte `0x00`
  - These glyphs are stored outside the 255-entry low-byte bucket table
- `+0x38 .. +0x433`: page table

The page table is `255 * 4 = 0x3FC` bytes long, so the fixed block header size is:

- `0x38 + 0x3FC = 0x434`

## Glyph Records

When a block embeds glyphs:

- Glyph data starts at `block_offset + 0x434`
- The value at `+0x30` matches that location in the embedded samples
- Each glyph record is 24 bytes
- `glyph_count * 24` exactly matches the glyph data region size in the embedded samples
- The UTF-16BE codepoint is stored at glyph-record offset `+0x0E` as a big-endian `u16`

Examples:

- `DATA01/DPL_MICP00_RES/12/0.uifont`
  - block start: `0x14`
  - glyph data start: `0x448`
  - file size: `0x3280`
  - glyph region size: `0x2E38`
  - glyph count: `0x01ED`
  - `0x01ED * 24 = 0x2E38`

- `DATA01/DPL_MICW24B_RES/12/0.uifont`
  - block 0 start: `0x18`
  - glyph data start: `0x44C`
  - next block: `0x623C`
  - glyph region size: `0x5DF0`
  - glyph count: `0x03EA`
  - `0x03EA * 24 = 0x5DF0`

- `DATA00/DPL_UI_COMMON/0/0/0.uifont`
  - first block start: `0x38`
  - glyph data start: `0x46C`
  - next block: `0x319C`
  - glyph region size: `0x2D30`
  - glyph count: `0x01E2`
  - `0x01E2 * 24 = 0x2D30`

## Reference-Only Blocks

Some blocks appear to declare a fallback/shared font name without embedding glyphs.

Example:

- `DATA01/DPL_MICW24B_RES/12/0.uifont`
  - block 1 name: `Futura_MdCn_BT28`
  - block size is only the fixed header
  - page table is zeroed
  - no glyph data follows

This looks like a reference to a shared font rather than a self-contained bitmap font block.

## Page Table Meaning

The 255 page-table entries are not Unicode high-byte pages.

What matches local samples is:

- Entry `0` corresponds to low byte `0x01`
- Entry `1` corresponds to low byte `0x02`
- ...
- Entry `254` corresponds to low byte `0xFF`

Each entry is:

- `start`: first glyph index in that low-byte bucket
- `count`: number of glyphs in that bucket

Official ordering rule observed in the current workspace:

- Across the full local official scan, all checked embedded glyph blocks (`159 / 159`) are already
  sorted by:
  - `(codepoint & 0xFF)` ascending
  - then full UTF-16BE codepoint ascending within that low-byte bucket
- No checked official block required any other bucket-local ordering rule.

There is no table entry for low byte `0x00`.
Those glyphs are stored outside the 255-entry bucket table and explain why some blocks have:

- a non-zero first `start`
- `glyph_count` slightly larger than the number of bucket-covered glyphs

So the lookup flow is likely:

1. Read a UTF-16BE code unit
2. Use `codepoint & 0xFF` to choose the bucket
3. Scan the bucket's glyph slice
4. Compare the full codepoint stored at glyph-record `+0x0E`

Examples from local samples:

- In `Futura_MdCn_BT62`, the bucket for low byte `0x20` contains:
  - `U+0020`
  - `U+0420`
  - `U+2020`

- In `A_OTF_Shin_Go_Pr5_R20_radio`, the bucket for low byte `0x01` contains:
  - `U+3001`
  - `U+5A01`
  - several other `xx01` codepoints

- In `A_OTF_Shin_Go_Pr5_R20_radio`, the page-table-covered glyphs begin after several `xx00` codepoints:
  - `U+3000`
  - `U+4E00`
  - `U+6700`
  - `U+8A00`
  - `U+9000`

This explains why ASCII is not concentrated in a single bucket even though the text encoding is UTF-16BE.

## Partially Decoded Glyph Record Fields

The following fields are now confirmed or strongly supported:

- `+0x00 .. +0x01`: atlas page index as a big-endian `u16`
  - In single-atlas samples this is `0` for all glyphs.
  - In multi-atlas samples such as `DATA94/DPL_UI_COMMON/0/0/0.uifont`, glyphs use at least
    pages `0` and `1`, and the value selects which `1/1/<page>/1.nut` / atlas image contains
    the glyph bitmap.
  - `+0x02` / `+0x04` are page-local atlas coordinates, not global coordinates across all atlas pages.
- `+0x02`: atlas X
- `+0x04`: atlas Y
- `+0x06`: signed 26.6 horizontal offset / bearing
- `+0x08`: signed 26.6 vertical placement metric
  - Best current reading: glyph ascent above baseline
  - This explains descenders such as `g`, `p`, `Q`, `J`
  - It also explains `_`, where this field can go negative because the glyph sits fully below the baseline
- `+0x0A`: glyph advance width in 26.6 fixed-point
- `+0x0E`: UTF-16BE codepoint
- `+0x14` high byte: glyph class / category byte, not an atlas page index
  - This byte is stable per codepoint across all local samples checked so far.
  - Strong support: it is a glyph category code used by the layout/runtime rather than atlas placement data.
  - Current writer-side practical read, based on `DATA94/DPL_UI_COMMON/0/0/0.uifont` plus the
    local TSS hot-update subset samples under `E:\Games\Emulator\ACI\TSS\Unpack`:
    - `0x0D`: default CJK / kana body glyphs, including normal ideographs and most full-width letters
    - `0x0C`: generic Latin / non-CJK letters such as `U+03B2`
    - `0x05`: small kana / iteration / Japanese middle-dot family
      - verified examples: `U+30A9`, `U+30C3`, `U+30FB`
    - `0x06`: exclamation family
      - verified example: `U+FF01`
    - `0x08`: comma / colon family
      - verified example: `U+FF1A`
    - `0x09`: plus / currency / reverse-solidus style symbols
      - verified examples: `U+2116`, `U+FF0B`
    - `0x10`: hyphen-like separators
      - verified example: `U+2010`
    - `0x16`: general symbol / mark bucket
      - verified examples: `U+203B`, `U+2161`, `U+2500`, `U+25A0`, `U+25C6`, `U+25CB`
    - `0x17`: Unicode line separator
      - verified example: `U+2028`
  - Practical writer note:
    - A useful heuristic for full-width compatibility characters is to first normalize with
      `NFKC`, then reuse the normalized character's class when that normalized form is a single codepoint.
    - This is what lets newly added characters such as full-width punctuation inherit the same
      class bucket as their ASCII counterparts.

Best current read for the remaining bytes:

- `+0x0C`: ink bounding-box width
- `+0x0D`: ink bounding-box height
- `+0x10 .. +0x13`: zero in all local samples checked so far
- `+0x15 .. +0x17`: zero in all local samples checked so far

Current evidence for the reserved-byte ranges:

- In the official `DATA00/DPL_UI_COMMON/0/0/0.uifont` sample, all checked glyphs use:
  - `+0x10 .. +0x13 = 00 00 00 00`
  - `+0x15 .. +0x17 = 00 00 00`
- In the later official `DATA94/DPL_UI_COMMON/0/0/0.uifont` sample, this remains true even for
  glyphs that were newly added between `DATA00` and `DATA94`.
- In current local custom-build samples, synthetic glyphs such as `U+9ECE` were also written with
  all-zero values in these ranges.

Practical takeaway:

- Treat `+0x10 .. +0x13` and `+0x15 .. +0x17` as preserved reserved bytes.
- Current evidence supports writing zeros for newly synthesized glyphs because that matches all
  checked official and local samples so far.
- But current evidence does **not** prove that these bytes are semantically irrelevant, so a
  format-faithful writer should still preserve original values whenever a source glyph record
  already exists.

Important caveat for reverse-engineering and future repacking:

- Some glyph records are valid entries but have an empty ink bbox:
  - `+0x0C = 0`
  - `+0x0D = 0`
- This is not limited to whitespace or control characters.
- In the Latin/Cyrillic UI fonts, many such records are placeholder-style entries with a
  non-zero advance width but no bitmap ink.
- Examples include:
  - `U+0020`
  - `U+00A0`
  - `U+0009`
  - `U+000A`
  - several `U+0460`-range records in the local samples

So a writer should preserve these empty glyph records rather than dropping them.

Strong current read for common class/category byte values at `+0x14`:

- `0x0C`: Latin / Cyrillic letters and related alphabetic glyphs
- `0x0D`: CJK ideographs, kana, and full-width Japanese body text glyphs
- `0x0B`: digits
- `0x1D`: private-use icon glyphs (`U+E***`)
- `0x1C`: space (`U+0020`)
- `0x1A`: newline (`U+000A`)
- `0x02`: Japanese punctuation such as `U+3001` / `U+3002`
- `0x00` / `0x01`: paired opening / closing brackets and similar punctuation

Several smaller category codes also appear for punctuation families such as:

- quotes
- commas / periods / colons / semicolons
- hyphen / dash variants
- slash
- currency / math / unit symbols

The exact engine behavior attached to each category code is still open, but the byte is now
best treated as semantic metadata that must be preserved during repacking.

Current extraction takeaway from local samples:

- For ASCII letters and digits, `+0x0D` is a very strong height field.
- In `Futura_MdCn_BT62`, `Futura_MdCn_BT28`, `Futura_MdCn_BT26`, `Futura_MdCn_BT20`,
  `A_OTF_Shin_Go_Pr5_R20`, and `A_OTF_Shin_Go_Pr5_R16`, it matches the visible ink
  height for all tested ASCII alphanumerics.
- In the HUD fonts it is still usually right, but can overshoot by 1 pixel on a few
  glyphs such as `J`, `M`, `R`, and `k`.
- `+0x0C` often matches the visible ink width, but it is not universal.
  It under-reports glyphs with horizontal overshoot / serif caps such as the large
  `Futura_MdCn_BT62` `I`, where the visible bitmap is 14 px wide but `+0x0C` is `6`.

Strict extraction rule used locally for repack-oriented work:

1. Export a `cell` crop with:
   `x = atlas_x`, `y = atlas_y`, `width = +0x0A`, `height = +0x08`
2. Export an `ink` crop with:
   `x = atlas_x`, `y = atlas_y`, `width = +0x0C`, `height = +0x0D`
3. Do not trim transparent borders.
4. Do not expand the crop with fallback logic.

This keeps the output tied directly to explicit `.uifont` fields while separating:

- a larger placement / cell-style rectangle
- a tighter ink / body-style rectangle

This is now better understood semantically as:

- `+0x06`: left side bearing
- `+0x0A`: advance width
- `+0x0C`: ink width
- `+0x08`: ascent above baseline
- `+0x0D`: ink height

So the current `cell` export is not just a bitmap width/height pair:

- width from `+0x0A` is closer to logical horizontal advance
- height from `+0x08` is closer to ascent above the baseline

That distinction matters for future repacking work, because a faithful writer will likely
need both placement metrics and bitmap bbox metrics rather than a single crop rectangle.

The `I` glyph in `Futura_MdCn_BT62` is a good example of why this separation matters:

- `+0x0A = 14` includes side spacing and reaches into the neighboring atlas content
- `+0x0C = 6` is much closer to the central stroke width
- `offset_x = 4` is best treated as placement / bearing data, not as an atlas crop shift

Atlas crops using these fields match the expected glyphs for:

- `U+0041`
- `U+3001`
- `U+5A01`
- `U+0020`

## Known Font Names Seen Locally

- `Futura_MdCn_BT62`
- `Futura_MdCn_BT28`
- `Futura_MdCn_BT26`
- `Futura_MdCn_BT20`
- `A_OTF_Shin_Go_Pr5_R20`
- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- `HUD_12`
- `HUD_14`
- `HUD_18`

## Runtime Constraint Hypothesis

Current local rebuild evidence points to at least one important runtime-side limit that is
not exposed as a simple field-size limit in the `.uifont` file format itself.

### `A_OTF_Shin_Go_Pr5_R16 / R20 / R20_radio` shared glyph budget

Across the current local experiments:

- official `DATA94/DPL_UI_COMMON/0/0/0.uifont` has:
  - `A_OTF_Shin_Go_Pr5_R20 = 3462`
  - `A_OTF_Shin_Go_Pr5_R16 = 1647`
  - `A_OTF_Shin_Go_Pr5_R20_radio = 50`
  - family total = `5159` (`0x1427`)
- local testing indicates:
  - family total `5160` (`0x1428`) still loads
  - family total `5161+` causes the game to fail to enter
- additional local evidence now strongly reinforces that this limit is family-local:
  - when the same custom charset was redistributed so that many glyphs were no longer stored under
    `A_OTF_Shin_Go_*` and instead the output used `HUD_12`, the game could enter normally again
  - sample:
    - `Tools/ACI-Font-Tools/output/SourceHanSansSC-Medium-A_OTF-HUD-1536x1536/0.uifont`
  - that sample has:
    - `A_OTF_Shin_Go_Pr5_R20 = 291`
    - `A_OTF_Shin_Go_Pr5_R16 = 1647`
    - `A_OTF_Shin_Go_Pr5_R20_radio = 50`
    - family total = `1988`
    - `HUD_12 = 1324`
  - by contrast, the failing sample:
    - `Tools/ACI-Font-Tools/output/SourceHanSansSC-Medium-CharsetPart-Add-2048x2048/0.uifont`
    - keeps the same three-block family at:
      - `3463 + 1649 + 50 = 5162`
    - and fails to enter the game

Current strongest implication from the local sample set:

- the failure condition does not track whole-file glyph total
- it tracks the subtotal of the shared `A_OTF_Shin_Go_Pr5_R16 / R20 / R20_radio` family much more closely
- moving glyph pressure out of that family can restore bootability even when the `.uifont` still contains
  thousands of glyphs overall

Local official-sample ceiling observed so far:

- in the current FullGame + TSS hot-update scan available in this workspace, no official checked sample
  exceeds the `DATA94` `A_OTF_Shin_Go` family subtotal of `5159`

Best current read:

- the game appears to enforce a runtime family-level glyph capacity for the shared
  `A_OTF_Shin_Go_Pr5_R16 / R20 / R20_radio` group
- the current practical limit is therefore best modeled as:
  - maximum safe total glyphs across those three blocks = `5160` (`0x1428`)

Why this currently looks runtime-side rather than format-side:

- each block's `glyph_count` is only a `u16`, so the file format itself allows much larger values
- the whole-file glyph total is also not the limiter
  - for example, official `DATA00` has a larger total glyph count than official `DATA94`
  - but the observed failure boundary still tracks the `A_OTF_Shin_Go` family subtotal instead
- local custom builds already show that a single block such as `A_OTF_Shin_Go_Pr5_R16`
  can exceed its official `DATA94` count without immediately proving a block-local file-format cap

Practical takeaway for rebuilding today:

- treat `A_OTF_Shin_Go_Pr5_R16 + A_OTF_Shin_Go_Pr5_R20 + A_OTF_Shin_Go_Pr5_R20_radio`
  as sharing one combined glyph budget
- adding glyphs to one of these blocks should currently be assumed to require deleting the same
  number from the same family unless future runtime reverse-engineering finds a way to raise the cap

## Open Questions

- The exact formula behind metric 2 at block offset `+0x24`
  - It is very likely the font's face-level max character width, similar to `TEXTMETRIC.tmMaxCharWidth`
  - But it is not yet reduced to a precise reconstruction rule from glyph records alone
- The exact engine behavior attached to each glyph class byte at `+0x14`
- Whether the game ever uses non-zero values in glyph bytes `+0x10 .. +0x13` or `+0x15 .. +0x17`
- The exact writer-side rules needed to rebuild page tables and block metrics safely

## Useful Command

Run the parser on a sample:

```bash
python parse_uifont.py DATA01/DPL_MICW24B_RES/12/0.uifont
```
