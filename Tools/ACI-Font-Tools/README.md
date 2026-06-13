# ACI Font Tools

Small desktop utility for building font atlas PNGs and glyph metadata from
`TTF` / `OTF` fonts for Ace Combat Infinity font research.

Current stack:

- `freetype-py` for glyph rasterization and metrics
- `rpack` from `rectangle-packer` for rectangle packing
- `PyQt5` for the desktop GUI
- `Pillow` for atlas image creation

## Features

- Open a `TTF` or `OTF` font
- Enter a custom character set
- Generate a packed atlas PNG
- Export glyph metadata as JSON
- Preview the atlas in-app
- Inspect glyph metrics such as:
  - codepoint
  - atlas position
  - bitmap size
  - bearing
  - advance

## Project Layout

- `main.py`: application entry point
- `aci_font_tools/atlas_generator.py`: FreeType rasterization and atlas packing
- `aci_font_tools/gui.py`: PyQt5 GUI

## Run

Use the local virtual environment:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Dependencies

Installed into the local `.venv`:

- `freetype-py`
- `rectangle-packer`
- `PyQt5`
- `Pillow`
