from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable
import unicodedata

import freetype
from PIL import Image

from .dds_tools import build_game_dds_bytes
from .nut_tools import build_nut_pair_from_dds_bytes, load_nut_image
from .uifont_parser import (
    BLOCK_HEADER_SIZE,
    BLOCK_NAME_SIZE,
    GLYPH_RECORD_SIZE,
    UIFontBlock,
    UIFontContainer,
    UIFontGlyph,
    int_to_codepoint_bytes,
)


ProgressCallback = Callable[[int, int, str], None]


CLASS_05_CODEPOINTS = frozenset({
    0x3005,
    0x3041, 0x3043, 0x3045, 0x3047, 0x3049,
    0x3063, 0x3083, 0x3085, 0x3087, 0x308E,
    0x3099, 0x309A,
    0x30A1, 0x30A3, 0x30A5, 0x30A7, 0x30A9,
    0x30C3, 0x30E3, 0x30E5, 0x30E7, 0x30EE,
    0x30F5, 0x30F6,
    0x30FB, 0x30FC,
    0xFF6D, 0xFF70, 0xFF9E, 0xFF9F,
})

CLASS_09_CODEPOINTS = frozenset({
    0x0024, 0x002B, 0x005C,
    0x00A3, 0x00A4, 0x00A5, 0x00B1,
    0x20A3, 0x2116, 0x2212, 0xFF0B,
})

CLASS_0A_CODEPOINTS = frozenset({
    0x0025,
    0x00A2, 0x00B0,
    0x2030,
})

CLASS_0C_CODEPOINTS = frozenset({
    0x0023, 0x0026, 0x002A,
    0x003C, 0x003D, 0x003E,
    0x0040,
    0x005E, 0x005F, 0x0060,
    0x007E,
    0x00A6, 0x00A9, 0x00AC, 0x00AE, 0x00AF,
    0x02DC,
    0x0482,
    0x2022,
    0x2206, 0x2219,
    0x25CA,
})

CLASS_16_CODEPOINTS = frozenset({
    0x00A7, 0x00A8, 0x00AA,
    0x00B2, 0x00B3, 0x00B6, 0x00B7, 0x00B8, 0x00B9, 0x00BA,
    0x00BC, 0x00BD, 0x00BE,
    0x00D7, 0x00F7,
    0x02C7, 0x02D8, 0x02D9, 0x02DA, 0x02DB, 0x02DD,
    0x2015, 0x2020, 0x2021, 0x203B,
    0x2122, 0x2161, 0x2163, 0x2192, 0x21D2,
    0x2202, 0x220F, 0x2211, 0x2215, 0x221A, 0x221E, 0x222B,
    0x2248, 0x2260, 0x2264, 0x2265,
    0x2464, 0x2500,
    0x25A0, 0x25A1, 0x25BC, 0x25C6, 0x25CB, 0x25CF,
    0x2605,
})

CLASS_00_CODEPOINTS = frozenset({
    0x00A1, 0x00BF,
    0xE215, 0xE217, 0xE219, 0xE221,
})

CLASS_01_CODEPOINTS = frozenset({
    0xE216, 0xE218, 0xE220, 0xE222,
})

CLASS_04_CODEPOINTS = frozenset({
    0x00A0,
})

CLASS_10_CODEPOINTS = frozenset({
    0x007C,
    0x00AD,
})

CLASS_11_CODEPOINTS = frozenset({
    0x00B4,
})

CLASS_14_CODEPOINTS = frozenset({
    0x0090,
    0x0483, 0x0484, 0x0485, 0x0486,
})

CLASS_15_CODEPOINTS = frozenset({
    0xFEFF,
})

CLASS_1D_EXCEPTIONS = frozenset({
    0xE215, 0xE216, 0xE217, 0xE218,
    0xE219, 0xE220, 0xE221, 0xE222,
})


def _be16(value: int) -> bytes:
    return int(value).to_bytes(2, "big", signed=False)


def _be16s(value: int) -> bytes:
    return int(value).to_bytes(2, "big", signed=True)


def _be32(value: int) -> bytes:
    return int(value).to_bytes(4, "big", signed=False)


def _round_26_6(value: float) -> int:
    return int(round(value * 64.0))


