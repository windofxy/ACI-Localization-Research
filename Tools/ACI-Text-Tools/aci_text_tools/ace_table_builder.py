from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import re
import struct

from .ace_table_parser import (
    ACETableContainer,
    ACETableDisplayMode,
    ACETableRow,
    ACETableColumn,
    LVSTColumnType,
    infer_ace_table_stringish_display_mode,
)


@dataclass(frozen=True)
class ACETableEditValidationItem:
    row_index: int
    hash_id: int
    hash_name: str
    type_name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class ACETableEditValidationResult:
    items: list[ACETableEditValidationItem]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.items)

    @property
    def valid_count(self) -> int:
        return sum(1 for item in self.items if item.ok)

    @property
    def invalid_count(self) -> int:
        return sum(1 for item in self.items if not item.ok)


@dataclass(frozen=True)
class ACETableBuilderSupportItem:
    signature: str
    ok: bool
    column_count: int
    example_hash_name: str
    message: str


@dataclass(frozen=True)
class ACETableBuilderSupportSummary:
    items: list[ACETableBuilderSupportItem]

    @property
    def supported_signature_count(self) -> int:
        return sum(1 for item in self.items if item.ok)

    @property
    def unsupported_signature_count(self) -> int:
        return sum(1 for item in self.items if not item.ok)

    @property
    def supported_column_count(self) -> int:
        return sum(item.column_count for item in self.items if item.ok)

    @property
    def unsupported_column_count(self) -> int:
        return sum(item.column_count for item in self.items if not item.ok)


def export_edited_ace_table(
    container: ACETableContainer,
    edits: dict[tuple[int, int], str],
    display_mode: str,
    output_path: str | Path,
) -> Path:
    validation = validate_ace_table_edits(container, edits, display_mode)
    if not validation.ok:
        first_error = next(item for item in validation.items if not item.ok)
        raise ValueError(
            f"ACETable edit validation failed for row {first_error.row_index} {first_error.hash_name}: "
            f"{first_error.message}"
        )

    source_path = Path(container.source_file)
    data = bytearray(source_path.read_bytes())

    row_by_index = {row.index: row for row in container.rows}
    column_by_hash = {column.hash_id: column for column in container.columns}

    for (row_index, hash_id), value in sorted(edits.items()):
        row = row_by_index.get(row_index)
        column = column_by_hash.get(hash_id)
        if row is None or column is None:
            continue
        payload = _encode_cell_payload(column, row, value, display_mode)
        offset = _cell_payload_offset(column, row_index)
        data[offset : offset + len(payload)] = payload

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination


def validate_ace_table_edits(
    container: ACETableContainer,
    edits: dict[tuple[int, int], str],
    display_mode: str,
) -> ACETableEditValidationResult:
    row_by_index = {row.index: row for row in container.rows}
    column_by_hash = {column.hash_id: column for column in container.columns}
    items: list[ACETableEditValidationItem] = []

    for (row_index, hash_id), value in sorted(edits.items()):
        row = row_by_index.get(row_index)
        column = column_by_hash.get(hash_id)
        if row is None:
            items.append(
                ACETableEditValidationItem(
                    row_index=row_index,
                    hash_id=hash_id,
                    hash_name=f"0x{hash_id:08X}",
                    type_name="Unknown",
                    ok=False,
                    message="Row index does not exist in the current ACETable.",
                )
            )
            continue
        if column is None:
            items.append(
                ACETableEditValidationItem(
                    row_index=row_index,
                    hash_id=hash_id,
                    hash_name=f"0x{hash_id:08X}",
                    type_name="Unknown",
                    ok=False,
                    message="Column hash does not exist in the current ACETable.",
                )
            )
            continue

        try:
            _encode_cell_payload(column, row, value, display_mode)
        except Exception as exc:
            items.append(
                ACETableEditValidationItem(
                    row_index=row_index,
                    hash_id=hash_id,
                    hash_name=column.hash_name,
                    type_name=column.type_name,
                    ok=False,
                    message=str(exc),
                )
            )
            continue

        items.append(
            ACETableEditValidationItem(
                row_index=row_index,
                hash_id=hash_id,
                hash_name=column.hash_name,
                type_name=column.type_name,
                ok=True,
                message="OK",
            )
        )

    return ACETableEditValidationResult(items)


def summarize_ace_table_builder_support(container: ACETableContainer) -> ACETableBuilderSupportSummary:
    grouped: dict[tuple[int, int, int], list[ACETableColumn]] = {}
    for column in container.columns:
        grouped.setdefault((column.column_type, column.element_size, column.element_count), []).append(column)

    items: list[ACETableBuilderSupportItem] = []
    for signature, columns in sorted(grouped.items()):
        ok, message = _is_column_signature_supported(columns[0])
        column = columns[0]
        items.append(
            ACETableBuilderSupportItem(
                signature=f"type=0x{signature[0]:02X} size={signature[1]} count={signature[2]}",
                ok=ok,
                column_count=len(columns),
                example_hash_name=column.hash_name,
                message=message,
            )
        )
    return ACETableBuilderSupportSummary(items)


def _cell_payload_offset(column: ACETableColumn, row_index: int) -> int:
    if column.row_count <= 0:
        raise ValueError(f"Column {column.hash_name} has no row storage.")
    if row_index >= column.row_count:
        row_index %= column.row_count
    payload_size = column.element_size * column.element_count
    return column.data_offset + 0x08 + payload_size * row_index


