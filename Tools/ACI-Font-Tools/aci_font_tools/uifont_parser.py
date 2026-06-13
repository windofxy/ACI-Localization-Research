from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BLOCK_NAME_SIZE = 0x20
PAGE_TABLE_ENTRIES = 255
PAGE_TABLE_SIZE = PAGE_TABLE_ENTRIES * 4
BLOCK_FIXED_HEADER_SIZE = 0x38
BLOCK_HEADER_SIZE = BLOCK_FIXED_HEADER_SIZE + PAGE_TABLE_SIZE
GLYPH_RECORD_SIZE = 24


def be16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big", signed=False)


def be32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big", signed=False)


def codepoint_bytes_to_int(raw: bytes) -> int:
    if len(raw) != 2:
        raise ValueError(f"UIFONT codepoint field must be exactly 2 bytes, got {len(raw)}.")
    return int.from_bytes(raw, "big", signed=False)


def int_to_codepoint_bytes(codepoint: int) -> bytes:
    if codepoint < 0 or codepoint > 0xFFFF:
        raise ValueError(
            f"UIFONT stores codepoints as a single UTF-16BE code unit; U+{codepoint:04X} is out of range."
        )
    return int(codepoint).to_bytes(2, "big", signed=False)


def read_c_string(data: bytes, offset: int, size: int) -> str:
    raw = data[offset : offset + size]
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")


@dataclass
class UIFontPageEntry:
    page_index: int
    start: int
    count: int


@dataclass
class UIFontGlyph:
    source_file: str
    atlas_path: str
    nut1_path: str
    atlas_paths: dict[int, str]
    nut1_paths: dict[int, str]
    block_index: int
    glyph_index: int
    codepoint: int
    codepoint_bytes: bytes
    atlas_page_index: int
    atlas_x: int
    atlas_y: int
    offset_x_px: float
    ascent_px: float
    advance_x_px: float
    ink_width_px: int
    ink_height_px: int
    class_byte: int
    reserved_10_13: bytes
    reserved_15_17: bytes
    raw_bytes: bytes

    @property
    def leading_u16(self) -> int:
        return self.atlas_page_index

    @property
    def display_char(self) -> str:
        if 0x20 <= self.codepoint <= 0x7E:
            return chr(self.codepoint)
        return "."

    @property
    def char(self) -> str:
        return chr(self.codepoint)


@dataclass
class UIFontBlock:
    source_file: str
    atlas_path: str
    atlas_paths: dict[int, str]
    uitx_path: str
    nut1_path: str
    nut1_paths: dict[int, str]
    block_index: int
    name: str
    glyph_count: int
    glyphs: list[UIFontGlyph]
    metrics_raw: list[int]
    unk_2a: int
    unk_2c: int
    glyph_data_offset: int
    unk_34: int
    page_entries: list[UIFontPageEntry]
    block_offset: int
    next_offset: int

    @property
    def has_embedded_glyphs(self) -> bool:
        return self.glyph_data_offset != 0 and self.next_offset > self.glyph_data_offset

    @property
    def charset_text(self) -> str:
        return "".join(glyph.char for glyph in self.glyphs)


@dataclass
class UIFontContainer:
    source_file: str
    atlas_path: str
    atlas_paths: dict[int, str]
    uitx_path: str
    nut0_path: str
    nut0_paths: dict[int, str]
    nut1_path: str
    nut1_paths: dict[int, str]
    header_prefix: bytes
    blocks: list[UIFontBlock]


def _find_uifont_page_dirs(path: str | Path) -> list[tuple[int, Path]]:
    source_path = Path(path)
    atlas_root = source_path.parent / "1" / "1"
    if not atlas_root.is_dir():
        return []

    page_dirs: list[tuple[int, Path]] = []
    numeric_page_dirs = [
        page_dir
        for page_dir in atlas_root.iterdir()
        if page_dir.is_dir() and page_dir.name.isdigit()
    ]
    for page_dir in sorted(numeric_page_dirs, key=lambda item: int(item.name)):
        page_dirs.append((int(page_dir.name), page_dir))
    return page_dirs


def _pick_primary_page_path(paths: dict[int, str]) -> str:
    if 0 in paths:
        return paths[0]
    for page_index in sorted(paths):
        return paths[page_index]
    return ""


def find_atlas_images_for_uifont(path: str | Path) -> dict[int, str]:
    atlas_paths: dict[int, str] = {}
    for page_index, page_dir in _find_uifont_page_dirs(path):
        pngs = sorted(page_dir.glob("*.png"))
        if pngs:
            atlas_paths[page_index] = str(pngs[0])
            continue

        dds_files = sorted(page_dir.glob("*.dds"))
        if dds_files:
            atlas_paths[page_index] = str(dds_files[0])
    return atlas_paths


def find_atlas_image_for_uifont(path: str | Path) -> str:
    return _pick_primary_page_path(find_atlas_images_for_uifont(path))


def find_uitx_for_uifont(path: str | Path) -> str:
    source_path = Path(path)
    uitx_dir = source_path.parent / "1"
    if not uitx_dir.is_dir():
        return ""

    uitxs = sorted(uitx_dir.glob("*.uitx"))
    if not uitxs:
        return ""

    return str(uitxs[0])


def find_nut0_paths_for_uifont(path: str | Path) -> dict[int, str]:
    nut0_paths: dict[int, str] = {}
    for page_index, page_dir in _find_uifont_page_dirs(path):
        nut_path = page_dir / "0.nut"
        if nut_path.is_file():
            nut0_paths[page_index] = str(nut_path)
    return nut0_paths


