# ACI-Localization-Research

Research workspace for *Ace Combat Infinity* localization and font format reverse engineering.

This repository currently focuses on the game's `UIFONT` pipeline, related atlas containers, and tooling for rebuilding font assets from desktop fonts.

## Repository Layout

- [Docs](Docs): reverse-engineering notes, format models, and comparison tables.
- [Tools/ACI-Font-Tools](Tools/ACI-Font-Tools): desktop tool for inspecting template UIFONT assets and building replacement font packages.
- `Scripts`: helper scripts used during research.

## Docs

The [Docs](Docs) folder contains the working notes for the current reverse-engineering progress:

- [UIFONT_NOTES.md](Docs/UIFONT_NOTES.md): field notes for `.uifont` parsing, glyph records, buckets, and block structure.
- [UIFONT_CONTAINER_MODEL.md](Docs/UIFONT_CONTAINER_MODEL.md): high-level container model for how `.uifont` assets are organized.
- [UIFONT_REBUILD_MODEL.md](Docs/UIFONT_REBUILD_MODEL.md): current understanding of the minimum data needed to rebuild a valid `.uifont`.
- [UIFONT_SIBLING_UITX_MODEL.md](Docs/UIFONT_SIBLING_UITX_MODEL.md): notes on the relationship between `.uifont` and nearby `.uitx` files.
- [NUT_NOTES.md](Docs/NUT_NOTES.md): notes about atlas texture packaging in `.nut`.
- [uifont_header_08_0B_matrix.md](Docs/uifont_header_08_0B_matrix.md): comparison matrix for the `0x08-0x0B` UIFONT header field.
- [uifont_header_08_0B_fullgame.tsv](Docs/uifont_header_08_0B_fullgame.tsv): raw extracted table used for broader header comparison.

## ACI-Font-Tools

[ACI-Font-Tools](Tools/ACI-Font-Tools) is the main practical tool in this workspace. It is a PyQt5 desktop application used to:

- inspect `.uifont` templates and their glyph records
- load atlas images from `.nut`
- import charset files in `UTF-16BE`
- rasterize replacement glyphs from `TTF` / `OTF`
- merge glyphs into atlas pages
- export rebuilt `.uifont`, `.uitx`, and `.nut` outputs for in-game testing

Tool-specific setup and usage notes are documented in [Tools/ACI-Font-Tools/README.md](Tools/ACI-Font-Tools/README.md).
