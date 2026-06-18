from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ACT_HEADER_SIZE = 0x24
ACT_HASH_META_SIZE = 0x0C


@dataclass(frozen=True)
class ACETextHeader:
    magic: bytes
    version: int
    data_version: int
    is_big_endian: bool
    language_count: int
    text_count: int
    hash_count: int
    language_table_offset: int
    text_table_offset: int
    hash_table_offset: int


@dataclass(frozen=True)
class ACETextLanguage:
    name: str
    index: int


@dataclass(frozen=True)
class ACETextTextRef:
    text_index: int
    label: str
    label_offset: int
    text_offsets: list[int]


@dataclass(frozen=True)
class ACETextHashMeta:
    hash_value: int
    label: str
    label_offset: int
    text_index: int


@dataclass(frozen=True)
class ACETextEntry:
    hash_value: int
    hash_label: str
    hash_label_offset: int
    text_index: int
    text_label: str
    text_label_offset: int
    text_offsets: list[int]
    values: dict[str, str]
    value_code_units: dict[str, list[int]]

    @property
    def display_name(self) -> str:
        if self.hash_label:
            return self.hash_label
        return f"[0x{self.hash_value:08X}]"


@dataclass(frozen=True)
class ACETextContainer:
    source_file: str
    header: ACETextHeader
    languages: list[ACETextLanguage]
    texts: list[ACETextTextRef]
    hashes: list[ACETextHashMeta]
    entries: list[ACETextEntry]


def _be32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Offset 0x{offset:X} is outside the ACEText buffer.")
    return int.from_bytes(data[offset : offset + 4], "big", signed=True)


def _be32u(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Offset 0x{offset:X} is outside the ACEText buffer.")
    return int.from_bytes(data[offset : offset + 4], "big", signed=False)


def _read_null_terminated_string(data: bytes, offset: int, encoding: str, unit_size: int) -> str:
    if offset == 0:
        return ""
    if offset < 0 or offset >= len(data):
        raise ValueError(f"String offset 0x{offset:X} is outside the ACEText buffer.")

    cursor = offset
    while cursor + unit_size <= len(data):
        if data[cursor : cursor + unit_size] == b"\x00" * unit_size:
            break
        cursor += unit_size

    raw = data[offset:cursor]
    if not raw:
        return ""
    return raw.decode(encoding, errors="replace")


def _read_language_name(data: bytes, offset: int) -> str:
    raw = data[offset : offset + 3]
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def _read_utf16be_code_units(data: bytes, offset: int) -> list[int]:
    if offset == 0:
        return []
    if offset < 0 or offset >= len(data):
        raise ValueError(f"String offset 0x{offset:X} is outside the ACEText buffer.")

    cursor = offset
    code_units: list[int] = []
    while cursor + 2 <= len(data):
        code_unit = int.from_bytes(data[cursor : cursor + 2], "big", signed=False)
        if code_unit == 0:
            break
        code_units.append(code_unit)
        cursor += 2
    return code_units


def _decode_utf16be_code_units_for_view(code_units: list[int]) -> str:
    chars: list[str] = []
    for code_unit in code_units:
        if 0xD800 <= code_unit <= 0xDFFF:
            chars.append("\uFFFD")
        else:
            chars.append(chr(code_unit))
    return "".join(chars)


def parse_ace_text(path: str | Path) -> ACETextContainer:
    source_path = Path(path)
    data = source_path.read_bytes()
    if len(data) < ACT_HEADER_SIZE:
        raise ValueError(f"{source_path.name} is too small to be a valid ACEText file.")

    header = ACETextHeader(
        magic=data[0:4],
        version=_be32u(data, 0x04),
        data_version=_be32u(data, 0x08),
        is_big_endian=data[0x0C] != 0,
        language_count=data[0x0D],
        text_count=_be32(data, 0x10),
        hash_count=_be32(data, 0x14),
        language_table_offset=_be32(data, 0x18),
        text_table_offset=_be32(data, 0x1C),
        hash_table_offset=_be32(data, 0x20),
    )

    if header.magic != b"ACT\x00":
        raise ValueError(
            f"{source_path.name} does not start with ACT\\0 magic. Found {header.magic!r} instead."
        )

    languages: list[ACETextLanguage] = []
    for language_slot in range(header.language_count):
        entry_offset = header.language_table_offset + language_slot * 4
        if entry_offset + 4 > len(data):
            raise ValueError("ACEText language table extends beyond the end of the file.")
        languages.append(
            ACETextLanguage(
                name=_read_language_name(data, entry_offset),
                index=data[entry_offset + 3],
            )
        )
    languages.sort(key=lambda language: (language.index, language.name))

    texts: list[ACETextTextRef] = []
    for text_index in range(header.text_count):
        table_offset = header.text_table_offset + text_index * 4
        text_ref_offset = _be32(data, table_offset)
        label_offset = _be32(data, text_ref_offset)
        text_offsets: list[int] = []
        for language_slot in range(header.language_count):
            text_offsets.append(_be32(data, text_ref_offset + 4 + language_slot * 4))
        texts.append(
            ACETextTextRef(
                text_index=text_index,
                label=_read_null_terminated_string(data, label_offset, "cp932", 1),
                label_offset=label_offset,
                text_offsets=text_offsets,
            )
        )

    hashes: list[ACETextHashMeta] = []
    entries: list[ACETextEntry] = []
    index_to_text = {text.text_index: text for text in texts}
    languages_by_index = {language.index: language.name for language in languages}
    fallback_language_names = [language.name for language in languages]

    for hash_index in range(header.hash_count):
        meta_offset = header.hash_table_offset + hash_index * ACT_HASH_META_SIZE
        hash_value = _be32u(data, meta_offset)
        label_offset = _be32(data, meta_offset + 4)
        text_index = _be32(data, meta_offset + 8)
        hash_label = _read_null_terminated_string(data, label_offset, "cp932", 1)
        hash_meta = ACETextHashMeta(
            hash_value=hash_value,
            label=hash_label,
            label_offset=label_offset,
            text_index=text_index,
        )
        hashes.append(hash_meta)

        text_ref = index_to_text.get(text_index)
        if text_ref is None:
            raise ValueError(
                f"ACEText hash entry 0x{hash_value:08X} references missing text index {text_index}."
            )

        values: dict[str, str] = {}
        value_code_units: dict[str, list[int]] = {}
        for language_slot, text_offset in enumerate(text_ref.text_offsets):
            language_name = languages_by_index.get(language_slot, "")
            if not language_name:
                if language_slot < len(fallback_language_names):
                    language_name = fallback_language_names[language_slot]
                else:
                    language_name = f"lang_{language_slot}"
            code_units = _read_utf16be_code_units(data, text_offset)
            value_code_units[language_name] = code_units
            values[language_name] = _decode_utf16be_code_units_for_view(code_units)

        entries.append(
            ACETextEntry(
                hash_value=hash_value,
                hash_label=hash_label,
                hash_label_offset=label_offset,
                text_index=text_index,
                text_label=text_ref.label,
                text_label_offset=text_ref.label_offset,
                text_offsets=list(text_ref.text_offsets),
                values=values,
                value_code_units=value_code_units,
            )
        )

    return ACETextContainer(
        source_file=str(source_path),
        header=header,
        languages=languages,
        texts=texts,
        hashes=hashes,
        entries=entries,
    )
