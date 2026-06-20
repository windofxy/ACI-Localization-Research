from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ace_table_parser import ACETableContainer, parse_ace_table
from .ace_text_parser import ACETextContainer, ACETextEntry, parse_ace_text


SCHEDULE_EVENT_ID = 0x59FEC50B
SCHEDULE_START_DATE = 0xC9593D6F
SCHEDULE_START_TIME = 0xDF8C1FB7
SCHEDULE_END_DATE = 0x8CA04356
SCHEDULE_END_TIME = 0x38A4B1DD
SCHEDULE_ORDER = 0x50039A17
SCHEDULE_TEXT_HASH = 0x67D3BFDF
SCHEDULE_EXTRA = 0x0DDCC047

CHALLENGE_TARGET_ID = 0xF7740E1D
CHALLENGE_START_DATE = 0x72B5C53E
CHALLENGE_START_TIME = 0xC3649538
CHALLENGE_END_DATE = 0xEC64C9A0
CHALLENGE_END_TIME = 0x5DB599A6
CHALLENGE_TITLE_HASH = 0x26B6DAC0
CHALLENGE_MESSAGE_HASH = 0xF67C9878

DROP_EVENT_ID = 0xFAE44CAC
DROP_START_DATE = 0x72B5C53E
DROP_START_TIME = 0xC3649538
DROP_END_DATE = 0xEC64C9A0
DROP_END_TIME = 0x5DB599A6
DROP_FLAG_A = 0x535350D8
DROP_FLAG_B = 0x582550E2
DROP_FLAG_C = 0x28F3D7F7
DROP_TITLE_HASH = 0x66A9F6E3

CATALOG_MAIN_VISIBLE = 0x1F579B18
CATALOG_MAIN_SORT_ID = 0x233E40C9
CATALOG_MAIN_GROUP_ID = 0xDD3BA8C2
CATALOG_MAIN_ITEM_ID = 0x2169275B
CATALOG_MAIN_ITEM_ID_B = 0x1BF0FD45
CATALOG_MAIN_CATEGORY = 0xEA135027
CATALOG_MAIN_NAME_HASH = 0x0772A233
CATALOG_MAIN_DESC_HASH = 0x02546AE7
CATALOG_MAIN_CONTENT_ID = 0xC3B1A215
CATALOG_MAIN_PACKED_ID = 0x9C4E3B0A
CATALOG_MAIN_PRICE_A = 0x303B4E1D
CATALOG_MAIN_PRICE_B = 0x9768703A
CATALOG_MAIN_LIMIT_FLAG = 0x7FA3C486
CATALOG_MAIN_MULTIPLIER = 0xAD6CE22E
CATALOG_MAIN_FLAG = 0x743282A0

CATALOG_SUB_VISIBLE = 0x75E4EF66
CATALOG_SUB_SORT_ID = 0x49D0C120
CATALOG_SUB_GROUP_ID = 0xA52E91FE
CATALOG_SUB_ITEM_ID = 0x4BDA5325
CATALOG_SUB_ITEM_ID_B = 0xF0AAF6EE
CATALOG_SUB_CATEGORY = 0x73076217
CATALOG_SUB_NAME_HASH = 0x65F376FC
CATALOG_SUB_DESC_HASH = 0x60D5BE28
CATALOG_SUB_CONTENT_ID = 0xD0575984
CATALOG_SUB_PACKED_ID = 0xB8BD09F3
CATALOG_SUB_PRICE_A = 0xE3BE8242
CATALOG_SUB_PRICE_B = 0xF5E9A4F5
CATALOG_SUB_LIMIT_FLAG = 0xCB4A829E
CATALOG_SUB_MULTIPLIER = 0x7EE92E71
CATALOG_SUB_FLAG = 0x47A383E4

RANKING_VARIANT_ID = 0xC6B3F27B
RANKING_RULE_TYPE_A = 0x98AABE82
RANKING_RULE_EVENT_ID = 0x5CBA6059
RANKING_RULE_TYPE_B = 0x8CD486DF
RANKING_MENU_HASH = 0x469A8F16
RANKING_DESC_HASH = 0x94D96AA2
RANKING_METRIC = 0xE6F659E2
RANKING_MISSION_HASH = 0xD89CE092
RANKING_AIRCRAFT_HASH = 0xE3CB71BA

KNOWN_TEXT_HASH_LABELS: dict[int, str] = {
    0x184A15D3: "DebugRegulationName_cw1",
    0x1509330A: "DebugRegulationName_cw2",
    0x55BE208C: "DebugRegulationName_tc1",
}


@dataclass(frozen=True)
class GameEventChallenge:
    source_file: str
    source_lvst: str
    row_index: int
    target_id: int | None
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    title_hash: str
    title_label: str
    title_jp: str
    title_us: str
    message_hash: str
    message_label: str
    message_jp: str
    message_us: str


@dataclass(frozen=True)
class GameEventDrop:
    source_file: str
    source_lvst: str
    row_index: int
    drop_id: int
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    title_hash: str
    title_label: str
    title_jp: str
    title_us: str
    flag_a: int | None
    flag_b: int | None
    flag_c: int | None

    @property
    def start_text(self) -> str:
        return _join_datetime(self.start_date, self.start_time)

    @property
    def end_text(self) -> str:
        return _join_datetime(self.end_date, self.end_time)


