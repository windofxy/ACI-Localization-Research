from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import freetype
from PIL import Image

from .dds_tools import build_game_dds_bytes
from .nut_tools import build_nut_pair_from_dds_bytes
from .packing import pack_rectangles


ProgressCallback = Callable[[int, int, str], None]


@dataclass
class GlyphBitmap:
    char: str
    codepoint: int
    width: int
    height: int
    bearing_x: int
    bearing_y: int
    advance_x: float
    bitmap_rows: list[bytes]


@dataclass
class PackedGlyph:
    char: str
    codepoint: int
    atlas_x: int
    atlas_y: int
    width: int
    height: int
    bearing_x: int
    bearing_y: int
    advance_x: float


@dataclass
class AtlasResult:
    font_path: str
    pixel_size: int
    atlas_width: int
    atlas_height: int
    used_width: int
    used_height: int
    ascent: float
    descent: float
    line_height: float
    padding: int
    glyphs: list[PackedGlyph]
    atlas_image: Image.Image

    def to_metadata(self) -> dict[str, Any]:
        return {
            "font_path": self.font_path,
            "pixel_size": self.pixel_size,
            "atlas_width": self.atlas_width,
            "atlas_height": self.atlas_height,
            "used_width": self.used_width,
            "used_height": self.used_height,
            "ascent": self.ascent,
            "descent": self.descent,
            "line_height": self.line_height,
            "padding": self.padding,
            "glyph_count": len(self.glyphs),
            "glyphs": [asdict(glyph) for glyph in self.glyphs],
        }