def find_nut1_paths_for_uifont(path: str | Path) -> dict[int, str]:
    nut1_paths: dict[int, str] = {}
    for page_index, page_dir in _find_uifont_page_dirs(path):
        nut_path = page_dir / "1.nut"
        if nut_path.is_file():
            nut1_paths[page_index] = str(nut_path)
    return nut1_paths


def find_nut0_for_uifont(path: str | Path) -> str:
    return _pick_primary_page_path(find_nut0_paths_for_uifont(path))


def find_nut1_for_uifont(path: str | Path) -> str:
    return _pick_primary_page_path(find_nut1_paths_for_uifont(path))


def parse_uifont(path: str | Path) -> UIFontContainer:
    source_path = Path(path)
    data = source_path.read_bytes()
    if data[:4] != b"ACF\x00":
        raise ValueError(f"Not a UIFONT/ACF file: {source_path}")

    atlas_paths = find_atlas_images_for_uifont(source_path)
    atlas_path = _pick_primary_page_path(atlas_paths)
    uitx_path = find_uitx_for_uifont(source_path)
    nut0_paths = find_nut0_paths_for_uifont(source_path)
    nut1_paths = find_nut1_paths_for_uifont(source_path)
    nut0_path = _pick_primary_page_path(nut0_paths)
    nut1_path = _pick_primary_page_path(nut1_paths)
    block_count = data[0x0F]
    offsets = [be32(data, 0x10 + index * 4) for index in range(block_count)]

    blocks: list[UIFontBlock] = []
    for block_index, block_offset in enumerate(offsets):
        next_offset = offsets[block_index + 1] if block_index + 1 < len(offsets) else len(data)
        name = read_c_string(data, block_offset, BLOCK_NAME_SIZE)
        metrics_raw = [be16(data, block_offset + 0x20 + index * 2) for index in range(4)]
        glyph_count = be16(data, block_offset + 0x28)
        unk_2a = be16(data, block_offset + 0x2A)
        unk_2c = be32(data, block_offset + 0x2C)
        glyph_data_offset = be32(data, block_offset + 0x30)
        unk_34 = be32(data, block_offset + 0x34)

        page_entries: list[UIFontPageEntry] = []
        page_table_offset = block_offset + BLOCK_FIXED_HEADER_SIZE
        for page_index in range(PAGE_TABLE_ENTRIES):
            entry_offset = page_table_offset + page_index * 4
            page_entries.append(
                UIFontPageEntry(
                    page_index=page_index,
                    start=be16(data, entry_offset),
                    count=be16(data, entry_offset + 2),
                )
            )

        glyphs: list[UIFontGlyph] = []
        if glyph_data_offset and glyph_data_offset < next_offset:
            max_records = min(glyph_count, (next_offset - glyph_data_offset) // GLYPH_RECORD_SIZE)
            for glyph_index in range(max_records):
                record_offset = glyph_data_offset + glyph_index * GLYPH_RECORD_SIZE
                raw = data[record_offset : record_offset + GLYPH_RECORD_SIZE]
                atlas_page_index = be16(raw, 0x00)
                glyphs.append(
                    UIFontGlyph(
                        source_file=str(source_path),
                        atlas_path=atlas_paths.get(atlas_page_index, atlas_path),
                        nut1_path=nut1_paths.get(atlas_page_index, nut1_path),
                        atlas_paths=atlas_paths,
                        nut1_paths=nut1_paths,
                        block_index=block_index,
                        glyph_index=glyph_index,
                        codepoint=codepoint_bytes_to_int(raw[0x0E:0x10]),
                        codepoint_bytes=raw[0x0E:0x10],
                        atlas_page_index=atlas_page_index,
                        atlas_x=be16(raw, 0x02),
                        atlas_y=be16(raw, 0x04),
                        offset_x_px=int.from_bytes(raw[0x06:0x08], "big", signed=True) / 64.0,
                        ascent_px=int.from_bytes(raw[0x08:0x0A], "big", signed=True) / 64.0,
                        advance_x_px=be16(raw, 0x0A) / 64.0,
                        ink_width_px=raw[0x0C],
                        ink_height_px=raw[0x0D],
                        class_byte=raw[0x14],
                        reserved_10_13=raw[0x10:0x14],
                        reserved_15_17=raw[0x15:0x18],
                        raw_bytes=raw,
                    )
                )

        blocks.append(
            UIFontBlock(
                source_file=str(source_path),
                atlas_path=atlas_path,
                atlas_paths=atlas_paths,
                uitx_path=uitx_path,
                nut1_path=nut1_path,
                nut1_paths=nut1_paths,
                block_index=block_index,
                name=name,
                glyph_count=glyph_count,
                glyphs=glyphs,
                metrics_raw=metrics_raw,
                unk_2a=unk_2a,
                unk_2c=unk_2c,
                glyph_data_offset=glyph_data_offset,
                unk_34=unk_34,
                page_entries=page_entries,
                block_offset=block_offset,
                next_offset=next_offset,
            )
        )

    return UIFontContainer(
        source_file=str(source_path),
        atlas_path=atlas_path,
        atlas_paths=atlas_paths,
        uitx_path=uitx_path,
        nut0_path=nut0_path,
        nut0_paths=nut0_paths,
        nut1_path=nut1_path,
        nut1_paths=nut1_paths,
        header_prefix=data[:0x0F],
        blocks=blocks,
    )


def parse_uifont_directory(directory: str | Path) -> list[UIFontBlock]:
    root = Path(directory)
    blocks: list[UIFontBlock] = []
    for path in sorted(root.rglob("*.uifont")):
        blocks.extend(parse_uifont(path).blocks)
    return blocks