@dataclass(frozen=True)
class GameEventCatalogItem:
    source_file: str
    source_lvst: str
    row_index: int
    table_kind: str
    visible: int | None
    sort_id: int | None
    group_id: int | None
    item_id: int | None
    item_id_b: int | None
    category: int | None
    name_hash: str
    name_label: str
    name_jp: str
    name_us: str
    desc_hash: str
    desc_label: str
    desc_jp: str
    desc_us: str
    content_id: int | None
    packed_id: int | None
    price_a: int | None
    price_b: int | None
    limit_flag: int | None
    multiplier: float | None
    flag: int | None


@dataclass(frozen=True)
class GameEventRankingInfo:
    source_lvst: str
    row_index: int
    variant_id: int | None
    schedule_event_id: int
    menu_hash: str
    menu_label: str
    menu_jp: str
    menu_us: str
    description_hash: str
    description_label: str
    description_jp: str
    description_us: str
    mission_hash: str
    mission_label: str
    mission_jp: str
    mission_us: str
    aircraft_hash: str
    aircraft_label: str
    aircraft_jp: str
    aircraft_us: str
    rule_type_a: int | None
    rule_type_b: int | None
    metric_value: int | None

    def proxy_display_name(self, language: str) -> str:
        if language == "US":
            if self.menu_us:
                return self.menu_us
            if self.mission_us:
                return self.mission_us
        if language == "JP":
            if self.menu_jp:
                return self.menu_jp
            if self.mission_jp:
                return self.mission_jp
        return (
            self.menu_us
            or self.menu_jp
            or self.menu_label
            or self.mission_us
            or self.mission_jp
            or self.mission_label
            or self.menu_hash
            or self.mission_hash
        )


@dataclass(frozen=True)
class GameEventRecord:
    event_id: int
    event_name_jp: str
    event_name_us: str
    name_label: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    source_file: str
    source_lvst: str
    row_index: int
    order_value: int | None
    text_hash: str
    text_hash_jp: str
    text_hash_us: str
    extra_value: int | None
    ranking_info: GameEventRankingInfo | None = None
    challenges: list[GameEventChallenge] = field(default_factory=list)

    @property
    def start_text(self) -> str:
        return _join_datetime(self.start_date, self.start_time)

    @property
    def end_text(self) -> str:
        return _join_datetime(self.end_date, self.end_time)

    def display_name(self, language: str) -> str:
        if language == "US" and self.event_name_us:
            return self.event_name_us
        if language == "JP" and self.event_name_jp:
            return self.event_name_jp
        if self.ranking_info is not None:
            ranking_name = self.ranking_info.proxy_display_name(language)
            if ranking_name:
                return ranking_name
        return self.event_name_jp or self.event_name_us or self.name_label or f"Event {self.event_id}"


@dataclass(frozen=True)
class GameEventDataset:
    root_dir: str
    package_dirs: list[str]
    act_files: list[str]
    lvst_files: list[str]
    parsed_act_files: list[str]
    parsed_lvst_files: list[str]
    events: list[GameEventRecord]
    challenges: list[GameEventChallenge]
    drops: list[GameEventDrop]
    catalog_items: list[GameEventCatalogItem]
    warnings: list[str]
    plaintext_labels: dict[str, tuple[str, str]]


def _join_datetime(date_text: str, time_text: str) -> str:
    if date_text and time_text:
        return f"{date_text} {time_text}"
    return date_text or time_text


def _datetime_key(date_text: str, time_text: str, *, is_end: bool = False) -> tuple[str, str] | None:
    if not date_text:
        return None
    return (date_text, time_text or ("23:59:59" if is_end else "00:00:00"))


def _datetime_ranges_overlap(
    left_start_date: str,
    left_start_time: str,
    left_end_date: str,
    left_end_time: str,
    right_start_date: str,
    right_start_time: str,
    right_end_date: str,
    right_end_time: str,
) -> bool:
    left_start = _datetime_key(left_start_date, left_start_time)
    left_end = _datetime_key(left_end_date, left_end_time, is_end=True)
    right_start = _datetime_key(right_start_date, right_start_time)
    right_end = _datetime_key(right_end_date, right_end_time, is_end=True)
    if left_start is None or left_end is None or right_start is None or right_end is None:
        return False
    return left_start <= right_end and right_start <= left_end


