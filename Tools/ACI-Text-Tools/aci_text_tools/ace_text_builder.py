from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re

from .ace_text_parser import ACETextContainer, _read_utf16be_code_units, build_ace_text_export_entries, parse_ace_text


ACE_TEXT_MAGIC = b"ACT\x00"
ACE_TEXT_HEADER_SIZE = 0x24
ACT_HASH_META_SIZE = 0x0C
PLACEHOLDER_PATTERN = re.compile(r"\[\[U\+([0-9A-Fa-f]{1,6})\]\]")


@dataclass(frozen=True)
class ACETextJsonImport:
    source_file: str
    values_by_hash: dict[int, dict[str, list[int]]]


def _iter_utf16_code_unit_tokens_from_text(text: str) -> list[tuple[int, ...]]:
    tokens: list[tuple[int, ...]] = []
    cursor = 0
    for match in PLACEHOLDER_PATTERN.finditer(text):
        if match.start() > cursor:
            tokens.extend(_encode_python_text_to_utf16_tokens(text[cursor:match.start()]))
        value = int(match.group(1), 16)
        if value < 0 or value > 0x10FFFF:
            raise ValueError(f"Placeholder [[U+{match.group(1)}]] is outside the Unicode range.")
        if value <= 0xFFFF:
            tokens.append((value,))
        else:
            tokens.extend(_encode_python_text_to_utf16_tokens(chr(value)))
        cursor = match.end()
    if cursor < len(text):
        tokens.extend(_encode_python_text_to_utf16_tokens(text[cursor:]))
    return tokens


def _code_units_from_text(text: str) -> list[int]:
    code_units: list[int] = []
    for token in _iter_utf16_code_unit_tokens_from_text(text):
        code_units.extend(token)
    return code_units


def _encode_python_text_to_utf16_tokens(text: str) -> list[tuple[int, ...]]:
    tokens: list[tuple[int, ...]] = []
    for char in text:
        code_point = ord(char)
        if code_point <= 0xFFFF:
            tokens.append((code_point,))
            continue
        encoded = char.encode("utf-16-be")
        token: list[int] = []
        for index in range(0, len(encoded), 2):
            token.append(int.from_bytes(encoded[index : index + 2], "big", signed=False))
        tokens.append(tuple(token))
    return tokens


def _encode_code_units_to_utf16be_bytes(code_units: list[int]) -> bytes:
    encoded = bytearray()
    for code_unit in code_units:
        if code_unit < 0 or code_unit > 0xFFFF:
            raise ValueError(f"ACEText code unit U+{code_unit:X} is outside the UTF-16 range.")
        encoded.extend(code_unit.to_bytes(2, "big", signed=False))
    return bytes(encoded)


def _load_paratranz_payload(path: str | Path) -> list[dict]:
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ACEText ParaTranz charset export expects an array of objects.")
    return payload


def _build_paratranz_translation_charset_code_units_for_keys(
    payload: list[dict],
    valid_keys: set[str],
) -> list[int]:
    seen_tokens: set[tuple[int, ...]] = set()
    charset_code_units: list[int] = []
    for item_index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} must be an object.")
        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} is missing a string key.")
        if key not in valid_keys:
            continue
        translation = item.get("translation", "")
        if not isinstance(translation, str):
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} has a non-string translation field.")
        if not translation:
            continue
        for token in _iter_utf16_code_unit_tokens_from_text(translation):
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
            charset_code_units.extend(token)
    return charset_code_units


def _build_charset_code_units_from_import(imported: ACETextJsonImport) -> list[int]:
    seen_code_units: set[int] = set()
    charset_code_units: list[int] = []
    for values_by_language in imported.values_by_hash.values():
        for code_units in values_by_language.values():
            _append_code_units_deduplicated(charset_code_units, seen_code_units, code_units)
    return charset_code_units


def _append_code_units_deduplicated(
    charset_code_units: list[int],
    seen_code_units: set[int],
    code_units: Iterable[int],
) -> None:
    for code_unit in code_units:
        if code_unit in seen_code_units:
            continue
        seen_code_units.add(code_unit)
        charset_code_units.append(code_unit)


def build_paratranz_translation_charset_code_units(
    template: ACETextContainer | str | Path,
    path: str | Path,
) -> list[int]:
    template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
    payload = _load_paratranz_payload(path)
    valid_keys = {key for key, _entry in build_ace_text_export_entries(template_container)}
    return _build_paratranz_translation_charset_code_units_for_keys(payload, valid_keys)