def _align_up(value: int, alignment: int) -> int:
    if alignment <= 0:
        raise ValueError("Alignment must be greater than zero.")
    if value <= 0:
        return alignment
    return ((value + alignment - 1) // alignment) * alignment


def _dedupe_chars(text: str) -> list[str]:
    seen: set[str] = set()
    chars: list[str] = []
    for char in text:
        if char in seen:
            continue
        seen.add(char)
        chars.append(char)
    return chars


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
        row_data.append(buffer[start : start + width])

    if pitch < 0:
        row_data.reverse()
    return row_data


def _build_rgba_glyph_image(width: int, height: int, bitmap_rows: list[bytes]) -> Image.Image:
    if width <= 0 or height <= 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    alpha = Image.new("L", (width, height), 0)
    if bitmap_rows:
        alpha = Image.frombytes("L", (width, height), b"".join(bitmap_rows))

    rgba = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    rgba.putalpha(alpha)
    return rgba


@dataclass
class UIFontBuildConfig:
    block_index: int
    font_name: str
    font_path: str
    pixel_size: int
    charset_codepoints: list[int]

    @property
    def charset_text(self) -> str:
        return "".join(chr(codepoint) for codepoint in self.charset_codepoints)


@dataclass
class RasterizedTemplateGlyph:
    block_index: int
    glyph_index: int
    template_glyph: UIFontGlyph
    class_byte: int
    codepoint: int
    codepoint_bytes: bytes
    atlas_page_index: int
    width: int
    height: int
    bearing_x: float
    bearing_y: float
    advance_x: float
    bitmap_rows: list[bytes]
    image: Image.Image | None = None
    reused_template: bool = False
    atlas_x: int = 0
    atlas_y: int = 0


@dataclass
class BuiltAtlasPage:
    page_index: int
    width: int
    height: int
    used_width: int
    used_height: int
    image: Image.Image
    atlas_relative_path: str
    nut0_relative_path: str
    nut1_relative_path: str
    nut1_template_path: str
    packing_mode: str
    glyph_count: int


@dataclass
class UIFontBuildResult:
    template_path: str
    output_root: str
    atlas_width: int
    atlas_height: int
    used_width: int
    used_height: int
    atlas_image: Image.Image
    atlas_pages: list[BuiltAtlasPage]
    uifont_bytes: bytes
    uitx_bytes: bytes
    uifont_relative_path: str
    uitx_relative_path: str
    atlas_relative_path: str
    nut0_relative_path: str
    nut1_relative_path: str
    debug_metadata: dict[str, Any]


def build_uifont_package(
    template: UIFontContainer,
    font_configs: dict[int, UIFontBuildConfig],
    output_root: str | Path,
    atlas_width: int,
    atlas_height: int,
    padding: int,
    progress_callback: ProgressCallback | None = None,
) -> UIFontBuildResult:
    if atlas_width <= 0 or atlas_height <= 0:
        raise ValueError("Atlas size must be greater than zero.")
    if padding < 0:
        raise ValueError("Padding cannot be negative.")

    rasterized_by_block: dict[int, tuple[list[RasterizedTemplateGlyph], freetype.Face | None]] = {}
    pack_inputs: list[RasterizedTemplateGlyph] = []
    template_atlas_images: dict[str, Image.Image] = {}
    fallback_glyph_count = 0

    total_glyphs = 0
    for block in template.blocks:
        if not block.has_embedded_glyphs:
            continue
        config = font_configs.get(block.block_index)
        if config is not None:
            total_glyphs += len(_dedupe_codepoints(config.charset_codepoints))
    total_steps = total_glyphs * 2 + 2
    current_step = 0
    _report_progress(progress_callback, current_step, total_steps, "Preparing template atlas generation...")

    for block in template.blocks:
        if not block.has_embedded_glyphs:
            rasterized_by_block[block.block_index] = ([], None)
            continue

        config = font_configs.get(block.block_index)
        if config is None:
            raise ValueError(f"Missing build config for block {block.block_index} {block.name}.")
        if not config.font_path:
            raise ValueError(f"Block {block.name} has no source font selected.")
        if config.pixel_size <= 0:
            raise ValueError(f"Block {block.name} has invalid pixel size {config.pixel_size}.")

        template_glyphs_by_codepoint = {glyph.codepoint: glyph for glyph in block.glyphs}
        selected_codepoints = _dedupe_codepoints(config.charset_codepoints)

        face = freetype.Face(config.font_path)
        face.set_pixel_sizes(0, config.pixel_size)

        block_glyphs: list[RasterizedTemplateGlyph] = []
        for glyph_index, codepoint in enumerate(selected_codepoints):
            original_template_glyph = template_glyphs_by_codepoint.get(codepoint)
            template_glyph = original_template_glyph or _make_synthetic_template_glyph(block, codepoint)
            char_index = face.get_char_index(codepoint)

            if char_index == 0:
                if original_template_glyph is None:
                    raise ValueError(
                        f"Source font for block {block.name} does not contain U+{codepoint:04X}, "
                        "and the template has no fallback glyph for that codepoint."
                    )
                atlas_source_path = (
                    template_glyph.nut1_path
                    or template_glyph.atlas_path
                    or template.nut1_path
                    or template.atlas_path
                )
                if not atlas_source_path:
                    raise ValueError(
                        f"Template glyph U+{codepoint:04X} in block {block.name} has no atlas source path."
                    )
                if atlas_source_path not in template_atlas_images:
                    template_atlas_images[atlas_source_path] = _load_template_atlas_image(atlas_source_path)
                rasterized = _build_template_fallback_glyph(
                    block_index=block.block_index,
                    glyph_index=glyph_index,
                    template_glyph=template_glyph,
                    atlas_image=template_atlas_images[atlas_source_path],
                )
                fallback_glyph_count += 1
            else:
                face.load_char(chr(codepoint), freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
                slot = face.glyph
                bitmap = slot.bitmap
                rasterized = RasterizedTemplateGlyph(
                    block_index=block.block_index,
                    glyph_index=glyph_index,
                    template_glyph=template_glyph,
                    class_byte=template_glyph.class_byte,
                    codepoint=codepoint,
                    codepoint_bytes=template_glyph.codepoint_bytes,
                    atlas_page_index=template_glyph.atlas_page_index,
                    width=bitmap.width,
                    height=bitmap.rows,
                    bearing_x=slot.bitmap_left,
                    bearing_y=slot.bitmap_top,
                    advance_x=slot.advance.x / 64.0,
                    bitmap_rows=_decode_bitmap_rows(bitmap),
                )
            block_glyphs.append(rasterized)
            pack_inputs.append(rasterized)
            current_step += 1
            _report_progress(
                progress_callback,
                current_step,
                total_steps,
                f"Rasterizing template glyphs: {current_step}/{total_glyphs}",
            )

        block_glyphs = _order_glyphs_for_page_table(block_glyphs)
        rasterized_by_block[block.block_index] = (block_glyphs, face)

    current_step += 1
    _report_progress(progress_callback, current_step, total_steps, "Packing atlas pages...")
    built_pages = _pack_glyphs_into_pages(
        template=template,
        glyphs=pack_inputs,
        atlas_width=atlas_width,
        atlas_height=atlas_height,
        padding=padding,
        progress_callback=progress_callback,
        progress_current=current_step,
        progress_total=total_steps,
    )
    current_step += len(pack_inputs)

    uifont_bytes = _build_uifont_bytes(template, rasterized_by_block, len(built_pages))
    uitx_bytes = _build_uitx_bytes(template)
    preview_atlas = _build_preview_atlas_image(built_pages)
    preview_used_width = preview_atlas.width
    preview_used_height = preview_atlas.height
    primary_page = built_pages[0] if built_pages else BuiltAtlasPage(
        page_index=0,
        width=atlas_width,
        height=atlas_height,
        used_width=0,
        used_height=0,
        image=Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0)),
        atlas_relative_path=(Path("1") / "1" / "0" / "08000000@0.dds").as_posix(),
        nut0_relative_path=(Path("1") / "1" / "0" / "0.nut").as_posix(),
        nut1_relative_path=(Path("1") / "1" / "0" / "1.nut").as_posix(),
        nut1_template_path="",
        packing_mode="empty",
        glyph_count=0,
    )
    uitx_relative_path = _resolve_relative_output_path(
        template.source_file,
        template.uitx_path,
        Path("1") / "0.uitx",
    )
    uifont_relative_path = Path(Path(template.source_file).name).as_posix()

    metadata = {
        "template_path": template.source_file,
        "atlas_width": preview_atlas.width,
        "atlas_height": preview_atlas.height,
        "used_width": preview_used_width,
        "used_height": preview_used_height,
        "padding": padding,
        "atlas_page_count": len(built_pages),
        "fonts": [
            {
                "block_index": block.block_index,
                "name": block.name,
                "glyph_count": len(rasterized_by_block[block.block_index][0]),
                "font_path": font_configs[block.block_index].font_path if block.block_index in font_configs else "",
                "pixel_size": font_configs[block.block_index].pixel_size if block.block_index in font_configs else 0,
                "fallback_glyph_count": sum(
                    1 for glyph in rasterized_by_block[block.block_index][0] if glyph.reused_template
                ),
            }
            for block in template.blocks
        ],
        "pages": [
            {
                "page_index": page.page_index,
                "width": page.width,
                "height": page.height,
                "used_width": page.used_width,
                "used_height": page.used_height,
                "glyph_count": page.glyph_count,
                "packing_mode": page.packing_mode,
                "atlas_path": page.atlas_relative_path,
                "nut0_path": page.nut0_relative_path,
                "nut1_path": page.nut1_relative_path,
                "nut1_template_path": page.nut1_template_path,
            }
            for page in built_pages
        ],
        "uitx_path": uitx_relative_path.as_posix(),
        "uifont_path": uifont_relative_path,
        "fallback_glyph_count": fallback_glyph_count,
        "packing_mode": ", ".join(
            f"page {page.page_index}: {page.packing_mode}" for page in built_pages
        ) or "empty",
    }

    _report_progress(progress_callback, total_steps, total_steps, "Template atlas preview ready.")

    return UIFontBuildResult(
        template_path=template.source_file,
        output_root=str(output_root),
        atlas_width=preview_atlas.width,
        atlas_height=preview_atlas.height,
        used_width=preview_used_width,
        used_height=preview_used_height,
        atlas_image=preview_atlas,
        atlas_pages=built_pages,
        uifont_bytes=uifont_bytes,
        uitx_bytes=uitx_bytes,
        uifont_relative_path=uifont_relative_path,
        uitx_relative_path=uitx_relative_path.as_posix(),
        atlas_relative_path=primary_page.atlas_relative_path,
        nut0_relative_path=primary_page.nut0_relative_path,
        nut1_relative_path=primary_page.nut1_relative_path,
        debug_metadata=metadata,
    )