def _relative_path(root_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _display_source_path(package_dir: Path, path: Path) -> str:
    relative = _relative_path(package_dir, path)
    package_name = package_dir.name
    if package_name.startswith("NPWR04428_00-"):
        return f"{package_name}/{relative}"
    return relative


def _text_value(entry: ACETextEntry | None, language: str) -> str:
    if entry is None:
        return ""
    if language and entry.values.get(language):
        return entry.values[language]
    for fallback in ("JP", "US"):
        if entry.values.get(fallback):
            return entry.values[fallback]
    for value in entry.values.values():
        if value:
            return value
    return ""


def _is_tokenized_entry(entry: ACETextEntry | None) -> bool:
    if entry is None:
        return False
    for code_units in entry.value_code_units.values():
        if len(code_units) >= 2 and code_units[0] == 0xE020 and code_units[1] == 0x0001:
            return True
    return False


def _looks_tokenized_text(text: str) -> bool:
    return bool(text) and text.startswith("\uE020\x01")


def _clean_display_text(text: str) -> str:
    if _looks_tokenized_text(text):
        return ""
    return text


def _hash_text_to_int(value: object | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("0x"):
        try:
            return int(value, 16)
        except ValueError:
            return None
    return None


def _is_schedule_table(table: ACETableContainer) -> bool:
    columns = {column.hash_id for column in table.columns}
    required = {
        SCHEDULE_EVENT_ID,
        SCHEDULE_START_DATE,
        SCHEDULE_START_TIME,
        SCHEDULE_END_DATE,
        SCHEDULE_END_TIME,
    }
    return required.issubset(columns)


def _is_challenge_table(table: ACETableContainer) -> bool:
    columns = {column.hash_id for column in table.columns}
    required = {
        CHALLENGE_TARGET_ID,
        CHALLENGE_START_DATE,
        CHALLENGE_START_TIME,
        CHALLENGE_END_DATE,
        CHALLENGE_END_TIME,
        CHALLENGE_TITLE_HASH,
        CHALLENGE_MESSAGE_HASH,
    }
    return required.issubset(columns)


def _is_ranking_rule_table(table: ACETableContainer) -> bool:
    columns = {column.hash_id for column in table.columns}
    required = {
        RANKING_RULE_EVENT_ID,
        RANKING_MENU_HASH,
        RANKING_DESC_HASH,
        RANKING_MISSION_HASH,
    }
    return required.issubset(columns)


def _is_drop_item_table(table: ACETableContainer, lvst_path: Path) -> bool:
    if lvst_path.parent.name.lower() != "0x761b5e0d":
        return False
    columns = {column.hash_id for column in table.columns}
    required = {
        DROP_EVENT_ID,
        DROP_START_DATE,
        DROP_START_TIME,
        DROP_END_DATE,
        DROP_END_TIME,
        DROP_TITLE_HASH,
    }
    return required.issubset(columns)


def _is_catalog_table(table: ACETableContainer, lvst_path: Path) -> bool:
    if lvst_path.parent.name.lower() != "0x3f20632f" or lvst_path.name.lower() != "6.lvst":
        return False
    columns = {column.hash_id for column in table.columns}
    required = {
        CATALOG_MAIN_CATEGORY,
        CATALOG_MAIN_NAME_HASH,
        CATALOG_MAIN_DESC_HASH,
        CATALOG_MAIN_ITEM_ID,
    }
    return required.issubset(columns)


def _column_row_count(table: ACETableContainer, column_hash: int) -> int:
    for column in table.columns:
        if column.hash_id == column_hash:
            return column.row_count
    return 0


def _list_package_dirs(root_dir: Path) -> list[Path]:
    package_dirs = sorted(
        path
        for path in root_dir.iterdir()
        if path.is_dir() and path.name.startswith("NPWR04428_00-")
    )
    if package_dirs:
        return package_dirs
    return [root_dir]


def _resolve_name(
    event_id: int,
    label_index: dict[str, list[ACETextEntry]],
    hash_index: dict[int, list[ACETextEntry]],
    text_hash_value: object | None,
    plaintext_labels: dict[str, tuple[str, str]],
) -> tuple[str, str, str]:
    labels = [
        f"ShortName_RankEvent{event_id}",
        f"LongName_RankEvent{event_id}",
        f"Reward_RankEvent{event_id}",
    ]
    for label in labels:
        entries = label_index.get(label)
        if not entries:
            continue
        entry = entries[0]
        if _is_tokenized_entry(entry):
            plaintext = plaintext_labels.get(label)
            if plaintext is not None:
                return plaintext[0], plaintext[1], label
        return _clean_display_text(_text_value(entry, "JP")), _clean_display_text(_text_value(entry, "US")), label
    text_hash_int = _hash_text_to_int(text_hash_value)
    if text_hash_int is not None and hash_index.get(text_hash_int):
        entry = hash_index[text_hash_int][0]
        if _is_tokenized_entry(entry):
            plaintext = plaintext_labels.get(entry.hash_label)
            if plaintext is not None:
                return plaintext[0], plaintext[1], entry.hash_label
        return _clean_display_text(_text_value(entry, "JP")), _clean_display_text(_text_value(entry, "US")), entry.hash_label
    return "", "", ""


def _build_act_indexes(
    act_files: list[Path],
    warnings: list[str],
) -> tuple[list[str], dict[str, list[ACETextEntry]], dict[int, list[ACETextEntry]], dict[str, tuple[str, str]]]:
    parsed_paths: list[str] = []
    label_index: dict[str, list[ACETextEntry]] = {}
    hash_index: dict[int, list[ACETextEntry]] = {}
    plaintext_labels: dict[str, tuple[str, str]] = {}
    for act_path in act_files:
        try:
            container = parse_ace_text(act_path)
        except Exception as exc:
            warnings.append(f"Failed to parse ACT {act_path}: {exc}")
            continue
        parsed_paths.append(str(act_path))
        for entry in container.entries:
            if entry.hash_label:
                label_index.setdefault(entry.hash_label, []).append(entry)
            hash_index.setdefault(entry.hash_value, []).append(entry)
            if entry.hash_label and not _is_tokenized_entry(entry):
                jp_text = _clean_display_text(_text_value(entry, "JP"))
                us_text = _clean_display_text(_text_value(entry, "US"))
                if jp_text or us_text:
                    plaintext_labels.setdefault(entry.hash_label, (jp_text, us_text))
    return parsed_paths, label_index, hash_index, plaintext_labels


def _list_extra_act_files(extra_act_sources: list[Path] | None) -> list[Path]:
    if not extra_act_sources:
        return []
    result: list[Path] = []
    seen: set[Path] = set()
    for source in extra_act_sources:
        if source.is_file():
            candidates = [source] if source.suffix.lower() == ".act" else []
        elif source.is_dir():
            candidates = sorted(source.rglob("*.act"))
        else:
            candidates = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            result.append(candidate)
    return result


def _merge_entry_index(
    primary: dict[object, list[ACETextEntry]],
    fallback: dict[object, list[ACETextEntry]],
) -> dict[object, list[ACETextEntry]]:
    result: dict[object, list[ACETextEntry]] = {key: list(value) for key, value in primary.items()}
    for key, entries in fallback.items():
        result.setdefault(key, []).extend(entries)
    return result


def _merge_plaintext_labels(
    *sources: dict[str, tuple[str, str]],
) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for source in sources:
        for label, texts in source.items():
            result.setdefault(label, texts)
    return result


def _resolve_hash_display(
    hash_value: object | None,
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
) -> tuple[str, str, str]:
    hash_int = _hash_text_to_int(hash_value)
    if hash_int is None:
        return "", "", ""
    entries = hash_index.get(hash_int)
    if not entries:
        known_label = KNOWN_TEXT_HASH_LABELS.get(hash_int, "")
        return known_label, "", ""
    entry = entries[0]
    jp_text = _clean_display_text(_text_value(entry, "JP"))
    us_text = _clean_display_text(_text_value(entry, "US"))
    if _is_tokenized_entry(entry):
        plaintext = plaintext_labels.get(entry.hash_label)
        if plaintext is not None:
            jp_text, us_text = plaintext
    return entry.hash_label, jp_text, us_text


def _collect_sibling_plaintext_labels(root_dir: Path) -> dict[str, tuple[str, str]]:
    search_dirs = _list_package_dirs(root_dir)
    plaintext_labels: dict[str, tuple[str, str]] = {}
    for sibling_dir in search_dirs:
        act_path = sibling_dir / "0x58cf00c0" / "0" / "0.act"
        if not act_path.exists():
            continue
        try:
            container = parse_ace_text(act_path)
        except Exception:
            continue
        for entry in container.entries:
            if not entry.hash_label or _is_tokenized_entry(entry):
                continue
            jp_text = _clean_display_text(_text_value(entry, "JP"))
            us_text = _clean_display_text(_text_value(entry, "US"))
            if jp_text or us_text:
                plaintext_labels.setdefault(entry.hash_label, (jp_text, us_text))
    return plaintext_labels


def _build_challenge_map(
    root_dir: Path,
    lvst_files: list[Path],
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
    warnings: list[str],
) -> tuple[list[str], dict[int, list[GameEventChallenge]], list[GameEventChallenge]]:
    parsed_paths: list[str] = []
    result: dict[int, list[GameEventChallenge]] = {}
    challenges: list[GameEventChallenge] = []
    for lvst_path in lvst_files:
        try:
            table = parse_ace_table(lvst_path)
        except Exception as exc:
            warnings.append(f"Failed to parse LVST {lvst_path}: {exc}")
            continue
        if not _is_challenge_table(table):
            continue
        parsed_paths.append(str(lvst_path))
        source_rel = _display_source_path(root_dir, lvst_path)
        for row in table.rows:
            target_id = row.values.get(CHALLENGE_TARGET_ID)
            if not isinstance(target_id, int) or target_id <= 0:
                continue
            title_hash_text = row.values.get(CHALLENGE_TITLE_HASH)
            message_hash_text = row.values.get(CHALLENGE_MESSAGE_HASH)
            title_entry = None
            message_entry = None
            title_hash = _hash_text_to_int(title_hash_text)
            message_hash = _hash_text_to_int(message_hash_text)
            if title_hash is not None and hash_index.get(title_hash):
                title_entry = hash_index[title_hash][0]
            if message_hash is not None and hash_index.get(message_hash):
                message_entry = hash_index[message_hash][0]
            title_jp = _clean_display_text(_text_value(title_entry, "JP"))
            title_us = _clean_display_text(_text_value(title_entry, "US"))
            message_jp = _clean_display_text(_text_value(message_entry, "JP"))
            message_us = _clean_display_text(_text_value(message_entry, "US"))
            if title_entry is not None and _is_tokenized_entry(title_entry):
                plaintext = plaintext_labels.get(title_entry.hash_label)
                if plaintext is not None:
                    title_jp, title_us = plaintext
            if message_entry is not None and _is_tokenized_entry(message_entry):
                plaintext = plaintext_labels.get(message_entry.hash_label)
                if plaintext is not None:
                    message_jp, message_us = plaintext
            challenge = GameEventChallenge(
                source_file=str(lvst_path),
                source_lvst=source_rel,
                row_index=row.index,
                target_id=target_id,
                start_date=row.values.get(CHALLENGE_START_DATE) if isinstance(row.values.get(CHALLENGE_START_DATE), str) else "",
                start_time=row.values.get(CHALLENGE_START_TIME) if isinstance(row.values.get(CHALLENGE_START_TIME), str) else "",
                end_date=row.values.get(CHALLENGE_END_DATE) if isinstance(row.values.get(CHALLENGE_END_DATE), str) else "",
                end_time=row.values.get(CHALLENGE_END_TIME) if isinstance(row.values.get(CHALLENGE_END_TIME), str) else "",
                title_hash=title_hash_text if isinstance(title_hash_text, str) else "",
                title_label=title_entry.hash_label if title_entry is not None else "",
                title_jp=title_jp,
                title_us=title_us,
                message_hash=message_hash_text if isinstance(message_hash_text, str) else "",
                message_label=message_entry.hash_label if message_entry is not None else "",
                message_jp=message_jp,
                message_us=message_us,
            )
            result.setdefault(target_id, []).append(challenge)
            challenges.append(challenge)
    challenges.sort(
        key=lambda challenge: (
            challenge.start_date or "9999-99-99",
            challenge.start_time or "99:99:99",
            challenge.target_id if challenge.target_id is not None else -1,
            challenge.source_lvst,
            challenge.row_index,
        )
    )
    return parsed_paths, result, challenges


def _build_ranking_info_map(
    root_dir: Path,
    lvst_files: list[Path],
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
    warnings: list[str],
) -> tuple[list[str], dict[int, GameEventRankingInfo]]:
    parsed_paths: list[str] = []
    result: dict[int, GameEventRankingInfo] = {}
    for lvst_path in lvst_files:
        try:
            table = parse_ace_table(lvst_path)
        except Exception as exc:
            warnings.append(f"Failed to parse LVST {lvst_path}: {exc}")
            continue
        if not _is_ranking_rule_table(table):
            continue
        parsed_paths.append(str(lvst_path))
        source_rel = _display_source_path(root_dir, lvst_path)
        for row in table.rows:
            schedule_event_id = row.values.get(RANKING_RULE_EVENT_ID)
            if not isinstance(schedule_event_id, int) or schedule_event_id <= 0:
                continue
            menu_hash = row.values.get(RANKING_MENU_HASH)
            desc_hash = row.values.get(RANKING_DESC_HASH)
            mission_hash = row.values.get(RANKING_MISSION_HASH)
            aircraft_hash = row.values.get(RANKING_AIRCRAFT_HASH)
            menu_label, menu_jp, menu_us = _resolve_hash_display(menu_hash, hash_index, plaintext_labels)
            desc_label, desc_jp, desc_us = _resolve_hash_display(desc_hash, hash_index, plaintext_labels)
            mission_label, mission_jp, mission_us = _resolve_hash_display(mission_hash, hash_index, plaintext_labels)
            aircraft_label, aircraft_jp, aircraft_us = _resolve_hash_display(aircraft_hash, hash_index, plaintext_labels)
            result[schedule_event_id] = GameEventRankingInfo(
                source_lvst=source_rel,
                row_index=row.index,
                variant_id=row.values.get(RANKING_VARIANT_ID) if isinstance(row.values.get(RANKING_VARIANT_ID), int) else None,
                schedule_event_id=schedule_event_id,
                menu_hash=menu_hash if isinstance(menu_hash, str) else "",
                menu_label=menu_label,
                menu_jp=menu_jp,
                menu_us=menu_us,
                description_hash=desc_hash if isinstance(desc_hash, str) else "",
                description_label=desc_label,
                description_jp=desc_jp,
                description_us=desc_us,
                mission_hash=mission_hash if isinstance(mission_hash, str) else "",
                mission_label=mission_label,
                mission_jp=mission_jp,
                mission_us=mission_us,
                aircraft_hash=aircraft_hash if isinstance(aircraft_hash, str) else "",
                aircraft_label=aircraft_label,
                aircraft_jp=aircraft_jp,
                aircraft_us=aircraft_us,
                rule_type_a=row.values.get(RANKING_RULE_TYPE_A) if isinstance(row.values.get(RANKING_RULE_TYPE_A), int) else None,
                rule_type_b=row.values.get(RANKING_RULE_TYPE_B) if isinstance(row.values.get(RANKING_RULE_TYPE_B), int) else None,
                metric_value=row.values.get(RANKING_METRIC) if isinstance(row.values.get(RANKING_METRIC), int) else None,
            )
    return parsed_paths, result


def _build_drop_events(
    root_dir: Path,
    lvst_files: list[Path],
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
    warnings: list[str],
) -> tuple[list[str], list[GameEventDrop]]:
    parsed_paths: list[str] = []
    drops: list[GameEventDrop] = []
    for lvst_path in lvst_files:
        try:
            table = parse_ace_table(lvst_path)
        except Exception as exc:
            warnings.append(f"Failed to parse LVST {lvst_path}: {exc}")
            continue
        if not _is_drop_item_table(table, lvst_path):
            continue
        parsed_paths.append(str(lvst_path))
        source_rel = _display_source_path(root_dir, lvst_path)
        schedule_row_count = min(
            _column_row_count(table, DROP_EVENT_ID),
            _column_row_count(table, DROP_START_DATE),
            _column_row_count(table, DROP_START_TIME),
            _column_row_count(table, DROP_END_DATE),
            _column_row_count(table, DROP_END_TIME),
            _column_row_count(table, DROP_TITLE_HASH),
        )
        for row_index in range(schedule_row_count):
            row = table.rows[row_index]
            drop_id = row.values.get(DROP_EVENT_ID)
            if not isinstance(drop_id, int) or drop_id <= 0:
                continue
            title_hash = row.values.get(DROP_TITLE_HASH)
            title_label, title_jp, title_us = _resolve_hash_display(title_hash, hash_index, plaintext_labels)
            drops.append(
                GameEventDrop(
                    source_file=str(lvst_path),
                    source_lvst=source_rel,
                    row_index=row_index,
                    drop_id=drop_id,
                    start_date=row.values.get(DROP_START_DATE) if isinstance(row.values.get(DROP_START_DATE), str) else "",
                    start_time=row.values.get(DROP_START_TIME) if isinstance(row.values.get(DROP_START_TIME), str) else "",
                    end_date=row.values.get(DROP_END_DATE) if isinstance(row.values.get(DROP_END_DATE), str) else "",
                    end_time=row.values.get(DROP_END_TIME) if isinstance(row.values.get(DROP_END_TIME), str) else "",
                    title_hash=title_hash if isinstance(title_hash, str) else "",
                    title_label=title_label,
                    title_jp=title_jp,
                    title_us=title_us,
                    flag_a=row.values.get(DROP_FLAG_A) if isinstance(row.values.get(DROP_FLAG_A), int) else None,
                    flag_b=row.values.get(DROP_FLAG_B) if isinstance(row.values.get(DROP_FLAG_B), int) else None,
                    flag_c=row.values.get(DROP_FLAG_C) if isinstance(row.values.get(DROP_FLAG_C), int) else None,
                )
            )
    drops.sort(
        key=lambda drop: (
            drop.start_date or "9999-99-99",
            drop.start_time or "99:99:99",
            drop.drop_id,
            drop.source_lvst,
            drop.row_index,
        )
    )
    return parsed_paths, drops


def _int_value(row_values: dict[int, object | None], column_hash: int) -> int | None:
    value = row_values.get(column_hash)
    return value if isinstance(value, int) else None


def _float_value(row_values: dict[int, object | None], column_hash: int) -> float | None:
    value = row_values.get(column_hash)
    return value if isinstance(value, float) else None


def _hash_value(row_values: dict[int, object | None], column_hash: int) -> str:
    value = row_values.get(column_hash)
    return value if isinstance(value, str) else ""


def _build_catalog_item(
    lvst_path: Path,
    source_rel: str,
    row_index: int,
    row_values: dict[int, object | None],
    *,
    table_kind: str,
    schema: dict[str, int],
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
) -> GameEventCatalogItem:
    name_hash = row_values.get(schema["name_hash"])
    desc_hash = row_values.get(schema["desc_hash"])
    name_label, name_jp, name_us = _resolve_hash_display(name_hash, hash_index, plaintext_labels)
    desc_label, desc_jp, desc_us = _resolve_hash_display(desc_hash, hash_index, plaintext_labels)
    return GameEventCatalogItem(
        source_file=str(lvst_path),
        source_lvst=source_rel,
        row_index=row_index,
        table_kind=table_kind,
        visible=_int_value(row_values, schema["visible"]),
        sort_id=_int_value(row_values, schema["sort_id"]),
        group_id=_int_value(row_values, schema["group_id"]),
        item_id=_int_value(row_values, schema["item_id"]),
        item_id_b=_int_value(row_values, schema["item_id_b"]),
        category=_int_value(row_values, schema["category"]),
        name_hash=_hash_value(row_values, schema["name_hash"]),
        name_label=name_label,
        name_jp=name_jp,
        name_us=name_us,
        desc_hash=_hash_value(row_values, schema["desc_hash"]),
        desc_label=desc_label,
        desc_jp=desc_jp,
        desc_us=desc_us,
        content_id=_int_value(row_values, schema["content_id"]),
        packed_id=_int_value(row_values, schema["packed_id"]),
        price_a=_int_value(row_values, schema["price_a"]),
        price_b=_int_value(row_values, schema["price_b"]),
        limit_flag=_int_value(row_values, schema["limit_flag"]),
        multiplier=_float_value(row_values, schema["multiplier"]),
        flag=_int_value(row_values, schema["flag"]),
    )


def _build_catalog_items(
    root_dir: Path,
    lvst_files: list[Path],
    hash_index: dict[int, list[ACETextEntry]],
    plaintext_labels: dict[str, tuple[str, str]],
    warnings: list[str],
) -> tuple[list[str], list[GameEventCatalogItem]]:
    parsed_paths: list[str] = []
    items: list[GameEventCatalogItem] = []
    main_schema = {
        "visible": CATALOG_MAIN_VISIBLE,
        "sort_id": CATALOG_MAIN_SORT_ID,
        "group_id": CATALOG_MAIN_GROUP_ID,
        "item_id": CATALOG_MAIN_ITEM_ID,
        "item_id_b": CATALOG_MAIN_ITEM_ID_B,
        "category": CATALOG_MAIN_CATEGORY,
        "name_hash": CATALOG_MAIN_NAME_HASH,
        "desc_hash": CATALOG_MAIN_DESC_HASH,
        "content_id": CATALOG_MAIN_CONTENT_ID,
        "packed_id": CATALOG_MAIN_PACKED_ID,
        "price_a": CATALOG_MAIN_PRICE_A,
        "price_b": CATALOG_MAIN_PRICE_B,
        "limit_flag": CATALOG_MAIN_LIMIT_FLAG,
        "multiplier": CATALOG_MAIN_MULTIPLIER,
        "flag": CATALOG_MAIN_FLAG,
    }
    sub_schema = {
        "visible": CATALOG_SUB_VISIBLE,
        "sort_id": CATALOG_SUB_SORT_ID,
        "group_id": CATALOG_SUB_GROUP_ID,
        "item_id": CATALOG_SUB_ITEM_ID,
        "item_id_b": CATALOG_SUB_ITEM_ID_B,
        "category": CATALOG_SUB_CATEGORY,
        "name_hash": CATALOG_SUB_NAME_HASH,
        "desc_hash": CATALOG_SUB_DESC_HASH,
        "content_id": CATALOG_SUB_CONTENT_ID,
        "packed_id": CATALOG_SUB_PACKED_ID,
        "price_a": CATALOG_SUB_PRICE_A,
        "price_b": CATALOG_SUB_PRICE_B,
        "limit_flag": CATALOG_SUB_LIMIT_FLAG,
        "multiplier": CATALOG_SUB_MULTIPLIER,
        "flag": CATALOG_SUB_FLAG,
    }
    for lvst_path in lvst_files:
        try:
            table = parse_ace_table(lvst_path)
        except Exception as exc:
            warnings.append(f"Failed to parse catalog LVST {lvst_path}: {exc}")
            continue
        if not _is_catalog_table(table, lvst_path):
            continue
        parsed_paths.append(str(lvst_path))
        source_rel = _display_source_path(root_dir, lvst_path)
        main_row_count = _column_row_count(table, CATALOG_MAIN_CATEGORY)
        for row_index in range(main_row_count):
            row = table.rows[row_index]
            items.append(
                _build_catalog_item(
                    lvst_path,
                    source_rel,
                    row_index,
                    row.values,
                    table_kind="main",
                    schema=main_schema,
                    hash_index=hash_index,
                    plaintext_labels=plaintext_labels,
                )
            )
        sub_row_count = _column_row_count(table, CATALOG_SUB_CATEGORY)
        if sub_row_count <= 0:
            continue
        for row_index in range(sub_row_count):
            row = table.rows[row_index]
            items.append(
                _build_catalog_item(
                    lvst_path,
                    source_rel,
                    row_index,
                    row.values,
                    table_kind="sub",
                    schema=sub_schema,
                    hash_index=hash_index,
                    plaintext_labels=plaintext_labels,
                )
            )
    items.sort(
        key=lambda item: (
            item.sort_id if item.sort_id is not None else 9999999999,
            item.category if item.category is not None else -1,
            item.item_id if item.item_id is not None else -1,
            item.source_lvst,
            item.table_kind,
            item.row_index,
        )
    )
    return parsed_paths, items


def _parse_single_game_event_directory(
    package_dir: Path,
    plaintext_labels: dict[str, tuple[str, str]],
    fallback_label_index: dict[str, list[ACETextEntry]] | None = None,
    fallback_hash_index: dict[int, list[ACETextEntry]] | None = None,
    fallback_plaintext_labels: dict[str, tuple[str, str]] | None = None,
) -> GameEventDataset:
    act_files = sorted(package_dir.rglob("*.act"))
    lvst_files = sorted(package_dir.rglob("*.lvst"))
    warnings: list[str] = []

    parsed_act_files, label_index, hash_index, package_plaintext_labels = _build_act_indexes(act_files, warnings)
    if fallback_label_index:
        label_index = _merge_entry_index(label_index, fallback_label_index)  # type: ignore[assignment]
    if fallback_hash_index:
        hash_index = _merge_entry_index(hash_index, fallback_hash_index)  # type: ignore[assignment]
    plaintext_labels = _merge_plaintext_labels(
        package_plaintext_labels,
        plaintext_labels,
        fallback_plaintext_labels or {},
    )
    parsed_challenge_files, challenge_map, challenges = _build_challenge_map(
        package_dir,
        lvst_files,
        hash_index,
        plaintext_labels,
        warnings,
    )
    parsed_ranking_files, ranking_info_map = _build_ranking_info_map(
        package_dir,
        lvst_files,
        hash_index,
        plaintext_labels,
        warnings,
    )
    parsed_drop_files, drops = _build_drop_events(
        package_dir,
        lvst_files,
        hash_index,
        plaintext_labels,
        warnings,
    )
    parsed_catalog_files, catalog_items = _build_catalog_items(
        package_dir,
        lvst_files,
        hash_index,
        plaintext_labels,
        warnings,
    )

    parsed_lvst_files: list[str] = list(parsed_challenge_files)
    for parsed_path in parsed_ranking_files:
        if parsed_path not in parsed_lvst_files:
            parsed_lvst_files.append(parsed_path)
    for parsed_path in parsed_drop_files:
        if parsed_path not in parsed_lvst_files:
            parsed_lvst_files.append(parsed_path)
    for parsed_path in parsed_catalog_files:
        if parsed_path not in parsed_lvst_files:
            parsed_lvst_files.append(parsed_path)
    events: list[GameEventRecord] = []
    for lvst_path in lvst_files:
        try:
            table = parse_ace_table(lvst_path)
        except Exception as exc:
            warnings.append(f"Failed to parse LVST {lvst_path}: {exc}")
            continue
        if not _is_schedule_table(table):
            continue
        if str(lvst_path) not in parsed_lvst_files:
            parsed_lvst_files.append(str(lvst_path))
        source_rel = _display_source_path(package_dir, lvst_path)
        for row in table.rows:
            event_id = row.values.get(SCHEDULE_EVENT_ID)
            if not isinstance(event_id, int) or event_id <= 0:
                continue
            text_hash_value = row.values.get(SCHEDULE_TEXT_HASH)
            event_name_jp, event_name_us, name_label = _resolve_name(
                event_id,
                label_index,
                hash_index,
                text_hash_value,
                plaintext_labels,
            )
            text_hash_entry = None
            text_hash_int = _hash_text_to_int(text_hash_value)
            if text_hash_int is not None and hash_index.get(text_hash_int):
                text_hash_entry = hash_index[text_hash_int][0]
            text_hash_jp = _clean_display_text(_text_value(text_hash_entry, "JP"))
            text_hash_us = _clean_display_text(_text_value(text_hash_entry, "US"))
            if text_hash_entry is not None and _is_tokenized_entry(text_hash_entry):
                plaintext = plaintext_labels.get(text_hash_entry.hash_label)
                if plaintext is not None:
                    text_hash_jp, text_hash_us = plaintext
            start_date = row.values.get(SCHEDULE_START_DATE) if isinstance(row.values.get(SCHEDULE_START_DATE), str) else ""
            start_time = row.values.get(SCHEDULE_START_TIME) if isinstance(row.values.get(SCHEDULE_START_TIME), str) else ""
            end_date = row.values.get(SCHEDULE_END_DATE) if isinstance(row.values.get(SCHEDULE_END_DATE), str) else ""
            end_time = row.values.get(SCHEDULE_END_TIME) if isinstance(row.values.get(SCHEDULE_END_TIME), str) else ""
            linked_challenges = [
                challenge
                for challenge in challenge_map.get(event_id, [])
                if _datetime_ranges_overlap(
                    start_date,
                    start_time,
                    end_date,
                    end_time,
                    challenge.start_date,
                    challenge.start_time,
                    challenge.end_date,
                    challenge.end_time,
                )
            ]
            events.append(
                GameEventRecord(
                    event_id=event_id,
                    event_name_jp=event_name_jp,
                    event_name_us=event_name_us,
                    name_label=name_label,
                    start_date=start_date,
                    start_time=start_time,
                    end_date=end_date,
                    end_time=end_time,
                    source_file=str(lvst_path),
                    source_lvst=source_rel,
                    row_index=row.index,
                    order_value=row.values.get(SCHEDULE_ORDER) if isinstance(row.values.get(SCHEDULE_ORDER), int) else None,
                    text_hash=text_hash_value if isinstance(text_hash_value, str) else "",
                    text_hash_jp=text_hash_jp,
                    text_hash_us=text_hash_us,
                    extra_value=row.values.get(SCHEDULE_EXTRA) if isinstance(row.values.get(SCHEDULE_EXTRA), int) else None,
                    ranking_info=ranking_info_map.get(event_id),
                    challenges=linked_challenges,
                )
            )

    events.sort(
        key=lambda event: (
            event.start_date or "9999-99-99",
            event.start_time or "99:99:99",
            event.event_id,
            event.source_lvst,
            event.row_index,
        )
    )
    return GameEventDataset(
        root_dir=str(package_dir),
        package_dirs=[str(package_dir)],
        act_files=[str(path) for path in act_files],
        lvst_files=[str(path) for path in lvst_files],
        parsed_act_files=parsed_act_files,
        parsed_lvst_files=parsed_lvst_files,
        events=events,
        challenges=challenges,
        drops=drops,
        catalog_items=catalog_items,
        warnings=warnings,
        plaintext_labels=plaintext_labels,
    )


def parse_game_event_directory(path: str | Path, extra_act_sources: list[str | Path] | None = None) -> GameEventDataset:
    root_dir = Path(path)
    if not root_dir.is_dir():
        raise ValueError(f"{root_dir} is not a directory.")

    package_dirs = _list_package_dirs(root_dir)
    shared_plaintext_labels = _collect_sibling_plaintext_labels(root_dir)
    extra_act_files = _list_extra_act_files([Path(source) for source in extra_act_sources or []])
    extra_warnings: list[str] = []
    parsed_extra_act_files, fallback_label_index, fallback_hash_index, fallback_plaintext_labels = _build_act_indexes(
        extra_act_files,
        extra_warnings,
    )

    combined_act_files: list[str] = []
    combined_lvst_files: list[str] = []
    combined_parsed_act_files: list[str] = []
    combined_parsed_lvst_files: list[str] = []
    combined_events: list[GameEventRecord] = []
    combined_challenges: list[GameEventChallenge] = []
    combined_drops: list[GameEventDrop] = []
    combined_catalog_items: list[GameEventCatalogItem] = []
    combined_warnings: list[str] = []
    combined_package_dirs: list[str] = []
    combined_plaintext_labels = dict(shared_plaintext_labels)

    combined_act_files.extend(str(path) for path in extra_act_files)
    combined_parsed_act_files.extend(parsed_extra_act_files)
    combined_warnings.extend(extra_warnings)

    for package_dir in package_dirs:
        dataset = _parse_single_game_event_directory(
            package_dir,
            dict(shared_plaintext_labels),
            fallback_label_index,
            fallback_hash_index,
            fallback_plaintext_labels,
        )
        combined_package_dirs.append(str(package_dir))
        combined_act_files.extend(dataset.act_files)
        combined_lvst_files.extend(dataset.lvst_files)
        combined_parsed_act_files.extend(dataset.parsed_act_files)
        combined_parsed_lvst_files.extend(dataset.parsed_lvst_files)
        combined_events.extend(dataset.events)
        combined_challenges.extend(dataset.challenges)
        combined_drops.extend(dataset.drops)
        combined_catalog_items.extend(dataset.catalog_items)
        combined_warnings.extend(dataset.warnings)
        for label, texts in dataset.plaintext_labels.items():
            combined_plaintext_labels.setdefault(label, texts)

    combined_events.sort(
        key=lambda event: (
            event.start_date or "9999-99-99",
            event.start_time or "99:99:99",
            event.event_id,
            event.source_lvst,
            event.row_index,
        )
    )
    combined_challenges.sort(
        key=lambda challenge: (
            challenge.start_date or "9999-99-99",
            challenge.start_time or "99:99:99",
            challenge.target_id if challenge.target_id is not None else -1,
            challenge.source_lvst,
            challenge.row_index,
        )
    )
    combined_drops.sort(
        key=lambda drop: (
            drop.start_date or "9999-99-99",
            drop.start_time or "99:99:99",
            drop.drop_id,
            drop.source_lvst,
            drop.row_index,
        )
    )
    combined_catalog_items.sort(
        key=lambda item: (
            item.sort_id if item.sort_id is not None else 9999999999,
            item.category if item.category is not None else -1,
            item.item_id if item.item_id is not None else -1,
            item.source_lvst,
            item.table_kind,
            item.row_index,
        )
    )
    return GameEventDataset(
        root_dir=str(root_dir),
        package_dirs=combined_package_dirs,
        act_files=combined_act_files,
        lvst_files=combined_lvst_files,
        parsed_act_files=combined_parsed_act_files,
        parsed_lvst_files=combined_parsed_lvst_files,
        events=combined_events,
        challenges=combined_challenges,
        drops=combined_drops,
        catalog_items=combined_catalog_items,
        warnings=combined_warnings,
        plaintext_labels=combined_plaintext_labels,
    )
