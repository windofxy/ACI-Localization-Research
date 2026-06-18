from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import json
from pathlib import Path
import struct
import unicodedata


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


class ACETableDisplayMode:
    AUTO = "auto"
    UTF8 = "utf-8"
    UTF16BE = "utf-16-be"
    UTF32BE = "utf-32-be"
    RAW_HEX = "raw-hex"


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

    @property
    def row_count(self) -> int:
        return len(self.rows)


def ace_table_display_mode_labels() -> list[tuple[str, str]]:
    return [
        ("Auto", ACETableDisplayMode.AUTO),
        ("UTF-8", ACETableDisplayMode.UTF8),
        ("UTF-16BE", ACETableDisplayMode.UTF16BE),
        ("UTF-32BE", ACETableDisplayMode.UTF32BE),
        ("Raw Hex", ACETableDisplayMode.RAW_HEX),
    ]


def build_ulysses_ace_table_json_object(container: ACETableContainer) -> list[dict[str, object | None]]:
    rows: list[dict[str, object | None]] = []
    for row in container.rows:
        obj: dict[str, object | None] = {}
        for column in container.columns:
            obj[column.hash_name] = row.values.get(column.hash_id)
        rows.append(obj)
    return rows


def _is_private_use_code_point(code_point: int) -> bool:
    return (
        0xE000 <= code_point <= 0xF8FF
        or 0xF0000 <= code_point <= 0xFFFFD
        or 0x100000 <= code_point <= 0x10FFFD
    )


def _should_escape_code_point(code_point: int) -> bool:
    if code_point in {0x0009, 0x000A, 0x000D, 0x0085, 0x2028, 0x2029}:
        return True
    if 0xD800 <= code_point <= 0xDFFF:
        return True
    if _is_private_use_code_point(code_point):
        return True
    char = chr(code_point)
    if unicodedata.category(char).startswith("C"):
        return True
    return False


def _placeholder_from_code_point(code_point: int) -> str:
    return f"[[U+{code_point:04X}]]"


def _json_string_from_utf8_bytes(raw: bytes) -> str:
    payload = raw.split(b"\x00", 1)[0]
    text = payload.decode("utf-8", errors="surrogateescape")
    parts: list[str] = ['"']
    for char in text:
        code_point = ord(char)
        if 0xDC80 <= code_point <= 0xDCFF:
            parts.append(_placeholder_from_code_point(code_point - 0xDC00))
            continue
        if _should_escape_code_point(code_point):
            parts.append(_placeholder_from_code_point(code_point))
            continue
        parts.append(json.dumps(char, ensure_ascii=False)[1:-1])
    parts.append('"')
    return "".join(parts)


def _json_string_from_utf16be_bytes(raw: bytes) -> str:
    payload = raw
    code_units: list[int] = []
    cursor = 0
    while cursor + 2 <= len(payload):
        code_unit = int.from_bytes(payload[cursor : cursor + 2], "big", signed=False)
        if code_unit == 0:
            break
        code_units.append(code_unit)
        cursor += 2

    parts: list[str] = ['"']
    index = 0
    while index < len(code_units):
        code_unit = code_units[index]
        if (
            0xD800 <= code_unit <= 0xDBFF
            and index + 1 < len(code_units)
            and 0xDC00 <= code_units[index + 1] <= 0xDFFF
        ):
            high = code_unit
            low = code_units[index + 1]
            code_point = 0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)
            if _should_escape_code_point(code_point):
                parts.append(_placeholder_from_code_point(high))
                parts.append(_placeholder_from_code_point(low))
            else:
                parts.append(json.dumps(chr(code_point), ensure_ascii=False)[1:-1])
            index += 2
            continue

        if _should_escape_code_point(code_unit):
            parts.append(_placeholder_from_code_point(code_unit))
        else:
            parts.append(json.dumps(chr(code_unit), ensure_ascii=False)[1:-1])
        index += 1

    parts.append('"')
    return "".join(parts)


def _json_string_from_utf32be_bytes(raw: bytes) -> str:
    parts: list[str] = ['"']
    cursor = 0
    while cursor + 4 <= len(raw):
        code_point = int.from_bytes(raw[cursor : cursor + 4], "big", signed=False)
        if code_point == 0:
            break
        if code_point > 0x10FFFF:
            byte_chunk = raw[cursor : cursor + 4]
            for byte_value in byte_chunk:
                parts.append(_placeholder_from_code_point(byte_value))
            cursor += 4
            continue
        if _should_escape_code_point(code_point):
            parts.append(_placeholder_from_code_point(code_point))
        else:
            parts.append(json.dumps(chr(code_point), ensure_ascii=False)[1:-1])
        cursor += 4
    parts.append('"')
    return "".join(parts)