def _report_progress(progress_callback: ProgressCallback | None, current: int, total: int, message: str) -> None:
    if progress_callback is not None:
        progress_callback(current, max(1, total), message)


def _pack_glyphs_into_pages(
    template: UIFontContainer,
    glyphs: list[RasterizedTemplateGlyph],
    atlas_width: int,
    atlas_height: int,
    padding: int,
    progress_callback: ProgressCallback | None,
    progress_current: int,
    progress_total: int,
) -> list[BuiltAtlasPage]:
    built_pages: list[BuiltAtlasPage] = []
    completed = 0
    total_glyphs = len(glyphs)
    if total_glyphs == 0:
        _report_progress(progress_callback, progress_current, progress_total, "No glyphs to pack.")
        return built_pages

    page_index = 0
    page_glyph_count = 0
    cursor_x = 0
    cursor_y = 0
    row_height = 0
    used_width = 0
    used_height = 0
    atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))

    for glyph in glyphs:
        rect_width = max(1, glyph.width) + padding * 2
        rect_height = max(1, glyph.height) + padding * 2
        if rect_width > atlas_width or rect_height > atlas_height:
            raise ValueError(
                f"Merged atlas packing contains a glyph rectangle {rect_width}x{rect_height} "
                f"that exceeds the atlas size {atlas_width}x{atlas_height}."
            )

        if cursor_x > 0 and cursor_x + rect_width > atlas_width:
            cursor_y += row_height
            cursor_x = 0
            row_height = 0

        if cursor_y + rect_height > atlas_height:
            built_pages.append(
                _build_generated_page(
                    template=template,
                    page_index=page_index,
                    atlas_width=atlas_width,
                    atlas_height=atlas_height,
                    used_width=used_width,
                    used_height=used_height,
                    atlas=atlas,
                    glyph_count=page_glyph_count,
                )
            )
            page_index += 1
            page_glyph_count = 0
            cursor_x = 0
            cursor_y = 0
            row_height = 0
            used_width = 0
            used_height = 0
            atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))

        glyph.atlas_page_index = page_index
        glyph.atlas_x = cursor_x + padding
        glyph.atlas_y = cursor_y + padding
        if glyph.width > 0 and glyph.height > 0:
            glyph_image = glyph.image if glyph.image is not None else _build_rgba_glyph_image(
                glyph.width,
                glyph.height,
                glyph.bitmap_rows,
            )
            atlas.alpha_composite(glyph_image, (glyph.atlas_x, glyph.atlas_y))

        cursor_x += rect_width
        row_height = max(row_height, rect_height)
        used_width = max(used_width, cursor_x)
        used_height = max(used_height, cursor_y + rect_height)
        page_glyph_count += 1
        completed += 1
        _report_progress(
            progress_callback,
            progress_current + completed,
            progress_total,
            f"Compositing atlas page {page_index}: {page_glyph_count} glyphs placed (shelf)",
        )

    built_pages.append(
        _build_generated_page(
            template=template,
            page_index=page_index,
            atlas_width=atlas_width,
            atlas_height=atlas_height,
            used_width=used_width,
            used_height=used_height,
            atlas=atlas,
            glyph_count=page_glyph_count,
            crop_to_used_bounds=True,
        )
    )
    return built_pages


