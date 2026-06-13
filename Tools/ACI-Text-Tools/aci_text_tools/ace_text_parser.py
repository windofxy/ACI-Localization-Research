from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import unicodedata


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

    @property
    def best_label(self) -> str:
        if self.hash_label:
            return self.hash_label
        if self.text_label:
            return self.text_label
        return f"[0x{self.hash_value:08X}]"


@dataclass(frozen=True)
class ACETextContainer:
    source_file: str
    header: ACETextHeader
    languages: list[ACETextLanguage]
    texts: list[ACETextTextRef]
    hashes: list[ACETextHashMeta]
    entries: list[ACETextEntry]


def build_ace_text_export_entries(container: ACETextContainer) -> list[tuple[str, ACETextEntry]]:
    used_keys: set[str] = set()
    return [(_entry_json_key(entry, used_keys), entry) for entry in container.entries]


def _entry_json_key(entry: ACETextEntry, used_keys: set[str]) -> str:
    preferred = entry.hash_label or f"[0x{entry.hash_value:08X}]"
    if preferred not in used_keys:
        used_keys.add(preferred)
        return preferred

    duplicate_index = 2
    while True:
        candidate = f"{preferred}#{duplicate_index}"
        if candidate not in used_keys:
            used_keys.add(candidate)
            return candidate
        duplicate_index += 1


def build_ulysses_ace_text_json_object(container: ACETextContainer) -> dict[str, object]:
    result: dict[str, object] = {}
    used_keys: set[str] = set()
    for entry in container.entries:
        key = _entry_json_key(entry, used_keys)
        result[key] = {
            "Hash": f"0x{entry.hash_value:08x}",
            "Label": entry.text_label,
            "Values": dict(entry.values),
        }
    return result


def _should_escape_code_unit(code_unit: int) -> bool:
    if code_unit in {0x0009, 0x000A, 0x000D, 0x0085, 0x2028, 0x2029}:
        return True
    if 0xD800 <= code_unit <= 0xDFFF:
        return True
    if 0xE000 <= code_unit <= 0xF8FF:
        return True
    char = chr(code_unit)
    if unicodedata.category(char).startswith("C"):
        return True
    return False


def _json_string_from_code_units(code_units: list[int]) -> str:
    parts: list[str] = ['"']
    for code_unit in code_units:
        if _should_escape_code_unit(code_unit):
            parts.append(f"[[U+{code_unit:04X}]]")
            continue
        parts.append(json.dumps(chr(code_unit), ensure_ascii=False)[1:-1])
    parts.append('"')
    return "".join(parts)


def _paratranz_json_string_from_code_units(code_units: list[int]) -> str:
    return _json_string_from_code_units(code_units)