def build_paratranz_translation_charset_code_units_for_templates(
    templates: Iterable[ACETextContainer | str | Path],
    path: str | Path,
) -> list[int]:
    payload = _load_paratranz_payload(path)
    valid_keys: set[str] = set()
    for template in templates:
        template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
        valid_keys.update(key for key, _entry in build_ace_text_export_entries(template_container))
    return _build_paratranz_translation_charset_code_units_for_keys(payload, valid_keys)


def build_applied_paratranz_translation_charset_code_units(
    template: ACETextContainer | str | Path,
    path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> list[int]:
    template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
    imported = load_ace_text_paratranz_import(
        template_container,
        path,
        target_language=target_language,
        fallback_language=fallback_language,
    )
    return _build_charset_code_units_from_import(imported)


def build_applied_paratranz_translation_charset_code_units_for_templates(
    templates: Iterable[ACETextContainer | str | Path],
    path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> list[int]:
    seen_code_units: set[int] = set()
    charset_code_units: list[int] = []
    for template in templates:
        template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
        imported = load_ace_text_paratranz_import(
            template_container,
            path,
            target_language=target_language,
            fallback_language=fallback_language,
        )
        _append_code_units_deduplicated(
            charset_code_units,
            seen_code_units,
            _build_charset_code_units_from_import(imported),
        )
    return charset_code_units


def build_applied_paratranz_translation_charset_code_units_partitioned(
    template: ACETextContainer | str | Path,
    path: str | Path,
    include_key_filters: Iterable[str],
    target_language: str = "US",
    fallback_language: str | None = None,
) -> tuple[list[int], list[int]]:
    template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
    filters = [pattern.strip() for pattern in include_key_filters if isinstance(pattern, str) and pattern.strip()]
    if not filters:
        return (
            build_applied_paratranz_translation_charset_code_units(
                template_container,
                path,
                target_language=target_language,
                fallback_language=fallback_language,
            ),
            [],
        )

    payload = _load_paratranz_payload(path)
    entry_by_key = {key: entry for key, entry in build_ace_text_export_entries(template_container)}
    unique_seen: set[int] = set()
    total_seen: set[int] = set()
    unique_code_units: list[int] = []
    total_code_units: list[int] = []

    for item_index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} must be an object.")

        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} is missing a string key.")

        entry = entry_by_key.get(key)
        if entry is None:
            continue

        translation = item.get("translation", "")
        if not isinstance(translation, str):
            raise ValueError(f"ACEText ParaTranz entry {key!r} has a non-string translation field.")

        code_units: list[int] | None = None
        if translation:
            code_units = _code_units_from_text(translation)
        elif isinstance(fallback_language, str) and fallback_language:
            fallback_code_units = entry.value_code_units.get(fallback_language, [])
            if fallback_code_units:
                code_units = list(fallback_code_units)
        if code_units is None:
            continue

        if any(fnmatchcase(key, pattern) for pattern in filters):
            _append_code_units_deduplicated(unique_code_units, unique_seen, code_units)
        else:
            _append_code_units_deduplicated(total_code_units, total_seen, code_units)

    return unique_code_units, total_code_units


def export_paratranz_translation_charset(
    template: ACETextContainer | str | Path,
    path: str | Path,
    output_path: str | Path,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        b"\xFE\xFF"
        + _encode_code_units_to_utf16be_bytes(build_paratranz_translation_charset_code_units(template, path))
    )
    return destination


def export_paratranz_translation_charset_for_templates(
    templates: Iterable[ACETextContainer | str | Path],
    path: str | Path,
    output_path: str | Path,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        b"\xFE\xFF"
        + _encode_code_units_to_utf16be_bytes(
            build_paratranz_translation_charset_code_units_for_templates(templates, path)
        )
    )
    return destination


def export_applied_paratranz_translation_charset(
    template: ACETextContainer | str | Path,
    path: str | Path,
    output_path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        b"\xFE\xFF"
        + _encode_code_units_to_utf16be_bytes(
            build_applied_paratranz_translation_charset_code_units(
                template,
                path,
                target_language=target_language,
                fallback_language=fallback_language,
            )
        )
    )
    return destination


def export_applied_paratranz_translation_charset_for_templates(
    templates: Iterable[ACETextContainer | str | Path],
    path: str | Path,
    output_path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        b"\xFE\xFF"
        + _encode_code_units_to_utf16be_bytes(
            build_applied_paratranz_translation_charset_code_units_for_templates(
                templates,
                path,
                target_language=target_language,
                fallback_language=fallback_language,
            )
        )
    )
    return destination