def _build_generated_page(
    template: UIFontContainer,
    page_index: int,
    atlas_width: int,
    atlas_height: int,
    used_width: int,
    used_height: int,
    atlas: Image.Image,
    glyph_count: int,
    crop_to_used_bounds: bool = False,
) -> BuiltAtlasPage:
    output_width = atlas_width
    output_height = atlas_height
    output_image = atlas
    if crop_to_used_bounds and glyph_count > 0:
        output_width = min(atlas_width, _align_up(used_width, 64))
        output_height = min(atlas_height, _align_up(used_height, 64))
        output_image = atlas.crop((0, 0, output_width, output_height))

    atlas_relative_path = _resolve_relative_output_path(
        template.source_file,
        template.atlas_paths.get(page_index, ""),
        Path("1") / "1" / str(page_index) / "08000000@0.dds",
    ).with_suffix(".dds")
    nut0_relative_path = _resolve_relative_output_path(
        template.source_file,
        template.nut0_paths.get(page_index, ""),
        Path("1") / "1" / str(page_index) / "0.nut",
    )
    nut1_relative_path = _resolve_relative_output_path(
        template.source_file,
        template.nut1_paths.get(page_index, ""),
        Path("1") / "1" / str(page_index) / "1.nut",
    )
    nut1_template_path = (
        template.nut1_paths.get(page_index)
        or template.nut1_path
        or (template.nut1_paths[sorted(template.nut1_paths)[0]] if template.nut1_paths else "")
    )
    return BuiltAtlasPage(
        page_index=page_index,
        width=output_width,
        height=output_height,
        used_width=used_width,
        used_height=used_height,
        image=output_image,
        atlas_relative_path=atlas_relative_path.as_posix(),
        nut0_relative_path=nut0_relative_path.as_posix(),
        nut1_relative_path=nut1_relative_path.as_posix(),
        nut1_template_path=nut1_template_path,
        packing_mode="shelf",
        glyph_count=glyph_count,
    )