def _json_value_text(column: ACETableColumn, row: ACETableRow) -> str:
    value = row.values.get(column.hash_id)
    if column.column_type in {LVSTColumnType.STRING, LVSTColumnType.BUFFER}:
        return json.dumps(format_ace_table_cell_display(column, row, ACETableDisplayMode.AUTO), ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def build_ulysses_ace_table_json_text(container: ACETableContainer) -> str:
    lines: list[str] = ["["]
    for row_index, row in enumerate(container.rows):
        lines.append("  {")
        for column_index, column in enumerate(container.columns):
            suffix = "," if column_index < len(container.columns) - 1 else ""
            lines.append(
                f"    {json.dumps(column.hash_name)}: {_json_value_text(column, row)}{suffix}"
            )
        lines.append(f"  }}{',' if row_index < len(container.rows) - 1 else ''}")
    lines.append("]")
    return "\n".join(lines) + "\n"


def export_ace_table_json(container: ACETableContainer, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_ulysses_ace_table_json_text(container), encoding="utf-8")
    return output_path


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
    if not raw:
        return ""
    cursor = 0
    terminator = b"\x00" * unit_size
    while cursor + unit_size <= len(raw):
        if raw[cursor : cursor + unit_size] == terminator:
            break
        cursor += unit_size
    raw = raw[:cursor]
    if not raw:
        return ""
    return raw.decode(encoding, errors="replace")


def _format_raw_hex(raw: bytes) -> str:
    if not raw:
        return ""
    return raw.hex(" ")


def _looks_like_single_byte_value(raw: bytes) -> bool:
    return len(raw) == 1


def _is_ascii_text_payload(payload: bytes) -> bool:
    if not payload:
        return False
    return all(0x20 <= byte_value <= 0x7E for byte_value in payload)


def _decode_zero_terminated_bytes(raw: bytes) -> bytes:
    return raw.split(b"\x00", 1)[0]


def _is_likely_text_string(text: str) -> bool:
    if not text:
        return False
    for char in text:
        if char in "\t\r\n":
            continue
        if not char.isprintable():
            return False
    return True


def _is_likely_utf8_text_payload(payload: bytes) -> bool:
    if not payload:
        return False
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return _is_likely_text_string(text)


def infer_ace_table_stringish_display_mode(column: ACETableColumn, row: ACETableRow) -> str:
    raw = row.raw_values.get(column.hash_id, b"")

    if column.element_size == 2:
        return ACETableDisplayMode.UTF16BE
    if column.element_size == 4:
        return ACETableDisplayMode.UTF32BE
    if column.element_size != 1:
        return ACETableDisplayMode.RAW_HEX

    if column.column_type == LVSTColumnType.STRING:
        if column.element_count <= 1 or _looks_like_single_byte_value(raw):
            return ACETableDisplayMode.RAW_HEX
        payload = _decode_zero_terminated_bytes(raw)
        if _is_likely_utf8_text_payload(payload):
            return ACETableDisplayMode.UTF8
        return ACETableDisplayMode.RAW_HEX

    if column.column_type == LVSTColumnType.BUFFER:
        payload = _decode_zero_terminated_bytes(raw)
        if _is_likely_utf8_text_payload(payload):
            return ACETableDisplayMode.UTF8
        return ACETableDisplayMode.RAW_HEX

    return ACETableDisplayMode.RAW_HEX


def _display_stringish_value_auto(column: ACETableColumn, raw: bytes) -> str:
    fake_row = ACETableRow(index=0, values={}, raw_values={column.hash_id: raw})
    inferred_mode = infer_ace_table_stringish_display_mode(column, fake_row)
    if inferred_mode == ACETableDisplayMode.UTF8:
        return _decode_zero_terminated(raw, "utf-8", 1)
    if inferred_mode == ACETableDisplayMode.UTF16BE:
        return _decode_zero_terminated(raw, "utf-16-be", 2)
    if inferred_mode == ACETableDisplayMode.UTF32BE:
        return _decode_zero_terminated(raw, "utf-32-be", 4)
    return _format_raw_hex(raw)


def format_ace_table_cell_display(
    column: ACETableColumn,
    row: ACETableRow,
    mode: str = ACETableDisplayMode.AUTO,
) -> str:
    raw = row.raw_values.get(column.hash_id, b"")
    value = row.values.get(column.hash_id)

    if column.column_type in {LVSTColumnType.STRING, LVSTColumnType.BUFFER}:
        if mode == ACETableDisplayMode.RAW_HEX:
            return _format_raw_hex(raw)
        if mode == ACETableDisplayMode.UTF8:
            return _decode_zero_terminated(raw, "utf-8", 1)
        if mode == ACETableDisplayMode.UTF16BE:
            return _decode_zero_terminated(raw, "utf-16-be", 2)
        if mode == ACETableDisplayMode.UTF32BE:
            return _decode_zero_terminated(raw, "utf-32-be", 4)
        return _display_stringish_value_auto(column, raw)

    return "" if value is None else str(value)


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
    return str(timedelta(seconds=value))


def _read_cell_bytes(data: bytes, column: ACETableColumn, row_index: int) -> bytes:
    if column.row_count <= 0:
        return b""
    if row_index >= column.row_count:
        row_index %= column.row_count

    payload_size = column.element_size * column.element_count
    payload_offset = column.data_offset + LVST_COLUMN_INFO_SIZE + payload_size * row_index
    if payload_offset < 0 or payload_offset + payload_size > len(data):
        raise ValueError(
            f"Cell payload for column {column.index} row {row_index} exceeds the ACETable buffer."
        )
    return data[payload_offset : payload_offset + payload_size]


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
            raise ValueError(
                f"Column {column_index} has invalid data offset 0x{data_offset:X}."
            )
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