def export_utf16be_charset_code_units(code_units: Iterable[int], output_path: str | Path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"\xFE\xFF" + _encode_code_units_to_utf16be_bytes(list(code_units)))
    return destination


def build_default_paratranz_translation_charset_path(paratranz_json_path: str | Path) -> Path:
    json_path = Path(paratranz_json_path)
    return json_path.with_name(f"{json_path.stem}.charset.txt")


def load_ace_text_json_import(path: str | Path) -> ACETextJsonImport:
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ACEText JSON import expects an object keyed by exported entry name.")

    values_by_hash: dict[int, dict[str, list[int]]] = {}
    for object_name, object_payload in payload.items():
        if not isinstance(object_payload, dict):
            raise ValueError(f"ACEText JSON entry {object_name!r} must be an object.")

        hash_value_raw = object_payload.get("Hash")
        if not isinstance(hash_value_raw, str):
            raise ValueError(f"ACEText JSON entry {object_name!r} is missing a string Hash field.")
        try:
            hash_value = int(hash_value_raw, 16)
        except ValueError as exc:
            raise ValueError(f"ACEText JSON entry {object_name!r} has invalid Hash {hash_value_raw!r}.") from exc

        values_payload = object_payload.get("Values")
        if not isinstance(values_payload, dict):
            raise ValueError(f"ACEText JSON entry {object_name!r} is missing a Values object.")

        imported_values: dict[str, list[int]] = {}
        for language_name, value in values_payload.items():
            if not isinstance(language_name, str):
                raise ValueError(f"ACEText JSON entry {object_name!r} has a non-string language key.")
            if not isinstance(value, str):
                raise ValueError(
                    f"ACEText JSON entry {object_name!r} language {language_name!r} must be a string."
                )
            imported_values[language_name] = _code_units_from_text(value)

        previous = values_by_hash.get(hash_value)
        if previous is not None and previous != imported_values:
            raise ValueError(f"ACEText JSON contains conflicting duplicate Hash values for 0x{hash_value:08X}.")
        values_by_hash[hash_value] = imported_values

    return ACETextJsonImport(source_file=str(source_path), values_by_hash=values_by_hash)


def load_ace_text_paratranz_import(
    template: ACETextContainer,
    path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> ACETextJsonImport:
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ACEText ParaTranz import expects an array of objects.")

    entry_by_key = {key: entry for key, entry in build_ace_text_export_entries(template)}
    values_by_hash: dict[int, dict[str, list[int]]] = {}

    for item_index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} must be an object.")

        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"ACEText ParaTranz entry at index {item_index} is missing a string key.")

        entry = entry_by_key.get(key)
        if entry is None:
            continue

        translation = item.get("translation", "")
        if not isinstance(translation, str):
            raise ValueError(f"ACEText ParaTranz entry {key!r} has a non-string translation field.")
        code_units: list[int] | None = None
        if translation:
            code_units = _code_units_from_text(translation)
        elif isinstance(fallback_language, str) and fallback_language:
            fallback_code_units = entry.value_code_units.get(fallback_language, [])
            if fallback_code_units:
                code_units = list(fallback_code_units)
        if code_units is None:
            continue

        imported_values = {target_language: code_units}
        previous = values_by_hash.get(entry.hash_value)
        if previous is not None and previous != imported_values:
            raise ValueError(f"ACEText ParaTranz contains conflicting duplicate keys for hash 0x{entry.hash_value:08X}.")
        values_by_hash[entry.hash_value] = imported_values

    return ACETextJsonImport(source_file=str(source_path), values_by_hash=values_by_hash)


def build_ace_text_from_json(
    template: ACETextContainer | str | Path,
    json_path: str | Path,
    output_path: str | Path,
) -> Path:
    template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
    imported = load_ace_text_json_import(json_path)
    rebuilt_bytes = build_ace_text_binary(template_container, imported)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rebuilt_bytes)

    _validate_rebuilt_ace_text(destination, template_container, imported)
    return destination


def build_ace_text_from_paratranz_json(
    template: ACETextContainer | str | Path,
    json_path: str | Path,
    output_path: str | Path,
    target_language: str = "US",
    fallback_language: str | None = None,
) -> Path:
    template_container = template if isinstance(template, ACETextContainer) else parse_ace_text(template)
    imported = load_ace_text_paratranz_import(
        template_container,
        json_path,
        target_language=target_language,
        fallback_language=fallback_language,
    )
    rebuilt_bytes = build_ace_text_binary(template_container, imported)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rebuilt_bytes)

    _validate_rebuilt_ace_text(destination, template_container, imported)
    return destination