def _build_preview_atlas_image(pages: list[BuiltAtlasPage]) -> Image.Image:
    if not pages:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    if len(pages) == 1:
        return pages[0].image.copy()

    gap = 16
    width = sum(page.width for page in pages) + gap * (len(pages) - 1)
    height = max(page.height for page in pages)
    preview = Image.new("RGBA", (max(1, width), max(1, height)), (0, 0, 0, 0))
    cursor_x = 0
    for page in pages:
        preview.alpha_composite(page.image, (cursor_x, 0))
        cursor_x += page.width + gap
    return preview


def _make_synthetic_template_glyph(block: UIFontBlock, codepoint: int) -> UIFontGlyph:
    if not block.glyphs:
        raise ValueError(f"Block {block.name} has no template glyphs to derive record defaults from.")

    prototype = _select_block_prototype_glyph(block)
    inferred_class_byte = _infer_class_byte_for_codepoint(codepoint, prototype.class_byte)
    return replace(
        prototype,
        source_file=block.source_file,
        atlas_path=prototype.atlas_path or block.atlas_path,
        nut1_path=prototype.nut1_path or block.nut1_path,
        atlas_paths=block.atlas_paths,
        nut1_paths=block.nut1_paths,
        block_index=block.block_index,
        glyph_index=len(block.glyphs),
        codepoint=codepoint,
        codepoint_bytes=int_to_codepoint_bytes(codepoint),
        atlas_x=0,
        atlas_y=0,
        offset_x_px=0.0,
        ascent_px=0.0,
        advance_x_px=0.0,
        ink_width_px=0,
        ink_height_px=0,
        class_byte=inferred_class_byte,
    )


def _select_block_prototype_glyph(block: UIFontBlock) -> UIFontGlyph:
    prototype_counts: dict[tuple[int, bytes, bytes], int] = {}
    for glyph in block.glyphs:
        key = (glyph.class_byte, glyph.reserved_10_13, glyph.reserved_15_17)
        prototype_counts[key] = prototype_counts.get(key, 0) + 1

    selected_key = max(
        prototype_counts.items(),
        key=lambda item: (item[1], -block.glyphs.index(next(g for g in block.glyphs if (
            g.class_byte,
            g.reserved_10_13,
            g.reserved_15_17,
        ) == item[0]))),
    )[0]
    for glyph in block.glyphs:
        if (
            glyph.class_byte,
            glyph.reserved_10_13,
            glyph.reserved_15_17,
        ) == selected_key:
            return glyph
    return block.glyphs[0]


def _codepoint_low_byte(codepoint_bytes: bytes) -> int:
    if len(codepoint_bytes) != 2:
        raise ValueError(f"UIFONT codepoint field must be exactly 2 bytes, got {len(codepoint_bytes)}.")
    return codepoint_bytes[1]


def _order_glyphs_for_page_table(glyphs: list[RasterizedTemplateGlyph]) -> list[RasterizedTemplateGlyph]:
    indexed = list(enumerate(glyphs))
    indexed.sort(key=lambda pair: (_codepoint_low_byte(pair[1].codepoint_bytes), pair[1].codepoint_bytes, pair[0]))
    return [glyph for _, glyph in indexed]