def normalize_charset(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for char in text:
        if char in seen:
            continue
        seen.add(char)
        ordered.append(char)
    return ordered


def build_ascii_charset() -> str:
    return "".join(chr(codepoint) for codepoint in range(32, 127))


def _decode_bitmap_rows(bitmap: freetype.Bitmap) -> list[bytes]:
    width = bitmap.width
    rows = bitmap.rows
    pitch = bitmap.pitch
    buffer = bytes(bitmap.buffer)

    if width == 0 or rows == 0:
        return []

    abs_pitch = abs(pitch)
    row_data: list[bytes] = []

    for row_index in range(rows):
        start = row_index * abs_pitch
        row = buffer[start : start + width]
        row_data.append(row)

    if pitch < 0:
        row_data.reverse()

    return row_data


def _report_progress(progress_callback: ProgressCallback | None, current: int, total: int, message: str) -> None:
    if progress_callback is not None:
        progress_callback(current, total, message)


def rasterize_glyphs(
    font_path: str | Path,
    charset: str,
    pixel_size: int,
    progress_callback: ProgressCallback | None = None,
    progress_offset: int = 0,
    progress_total: int = 0,
) -> tuple[freetype.Face, list[GlyphBitmap]]:
    face = freetype.Face(str(font_path))
    face.set_pixel_sizes(0, pixel_size)

    glyphs: list[GlyphBitmap] = []
    chars = normalize_charset(charset)
    for index, char in enumerate(chars, start=1):
        face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        slot = face.glyph
        bitmap = slot.bitmap

        glyphs.append(
            GlyphBitmap(
                char=char,
                codepoint=ord(char),
                width=bitmap.width,
                height=bitmap.rows,
                bearing_x=slot.bitmap_left,
                bearing_y=slot.bitmap_top,
                advance_x=slot.advance.x / 64.0,
                bitmap_rows=_decode_bitmap_rows(bitmap),
            )
        )
        _report_progress(
            progress_callback,
            progress_offset + index,
            progress_total,
            f"Rasterizing glyphs: {index}/{len(chars)}",
        )

    return face, glyphs


def _build_rgba_glyph_image(glyph: GlyphBitmap) -> Image.Image:
    if glyph.width <= 0 or glyph.height <= 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    alpha = Image.new("L", (glyph.width, glyph.height), 0)
    if glyph.bitmap_rows:
        alpha = Image.frombytes(
            "L",
            (glyph.width, glyph.height),
            b"".join(glyph.bitmap_rows),
        )

    rgba = Image.new("RGBA", (glyph.width, glyph.height), (255, 255, 255, 0))
    rgba.putalpha(alpha)
    return rgba


def _pack_glyphs(
    glyphs: list[GlyphBitmap],
    padding: int,
    max_width: int,
    max_height: int,
) -> tuple[list[tuple[int, int]], int, int, str]:
    sizes = []
    for glyph in glyphs:
        pack_width = max(1, glyph.width) + padding * 2
        pack_height = max(1, glyph.height) + padding * 2
        sizes.append((pack_width, pack_height))

    layout = pack_rectangles(
        sizes,
        max_width=max_width,
        max_height=max_height,
        context="Atlas packing",
    )
    return layout.positions, layout.used_width, layout.used_height, layout.mode


def generate_atlas(
    font_path: str | Path,
    charset: str,
    pixel_size: int,
    max_width: int,
    max_height: int,
    padding: int,
    progress_callback: ProgressCallback | None = None,
) -> AtlasResult:
    if not charset:
        raise ValueError("Character set is empty.")
    if pixel_size <= 0:
        raise ValueError("Pixel size must be greater than zero.")
    if max_width <= 0 or max_height <= 0:
        raise ValueError("Atlas size must be greater than zero.")
    if padding < 0:
        raise ValueError("Padding cannot be negative.")

    glyph_count = len(normalize_charset(charset))
    total_steps = glyph_count * 2 + 2
    _report_progress(progress_callback, 0, total_steps, "Preparing atlas generation...")
    face, glyph_bitmaps = rasterize_glyphs(
        font_path,
        charset,
        pixel_size,
        progress_callback=progress_callback,
        progress_offset=0,
        progress_total=total_steps,
    )
    _report_progress(progress_callback, glyph_count + 1, total_steps, "Packing glyphs...")
    positions, atlas_width, atlas_height, packing_mode = _pack_glyphs(
        glyph_bitmaps, padding=padding, max_width=max_width, max_height=max_height
    )

    atlas = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
    packed_glyphs: list[PackedGlyph] = []

    for index, (glyph, (pack_x, pack_y)) in enumerate(zip(glyph_bitmaps, positions), start=1):
        atlas_x = pack_x + padding
        atlas_y = pack_y + padding

        if glyph.width > 0 and glyph.height > 0:
            glyph_image = _build_rgba_glyph_image(glyph)
            atlas.alpha_composite(glyph_image, (atlas_x, atlas_y))

        packed_glyphs.append(
            PackedGlyph(
                char=glyph.char,
                codepoint=glyph.codepoint,
                atlas_x=atlas_x,
                atlas_y=atlas_y,
                width=glyph.width,
                height=glyph.height,
                bearing_x=glyph.bearing_x,
                bearing_y=glyph.bearing_y,
                advance_x=glyph.advance_x,
            )
        )
        _report_progress(
            progress_callback,
            glyph_count + 1 + index,
            total_steps,
            f"Compositing atlas: {index}/{glyph_count} ({packing_mode})",
        )

    _report_progress(progress_callback, total_steps, total_steps, "Atlas preview ready.")

    return AtlasResult(
        font_path=str(font_path),
        pixel_size=pixel_size,
        atlas_width=max_width,
        atlas_height=max_height,
        used_width=atlas_width,
        used_height=atlas_height,
        ascent=face.size.ascender / 64.0,
        descent=abs(face.size.descender / 64.0),
        line_height=face.size.height / 64.0,
        padding=padding,
        glyphs=packed_glyphs,
        atlas_image=atlas,
    )


def save_result(result: AtlasResult, output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    nut0_path = output_path / "0.nut"
    nut1_path = output_path / "1.nut"

    dds_bytes = build_game_dds_bytes(result.atlas_image)
    nut0_bytes, nut1_bytes = build_nut_pair_from_dds_bytes(dds_bytes)
    nut0_path.write_bytes(nut0_bytes)
    nut1_path.write_bytes(nut1_bytes)
    return {
        "nut0": nut0_path,
        "nut1": nut1_path,
    }