def build_ace_text_binary(template: ACETextContainer, imported: ACETextJsonImport) -> bytes:
    language_names = [language.name for language in template.languages]
    template_entries_by_hash = {entry.hash_value: entry for entry in template.entries}
    unknown_hashes = sorted(set(imported.values_by_hash) - set(template_entries_by_hash))
    if unknown_hashes:
        preview = ", ".join(f"0x{hash_value:08X}" for hash_value in unknown_hashes[:8])
        if len(unknown_hashes) > 8:
            preview += f", ... ({len(unknown_hashes)} total)"
        raise ValueError(f"ACEText JSON contains hashes not present in the template: {preview}")

    text_values_by_index = _read_template_text_values(template)
    override_owners: dict[tuple[int, str], int] = {}

    for hash_value, imported_values in imported.values_by_hash.items():
        entry = template_entries_by_hash[hash_value]
        text_values = text_values_by_index[entry.text_index]
        for language_name, code_units in imported_values.items():
            if language_name not in language_names:
                raise ValueError(
                    f"ACEText JSON entry 0x{hash_value:08X} uses language {language_name!r}, "
                    "which is not present in the template language table."
                )
            owner_key = (entry.text_index, language_name)
            previous_owner = override_owners.get(owner_key)
            previous_value = text_values.get(language_name, [])
            if previous_owner is not None and previous_owner != hash_value and previous_value != code_units:
                raise ValueError(
                    "ACEText JSON contains conflicting values for "
                    f"text index {entry.text_index} language {language_name!r} "
                    f"via hashes 0x{previous_owner:08X} and 0x{hash_value:08X}."
                )
            text_values[language_name] = list(code_units)
            override_owners[owner_key] = hash_value

    language_count = len(template.languages)
    text_count = len(template.texts)
    hash_count = len(template.entries)
    text_ref_size = 4 + 4 * language_count
    language_table_offset = ACE_TEXT_HEADER_SIZE
    text_table_offset = language_table_offset + language_count * 4
    text_ref_block_offset = text_table_offset + text_count * 4
    hash_table_offset = text_ref_block_offset + text_count * text_ref_size
    string_pool_offset = hash_table_offset + hash_count * ACT_HASH_META_SIZE

    string_pool = bytearray()
    cp932_offsets: dict[bytes, int] = {}
    utf16_offsets: dict[bytes, int] = {}

    def intern_bytes(pool: dict[bytes, int], data: bytes) -> int:
        offset = pool.get(data)
        if offset is not None:
            return offset
        offset = string_pool_offset + len(string_pool)
        pool[data] = offset
        string_pool.extend(data)
        return offset

    def intern_cp932(text: str) -> int:
        return intern_bytes(cp932_offsets, text.encode("cp932") + b"\x00")

    def intern_utf16(code_units: list[int]) -> int:
        encoded = bytearray()
        for code_unit in code_units:
            if code_unit < 0 or code_unit > 0xFFFF:
                raise ValueError(f"ACEText code unit U+{code_unit:X} is outside the UTF-16 range.")
            encoded.extend(code_unit.to_bytes(2, "big", signed=False))
        encoded.extend(b"\x00\x00")
        return intern_bytes(utf16_offsets, bytes(encoded))

    text_label_offsets = [intern_cp932(text.label) for text in template.texts]
    hash_label_offsets = [intern_cp932(entry.hash_label) for entry in template.entries]
    text_value_offsets: list[list[int]] = []
    for text in template.texts:
        text_values = text_values_by_index[text.text_index]
        offsets: list[int] = []
        for language_name in language_names:
            offsets.append(intern_utf16(text_values.get(language_name, [])))
        text_value_offsets.append(offsets)

    output = bytearray()
    output.extend(ACE_TEXT_MAGIC)
    output.extend(template.header.version.to_bytes(4, "big", signed=False))
    output.extend(template.header.data_version.to_bytes(4, "big", signed=False))
    output.append(1 if template.header.is_big_endian else 0)
    output.append(language_count & 0xFF)
    output.extend(b"\x00\x00")
    output.extend(text_count.to_bytes(4, "big", signed=True))
    output.extend(hash_count.to_bytes(4, "big", signed=True))
    output.extend(language_table_offset.to_bytes(4, "big", signed=True))
    output.extend(text_table_offset.to_bytes(4, "big", signed=True))
    output.extend(hash_table_offset.to_bytes(4, "big", signed=True))

    if len(output) != ACE_TEXT_HEADER_SIZE:
        raise ValueError(f"Internal ACEText header size mismatch: expected 0x{ACE_TEXT_HEADER_SIZE:X}, got 0x{len(output):X}.")

    for language in template.languages:
        encoded_name = language.name.encode("ascii")
        if len(encoded_name) > 3:
            raise ValueError(f"Template language name {language.name!r} exceeds the 3-byte ACT limit.")
        output.extend(encoded_name.ljust(3, b"\x00"))
        output.append(language.index & 0xFF)

    for text_index in range(text_count):
        text_ref_offset = text_ref_block_offset + text_index * text_ref_size
        output.extend(text_ref_offset.to_bytes(4, "big", signed=True))

    for text_index, text in enumerate(template.texts):
        del text
        output.extend(text_label_offsets[text_index].to_bytes(4, "big", signed=True))
        for value_offset in text_value_offsets[text_index]:
            output.extend(value_offset.to_bytes(4, "big", signed=True))

    for entry_index, entry in enumerate(template.entries):
        output.extend(entry.hash_value.to_bytes(4, "big", signed=False))
        output.extend(hash_label_offsets[entry_index].to_bytes(4, "big", signed=True))
        output.extend(entry.text_index.to_bytes(4, "big", signed=True))

    output.extend(string_pool)
    return bytes(output)