def _infer_class_byte_for_codepoint(
    codepoint: int,
    fallback_class_byte: int,
    compatibility_seen: set[int] | None = None,
) -> int:
    if compatibility_seen is None:
        compatibility_seen = set()
    if codepoint in compatibility_seen:
        return fallback_class_byte
    compatibility_seen.add(codepoint)

    char = chr(codepoint)
    category = unicodedata.category(char)
    east_asian_width = unicodedata.east_asian_width(char)

    if codepoint in {0x000A, 0x000D}:
        return 0x1A
    if codepoint == 0x2028:
        return 0x17
    if codepoint == 0x0009:
        return 0x10
    if codepoint in CLASS_15_CODEPOINTS:
        return 0x15
    if codepoint in CLASS_14_CODEPOINTS:
        return 0x14
    if codepoint in CLASS_11_CODEPOINTS:
        return 0x11
    if codepoint in CLASS_10_CODEPOINTS:
        return 0x10
    if codepoint in CLASS_04_CODEPOINTS:
        return 0x04
    if codepoint == 0x3000:
        return 0x0D
    if codepoint == 0x0020 or category == "Zs":
        return 0x1C
    if 0xE000 <= codepoint <= 0xF8FF and codepoint not in CLASS_1D_EXCEPTIONS:
        return 0x1D
    if codepoint in CLASS_00_CODEPOINTS:
        return 0x00
    if codepoint in CLASS_01_CODEPOINTS:
        return 0x01
    if category == "Nd":
        return 0x0B
    if codepoint in CLASS_05_CODEPOINTS:
        return 0x05
    if codepoint in CLASS_09_CODEPOINTS:
        return 0x09
    if codepoint in CLASS_0A_CODEPOINTS:
        return 0x0A
    if codepoint in CLASS_0C_CODEPOINTS:
        return 0x0C
    if codepoint in CLASS_16_CODEPOINTS:
        return 0x16
    if codepoint in {0x3001, 0x3002}:
        return 0x02
    if codepoint in {
        0x0028, 0x005B, 0x007B, 0x3008, 0x300A, 0x300C, 0x300E,
        0x3010, 0x3014, 0x3016, 0xFF08, 0xFF3B, 0xFF5B,
    } or category == "Ps":
        return 0x00
    if codepoint in {
        0x0029, 0x005D, 0x007D, 0x3009, 0x300B, 0x300D, 0x300F,
        0x3011, 0x3015, 0x3017, 0xFF09, 0xFF3D, 0xFF5D,
    } or category == "Pe":
        return 0x01
    if codepoint in {0x0022, 0x0027, 0x2018, 0x2019, 0x201C, 0x201D, 0x00AB, 0x00BB, 0x2039, 0x203A}:
        return 0x03
    if codepoint == 0x30FB:
        return 0x05
    if codepoint in {0x0021, 0x003F, 0xFF01, 0xFF1F}:
        return 0x06
    if codepoint == 0x002F:
        return 0x07
    if codepoint in {0x002C, 0x002E, 0x003A, 0x003B, 0xFF0C, 0xFF0E, 0xFF1A, 0xFF1B}:
        return 0x08
    if codepoint in {0x005C, 0x2212}:
        return 0x09
    if codepoint in {0x002D, 0xFF0D}:
        return 0x0F
    if codepoint in {0x2010, 0x2011, 0x2012, 0x2013}:
        return 0x10
    if codepoint == 0x2014:
        return 0x12
    if codepoint == 0x2026:
        return 0x0E

    normalized = unicodedata.normalize("NFKC", char)
    if len(normalized) == 1:
        normalized_codepoint = ord(normalized)
        if normalized_codepoint != codepoint:
            normalized_class = _infer_class_byte_for_codepoint(
                normalized_codepoint,
                fallback_class_byte,
                compatibility_seen,
            )
            if normalized_class != fallback_class_byte:
                return normalized_class

    if 0xFF66 <= codepoint <= 0xFF9D:
        return 0x0C
    if _is_cjk_or_kana_codepoint(codepoint) or (category.startswith("L") and east_asian_width in {"W", "F"}):
        return 0x0D
    if category.startswith("L"):
        return 0x0C

    return fallback_class_byte


def _is_cjk_or_kana_codepoint(codepoint: int) -> bool:
    return (
        0x3040 <= codepoint <= 0x30FF
        or 0x31F0 <= codepoint <= 0x31FF
        or 0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xAC00 <= codepoint <= 0xD7AF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0xFF66 <= codepoint <= 0xFF9F
    )