def build_ulysses_ace_text_json_text(container: ACETextContainer) -> str:
    used_keys: set[str] = set()
    lines: list[str] = ["{"]
    for entry_index, entry in enumerate(container.entries):
        key = _entry_json_key(entry, used_keys)
        lines.append(f"  {json.dumps(key, ensure_ascii=False)}: {{")
        lines.append(f'    "Hash": {json.dumps(f"0x{entry.hash_value:08x}")},')
        lines.append(f'    "Label": {json.dumps(entry.text_label, ensure_ascii=False)},')
        lines.append('    "Values": {')
        language_items = list(entry.values.items())
        for language_index, (language, value) in enumerate(language_items):
            del value
            suffix = "," if language_index < len(language_items) - 1 else ""
            lines.append(
                f"      {json.dumps(language, ensure_ascii=False)}: "
                f"{_json_string_from_code_units(entry.value_code_units.get(language, []))}{suffix}"
            )
        lines.append("    }")
        lines.append(f"  }}{',' if entry_index < len(container.entries) - 1 else ''}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_paratranz_ace_text_json_text(container: ACETextContainer) -> str:
    lines: list[str] = ["["]
    export_entries = build_ace_text_export_entries(container)
    for entry_index, (key, entry) in enumerate(export_entries):
        original_units = entry.value_code_units.get("US", [])
        context_units = entry.value_code_units.get("JP", [])
        lines.append("  {")
        lines.append(f'    "key": {json.dumps(key, ensure_ascii=False)},')
        lines.append(f'    "original": {_paratranz_json_string_from_code_units(original_units)},')
        lines.append('    "translation": "",')
        lines.append(f'    "context": {_paratranz_json_string_from_code_units(context_units)}')
        lines.append(f"  }}{',' if entry_index < len(export_entries) - 1 else ''}")
    lines.append("]")
    return "\n".join(lines) + "\n"


def _merge_code_unit_values(
    existing: dict[str, list[int]],
    incoming: dict[str, list[int]],
) -> dict[str, list[int]]:
    merged: dict[str, list[int]] = {language: list(code_units) for language, code_units in existing.items()}
    for language, code_units in incoming.items():
        current = merged.get(language)
        if current is None or not current:
            merged[language] = list(code_units)
    return merged


def _build_merged_total_entries(
    export_entries: list[tuple[str, ACETextEntry]],
) -> list[tuple[str, str, str, dict[str, list[int]]]]:
    sorted_entries = sorted(
        export_entries,
        key=lambda item: (item[0].lower(), item[1].hash_value, item[1].text_index),
    )

    merged_entries: dict[str, dict[str, object]] = {}
    for key, entry in sorted_entries:
        entry_hash = f"0x{entry.hash_value:08x}"
        entry_values = {language: list(code_units) for language, code_units in entry.value_code_units.items()}
        merged = merged_entries.get(key)
        if merged is None:
            merged_entries[key] = {
                "Hash": entry_hash,
                "Label": entry.text_label,
                "Values": entry_values,
            }
            continue

        if not merged["Label"] and entry.text_label:
            merged["Label"] = entry.text_label
        merged["Values"] = _merge_code_unit_values(
            merged["Values"],  # type: ignore[arg-type]
            entry_values,
        )

    return [
        (
            key,
            merged["Hash"],  # type: ignore[index]
            merged["Label"],  # type: ignore[index]
            merged["Values"],  # type: ignore[index]
        )
        for key, merged in merged_entries.items()
    ]


def build_ulysses_ace_text_total_json_object(
    export_entries: list[tuple[str, ACETextEntry]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for key, entry_hash, label, values in _build_merged_total_entries(export_entries):
        result[key] = {
            "Hash": entry_hash,
            "Label": label,
            "Values": {language: list(code_units) for language, code_units in values.items()},
        }
    return result


def build_ulysses_ace_text_total_json_text(export_entries: list[tuple[str, ACETextEntry]]) -> str:
    merged_object = build_ulysses_ace_text_total_json_object(export_entries)
    lines: list[str] = ["{"]
    merged_items = list(merged_object.items())
    for entry_index, (key, payload) in enumerate(merged_items):
        entry_hash = payload["Hash"]
        label = payload["Label"]
        values = payload["Values"]
        lines.append(f"  {json.dumps(key, ensure_ascii=False)}: {{")
        lines.append(f'    "Hash": {json.dumps(entry_hash)},')
        lines.append(f'    "Label": {json.dumps(label, ensure_ascii=False)},')
        lines.append('    "Values": {')
        language_items = list(values.items())  # type: ignore[union-attr]
        for language_index, (language, code_units) in enumerate(language_items):
            suffix = "," if language_index < len(language_items) - 1 else ""
            lines.append(
                f"      {json.dumps(language, ensure_ascii=False)}: "
                f"{_json_string_from_code_units(code_units)}{suffix}"
            )
        lines.append("    }")
        lines.append(f"  }}{',' if entry_index < len(merged_items) - 1 else ''}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_paratranz_ace_text_total_json_text(export_entries: list[tuple[str, ACETextEntry]]) -> str:
    merged_object = build_ulysses_ace_text_total_json_object(export_entries)
    lines: list[str] = ["["]
    merged_items = list(merged_object.items())
    for entry_index, (key, payload) in enumerate(merged_items):
        values = payload["Values"]
        original_units = values.get("US", [])  # type: ignore[union-attr]
        context_units = values.get("JP", [])  # type: ignore[union-attr]
        lines.append("  {")
        lines.append(f'    "key": {json.dumps(key, ensure_ascii=False)},')
        lines.append(f'    "original": {_paratranz_json_string_from_code_units(original_units)},')
        lines.append('    "translation": "",')
        lines.append(f'    "context": {_paratranz_json_string_from_code_units(context_units)}')
        lines.append(f"  }}{',' if entry_index < len(merged_items) - 1 else ''}")
    lines.append("]")
    return "\n".join(lines) + "\n"


def export_ace_text_json(container: ACETextContainer, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_ulysses_ace_text_json_text(container), encoding="utf-8")
    return output_path


def export_ace_text_paratranz_json(container: ACETextContainer, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_paratranz_ace_text_json_text(container), encoding="utf-8")
    return output_path


def export_ace_text_total_json(export_entries: list[tuple[str, ACETextEntry]], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_ulysses_ace_text_total_json_text(export_entries), encoding="utf-8")
    return output_path


def export_ace_text_total_paratranz_json(export_entries: list[tuple[str, ACETextEntry]], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_paratranz_ace_text_total_json_text(export_entries), encoding="utf-8")
    return output_path


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
