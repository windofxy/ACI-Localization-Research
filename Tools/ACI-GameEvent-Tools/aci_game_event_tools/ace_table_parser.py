from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import struct


LVST_HEADER_SIZE = 0x10
LVST_COLUMN_INFO_SIZE = 0x08


class LVSTColumnType:
    NONE = 0x00
    STRING = 0x10
    BUFFER = 0x14
    FLOAT = 0x30
    INT = 0x40
    HASH = 0x41
    DATE = 0x91
    TIME = 0x92
    NULL = 0xFF


@dataclass(frozen=True)
class ACETableHeader:
    magic: bytes
    version: int
    reserved_1: int
    reserved_2: int


@dataclass(frozen=True)
class ACETableColumn:
    index: int
    hash_id: int
    data_offset: int
    column_type: int
    element_size: int
    element_count: int
    reserved: int
    row_count: int

    @property
    def hash_name(self) -> str:
        return f"0x{self.hash_id:08X}"

    @property
    def type_name(self) -> str:
        return _column_type_name(self.column_type)


@dataclass(frozen=True)
class ACETableRow:
    index: int
    values: dict[int, object | None]
    raw_values: dict[int, bytes]


@dataclass(frozen=True)
class ACETableContainer:
    source_file: str
    header: ACETableHeader
    columns: list[ACETableColumn]
    rows: list[ACETableRow]


def encode_date_text(date_text: str) -> int:
    if not date_text:
        return 0
    year_text, month_text, day_text = date_text.split("-", 2)
    encoded = int(year_text) * 10000 + int(month_text) * 100 + int(day_text)
    _decode_date(encoded)
    return encoded


def encode_time_text(time_text: str) -> int:
    if not time_text:
        return 0
    hour_text, minute_text, second_text = time_text.split(":", 2)
    encoded = int(hour_text) * 10000 + int(minute_text) * 100 + int(second_text)
    decoded = _decode_time(encoded)
    if decoded.startswith("invalid") or "day" in decoded:
        raise ValueError(f"Invalid time text: {time_text!r}")
    return encoded


def _be32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Offset 0x{offset:X} is outside the ACETable buffer.")
    return int.from_bytes(data[offset : offset + 4], "big", signed=True)