def _dedupe_codepoints(codepoints: list[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for codepoint in codepoints:
        if codepoint in seen:
            continue
        seen.add(codepoint)
        ordered.append(codepoint)
    return ordered


def _load_template_atlas_image(atlas_source_path_text: str) -> Image.Image:
    if not atlas_source_path_text:
        raise ValueError("Template atlas source is required when reusing missing glyphs, but no source path was found.")
    atlas_source_path = Path(atlas_source_path_text)
    if not atlas_source_path.is_file():
        raise ValueError(f"Template atlas source was not found: {atlas_source_path}")
    if atlas_source_path.suffix.lower() == ".nut":
        return load_nut_image(atlas_source_path)
    return Image.open(atlas_source_path).convert("RGBA")


def _extract_template_glyph_image(atlas_image: Image.Image, glyph: UIFontGlyph) -> Image.Image:
    if glyph.ink_width_px <= 0 or glyph.ink_height_px <= 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return atlas_image.crop(
        (
            glyph.atlas_x,
            glyph.atlas_y,
            glyph.atlas_x + glyph.ink_width_px,
            glyph.atlas_y + glyph.ink_height_px,
        )
    )


def _build_template_fallback_glyph(
    block_index: int,
    glyph_index: int,
    template_glyph: UIFontGlyph,
    atlas_image: Image.Image,
) -> RasterizedTemplateGlyph:
    return RasterizedTemplateGlyph(
        block_index=block_index,
        glyph_index=glyph_index,
        template_glyph=template_glyph,
        class_byte=template_glyph.class_byte,
        codepoint=template_glyph.codepoint,
        codepoint_bytes=template_glyph.codepoint_bytes,
        atlas_page_index=template_glyph.atlas_page_index,
        width=template_glyph.ink_width_px,
        height=template_glyph.ink_height_px,
        bearing_x=template_glyph.offset_x_px,
        bearing_y=template_glyph.ascent_px,
        advance_x=template_glyph.advance_x_px,
        bitmap_rows=[],
        image=_extract_template_glyph_image(atlas_image, template_glyph),
        reused_template=True,
    )


def save_uifont_package(result: UIFontBuildResult) -> dict[str, Path]:
    output_root = Path(result.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    uifont_path = output_root / Path(result.uifont_relative_path)
    uitx_path = output_root / Path(result.uitx_relative_path)

    uifont_path.parent.mkdir(parents=True, exist_ok=True)
    uitx_path.parent.mkdir(parents=True, exist_ok=True)

    uifont_path.write_bytes(result.uifont_bytes)
    uitx_path.write_bytes(result.uitx_bytes)

    nut0_paths: list[Path] = []
    nut1_paths: list[Path] = []
    for page in result.atlas_pages:
        nut0_path = output_root / Path(page.nut0_relative_path)
        nut1_path = output_root / Path(page.nut1_relative_path)
        nut0_path.parent.mkdir(parents=True, exist_ok=True)
        nut1_path.parent.mkdir(parents=True, exist_ok=True)

        dds_bytes = build_game_dds_bytes(page.image)
        nut0_bytes, nut1_bytes = build_nut_pair_from_dds_bytes(dds_bytes, page.nut1_template_path or None)
        nut0_path.write_bytes(nut0_bytes)
        nut1_path.write_bytes(nut1_bytes)
        nut0_paths.append(nut0_path)
        nut1_paths.append(nut1_path)

    primary_nut0_path = nut0_paths[0] if nut0_paths else output_root / Path(result.nut0_relative_path)
    primary_nut1_path = nut1_paths[0] if nut1_paths else output_root / Path(result.nut1_relative_path)

    paths = {
        "uifont": uifont_path,
        "uitx": uitx_path,
        "nut0": primary_nut0_path,
        "nut1": primary_nut1_path,
        "nut0_pages": nut0_paths,
        "nut1_pages": nut1_paths,
    }
    return paths


def _build_uifont_bytes(
    template: UIFontContainer,
    rasterized_by_block: dict[int, tuple[list[RasterizedTemplateGlyph], freetype.Face | None]],
    atlas_page_count: int,
) -> bytes:
    block_bodies: list[bytes] = []
    block_count = len(template.blocks)
    container_header_size = 0x10 + block_count * 4
    current_offset = container_header_size
    block_offsets: list[int] = []

    for block in template.blocks:
        block_offsets.append(current_offset)
        glyphs, face = rasterized_by_block[block.block_index]
        block_bytes = _build_block_bytes(block, glyphs, face, current_offset)
        block_bodies.append(block_bytes)
        current_offset += len(block_bytes)

    data = bytearray()
    header_prefix = bytearray(template.header_prefix[:0x0F])
    if len(header_prefix) < 0x0F:
        raise ValueError("Template UIFONT header prefix is shorter than 0x0F bytes.")
    header_prefix[0x0D] = atlas_page_count & 0xFF
    data.extend(header_prefix)
    data.append(block_count & 0xFF)
    for block_offset in block_offsets:
        data.extend(_be32(block_offset))
    for block_bytes in block_bodies:
        data.extend(block_bytes)
    return bytes(data)


def _build_block_bytes(
    template_block: UIFontBlock,
    glyphs: list[RasterizedTemplateGlyph],
    face: freetype.Face | None,
    block_offset: int,
) -> bytes:
    has_glyphs = len(glyphs) > 0
    block_size = BLOCK_HEADER_SIZE + len(glyphs) * GLYPH_RECORD_SIZE if has_glyphs else BLOCK_HEADER_SIZE
    data = bytearray(block_size)

    name_bytes = template_block.name.encode("ascii", errors="replace")[:BLOCK_NAME_SIZE]
    data[0:len(name_bytes)] = name_bytes

    metrics_raw = _compute_block_metrics_raw(template_block, glyphs, face)
    for index, value in enumerate(metrics_raw[:4]):
        data[0x20 + index * 2 : 0x22 + index * 2] = _be16(value)

    data[0x28:0x2A] = _be16(len(glyphs))
    data[0x2A:0x2C] = _be16(template_block.unk_2a)
    data[0x2C:0x30] = _be32(template_block.unk_2c)
    data[0x30:0x34] = _be32(block_offset + BLOCK_HEADER_SIZE if has_glyphs else 0)
    data[0x34:0x38] = _be32(sum(1 for glyph in glyphs if _codepoint_low_byte(glyph.codepoint_bytes) == 0))

    page_entries = _build_page_entries(glyphs)
    for page_index, (start, count) in enumerate(page_entries):
        entry_offset = BLOCK_HEADER_SIZE - (255 - page_index) * 4
        data[entry_offset : entry_offset + 2] = _be16(start)
        data[entry_offset + 2 : entry_offset + 4] = _be16(count)

    if not has_glyphs:
        return bytes(data)

    glyph_offset = BLOCK_HEADER_SIZE
    for glyph in glyphs:
        record = _build_glyph_record(glyph)
        data[glyph_offset : glyph_offset + GLYPH_RECORD_SIZE] = record
        glyph_offset += GLYPH_RECORD_SIZE

    return bytes(data)


def _compute_block_metrics_raw(
    template_block: UIFontBlock,
    glyphs: list[RasterizedTemplateGlyph],
    face: freetype.Face | None,
) -> list[int]:
    if face is None or not glyphs:
        return list(template_block.metrics_raw)

    try:
        ascent = max(0, int(face.size.ascender))
        descent = max(0, -int(face.size.descender))
        max_advance = max(0, int(face.size.max_advance))
        line_height = max(0, int(face.size.height))
    except Exception:
        return list(template_block.metrics_raw)

    if line_height <= 0:
        line_height = ascent + descent
    if max_advance <= 0:
        max_advance = max(
            [_round_26_6(glyph.advance_x) for glyph in glyphs] + [template_block.metrics_raw[2] if len(template_block.metrics_raw) >= 3 else 0]
        )

    metrics = [ascent, descent, max_advance, line_height]
    return metrics


def _build_page_entries(glyphs: list[RasterizedTemplateGlyph]) -> list[tuple[int, int]]:
    entries: list[tuple[int, int]] = []
    for low_byte in range(1, 256):
        indexes = [
            index
            for index, glyph in enumerate(glyphs)
            if _codepoint_low_byte(glyph.codepoint_bytes) == low_byte
        ]
        if not indexes:
            entries.append((0, 0))
            continue

        start = min(indexes)
        count = len(indexes)
        if indexes != list(range(start, start + count)):
            raise ValueError(
                f"Glyph order cannot be represented in UIFONT page table for low byte 0x{low_byte:02X}."
            )
        entries.append((start, count))
    return entries


def _build_glyph_record(glyph: RasterizedTemplateGlyph) -> bytes:
    template = glyph.template_glyph
    data = bytearray(GLYPH_RECORD_SIZE)
    data[0x00:0x02] = _be16(glyph.atlas_page_index)
    data[0x02:0x04] = _be16(glyph.atlas_x)
    data[0x04:0x06] = _be16(glyph.atlas_y)
    data[0x06:0x08] = _be16s(_round_26_6(glyph.bearing_x))
    data[0x08:0x0A] = _be16s(_round_26_6(glyph.bearing_y))
    data[0x0A:0x0C] = _be16(max(0, _round_26_6(glyph.advance_x)))
    data[0x0C] = max(0, min(255, glyph.width))
    data[0x0D] = max(0, min(255, glyph.height))
    data[0x0E:0x10] = glyph.codepoint_bytes
    data[0x10:0x14] = template.reserved_10_13
    data[0x14] = glyph.class_byte
    data[0x15:0x18] = template.reserved_15_17
    return bytes(data)


def _build_uitx_bytes(template: UIFontContainer) -> bytes:
    if template.uitx_path:
        source_path = Path(template.uitx_path)
        if source_path.is_file():
            data = source_path.read_bytes()
            if data[:4] == b"UITX":
                return data
    return b"UITX" + _be32(0) + _be32(0) + _be32(0) + _be32(0x14)


def _resolve_relative_output_path(
    template_uifont_path: str,
    candidate_path: str,
    fallback: Path,
) -> Path:
    if candidate_path:
        template_root = Path(template_uifont_path).parent
        candidate = Path(candidate_path)
        try:
            return candidate.relative_to(template_root)
        except ValueError:
            pass
    return fallback