def _read_template_text_values(template: ACETextContainer) -> dict[int, dict[str, list[int]]]:
    data = Path(template.source_file).read_bytes()
    values_by_index: dict[int, dict[str, list[int]]] = {}
    language_names = [language.name for language in template.languages]
    for text in template.texts:
        values_by_language: dict[str, list[int]] = {}
        for language_slot, text_offset in enumerate(text.text_offsets):
            language_name = language_names[language_slot] if language_slot < len(language_names) else f"lang_{language_slot}"
            values_by_language[language_name] = _read_utf16be_code_units(data, text_offset)
        values_by_index[text.text_index] = values_by_language
    return values_by_index


def _validate_rebuilt_ace_text(
    rebuilt_path: Path,
    template: ACETextContainer,
    imported: ACETextJsonImport,
) -> None:
    rebuilt = parse_ace_text(rebuilt_path)

    if template.header.version != rebuilt.header.version or template.header.data_version != rebuilt.header.data_version:
        raise ValueError("Rebuilt ACEText header version fields do not match the template.")
    if [(language.name, language.index) for language in template.languages] != [
        (language.name, language.index) for language in rebuilt.languages
    ]:
        raise ValueError("Rebuilt ACEText language table does not match the template.")
    if len(template.texts) != len(rebuilt.texts) or len(template.entries) != len(rebuilt.entries):
        raise ValueError("Rebuilt ACEText entry counts do not match the template.")

    expected_text_values = _read_template_text_values(template)
    template_entries_by_hash = {entry.hash_value: entry for entry in template.entries}
    for hash_value, imported_values in imported.values_by_hash.items():
        entry = template_entries_by_hash[hash_value]
        text_values = expected_text_values[entry.text_index]
        for language_name, code_units in imported_values.items():
            text_values[language_name] = list(code_units)

    rebuilt_entries_by_hash = {entry.hash_value: entry for entry in rebuilt.entries}
    for template_entry in template.entries:
        rebuilt_entry = rebuilt_entries_by_hash.get(template_entry.hash_value)
        if rebuilt_entry is None:
            raise ValueError(f"Rebuilt ACEText is missing hash 0x{template_entry.hash_value:08X}.")
        if rebuilt_entry.hash_label != template_entry.hash_label:
            raise ValueError(f"Rebuilt ACEText changed hash label for 0x{template_entry.hash_value:08X}.")
        if rebuilt_entry.text_index != template_entry.text_index:
            raise ValueError(f"Rebuilt ACEText changed text index for 0x{template_entry.hash_value:08X}.")
        if rebuilt_entry.text_label != template_entry.text_label:
            raise ValueError(f"Rebuilt ACEText changed text label for 0x{template_entry.hash_value:08X}.")

        expected_values = expected_text_values[template_entry.text_index]
        for language_name, expected_code_units in expected_values.items():
            rebuilt_code_units = rebuilt_entry.value_code_units.get(language_name, [])
            if rebuilt_code_units != expected_code_units:
                raise ValueError(
                    "Rebuilt ACEText value mismatch for "
                    f"0x{template_entry.hash_value:08X} language {language_name!r}."
                )