def _be32u(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Offset 0x{offset:X} is outside the ACETable buffer.")
    return int.from_bytes(data[offset : offset + 4], "big", signed=False)


def _column_type_name(column_type: int) -> str:
    return {
        LVSTColumnType.NONE: "None",
        LVSTColumnType.STRING: "String",
        LVSTColumnType.BUFFER: "Buffer",
        LVSTColumnType.FLOAT: "Float",
        LVSTColumnType.INT: "Int",
        LVSTColumnType.HASH: "Hash",
        LVSTColumnType.DATE: "Date",
        LVSTColumnType.TIME: "Time",
        LVSTColumnType.NULL: "Null",
    }.get(column_type, f"Unknown(0x{column_type:02X})")


def _decode_zero_terminated(raw: bytes, encoding: str, unit_size: int) -> str:
    end = len(raw)
    cursor = 0
    terminator = b"\x00" * unit_size
    while cursor + unit_size <= len(raw):
        if raw[cursor : cursor + unit_size] == terminator:
            end = cursor
            break
        cursor += unit_size
    return raw[:end].decode(encoding, errors="replace")


def _decode_date(value: int) -> str:
    if value == 0:
        return ""
    year = value // 10000
    month = (value // 100) % 100
    day = value % 100
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return f"invalid-date(0x{value:08X})"


def _decode_time(value: int) -> str:
    if value == 0:
        return ""
    hours = value // 10000
    minutes = (value // 100) % 100
    seconds = value % 100
    if 0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return str(timedelta(seconds=value))


def _read_cell_bytes(data: bytes, column: ACETableColumn, row_index: int) -> bytes:
    if column.row_count <= 0:
        return b""
    if row_index >= column.row_count:
        row_index %= column.row_count

    payload_size = column.element_size * column.element_count
    payload_offset = _cell_payload_offset(column, row_index)
    if payload_offset < 0 or payload_offset + payload_size > len(data):
        raise ValueError(
            f"Cell payload for column {column.index} row {row_index} exceeds the ACETable buffer."
        )
    return data[payload_offset : payload_offset + payload_size]


def _cell_payload_offset(column: ACETableColumn, row_index: int) -> int:
    payload_size = column.element_size * column.element_count
    return column.data_offset + LVST_COLUMN_INFO_SIZE + payload_size * row_index


def _read_cell_value(data: bytes, column: ACETableColumn, row_index: int) -> object | None:
    raw = _read_cell_bytes(data, column, row_index)
    if not raw:
        return None

    if column.column_type == LVSTColumnType.NULL:
        return None
    if column.column_type == LVSTColumnType.STRING and column.element_size == 1:
        return _decode_zero_terminated(raw, "utf-8", 1)
    if column.column_type == LVSTColumnType.STRING and column.element_size == 2:
        return _decode_zero_terminated(raw, "utf-16-be", 2)
    if column.column_type == LVSTColumnType.STRING and column.element_size == 4:
        return _decode_zero_terminated(raw, "utf-32-be", 4)
    if column.column_type == LVSTColumnType.BUFFER and column.element_size == 1:
        return _decode_zero_terminated(raw, "utf-8", 1)
    if column.column_type == LVSTColumnType.FLOAT and column.element_size == 4 and column.element_count == 1:
        return struct.unpack(">f", raw)[0]
    if column.column_type == LVSTColumnType.INT and column.element_size == 4 and column.element_count == 1:
        return int.from_bytes(raw, "big", signed=True)
    if column.column_type == LVSTColumnType.HASH and column.element_size == 4 and column.element_count == 1:
        return f"0x{int.from_bytes(raw, 'big', signed=False):08X}"
    if column.column_type == LVSTColumnType.DATE and column.element_size == 4 and column.element_count == 1:
        return _decode_date(int.from_bytes(raw, "big", signed=False))
    if column.column_type == LVSTColumnType.TIME and column.element_size == 4 and column.element_count == 1:
        return _decode_time(int.from_bytes(raw, "big", signed=False))
    return raw.hex()


def parse_ace_table(path: str | Path) -> ACETableContainer:
    source_path = Path(path)
    data = source_path.read_bytes()
    if len(data) < LVST_HEADER_SIZE:
        raise ValueError(f"{source_path.name} is too small to be a valid ACETable file.")

    header = ACETableHeader(
        magic=data[0:4],
        version=_be32u(data, 0x04),
        reserved_1=_be32u(data, 0x08),
        reserved_2=_be32u(data, 0x0C),
    )
    if header.magic != b"LVST":
        raise ValueError(
            f"{source_path.name} does not start with LVST magic. Found {header.magic!r} instead."
        )

    id_byte_size = _be32(data, 0x10)
    if id_byte_size < 0 or id_byte_size % 4 != 0:
        raise ValueError(f"Invalid ACETable column-id byte size: {id_byte_size}.")
    column_count = id_byte_size // 4

    column_ids_offset = 0x14
    offset_size_offset = column_ids_offset + id_byte_size
    offset_byte_size = _be32(data, offset_size_offset)
    if offset_byte_size != id_byte_size:
        raise ValueError(
            f"Mismatched ACETable sizes: id byte size={id_byte_size}, offset byte size={offset_byte_size}."
        )
    column_offsets_offset = offset_size_offset + 4

    columns: list[ACETableColumn] = []
    max_row_count = 0
    for column_index in range(column_count):
        hash_id = _be32u(data, column_ids_offset + column_index * 4)
        data_offset = _be32(data, column_offsets_offset + column_index * 4)
        if data_offset < 0 or data_offset + LVST_COLUMN_INFO_SIZE > len(data):
            raise ValueError(f"Column {column_index} has invalid data offset 0x{data_offset:X}.")
        column = ACETableColumn(
            index=column_index,
            hash_id=hash_id,
            data_offset=data_offset,
            column_type=data[data_offset],
            element_size=data[data_offset + 1],
            element_count=data[data_offset + 2],
            reserved=data[data_offset + 3],
            row_count=_be32(data, data_offset + 4),
        )
        columns.append(column)
        max_row_count = max(max_row_count, column.row_count)

    rows: list[ACETableRow] = []
    for row_index in range(max_row_count):
        values: dict[int, object | None] = {}
        raw_values: dict[int, bytes] = {}
        for column in columns:
            raw = _read_cell_bytes(data, column, row_index)
            raw_values[column.hash_id] = raw
            values[column.hash_id] = _read_cell_value(data, column, row_index)
        rows.append(ACETableRow(index=row_index, values=values, raw_values=raw_values))

    return ACETableContainer(
        source_file=str(source_path),
        header=header,
        columns=columns,
        rows=rows,
    )


def patch_ace_table_u32_cell(
    path: str | Path,
    column_hash: int,
    row_index: int,
    value: int,
    *,
    allowed_types: set[int] | None = None,
) -> bytes:
    source_path = Path(path)
    data = bytearray(source_path.read_bytes())
    table = parse_ace_table(source_path)
    patch_ace_table_u32_cell_in_data(
        data,
        table,
        column_hash,
        row_index,
        value,
        allowed_types=allowed_types,
    )
    return bytes(data)


def patch_ace_table_u32_cell_in_data(
    data: bytearray,
    table: ACETableContainer,
    column_hash: int,
    row_index: int,
    value: int,
    *,
    allowed_types: set[int] | None = None,
) -> None:
    target_column = next((column for column in table.columns if column.hash_id == column_hash), None)
    if target_column is None:
        raise ValueError(f"Column 0x{column_hash:08X} does not exist in {Path(table.source_file).name}.")
    if allowed_types is not None and target_column.column_type not in allowed_types:
        raise ValueError(
            f"Column 0x{column_hash:08X} has type 0x{target_column.column_type:02X}, "
            f"not in allowed set {sorted(allowed_types)}."
        )
    if target_column.element_size != 4 or target_column.element_count != 1:
        raise ValueError(
            f"Column 0x{column_hash:08X} is not a scalar 32-bit column "
            f"(size={target_column.element_size}, count={target_column.element_count})."
        )
    if target_column.row_count <= 0:
        raise ValueError(f"Column 0x{column_hash:08X} has no rows.")
    if row_index < 0 or row_index >= target_column.row_count:
        raise ValueError(
            f"Row {row_index} is outside column 0x{column_hash:08X} row count {target_column.row_count}."
        )

    payload_offset = _cell_payload_offset(target_column, row_index)
    data[payload_offset : payload_offset + 4] = int(value).to_bytes(4, "big", signed=False)
