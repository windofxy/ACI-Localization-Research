# UIFONT Sibling UITX Model

This document defines the current minimal rebuild model for the `.uitx` files
found directly under font resource directories.

Current exporter:

- [export_font_sibling_uitx_model.py](/E:/Games/Emulator/ACI-Reverse-Engineering/ACI-Localization-Research/Scripts/export_font_sibling_uitx_model.py:1)

Current writer:

- [build_font_sibling_uitx_from_model.py](/E:/Games/Emulator/ACI-Reverse-Engineering/ACI-Localization-Research/Scripts/build_font_sibling_uitx_from_model.py:1)

Schema name:

- `aci_font_sibling_uitx_model_v1`

## Scope

This model only covers the `.uitx` files that appear as the direct sibling
resource under font directories:

- `.../0.uifont`
- `.../1/0.uitx`
- `.../1/1/<page>/...`

It does not attempt to describe general-purpose `.uitx` files used by ordinary
UI images.

## Observed Relationship To UIFONT

For every sampled `.uifont` file in the current workspace:

- a sibling `.uitx` exists at `1/0.uitx`
- one or more child atlas resources exist below it at `1/1/<page>/`

That supports the practical interpretation:

- `.uifont` stores glyph layout and atlas coordinate data
- the sibling `.uitx` is the texture-side resource node for the atlas set
- the actual atlas pixels live in one or more child texture resources
- atlas page selection is not stored in `.uitx`; it is carried by each glyph record's
  `+0x00 .. +0x01` atlas page index in the sibling `.uifont`

Observed layouts now include both:

- single-page font resources such as:
  - `1/1/0/0.nut`
  - `1/1/0/1.nut`
- multi-page font resources such as:
  - `1/1/0/0.nut`
  - `1/1/0/1.nut`
  - `1/1/1/0.nut`
  - `1/1/1/1.nut`

## Proven Binary Layout

All sampled font-sibling `.uitx` files are byte-identical and exactly `0x14`
bytes long:

```text
55 49 54 58  00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 14
```

Interpreted as the known `UITXHeader` layout from the C# parser:

- magic = `UITX`
- `variable_count = 0`
- `variable_offset = 0`
- `texture_count = 0`
- `texture_offset = 0x14`

So this is a header-only `.uitx` with no variable-texture table and no
cropping/texture-entry table.

## Preserve As-Is

The current model preserves the entire raw file:

- `raw_hex`
- parsed header fields for readability and validation

Because all current samples are byte-identical, preserving the raw bytes is the
smallest safe rebuild rule.

## Recompute

Nothing is recomputed in `v1`.

The current writer simply rebuilds from the preserved raw bytes.

## Current Confidence

High confidence:

- font-sibling `.uitx` files are always `0x14` bytes in current samples
- they contain only a `UITXHeader`
- they are byte-identical across all sampled font resources

Medium confidence:

- `texture_offset = 0x14` is just the canonical end-of-header offset for an
  otherwise empty `.uitx`

Lower confidence:

- whether every possible font resource in the game uses this exact same empty
  sibling `.uitx`

## Practical Implication

For the font resource chain currently understood in this workspace:

1. rebuild `.uifont`
2. preserve or rebuild the sibling `1/0.uitx` as this fixed 20-byte header-only
   file
3. replace the child texture payload below `1/1/...` if atlas pixels change

That means the font-side `.uitx` is not a blocker for custom font repacking.
The meaningful remaining work is on the texture payload and outer package
reinsertion layers.

Current local evidence also supports a stronger negative conclusion:

- the sibling `.uitx` does not expand or change when atlas page count changes
- moving from one atlas page to multiple atlas pages is handled by the `1/1/<page>/`
  sibling resource tree plus glyph-record atlas page indices, not by adding tables to
  the font-side `.uitx`