def _is_column_signature_supported(column: ACETableColumn) -> tuple[bool, str]:
    if column.column_type == LVSTColumnType.NULL:
        return True, "Supported as zero-filled payload."
    if column.column_type == LVSTColumnType.FLOAT and column.element_size == 4 and column.element_count == 1:
        return True, "Supported float scalar."
    if column.column_type == LVSTColumnType.INT and column.element_size == 4 and column.element_count == 1:
        return True, "Supported int scalar."
    if column.column_type == LVSTColumnType.HASH and column.element_size == 4 and column.element_count == 1:
        return True, "Supported hash scalar."
    if column.column_type == LVSTColumnType.DATE and column.element_size == 4 and column.element_count == 1:
        return True, "Supported date scalar."
    if column.column_type == LVSTColumnType.TIME and column.element_size == 4 and column.element_count == 1:
        return True, "Supported time scalar."
    if column.column_type in {LVSTColumnType.STRING, LVSTColumnType.BUFFER}:
        return True, "Supported string/buffer payload with display-mode-aware encoding."
    return False, "Unsupported column signature for safe in-place overwrite."


def _encode_cell_payload(
    column: ACETableColumn,
    row: ACETableRow,
    value: str,
    display_mode: str,
) -> bytes:
    payload_size = column.element_size * column.element_count

    if column.column_type == LVSTColumnType.NULL:
        return b"\x00" * payload_size

    if column.column_type == LVSTColumnType.FLOAT and column.element_size == 4 and column.element_count == 1:
        return struct.pack(">f", float(value.strip() or "0"))

    if column.column_type == LVSTColumnType.INT and column.element_size == 4 and column.element_count == 1:
        parsed = int(value.strip() or "0", 0)
        return parsed.to_bytes(4, "big", signed=True)

    if column.column_type == LVSTColumnType.HASH and column.element_size == 4 and column.element_count == 1:
        parsed = int(value.strip() or "0", 0)
        if parsed < 0 or parsed > 0xFFFFFFFF:
            raise ValueError(f"{column.hash_name} hash value is outside uint32 range: {value!r}")
        return parsed.to_bytes(4, "big", signed=False)

    if column.column_type == LVSTColumnType.DATE and column.element_size == 4 and column.element_count == 1:
        parsed = _parse_date_value(value)
        return parsed.to_bytes(4, "big", signed=False)

    if column.column_type == LVSTColumnType.TIME and column.element_size == 4 and column.element_count == 1:
        parsed = _parse_time_value(value)
        return parsed.to_bytes(4, "big", signed=False)

    if column.column_type in {LVSTColumnType.STRING, LVSTColumnType.BUFFER}:
        return _encode_stringish_payload(column, row, value, display_mode, payload_size)

    raise ValueError(
        f"Editing is not supported yet for column {column.hash_name} "
        f"({column.type_name}, {column.element_size}x{column.element_count})."
    )


def _encode_stringish_payload(
    column: ACETableColumn,
    row: ACETableRow,
    value: str,
    display_mode: str,
    payload_size: int,
) -> bytes:
    mode = display_mode
    if mode == ACETableDisplayMode.AUTO:
        mode = _infer_auto_edit_encoding_mode(column, row)

    if mode == ACETableDisplayMode.RAW_HEX:
        raw = _parse_hex_bytes(value)
        if len(raw) > payload_size:
            raise ValueError(
                f"{column.hash_name} edited hex payload is too large: {len(raw)} > {payload_size} bytes."
            )
        return raw.ljust(payload_size, b"\x00")

    if mode == ACETableDisplayMode.UTF8:
        encoded = value.encode("utf-8")
        return _fit_encoded_payload(encoded, payload_size)

    if mode == ACETableDisplayMode.UTF16BE:
        encoded = value.encode("utf-16-be")
        return _fit_encoded_payload(encoded, payload_size)

    if mode == ACETableDisplayMode.UTF32BE:
        encoded = value.encode("utf-32-be")
        return _fit_encoded_payload(encoded, payload_size)

    raise ValueError(f"Unsupported ACETable display mode for export: {display_mode!r}")


def _infer_auto_edit_encoding_mode(column: ACETableColumn, row: ACETableRow) -> str:
    return infer_ace_table_stringish_display_mode(column, row)


def _fit_encoded_payload(encoded: bytes, payload_size: int) -> bytes:
    if len(encoded) > payload_size:
        raise ValueError(
            f"Edited text payload is too large: {len(encoded)} > {payload_size} bytes."
        )
    return encoded.ljust(payload_size, b"\x00")


def _parse_hex_bytes(value: str) -> bytes:
    normalized = value.strip()
    if not normalized:
        return b""
    normalized = normalized.replace(",", " ").replace("0x", " ").replace("0X", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    try:
        return bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid hex byte string: {value!r}") from exc


def _parse_date_value(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if "-" not in text:
        parsed = int(text, 0)
        if parsed < 0 or parsed > 0xFFFFFFFF:
            raise ValueError(f"Date value is outside uint32 range: {value!r}")
        return parsed
    parsed_date = datetime.strptime(text, "%Y-%m-%d").date()
    return parsed_date.year * 10000 + parsed_date.month * 100 + parsed_date.day


def _parse_time_value(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if ":" not in text:
        parsed = int(text, 0)
        if parsed < 0 or parsed > 0xFFFFFFFF:
            raise ValueError(f"Time value is outside uint32 range: {value!r}")
        return parsed
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError(f"Time value must be seconds or HH:MM:SS: {value!r}")
    hours = int(parts[0], 10)
    minutes = int(parts[1], 10)
    seconds = int(parts[2], 10)
    if minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59 or hours < 0:
        raise ValueError(f"Invalid HH:MM:SS time value: {value!r}")
    total_seconds = hours * 3600 + minutes * 60 + seconds
    if total_seconds > 0xFFFFFFFF:
        raise ValueError(f"Time value is outside uint32 range: {value!r}")
    return total_seconds
