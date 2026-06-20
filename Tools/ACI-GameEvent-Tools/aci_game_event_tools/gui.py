from __future__ import annotations

from dataclasses import dataclass
import json
import sys
import traceback
from pathlib import Path

from PyQt5.QtCore import QSignalBlocker, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ace_table_parser import (
    LVSTColumnType,
    encode_date_text,
    encode_time_text,
    parse_ace_table,
    patch_ace_table_u32_cell_in_data,
)
from .event_parser import (
    CHALLENGE_END_DATE,
    CHALLENGE_END_TIME,
    CHALLENGE_START_DATE,
    CHALLENGE_START_TIME,
    DROP_END_DATE,
    DROP_END_TIME,
    DROP_START_DATE,
    DROP_START_TIME,
    SCHEDULE_END_DATE,
    SCHEDULE_END_TIME,
    SCHEDULE_START_DATE,
    SCHEDULE_START_TIME,
    GameEventChallenge,
    GameEventCatalogItem,
    GameEventDataset,
    GameEventDrop,
    GameEventRecord,
    parse_game_event_directory,
)


WINDOW_STYLESHEET = """
QWidget {
    background: #1f2228;
    color: #d7dde8;
}
QGroupBox {
    border: 1px solid #3b4048;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLineEdit, QTextEdit, QTableWidget {
    background: #171a1f;
    border: 1px solid #3b4048;
    selection-background-color: #ff5a36;
    selection-color: #ffffff;
}
QPushButton {
    background: #2a2f37;
    border: 1px solid #4b525d;
    padding: 6px 10px;
}
QPushButton:hover {
    background: #323844;
}
QHeaderView::section {
    background: #2a2f37;
    color: #d7dde8;
    border: 1px solid #3b4048;
    padding: 4px;
}
QTabWidget::pane {
    border: 1px solid #3b4048;
}
QTabBar::tab {
    background: #2a2f37;
    color: #d7dde8;
    padding: 8px 14px;
    border: 1px solid #3b4048;
}
QTabBar::tab:selected {
    background: #1f2228;
}
QSplitter::handle {
    background: #313742;
}
"""


def _normalize_path_text(path: str | Path) -> str:
    return str(path).strip().replace("\\", "/")


def _join_datetime(date_text: str, time_text: str) -> str:
    if date_text and time_text:
        return f"{date_text} {time_text}"
    return date_text or time_text


def _source_package_name(source_lvst: str) -> str:
    prefix = source_lvst.split("/", 1)[0]
    if prefix.startswith("NPWR04428_00-"):
        return prefix
    return "(Current Package)"


def _source_package_order(source_lvst: str) -> tuple[int, str]:
    package_name = _source_package_name(source_lvst)
    if package_name.startswith("NPWR04428_00-"):
        suffix = package_name.removeprefix("NPWR04428_00-")
        try:
            return int(suffix), package_name
        except ValueError:
            return -1, package_name
    return -1, package_name


def _is_event_title_like_label(label: str) -> bool:
    return (
        label.startswith("InfoMsg_EventTitle_")
        or label.startswith("ShortName_RankEvent")
        or label.startswith("LongName_RankEvent")
        or label.startswith("Reward_RankEvent")
    )


@dataclass(frozen=True)
class EventDisplayItem:
    event: GameEventRecord
    events: list[GameEventRecord]
    source_text: str
    effective_package_text: str
    display_name: str

    @property
    def challenge_count(self) -> int:
        return sum(len(event.challenges) for event in self.events)


@dataclass(frozen=True)
class ChallengeDisplayItem:
    challenge: GameEventChallenge
    challenges: list[GameEventChallenge]
    source_text: str
    effective_package_text: str
    target_text: str
    title_text: str
    message_text: str

    @property
    def start_text(self) -> str:
        return _join_datetime(self.challenge.start_date, self.challenge.start_time)

    @property
    def end_text(self) -> str:
        return _join_datetime(self.challenge.end_date, self.challenge.end_time)


@dataclass(frozen=True)
class DropDisplayItem:
    drop: GameEventDrop
    drops: list[GameEventDrop]
    source_text: str
    effective_package_text: str
    title_text: str

    @property
    def start_text(self) -> str:
        return _join_datetime(self.drop.start_date, self.drop.start_time)

    @property
    def end_text(self) -> str:
        return _join_datetime(self.drop.end_date, self.drop.end_time)


@dataclass(frozen=True)
class CatalogDisplayItem:
    item: GameEventCatalogItem
    items: list[GameEventCatalogItem]
    source_text: str
    effective_package_text: str
    name_text: str
    desc_text: str


@dataclass(frozen=True)
class EventDateOverride:
    start_date: str
    start_time: str
    end_date: str
    end_time: str


class EventDateEditDialog(QDialog):
    def __init__(self, event: GameEventRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit Event {event.event_id} Dates")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form_layout = QGridLayout()

        self.start_date_edit = QLineEdit(event.start_date)
        self.start_time_edit = QLineEdit(event.start_time)
        self.end_date_edit = QLineEdit(event.end_date)
        self.end_time_edit = QLineEdit(event.end_time)

        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.start_time_edit.setPlaceholderText("HH:MM:SS")
        self.end_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.end_time_edit.setPlaceholderText("HH:MM:SS")

        form_layout.addWidget(QLabel("Start Date"), 0, 0)
        form_layout.addWidget(self.start_date_edit, 0, 1)
        form_layout.addWidget(QLabel("Start Time"), 1, 0)
        form_layout.addWidget(self.start_time_edit, 1, 1)
        form_layout.addWidget(QLabel("End Date"), 2, 0)
        form_layout.addWidget(self.end_date_edit, 2, 1)
        form_layout.addWidget(QLabel("End Time"), 3, 0)
        form_layout.addWidget(self.end_time_edit, 3, 1)
        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def values(self) -> EventDateOverride:
        return EventDateOverride(
            start_date=self.start_date_edit.text().strip(),
            start_time=self.start_time_edit.text().strip(),
            end_date=self.end_date_edit.text().strip(),
            end_time=self.end_time_edit.text().strip(),
        )


class ChallengeDateEditDialog(QDialog):
    def __init__(
        self,
        challenge: GameEventChallenge,
        values: EventDateOverride | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit Challenge Row {challenge.row_index} Dates")
        self.setModal(True)

        initial = values or EventDateOverride(
            start_date=challenge.start_date,
            start_time=challenge.start_time,
            end_date=challenge.end_date,
            end_time=challenge.end_time,
        )

        layout = QVBoxLayout(self)
        form_layout = QGridLayout()

        self.start_date_edit = QLineEdit(initial.start_date)
        self.start_time_edit = QLineEdit(initial.start_time)
        self.end_date_edit = QLineEdit(initial.end_date)
        self.end_time_edit = QLineEdit(initial.end_time)

        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.start_time_edit.setPlaceholderText("HH:MM:SS")
        self.end_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.end_time_edit.setPlaceholderText("HH:MM:SS")

        form_layout.addWidget(QLabel("Start Date"), 0, 0)
        form_layout.addWidget(self.start_date_edit, 0, 1)
        form_layout.addWidget(QLabel("Start Time"), 1, 0)
        form_layout.addWidget(self.start_time_edit, 1, 1)
        form_layout.addWidget(QLabel("End Date"), 2, 0)
        form_layout.addWidget(self.end_date_edit, 2, 1)
        form_layout.addWidget(QLabel("End Time"), 3, 0)
        form_layout.addWidget(self.end_time_edit, 3, 1)
        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def values(self) -> EventDateOverride:
        return EventDateOverride(
            start_date=self.start_date_edit.text().strip(),
            start_time=self.start_time_edit.text().strip(),
            end_date=self.end_date_edit.text().strip(),
            end_time=self.end_time_edit.text().strip(),
        )


class DropDateEditDialog(QDialog):
    def __init__(
        self,
        drop: GameEventDrop,
        values: EventDateOverride | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit Drop Row {drop.row_index} Dates")
        self.setModal(True)

        initial = values or EventDateOverride(
            start_date=drop.start_date,
            start_time=drop.start_time,
            end_date=drop.end_date,
            end_time=drop.end_time,
        )

        layout = QVBoxLayout(self)
        form_layout = QGridLayout()

        self.start_date_edit = QLineEdit(initial.start_date)
        self.start_time_edit = QLineEdit(initial.start_time)
        self.end_date_edit = QLineEdit(initial.end_date)
        self.end_time_edit = QLineEdit(initial.end_time)

        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.start_time_edit.setPlaceholderText("HH:MM:SS")
        self.end_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.end_time_edit.setPlaceholderText("HH:MM:SS")

        form_layout.addWidget(QLabel("Start Date"), 0, 0)
        form_layout.addWidget(self.start_date_edit, 0, 1)
        form_layout.addWidget(QLabel("Start Time"), 1, 0)
        form_layout.addWidget(self.start_time_edit, 1, 1)
        form_layout.addWidget(QLabel("End Date"), 2, 0)
        form_layout.addWidget(self.end_date_edit, 2, 1)
        form_layout.addWidget(QLabel("End Time"), 3, 0)
        form_layout.addWidget(self.end_time_edit, 3, 1)
        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def values(self) -> EventDateOverride:
        return EventDateOverride(
            start_date=self.start_date_edit.text().strip(),
            start_time=self.start_time_edit.text().strip(),
            end_date=self.end_date_edit.text().strip(),
            end_time=self.end_time_edit.text().strip(),
        )


class ChallengeListDialog(QDialog):
    def __init__(
        self,
        display_item: EventDisplayItem,
        challenges: list[GameEventChallenge],
        parent: "MainWindow",
    ) -> None:
        super().__init__(parent)
        self.display_item = display_item
        self.challenges = challenges
        self.main_window = parent

        self.setWindowTitle(f"Linked Challenges - Event {display_item.event.event_id}")
        self.resize(1120, 620)
        self.setModal(False)

        layout = QVBoxLayout(self)
        title = QLabel(
            f"Event {display_item.event.event_id}: {display_item.display_name or '(unresolved)'} "
            f"({len(challenges)} challenge row(s))"
        )
        layout.addWidget(title)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            ["Source", "Row", "Target ID", "Start", "End", "Title (US)", "Title (JP)", "Message (US)", "Title Hash", "Message Hash"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.itemDoubleClicked.connect(self._edit_selected_challenge)
        layout.addWidget(self.table, stretch=1)

        button_layout = QHBoxLayout()
        edit_button = QPushButton("Edit Selected Date/Time")
        reset_button = QPushButton("Reset Selected Date/Time")
        close_button = QPushButton("Close")
        edit_button.clicked.connect(self._edit_selected_challenge)
        reset_button.clicked.connect(self._reset_selected_challenge)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(reset_button)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        self._refresh_rows()

    def _refresh_rows(self) -> None:
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self.challenges))
            for row_index, challenge in enumerate(self.challenges):
                values = [
                    challenge.source_lvst,
                    str(challenge.row_index),
                    str(challenge.target_id) if challenge.target_id is not None else "",
                    self.main_window._challenge_start_text(challenge),
                    self.main_window._challenge_end_text(challenge),
                    challenge.title_us or "(unresolved)",
                    challenge.title_jp or "(unresolved)",
                    challenge.message_us or "(unresolved)",
                    challenge.title_hash or "(none)",
                    challenge.message_hash or "(none)",
                ]
                is_edited = self.main_window._has_challenge_override(challenge)
                for column_index, value in enumerate(values):
                    item = self.table.item(row_index, column_index)
                    if item is None:
                        item = QTableWidgetItem()
                        self.table.setItem(row_index, column_index, item)
                    item.setText(value)
                    item.setData(Qt.UserRole, row_index)
                    item.setToolTip("Edited" if is_edited and column_index in {3, 4} else "")
        finally:
            self.table.setUpdatesEnabled(True)

    def _selected_challenge(self) -> GameEventChallenge | None:
        selected_rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        if not selected_rows:
            return None
        row_index = selected_rows[0].row()
        if row_index < 0 or row_index >= len(self.challenges):
            return None
        return self.challenges[row_index]

    def _edit_selected_challenge(self, *_args) -> None:
        challenge = self._selected_challenge()
        if challenge is None:
            return
        self._edit_challenge(challenge)

    def _edit_challenge(self, challenge: GameEventChallenge) -> None:
        dialog = ChallengeDateEditDialog(challenge, self.main_window._challenge_override(challenge), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        override = dialog.values()
        try:
            self.main_window._validate_challenge_override(override)
        except Exception as exc:
            QMessageBox.warning(self, "Edit Challenge Dates", f"Invalid date/time value:\n{exc}")
            return

        key = self.main_window._challenge_override_key(challenge)
        if (
            override.start_date == challenge.start_date
            and override.start_time == challenge.start_time
            and override.end_date == challenge.end_date
            and override.end_time == challenge.end_time
        ):
            self.main_window.challenge_date_overrides.pop(key, None)
        else:
            self.main_window.challenge_date_overrides[key] = override
        self._refresh_rows()
        self.main_window._refresh_summary()
        self.main_window._apply_challenge_filter()
        self.main_window._sync_selected_event()
        self.main_window.statusBar().showMessage(
            f"Edited challenge row {challenge.row_index} in {challenge.source_lvst}"
        )

    def _reset_selected_challenge(self) -> None:
        challenge = self._selected_challenge()
        if challenge is None:
            return
        if self.main_window.challenge_date_overrides.pop(self.main_window._challenge_override_key(challenge), None) is None:
            return
        self._refresh_rows()
        self.main_window._refresh_summary()
        self.main_window._apply_challenge_filter()
        self.main_window._sync_selected_event()
        self.main_window.statusBar().showMessage(
            f"Reset challenge row {challenge.row_index} in {challenge.source_lvst}"
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ACI Game Event Tools")
        self.resize(1360, 920)
        self.setStyleSheet(WINDOW_STYLESHEET)

        self.project_root = Path(__file__).resolve().parents[1]
        self.current_dataset: GameEventDataset | None = None
        self.filtered_display_items: list[EventDisplayItem] = []
        self.filtered_challenge_items: list[ChallengeDisplayItem] = []
        self.filtered_drop_items: list[DropDisplayItem] = []
        self.filtered_catalog_items: list[CatalogDisplayItem] = []
        self.sort_column = 2
        self.sort_descending = False
        self.challenge_sort_column = 1
        self.challenge_sort_descending = False
        self.drop_sort_column = 1
        self.drop_sort_descending = False
        self.catalog_sort_column = 1
        self.catalog_sort_descending = False
        self.full_game_act_json_hash_to_label: dict[str, str] = {}
        self.paratranz_label_to_text: dict[str, str] = {}
        self.date_overrides: dict[tuple[str, int], EventDateOverride] = {}
        self.challenge_date_overrides: dict[tuple[str, int], EventDateOverride] = {}
        self.drop_date_overrides: dict[tuple[str, int], EventDateOverride] = {}

        self.tabs = QTabWidget()
        self.tss_dir_edit = QLineEdit()
        self.full_game_act_source_edit = QLineEdit()
        self.full_game_act_json_edit = QLineEdit()
        self.paratranz_json_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        self.package_filter_combo = QComboBox()
        self.package_filter_combo.addItem("All Packages", "")
        self.merge_mode_combo = QComboBox()
        self.merge_mode_combo.addItem("Merged by Event ID", "event_id")
        self.merge_mode_combo.addItem("Merged by Content", "content")
        self.merge_mode_combo.addItem("Raw Rows", "raw")
        self.event_filter_edit = QLineEdit()
        self.event_filter_edit.setPlaceholderText("Search by ID, name, source, label, or linked challenge text")
        self.challenge_filter_edit = QLineEdit()
        self.challenge_filter_edit.setPlaceholderText("Search by target id, title, message, or source")
        self.drop_filter_edit = QLineEdit()
        self.drop_filter_edit.setPlaceholderText("Search by drop id, title, source, or date")
        self.catalog_filter_edit = QLineEdit()
        self.catalog_filter_edit.setPlaceholderText("Search by item id, category, name, description, group, source, or label")
        self.event_table = QTableWidget(0, 7)
        self.event_table.setHorizontalHeaderLabels(["ID", "Name", "Start", "End", "Effective Package", "Source", "Challenges"])
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.event_table.setWordWrap(False)
        self.event_table.setAlternatingRowColors(False)
        self.event_table.horizontalHeader().setSectionsClickable(True)
        self.event_table.horizontalHeader().setSortIndicatorShown(True)
        self.event_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.event_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.event_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.challenge_table = QTableWidget(0, 7)
        self.challenge_table.setHorizontalHeaderLabels(["Target ID", "Start", "End", "Title", "Message", "Source", "Row"])
        self.challenge_table.verticalHeader().setVisible(False)
        self.challenge_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.challenge_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.challenge_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.challenge_table.setWordWrap(False)
        self.challenge_table.setAlternatingRowColors(False)
        self.challenge_table.horizontalHeader().setSectionsClickable(True)
        self.challenge_table.horizontalHeader().setSortIndicatorShown(True)
        self.challenge_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.challenge_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.challenge_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.challenge_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.challenge_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.challenge_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.challenge_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.challenge_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.drop_table = QTableWidget(0, 7)
        self.drop_table.setHorizontalHeaderLabels(["Drop ID", "Start", "End", "Title", "Flags", "Source", "Row"])
        self.drop_table.verticalHeader().setVisible(False)
        self.drop_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.drop_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.drop_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.drop_table.setWordWrap(False)
        self.drop_table.setAlternatingRowColors(False)
        self.drop_table.horizontalHeader().setSectionsClickable(True)
        self.drop_table.horizontalHeader().setSortIndicatorShown(True)
        self.drop_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.drop_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.drop_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.drop_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.drop_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.drop_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.drop_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.drop_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.catalog_table = QTableWidget(0, 10)
        self.catalog_table.setHorizontalHeaderLabels(
            ["Category", "Name", "Description", "Group ID", "Item ID", "Content ID", "Price", "Effective Package", "Source", "Row"]
        )
        self.catalog_table.verticalHeader().setVisible(False)
        self.catalog_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.catalog_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.catalog_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.catalog_table.setWordWrap(False)
        self.catalog_table.setAlternatingRowColors(False)
        self.catalog_table.horizontalHeader().setSectionsClickable(True)
        self.catalog_table.horizontalHeader().setSortIndicatorShown(True)
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.summary_edit = QTextEdit()
        self.summary_edit.setReadOnly(True)
        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)

        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar())

        self.tabs.addTab(self._build_game_event_view_page(), "Game Event View")
        self.tabs.addTab(self._build_challenge_view_page(), "Challenge View")
        self.tabs.addTab(self._build_drop_view_page(), "Event Drop View")
        self.tabs.addTab(self._build_catalog_view_page(), "Reward Catalog View")

        self.event_filter_edit.textChanged.connect(self._apply_event_filter)
        self.challenge_filter_edit.textChanged.connect(self._apply_challenge_filter)
        self.drop_filter_edit.textChanged.connect(self._apply_drop_filter)
        self.catalog_filter_edit.textChanged.connect(self._apply_catalog_filter)
        self.package_filter_combo.currentIndexChanged.connect(self._apply_event_filter)
        self.package_filter_combo.currentIndexChanged.connect(self._apply_catalog_filter)
        self.merge_mode_combo.currentIndexChanged.connect(self._apply_event_filter)
        self.event_table.itemSelectionChanged.connect(self._sync_selected_event)
        self.event_table.itemDoubleClicked.connect(self._open_event_challenges_from_item)
        self.event_table.horizontalHeader().sectionClicked.connect(self._handle_header_sort)
        self.event_table.customContextMenuRequested.connect(self._show_event_context_menu)
        self.challenge_table.itemSelectionChanged.connect(self._sync_selected_challenge)
        self.challenge_table.itemDoubleClicked.connect(self._edit_selected_challenge_from_item)
        self.challenge_table.horizontalHeader().sectionClicked.connect(self._handle_challenge_header_sort)
        self.challenge_table.customContextMenuRequested.connect(self._show_challenge_context_menu)
        self.drop_table.itemSelectionChanged.connect(self._sync_selected_drop)
        self.drop_table.itemDoubleClicked.connect(self._edit_selected_drop_from_item)
        self.drop_table.horizontalHeader().sectionClicked.connect(self._handle_drop_header_sort)
        self.drop_table.customContextMenuRequested.connect(self._show_drop_context_menu)
        self.catalog_table.itemSelectionChanged.connect(self._sync_selected_catalog)
        self.catalog_table.horizontalHeader().sectionClicked.connect(self._handle_catalog_header_sort)
        self.tss_dir_edit.returnPressed.connect(self._load_from_edit)

        self.statusBar().showMessage("Ready")

    def _make_button(self, label: str, callback) -> QPushButton:
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def _build_game_event_view_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        source_group = QGroupBox("Game Event Source")
        source_layout = QGridLayout(source_group)
        browse_button = self._make_button("Select Folder", self._browse_tss_dir)
        load_button = self._make_button("Load", self._load_from_edit)
        act_source_browse_button = self._make_button("Select File/Folder", self._browse_full_game_act_source)
        act_json_browse_button = self._make_button("Select File", self._browse_full_game_act_json)
        paratranz_browse_button = self._make_button("Select File", self._browse_paratranz_json)
        output_browse_button = self._make_button("Select Folder", self._browse_output_dir)
        export_button = self._make_button("Export", self._export_modified_lvst_files)
        source_layout.addWidget(QLabel("TSS Root / Package Dir"), 0, 0)
        source_layout.addWidget(self.tss_dir_edit, 0, 1)
        source_layout.addWidget(browse_button, 0, 2)
        source_layout.addWidget(load_button, 0, 3)
        source_layout.addWidget(QLabel("Full Game ACT Source"), 1, 0)
        source_layout.addWidget(self.full_game_act_source_edit, 1, 1)
        source_layout.addWidget(act_source_browse_button, 1, 2)
        source_layout.addWidget(QLabel(""), 1, 3)
        source_layout.addWidget(QLabel("Full Game ACT Json"), 2, 0)
        source_layout.addWidget(self.full_game_act_json_edit, 2, 1)
        source_layout.addWidget(act_json_browse_button, 2, 2)
        source_layout.addWidget(QLabel(""), 2, 3)
        source_layout.addWidget(QLabel("ParaTranz Json"), 3, 0)
        source_layout.addWidget(self.paratranz_json_edit, 3, 1)
        source_layout.addWidget(paratranz_browse_button, 3, 2)
        source_layout.addWidget(QLabel(""), 3, 3)
        source_layout.addWidget(QLabel("Output Dir"), 4, 0)
        source_layout.addWidget(self.output_dir_edit, 4, 1)
        source_layout.addWidget(output_browse_button, 4, 2)
        source_layout.addWidget(export_button, 4, 3)
        source_layout.addWidget(QLabel("Package"), 5, 0)
        source_layout.addWidget(self.package_filter_combo, 5, 1)
        source_layout.addWidget(QLabel("Merge Mode"), 5, 2)
        source_layout.addWidget(self.merge_mode_combo, 5, 3)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.addWidget(self._build_event_left_panel())
        content_splitter.addWidget(self._build_event_right_panel())
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)

        layout.addWidget(source_group)
        layout.addWidget(content_splitter, stretch=1)
        return page

    def _build_challenge_view_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        filter_group = QGroupBox("Challenge List")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.addWidget(self.challenge_filter_edit)
        filter_layout.addWidget(self.challenge_table, stretch=1)

        layout.addWidget(filter_group, stretch=1)
        return page

    def _build_drop_view_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        filter_group = QGroupBox("Event Drop List")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.addWidget(self.drop_filter_edit)
        filter_layout.addWidget(self.drop_table, stretch=1)

        layout.addWidget(filter_group, stretch=1)
        return page

    def _build_catalog_view_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        filter_group = QGroupBox("Reward Catalog List")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.addWidget(self.catalog_filter_edit)
        filter_layout.addWidget(self.catalog_table, stretch=1)

        layout.addWidget(filter_group, stretch=1)
        return page

    def _build_event_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        list_group = QGroupBox("Event List")
        list_layout = QVBoxLayout(list_group)
        list_layout.addWidget(self.event_filter_edit)
        list_layout.addWidget(self.event_table, stretch=1)

        layout.addWidget(list_group, stretch=1)
        return panel

    def _build_event_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(self.summary_edit)

        detail_group = QGroupBox("Event Detail")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(self.detail_edit)

        layout.addWidget(summary_group, stretch=1)
        layout.addWidget(detail_group, stretch=2)
        return panel

    def _browse_tss_dir(self) -> None:
        current = self.tss_dir_edit.text().strip()
        selected = QFileDialog.getExistingDirectory(self, "Select Unpacked TSS Directory", current or str(self.project_root))
        if selected:
            self.tss_dir_edit.setText(_normalize_path_text(selected))
            self._load_from_edit()

    def _browse_full_game_act_source(self) -> None:
        current = self.full_game_act_source_edit.text().strip()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Full Game ACT File",
            current or str(self.project_root),
            "ACEText Files (*.act);;All Files (*.*)",
        )
        if not selected:
            selected = QFileDialog.getExistingDirectory(
                self,
                "Select Full Game ACT Directory",
                current or str(self.project_root),
            )
        if selected:
            self.full_game_act_source_edit.setText(_normalize_path_text(selected))
            if self.tss_dir_edit.text().strip():
                self._load_from_edit()

    def _browse_full_game_act_json(self) -> None:
        current = self.full_game_act_json_edit.text().strip()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Full Game ACT Json",
            current or str(self.project_root),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if selected:
            self.full_game_act_json_edit.setText(_normalize_path_text(selected))
            self._reload_external_name_sources()

    def _browse_paratranz_json(self) -> None:
        current = self.paratranz_json_edit.text().strip()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select ParaTranz Json",
            current or str(self.project_root),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if selected:
            self.paratranz_json_edit.setText(_normalize_path_text(selected))
            self._reload_external_name_sources()

    def _browse_output_dir(self) -> None:
        current = self.output_dir_edit.text().strip()
        selected = QFileDialog.getExistingDirectory(self, "Select Output Directory", current or str(self.project_root))
        if selected:
            self.output_dir_edit.setText(_normalize_path_text(selected))

    def _load_from_edit(self) -> None:
        path_text = self.tss_dir_edit.text().strip()
        if not path_text:
            QMessageBox.warning(self, "Load Game Events", "Select a TSS unpack directory first.")
            return
        self._load_game_event_directory(Path(path_text))

    def _load_game_event_directory(self, root_dir: Path) -> None:
        try:
            self.statusBar().showMessage("Loading game event data...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            extra_act_sources = []
            full_game_act_source_text = self.full_game_act_source_edit.text().strip()
            if full_game_act_source_text:
                extra_act_sources.append(Path(full_game_act_source_text))
            dataset = parse_game_event_directory(root_dir, extra_act_sources=extra_act_sources)
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Load Game Events", f"Failed to load game event data:\n{exc}")
            self.statusBar().showMessage("Load failed")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.current_dataset = dataset
        self.date_overrides.clear()
        self.challenge_date_overrides.clear()
        self.drop_date_overrides.clear()
        self.tss_dir_edit.setText(_normalize_path_text(root_dir))
        self._reload_external_name_sources(refresh=False)
        self._refresh_package_filter()
        self._apply_event_filter()
        self._apply_challenge_filter()
        self._apply_drop_filter()
        self._apply_catalog_filter()
        self._refresh_summary()
        warning_suffix = f", warnings={len(dataset.warnings)}" if dataset.warnings else ""
        self.statusBar().showMessage(
            f"Loaded {len(dataset.events)} event rows, {len(dataset.drops)} drop rows, {len(dataset.catalog_items)} catalog rows{warning_suffix}"
        )

    def _load_full_game_act_json_hash_to_label(self, path: Path) -> dict[str, str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("ACT Json root must be an object.")
        result: dict[str, str] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            hash_text = value.get("Hash")
            if isinstance(hash_text, str):
                normalized_hash = hash_text.strip().lower()
                if normalized_hash.startswith("0x"):
                    result[normalized_hash] = key
        return result

    def _load_paratranz_label_to_text(self, path: Path) -> dict[str, str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("ParaTranz Json root must be an array.")
        result: dict[str, str] = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key")
            if not isinstance(key, str) or not key:
                continue
            translation = entry.get("translation")
            original = entry.get("original")
            if isinstance(translation, str) and translation.strip():
                result[key] = translation
            elif isinstance(original, str) and original.strip():
                result[key] = original
        return result

    def _reload_external_name_sources(self, refresh: bool = True) -> None:
        self.full_game_act_json_hash_to_label = {}
        self.paratranz_label_to_text = {}

        act_json_path_text = self.full_game_act_json_edit.text().strip()
        if act_json_path_text:
            try:
                self.full_game_act_json_hash_to_label = self._load_full_game_act_json_hash_to_label(Path(act_json_path_text))
            except Exception as exc:
                QMessageBox.warning(self, "Load Full Game ACT Json", f"Failed to load ACT Json:\n{exc}")
                self.full_game_act_json_hash_to_label = {}

        paratranz_path_text = self.paratranz_json_edit.text().strip()
        if paratranz_path_text:
            try:
                self.paratranz_label_to_text = self._load_paratranz_label_to_text(Path(paratranz_path_text))
            except Exception as exc:
                QMessageBox.warning(self, "Load ParaTranz Json", f"Failed to load ParaTranz Json:\n{exc}")
                self.paratranz_label_to_text = {}

        if refresh and self.current_dataset is not None:
            self._apply_event_filter()
            self._apply_challenge_filter()
            self._apply_drop_filter()
            self._apply_catalog_filter()

    def _is_shared_text_hash_across_events(self, hash_text: str, event_id: int) -> bool:
        dataset = self.current_dataset
        if dataset is None:
            return False
        normalized_hash = hash_text.strip().lower()
        if not normalized_hash.startswith("0x"):
            return False
        event_ids = {
            candidate.event_id
            for candidate in dataset.events
            if candidate.text_hash.strip().lower() == normalized_hash
        }
        return len(event_ids - {event_id}) > 0

    def _resolve_external_name(self, event: GameEventRecord) -> str:
        if event.name_label:
            label_text = self.paratranz_label_to_text.get(event.name_label, "")
            if label_text:
                return label_text
        hash_text = event.text_hash.strip().lower()
        if not hash_text.startswith("0x"):
            return ""
        label = self.full_game_act_json_hash_to_label.get(hash_text)
        if not label:
            return ""
        if not _is_event_title_like_label(label):
            return ""
        if self._is_shared_text_hash_across_events(hash_text, event.event_id):
            return ""
        return self.paratranz_label_to_text.get(label, "")

    def _resolve_external_label_from_hash(self, hash_text: str) -> str:
        normalized_hash = hash_text.strip().lower()
        if not normalized_hash.startswith("0x"):
            return ""
        return self.full_game_act_json_hash_to_label.get(normalized_hash, "")

    def _resolve_external_text_from_hash(self, hash_text: str) -> str:
        label = self._resolve_external_label_from_hash(hash_text)
        if not label:
            return ""
        return self.paratranz_label_to_text.get(label, "")

    def _resolve_challenge_label(self, hash_text: str, parsed_label: str) -> str:
        if parsed_label:
            return parsed_label
        return self._resolve_external_label_from_hash(hash_text)

    def _resolve_challenge_translation(self, hash_text: str, parsed_label: str) -> str:
        label = self._resolve_challenge_label(hash_text, parsed_label)
        if not label:
            return ""
        return self.paratranz_label_to_text.get(label, "")

    def _challenge_title_display_text(self, challenge: GameEventChallenge) -> str:
        return (
            self._resolve_challenge_translation(challenge.title_hash, challenge.title_label)
            or challenge.title_us
            or challenge.title_jp
            or challenge.title_hash
            or "(unresolved)"
        )

    def _challenge_message_display_text(self, challenge: GameEventChallenge) -> str:
        return (
            self._resolve_challenge_translation(challenge.message_hash, challenge.message_label)
            or challenge.message_us
            or challenge.message_jp
            or challenge.message_hash
            or "(unresolved)"
        )

    def _catalog_label(self, hash_text: str, parsed_label: str) -> str:
        if parsed_label:
            return parsed_label
        return self._resolve_external_label_from_hash(hash_text)

    def _catalog_translation(self, hash_text: str, parsed_label: str) -> str:
        label = self._catalog_label(hash_text, parsed_label)
        if not label:
            return ""
        return self.paratranz_label_to_text.get(label, "")

    def _catalog_name_display_text(self, item: GameEventCatalogItem) -> str:
        return (
            self._catalog_translation(item.name_hash, item.name_label)
            or item.name_us
            or item.name_jp
            or self._catalog_label(item.name_hash, item.name_label)
            or item.name_hash
            or "(unresolved)"
        )

    def _catalog_desc_display_text(self, item: GameEventCatalogItem) -> str:
        return (
            self._catalog_translation(item.desc_hash, item.desc_label)
            or item.desc_us
            or item.desc_jp
            or self._catalog_label(item.desc_hash, item.desc_label)
            or item.desc_hash
            or ""
        )

    def _build_ranking_proxy_name(self, event: GameEventRecord) -> str:
        ranking = event.ranking_info
        if ranking is None:
            return ""

        for hash_text in (ranking.menu_hash, ranking.mission_hash):
            text = self._resolve_external_text_from_hash(hash_text)
            if text:
                return text

        for text in (
            ranking.menu_us,
            ranking.menu_jp,
            ranking.mission_us,
            ranking.mission_jp,
        ):
            if text:
                return text

        for hash_text, label in (
            (ranking.menu_hash, ranking.menu_label),
            (ranking.mission_hash, ranking.mission_label),
        ):
            external_label = self._resolve_external_label_from_hash(hash_text)
            if external_label:
                return external_label
            if label:
                return label

        if ranking.menu_hash and ranking.mission_hash:
            return f"{ranking.menu_hash} | {ranking.mission_hash}"
        return ranking.menu_hash or ranking.mission_hash

    def _choose_display_name(self, event: GameEventRecord) -> str:
        if event.event_name_us:
            return event.event_name_us
        if event.ranking_info is not None:
            ranking_name = self._build_ranking_proxy_name(event)
            if ranking_name:
                return ranking_name
        external_name = self._resolve_external_name(event)
        if external_name:
            return external_name
        if event.event_name_jp:
            return event.event_name_jp
        if event.ranking_info is not None:
            ranking_name = self._build_ranking_proxy_name(event)
            if ranking_name:
                return ranking_name
        if event.name_label:
            return event.name_label
        return f"Event {event.event_id}"

    def _refresh_package_filter(self) -> None:
        dataset = self.current_dataset
        current_value = self.package_filter_combo.currentData()
        self.package_filter_combo.blockSignals(True)
        self.package_filter_combo.clear()
        self.package_filter_combo.addItem("All Packages", "")
        if dataset is not None:
            package_names = sorted(
                {_source_package_name(event.source_lvst) for event in dataset.events}
                | {_source_package_name(challenge.source_lvst) for challenge in dataset.challenges}
                | {_source_package_name(drop.source_lvst) for drop in dataset.drops}
                | {_source_package_name(item.source_lvst) for item in dataset.catalog_items}
            )
            for package_name in package_names:
                self.package_filter_combo.addItem(package_name, package_name)
        index = self.package_filter_combo.findData(current_value)
        if index < 0:
            index = 0
        self.package_filter_combo.setCurrentIndex(index)
        self.package_filter_combo.blockSignals(False)

    def _build_display_items(self, events: list[GameEventRecord]) -> list[EventDisplayItem]:
        merge_mode = self.merge_mode_combo.currentData()
        if merge_mode == "raw":
            display_items = [
                EventDisplayItem(
                    event=event,
                    events=[event],
                    source_text=event.source_lvst,
                    effective_package_text=_source_package_name(event.source_lvst),
                    display_name=self._choose_display_name(event),
                )
                for event in events
            ]
            return self._sort_display_items(display_items)

        if merge_mode == "event_id":
            grouped_by_event_id: dict[int, list[GameEventRecord]] = {}
            for event in events:
                grouped_by_event_id.setdefault(event.event_id, []).append(event)

            display_items: list[EventDisplayItem] = []
            for event_id, grouped_events in grouped_by_event_id.items():
                del event_id
                representative = max(
                    grouped_events,
                    key=lambda event: (
                        _source_package_order(event.source_lvst)[0],
                        self._event_sort_start_date(event),
                        self._event_sort_start_time(event),
                        event.row_index,
                    ),
                )
                sorted_events = sorted(
                    grouped_events,
                    key=lambda event: (
                        _source_package_order(event.source_lvst)[0],
                        event.source_lvst,
                        event.row_index,
                    ),
                )
                source_text = representative.source_lvst
                if len(sorted_events) > 1:
                    source_text = f"{representative.source_lvst} (+{len(sorted_events) - 1})"
                effective_package_text = _source_package_name(representative.source_lvst)
                if len(sorted_events) > 1:
                    effective_package_text = f"{effective_package_text} (+{len(sorted_events) - 1})"
                display_items.append(
                    EventDisplayItem(
                        event=representative,
                        events=sorted_events,
                        source_text=source_text,
                        effective_package_text=effective_package_text,
                        display_name=self._choose_display_name(representative),
                    )
                )
            return self._sort_display_items(display_items)

        grouped: dict[tuple[object, ...], list[GameEventRecord]] = {}
        for event in events:
            key = (
                event.event_id,
                event.event_name_jp,
                event.event_name_us,
                event.name_label,
                self._event_start_date(event),
                self._event_start_time(event),
                self._event_end_date(event),
                self._event_end_time(event),
                event.order_value,
                event.text_hash,
                event.text_hash_jp,
                event.text_hash_us,
                event.extra_value,
                event.ranking_info.menu_hash if event.ranking_info is not None else "",
                event.ranking_info.description_hash if event.ranking_info is not None else "",
                event.ranking_info.mission_hash if event.ranking_info is not None else "",
                event.ranking_info.aircraft_hash if event.ranking_info is not None else "",
            )
            grouped.setdefault(key, []).append(event)

        display_items: list[EventDisplayItem] = []
        for grouped_events in grouped.values():
            representative = grouped_events[0]
            sources = sorted({event.source_lvst for event in grouped_events})
            source_text = sources[0] if len(sources) == 1 else f"{sources[0]} (+{len(sources) - 1})"
            effective_package_text = _source_package_name(representative.source_lvst)
            if len(grouped_events) > 1:
                effective_package_text = f"{effective_package_text} (+{len(grouped_events) - 1})"
            display_items.append(
                EventDisplayItem(
                    event=representative,
                    events=grouped_events,
                    source_text=source_text,
                    effective_package_text=effective_package_text,
                    display_name=self._choose_display_name(representative),
                )
            )
        return self._sort_display_items(display_items)

    def _sort_display_items(self, display_items: list[EventDisplayItem]) -> list[EventDisplayItem]:
        def datetime_key(date_text: str, time_text: str) -> tuple[str, str]:
            return (date_text or "9999-99-99", time_text or "99:99:99")

        def sort_key(item: EventDisplayItem) -> tuple[object, ...]:
            event = item.event
            if self.sort_column == 0:
                primary: tuple[object, ...] = (event.event_id,)
            elif self.sort_column == 2:
                primary = datetime_key(self._event_start_date(event), self._event_start_time(event))
            elif self.sort_column == 3:
                primary = datetime_key(self._event_end_date(event), self._event_end_time(event))
            else:
                primary = datetime_key(self._event_start_date(event), self._event_start_time(event))
            return (
                *primary,
                event.event_id,
                self._event_start_date(event) or "9999-99-99",
                self._event_start_time(event) or "99:99:99",
                _source_package_order(event.source_lvst)[0],
                item.source_text,
            )

        return sorted(display_items, key=sort_key, reverse=self.sort_descending)

    def _handle_header_sort(self, section: int) -> None:
        if section not in {0, 2, 3}:
            return
        if self.sort_column == section:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = section
            self.sort_descending = False
        self._apply_event_filter()

    def _apply_event_filter(self) -> None:
        previous_items = list(self.filtered_display_items)
        selected_identity = self._selected_display_item_identity()
        dataset = self.current_dataset
        if dataset is None:
            self.filtered_display_items = []
            self._refresh_event_table(previous_items, selected_identity)
            self._refresh_summary()
            self.detail_edit.clear()
            return

        query = self.event_filter_edit.text().strip().lower()
        selected_package = self.package_filter_combo.currentData()
        filtered_events: list[GameEventRecord] = []
        for event in dataset.events:
            if selected_package and _source_package_name(event.source_lvst) != selected_package:
                continue
            if not query:
                filtered_events.append(event)
                continue
            haystacks = [
                str(event.event_id),
                event.event_name_jp,
                event.event_name_us,
                event.name_label,
                event.text_hash_jp,
                event.text_hash_us,
                event.source_lvst,
                self._event_start_text(event),
                self._event_end_text(event),
            ]
            if event.ranking_info is not None:
                haystacks.extend(
                    [
                        event.ranking_info.menu_hash,
                        event.ranking_info.menu_label,
                        event.ranking_info.menu_jp,
                        event.ranking_info.menu_us,
                        event.ranking_info.description_hash,
                        event.ranking_info.description_label,
                        event.ranking_info.description_jp,
                        event.ranking_info.description_us,
                        event.ranking_info.mission_hash,
                        event.ranking_info.mission_label,
                        event.ranking_info.mission_jp,
                        event.ranking_info.mission_us,
                        event.ranking_info.aircraft_hash,
                        event.ranking_info.aircraft_label,
                        event.ranking_info.aircraft_jp,
                        event.ranking_info.aircraft_us,
                    ]
                )
            for challenge in event.challenges:
                haystacks.extend(
                    [
                        challenge.title_jp,
                        challenge.title_us,
                        challenge.message_jp,
                        challenge.message_us,
                        challenge.title_hash,
                        challenge.title_label,
                        challenge.message_hash,
                        challenge.message_label,
                        self._challenge_title_display_text(challenge),
                        self._challenge_message_display_text(challenge),
                    ]
                )
            combined = "\n".join(text for text in haystacks if text).lower()
            if query in combined:
                filtered_events.append(event)

        self.filtered_display_items = self._build_display_items(filtered_events)
        self._refresh_event_table(previous_items, selected_identity)
        self._refresh_summary()

    def _build_challenge_display_items(self, challenges: list[GameEventChallenge]) -> list[ChallengeDisplayItem]:
        grouped: dict[object, list[GameEventChallenge]] = {}
        for challenge in challenges:
            if challenge.target_id is None or challenge.target_id <= 0:
                grouped.setdefault((challenge.source_lvst, challenge.row_index), []).append(challenge)
                continue
            grouped.setdefault(challenge.target_id, []).append(challenge)

        display_items: list[ChallengeDisplayItem] = []
        for target_id, grouped_challenges in grouped.items():
            representative = max(
                grouped_challenges,
                key=lambda challenge: (
                    _source_package_order(challenge.source_lvst)[0],
                    self._challenge_start_date(challenge),
                    self._challenge_start_time(challenge),
                    challenge.row_index,
                ),
            )
            sorted_challenges = sorted(
                grouped_challenges,
                key=lambda challenge: (
                    _source_package_order(challenge.source_lvst)[0],
                    challenge.source_lvst,
                    challenge.row_index,
                ),
            )
            source_text = representative.source_lvst
            if len(sorted_challenges) > 1:
                source_text = f"{representative.source_lvst} (+{len(sorted_challenges) - 1})"
            effective_package_text = _source_package_name(representative.source_lvst)
            if len(sorted_challenges) > 1:
                effective_package_text = f"{effective_package_text} (+{len(sorted_challenges) - 1})"
            display_items.append(
                ChallengeDisplayItem(
                    challenge=representative,
                    challenges=sorted_challenges,
                    source_text=source_text,
                    effective_package_text=effective_package_text,
                    target_text=str(target_id) if isinstance(target_id, int) and target_id > 0 else "",
                    title_text=self._challenge_title_display_text(representative),
                    message_text=self._challenge_message_display_text(representative),
                )
            )
        return self._sort_challenge_display_items(display_items)

    def _build_drop_display_items(self, drops: list[GameEventDrop]) -> list[DropDisplayItem]:
        grouped: dict[int, list[GameEventDrop]] = {}
        for drop in drops:
            grouped.setdefault(drop.drop_id, []).append(drop)

        display_items: list[DropDisplayItem] = []
        for drop_id, grouped_drops in grouped.items():
            del drop_id
            representative = max(
                grouped_drops,
                key=lambda drop: (
                    _source_package_order(drop.source_lvst)[0],
                    drop.start_date,
                    drop.start_time,
                    drop.row_index,
                ),
            )
            sorted_drops = sorted(
                grouped_drops,
                key=lambda drop: (
                    _source_package_order(drop.source_lvst)[0],
                    drop.source_lvst,
                    drop.row_index,
                ),
            )
            source_text = representative.source_lvst
            if len(sorted_drops) > 1:
                source_text = f"{representative.source_lvst} (+{len(sorted_drops) - 1})"
            effective_package_text = _source_package_name(representative.source_lvst)
            if len(sorted_drops) > 1:
                effective_package_text = f"{effective_package_text} (+{len(sorted_drops) - 1})"
            display_items.append(
                DropDisplayItem(
                    drop=representative,
                    drops=sorted_drops,
                    source_text=source_text,
                    effective_package_text=effective_package_text,
                    title_text=representative.title_us or representative.title_jp or representative.title_label or representative.title_hash or "(unresolved)",
                )
            )
        return self._sort_drop_display_items(display_items)

    def _catalog_group_key(self, item: GameEventCatalogItem) -> tuple[object, ...]:
        if item.item_id is not None and item.item_id > 0:
            return (item.table_kind, item.item_id)
        return (item.table_kind, item.category, item.name_hash, item.desc_hash, item.source_lvst, item.row_index)

    def _build_catalog_display_items(self, catalog_items: list[GameEventCatalogItem]) -> list[CatalogDisplayItem]:
        grouped: dict[tuple[object, ...], list[GameEventCatalogItem]] = {}
        for item in catalog_items:
            grouped.setdefault(self._catalog_group_key(item), []).append(item)

        display_items: list[CatalogDisplayItem] = []
        for grouped_items in grouped.values():
            representative = max(
                grouped_items,
                key=lambda item: (
                    _source_package_order(item.source_lvst)[0],
                    item.sort_id if item.sort_id is not None else -1,
                    item.row_index,
                ),
            )
            sorted_items = sorted(
                grouped_items,
                key=lambda item: (
                    _source_package_order(item.source_lvst)[0],
                    item.source_lvst,
                    item.table_kind,
                    item.row_index,
                ),
            )
            source_text = representative.source_lvst
            if len(sorted_items) > 1:
                source_text = f"{representative.source_lvst} (+{len(sorted_items) - 1})"
            effective_package_text = _source_package_name(representative.source_lvst)
            if len(sorted_items) > 1:
                effective_package_text = f"{effective_package_text} (+{len(sorted_items) - 1})"
            display_items.append(
                CatalogDisplayItem(
                    item=representative,
                    items=sorted_items,
                    source_text=source_text,
                    effective_package_text=effective_package_text,
                    name_text=self._catalog_name_display_text(representative),
                    desc_text=self._catalog_desc_display_text(representative),
                )
            )
        return self._sort_catalog_display_items(display_items)

    def _sort_catalog_display_items(self, display_items: list[CatalogDisplayItem]) -> list[CatalogDisplayItem]:
        def sort_key(display_item: CatalogDisplayItem) -> tuple[object, ...]:
            item = display_item.item
            if self.catalog_sort_column == 0:
                primary: tuple[object, ...] = (item.category if item.category is not None else -1,)
            elif self.catalog_sort_column == 1:
                primary = (display_item.name_text.lower(),)
            elif self.catalog_sort_column == 3:
                primary = (item.group_id if item.group_id is not None else -1,)
            elif self.catalog_sort_column == 4:
                primary = (item.item_id if item.item_id is not None else -1,)
            elif self.catalog_sort_column == 5:
                primary = (item.content_id if item.content_id is not None else -1,)
            else:
                primary = (item.sort_id if item.sort_id is not None else 9999999999,)
            return (
                *primary,
                item.sort_id if item.sort_id is not None else 9999999999,
                item.category if item.category is not None else -1,
                item.item_id if item.item_id is not None else -1,
                _source_package_order(item.source_lvst)[0],
                item.source_lvst,
                item.table_kind,
                item.row_index,
            )

        return sorted(display_items, key=sort_key, reverse=self.catalog_sort_descending)

    def _sort_drop_display_items(self, display_items: list[DropDisplayItem]) -> list[DropDisplayItem]:
        def datetime_key(drop: GameEventDrop, *, end: bool = False) -> tuple[str, str]:
            date_text = drop.end_date if end else drop.start_date
            time_text = drop.end_time if end else drop.start_time
            return (date_text or "9999-99-99", time_text or "99:99:99")

        def sort_key(item: DropDisplayItem) -> tuple[object, ...]:
            drop = item.drop
            if self.drop_sort_column == 0:
                primary: tuple[object, ...] = (drop.drop_id,)
            elif self.drop_sort_column == 1:
                primary = datetime_key(drop)
            elif self.drop_sort_column == 2:
                primary = datetime_key(drop, end=True)
            else:
                primary = datetime_key(drop)
            return (
                *primary,
                drop.drop_id,
                drop.start_date or "9999-99-99",
                drop.start_time or "99:99:99",
                _source_package_order(drop.source_lvst)[0],
                drop.source_lvst,
                drop.row_index,
            )

        return sorted(display_items, key=sort_key, reverse=self.drop_sort_descending)

    def _sort_challenge_display_items(self, display_items: list[ChallengeDisplayItem]) -> list[ChallengeDisplayItem]:
        def datetime_key(challenge: GameEventChallenge, *, end: bool = False) -> tuple[str, str]:
            date_text = self._challenge_end_date(challenge) if end else self._challenge_start_date(challenge)
            time_text = self._challenge_end_time(challenge) if end else self._challenge_start_time(challenge)
            return (date_text or "9999-99-99", time_text or "99:99:99")

        def sort_key(item: ChallengeDisplayItem) -> tuple[object, ...]:
            challenge = item.challenge
            if self.challenge_sort_column == 0:
                primary: tuple[object, ...] = (challenge.target_id if challenge.target_id is not None else -1,)
            elif self.challenge_sort_column == 1:
                primary = datetime_key(challenge)
            elif self.challenge_sort_column == 2:
                primary = datetime_key(challenge, end=True)
            else:
                primary = datetime_key(challenge)
            return (
                *primary,
                challenge.target_id if challenge.target_id is not None else -1,
                self._challenge_start_date(challenge) or "9999-99-99",
                self._challenge_start_time(challenge) or "99:99:99",
                _source_package_order(challenge.source_lvst)[0],
                challenge.source_lvst,
                challenge.row_index,
            )

        return sorted(display_items, key=sort_key, reverse=self.challenge_sort_descending)

    def _handle_challenge_header_sort(self, section: int) -> None:
        if section not in {0, 1, 2}:
            return
        if self.challenge_sort_column == section:
            self.challenge_sort_descending = not self.challenge_sort_descending
        else:
            self.challenge_sort_column = section
            self.challenge_sort_descending = False
        self._apply_challenge_filter()

    def _handle_drop_header_sort(self, section: int) -> None:
        if section not in {0, 1, 2}:
            return
        if self.drop_sort_column == section:
            self.drop_sort_descending = not self.drop_sort_descending
        else:
            self.drop_sort_column = section
            self.drop_sort_descending = False
        self._apply_drop_filter()

    def _handle_catalog_header_sort(self, section: int) -> None:
        if section not in {0, 1, 3, 4, 5}:
            return
        if self.catalog_sort_column == section:
            self.catalog_sort_descending = not self.catalog_sort_descending
        else:
            self.catalog_sort_column = section
            self.catalog_sort_descending = False
        self._apply_catalog_filter()

    def _apply_challenge_filter(self) -> None:
        dataset = self.current_dataset
        if dataset is None:
            self.filtered_challenge_items = []
            self._refresh_challenge_table()
            return

        query = self.challenge_filter_edit.text().strip().lower()
        filtered: list[GameEventChallenge] = []
        for challenge in dataset.challenges:
            haystacks = [
                str(challenge.target_id) if challenge.target_id is not None else "",
                challenge.source_lvst,
                str(challenge.row_index),
                challenge.start_date,
                challenge.start_time,
                challenge.end_date,
                challenge.end_time,
                challenge.title_hash,
                challenge.title_label,
                challenge.title_jp,
                challenge.title_us,
                challenge.message_hash,
                challenge.message_label,
                challenge.message_jp,
                challenge.message_us,
                self._challenge_title_display_text(challenge),
                self._challenge_message_display_text(challenge),
            ]
            combined = "\n".join(text for text in haystacks if text).lower()
            if not query or query in combined:
                filtered.append(challenge)

        self.filtered_challenge_items = self._build_challenge_display_items(filtered)
        self._refresh_challenge_table()
        self._refresh_summary()

    def _apply_drop_filter(self) -> None:
        dataset = self.current_dataset
        if dataset is None:
            self.filtered_drop_items = []
            self._refresh_drop_table()
            self._refresh_summary()
            return

        query = self.drop_filter_edit.text().strip().lower()
        filtered: list[GameEventDrop] = []
        for drop in dataset.drops:
            haystacks = [
                str(drop.drop_id),
                drop.source_lvst,
                str(drop.row_index),
                drop.start_date,
                drop.start_time,
                drop.end_date,
                drop.end_time,
                drop.title_hash,
                drop.title_label,
                drop.title_jp,
                drop.title_us,
                str(drop.flag_a) if drop.flag_a is not None else "",
                str(drop.flag_b) if drop.flag_b is not None else "",
                str(drop.flag_c) if drop.flag_c is not None else "",
            ]
            combined = "\n".join(text for text in haystacks if text).lower()
            if not query or query in combined:
                filtered.append(drop)

        self.filtered_drop_items = self._build_drop_display_items(filtered)
        self._refresh_drop_table()
        self._refresh_summary()

    def _apply_catalog_filter(self) -> None:
        dataset = self.current_dataset
        if dataset is None:
            self.filtered_catalog_items = []
            self._refresh_catalog_table()
            self._refresh_summary()
            return

        query = self.catalog_filter_edit.text().strip().lower()
        selected_package = self.package_filter_combo.currentData()
        filtered: list[GameEventCatalogItem] = []
        for item in dataset.catalog_items:
            if selected_package and _source_package_name(item.source_lvst) != selected_package:
                continue
            name_label = self._catalog_label(item.name_hash, item.name_label)
            desc_label = self._catalog_label(item.desc_hash, item.desc_label)
            haystacks = [
                item.table_kind,
                str(item.visible) if item.visible is not None else "",
                str(item.sort_id) if item.sort_id is not None else "",
                str(item.group_id) if item.group_id is not None else "",
                str(item.item_id) if item.item_id is not None else "",
                str(item.item_id_b) if item.item_id_b is not None else "",
                str(item.category) if item.category is not None else "",
                item.name_hash,
                name_label,
                item.name_jp,
                item.name_us,
                self._catalog_name_display_text(item),
                item.desc_hash,
                desc_label,
                item.desc_jp,
                item.desc_us,
                self._catalog_desc_display_text(item),
                str(item.content_id) if item.content_id is not None else "",
                str(item.packed_id) if item.packed_id is not None else "",
                item.source_lvst,
                str(item.row_index),
            ]
            combined = "\n".join(text for text in haystacks if text).lower()
            if not query or query in combined:
                filtered.append(item)

        self.filtered_catalog_items = self._build_catalog_display_items(filtered)
        self._refresh_catalog_table()
        self._refresh_summary()

    def _refresh_challenge_table(self) -> None:
        self.challenge_table.setUpdatesEnabled(False)
        table_blocker = QSignalBlocker(self.challenge_table)
        selection_model = self.challenge_table.selectionModel()
        selection_blocker = QSignalBlocker(selection_model) if selection_model is not None else None
        try:
            self.challenge_table.setRowCount(len(self.filtered_challenge_items))
            for row_index, display_item in enumerate(self.filtered_challenge_items):
                self._write_challenge_table_row(row_index, display_item)
            sort_order = Qt.DescendingOrder if self.challenge_sort_descending else Qt.AscendingOrder
            self.challenge_table.horizontalHeader().setSortIndicator(self.challenge_sort_column, sort_order)
        finally:
            del table_blocker
            if selection_blocker is not None:
                del selection_blocker
            self.challenge_table.setUpdatesEnabled(True)

    def _refresh_drop_table(self) -> None:
        self.drop_table.setUpdatesEnabled(False)
        table_blocker = QSignalBlocker(self.drop_table)
        selection_model = self.drop_table.selectionModel()
        selection_blocker = QSignalBlocker(selection_model) if selection_model is not None else None
        try:
            self.drop_table.setRowCount(len(self.filtered_drop_items))
            for row_index, display_item in enumerate(self.filtered_drop_items):
                self._write_drop_table_row(row_index, display_item)
            sort_order = Qt.DescendingOrder if self.drop_sort_descending else Qt.AscendingOrder
            self.drop_table.horizontalHeader().setSortIndicator(self.drop_sort_column, sort_order)
        finally:
            del table_blocker
            if selection_blocker is not None:
                del selection_blocker
            self.drop_table.setUpdatesEnabled(True)

    def _refresh_catalog_table(self) -> None:
        self.catalog_table.setUpdatesEnabled(False)
        table_blocker = QSignalBlocker(self.catalog_table)
        selection_model = self.catalog_table.selectionModel()
        selection_blocker = QSignalBlocker(selection_model) if selection_model is not None else None
        try:
            self.catalog_table.setRowCount(len(self.filtered_catalog_items))
            for row_index, display_item in enumerate(self.filtered_catalog_items):
                self._write_catalog_table_row(row_index, display_item)
            sort_order = Qt.DescendingOrder if self.catalog_sort_descending else Qt.AscendingOrder
            self.catalog_table.horizontalHeader().setSortIndicator(self.catalog_sort_column, sort_order)
        finally:
            del table_blocker
            if selection_blocker is not None:
                del selection_blocker
            self.catalog_table.setUpdatesEnabled(True)

    def _category_text(self, category: int | None) -> str:
        names = {
            1: "1 Aircraft",
            2: "2 Skin",
            3: "3 Emblem",
            4: "4 Nickname",
            5: "5 Misc",
            6: "6 Item",
        }
        if category is None:
            return ""
        return names.get(category, str(category))

    def _catalog_price_text(self, item: GameEventCatalogItem) -> str:
        parts = []
        if item.price_a is not None:
            parts.append(str(item.price_a))
        if item.price_b is not None and item.price_b != 0:
            parts.append(f"sub={item.price_b}")
        if item.multiplier is not None and item.multiplier != 1.0:
            parts.append(f"x{item.multiplier:g}")
        return ", ".join(parts)

    def _write_catalog_table_row(self, row_index: int, display_item: CatalogDisplayItem) -> None:
        item = display_item.item
        values = [
            self._category_text(item.category),
            display_item.name_text,
            display_item.desc_text,
            str(item.group_id) if item.group_id is not None else "",
            str(item.item_id) if item.item_id is not None else "",
            str(item.content_id) if item.content_id is not None else "",
            self._catalog_price_text(item),
            display_item.effective_package_text,
            display_item.source_text,
            f"{item.table_kind}:{item.row_index} (+{len(display_item.items) - 1})" if len(display_item.items) > 1 else f"{item.table_kind}:{item.row_index}",
        ]
        for column_index, value in enumerate(values):
            table_item = self.catalog_table.item(row_index, column_index)
            if table_item is None:
                table_item = QTableWidgetItem()
                self.catalog_table.setItem(row_index, column_index, table_item)
            table_item.setText(value)
            table_item.setData(Qt.UserRole, row_index)

    def _write_drop_table_row(self, row_index: int, display_item: DropDisplayItem) -> None:
        drop = display_item.drop
        flags = ", ".join(
            part
            for part in [
                f"A={drop.flag_a}" if drop.flag_a is not None else "",
                f"B={drop.flag_b}" if drop.flag_b is not None else "",
                f"C={drop.flag_c}" if drop.flag_c is not None else "",
            ]
            if part
        )
        values = [
            str(drop.drop_id),
            self._drop_start_text(drop),
            self._drop_end_text(drop),
            display_item.title_text,
            flags,
            display_item.source_text,
            f"{drop.row_index} (+{len(display_item.drops) - 1})" if len(display_item.drops) > 1 else str(drop.row_index),
        ]
        for column_index, value in enumerate(values):
            item = self.drop_table.item(row_index, column_index)
            if item is None:
                item = QTableWidgetItem()
                self.drop_table.setItem(row_index, column_index, item)
            item.setText(value)
            item.setData(Qt.UserRole, row_index)
            item.setToolTip("Edited" if self._has_drop_override(drop) and column_index in {1, 2} else "")

    def _write_challenge_table_row(self, row_index: int, display_item: ChallengeDisplayItem) -> None:
        challenge = display_item.challenge
        values = [
            display_item.target_text,
            self._challenge_start_text(challenge),
            self._challenge_end_text(challenge),
            display_item.title_text,
            display_item.message_text,
            display_item.source_text,
            f"{challenge.row_index} (+{len(display_item.challenges) - 1})" if len(display_item.challenges) > 1 else str(challenge.row_index),
        ]
        is_edited = any(self._has_challenge_override(item) for item in display_item.challenges)
        for column_index, value in enumerate(values):
            item = self.challenge_table.item(row_index, column_index)
            if item is None:
                item = QTableWidgetItem()
                self.challenge_table.setItem(row_index, column_index, item)
            item.setText(value)
            item.setData(Qt.UserRole, row_index)
            item.setToolTip("Edited" if is_edited and column_index in {1, 2} else "")

    def _refresh_event_table(
        self,
        previous_items: list[EventDisplayItem] | None = None,
        selected_identity: tuple[tuple[str, int], ...] | None = None,
    ) -> None:
        previous_items = previous_items or []
        use_incremental = self._can_incrementally_refresh_event_table(previous_items, self.filtered_display_items)
        self.event_table.setUpdatesEnabled(False)
        table_blocker = QSignalBlocker(self.event_table)
        selection_model = self.event_table.selectionModel()
        selection_blocker = QSignalBlocker(selection_model) if selection_model is not None else None
        try:
            if use_incremental:
                self._incrementally_refresh_event_table_rows(previous_items, self.filtered_display_items)
            else:
                self._rebuild_event_table_rows()
            sort_order = Qt.DescendingOrder if self.sort_descending else Qt.AscendingOrder
            self.event_table.horizontalHeader().setSortIndicator(self.sort_column, sort_order)
            self._restore_event_table_selection(selected_identity, fallback_to_first=not use_incremental)
        finally:
            del table_blocker
            if selection_blocker is not None:
                del selection_blocker
            self.event_table.setUpdatesEnabled(True)
        self._sync_selected_event()

    def _rebuild_event_table_rows(self) -> None:
        self.event_table.setRowCount(len(self.filtered_display_items))
        for row_index, display_item in enumerate(self.filtered_display_items):
            self._write_event_table_row(row_index, display_item)

    def _incrementally_refresh_event_table_rows(
        self,
        previous_items: list[EventDisplayItem],
        new_items: list[EventDisplayItem],
    ) -> None:
        if self.event_table.rowCount() != len(new_items):
            self._rebuild_event_table_rows()
            return
        for row_index, (old_item, new_item) in enumerate(zip(previous_items, new_items)):
            if self._display_item_values(old_item) != self._display_item_values(new_item):
                self._write_event_table_row(row_index, new_item)
            else:
                for column_index in range(self.event_table.columnCount()):
                    existing_item = self.event_table.item(row_index, column_index)
                    if existing_item is not None:
                        existing_item.setData(Qt.UserRole, row_index)

    def _write_event_table_row(self, row_index: int, display_item: EventDisplayItem) -> None:
        values = self._display_item_values(display_item)
        for column_index, value in enumerate(values):
            item = self.event_table.item(row_index, column_index)
            if item is None:
                item = QTableWidgetItem()
                self.event_table.setItem(row_index, column_index, item)
            item.setText(value)
            item.setData(Qt.UserRole, row_index)
            if column_index in {2, 3} and self._has_override(display_item.event):
                item.setToolTip("Edited")
            else:
                item.setToolTip("")

    def _can_incrementally_refresh_event_table(
        self,
        previous_items: list[EventDisplayItem],
        new_items: list[EventDisplayItem],
    ) -> bool:
        if len(previous_items) != len(new_items):
            return False
        return [self._display_item_identity(item) for item in previous_items] == [
            self._display_item_identity(item) for item in new_items
        ]

    def _display_item_identity(self, display_item: EventDisplayItem) -> tuple[tuple[str, int], ...]:
        return tuple(sorted(self._event_override_key(event) for event in display_item.events))

    def _display_item_values(self, display_item: EventDisplayItem) -> list[str]:
        event = display_item.event
        return [
            str(event.event_id),
            display_item.display_name,
            self._event_start_text(event),
            self._event_end_text(event),
            display_item.effective_package_text,
            display_item.source_text,
            str(display_item.challenge_count),
        ]

    def _selected_display_item_identity(self) -> tuple[tuple[str, int], ...] | None:
        selected_indexes = self.event_table.selectionModel().selectedRows() if self.event_table.selectionModel() is not None else []
        if not selected_indexes:
            return None
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_display_items):
            return None
        return self._display_item_identity(self.filtered_display_items[row_index])

    def _restore_event_table_selection(
        self,
        selected_identity: tuple[tuple[str, int], ...] | None,
        *,
        fallback_to_first: bool,
    ) -> None:
        if not self.filtered_display_items:
            self.detail_edit.clear()
            return
        target_row = -1
        if selected_identity is not None:
            for row_index, display_item in enumerate(self.filtered_display_items):
                if self._display_item_identity(display_item) == selected_identity:
                    target_row = row_index
                    break
        if target_row < 0 and fallback_to_first:
            target_row = 0
        if target_row >= 0:
            self.event_table.selectRow(target_row)

    def _refresh_summary(self) -> None:
        if self.current_dataset is None:
            self.summary_edit.setPlainText("No game event directory loaded.")
            return
        dataset = self.current_dataset
        selected_package = self.package_filter_combo.currentData()
        lines = [
            f"Root: {_normalize_path_text(dataset.root_dir)}",
            f"Packages: {len(dataset.package_dirs)}",
            f"Package Filter: {selected_package or 'All Packages'}",
            f"Merge Mode: {self.merge_mode_combo.currentText()}",
            f"Full Game ACT Source: {self.full_game_act_source_edit.text().strip() or '(none)'}",
            f"Full Game ACT Json Labels: {len(self.full_game_act_json_hash_to_label)}",
            f"ParaTranz Labels: {len(self.paratranz_label_to_text)}",
            f"Edited schedule rows: {len(self.date_overrides)}",
            f"Edited challenge rows: {len(self.challenge_date_overrides)}",
            f"Edited drop rows: {len(self.drop_date_overrides)}",
            f"Visible list rows: {len(self.filtered_display_items)}",
            f"Raw event rows: {len(dataset.events)}",
            f"Raw challenge rows: {len(dataset.challenges)}",
            f"Visible challenge rows: {len(self.filtered_challenge_items)}",
            f"Raw drop rows: {len(dataset.drops)}",
            f"Visible drop rows: {len(self.filtered_drop_items)}",
            f"Raw catalog rows: {len(dataset.catalog_items)}",
            f"Visible catalog rows: {len(self.filtered_catalog_items)}",
            f"ACT files found: {len(dataset.act_files)} (parsed {len(dataset.parsed_act_files)})",
            f"LVST files found: {len(dataset.lvst_files)} (parsed event-related {len(dataset.parsed_lvst_files)})",
            f"Plaintext fallback labels: {len(dataset.plaintext_labels)}",
            f"Warnings: {len(dataset.warnings)}",
        ]
        if dataset.package_dirs:
            lines.append("")
            lines.append("Loaded packages:")
            for package_dir in dataset.package_dirs[:12]:
                lines.append(f"- {_normalize_path_text(package_dir)}")
            if len(dataset.package_dirs) > 12:
                lines.append(f"- ... and {len(dataset.package_dirs) - 12} more")
        if dataset.warnings:
            lines.append("")
            lines.append("Recent warnings:")
            for warning in dataset.warnings[:8]:
                lines.append(f"- {warning}")
        self.summary_edit.setPlainText("\n".join(lines))

    def _sync_selected_event(self) -> None:
        selected_indexes = self.event_table.selectionModel().selectedRows()
        if not selected_indexes:
            self.detail_edit.clear()
            return
        model_index = selected_indexes[0]
        row_index = model_index.row()
        if row_index < 0 or row_index >= len(self.filtered_display_items):
            self.detail_edit.clear()
            return
        display_item = self.filtered_display_items[row_index]
        self.detail_edit.setPlainText(self._build_event_detail_text(display_item))

    def _sync_selected_challenge(self) -> None:
        selected_indexes = self.challenge_table.selectionModel().selectedRows()
        if not selected_indexes:
            return
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_challenge_items):
            return
        self.detail_edit.setPlainText(self._build_challenge_detail_text(self.filtered_challenge_items[row_index]))

    def _sync_selected_drop(self) -> None:
        selected_indexes = self.drop_table.selectionModel().selectedRows()
        if not selected_indexes:
            self.detail_edit.clear()
            return
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_drop_items):
            self.detail_edit.clear()
            return
        self.detail_edit.setPlainText(self._build_drop_detail_text(self.filtered_drop_items[row_index]))

    def _sync_selected_catalog(self) -> None:
        selected_indexes = self.catalog_table.selectionModel().selectedRows()
        if not selected_indexes:
            self.detail_edit.clear()
            return
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_catalog_items):
            self.detail_edit.clear()
            return
        self.detail_edit.setPlainText(self._build_catalog_detail_text(self.filtered_catalog_items[row_index]))

    def _build_challenge_detail_text(self, display_item: ChallengeDisplayItem) -> str:
        challenge = display_item.challenge
        lines = [
            f"Target ID: {challenge.target_id if challenge.target_id is not None else '(none)'}",
            f"Effective Source: {challenge.source_lvst} [row {challenge.row_index}]",
            f"Merged Target-ID Rows: {len(display_item.challenges)}",
            f"Start: {self._challenge_start_text(challenge) or '(none)'}",
            f"End: {self._challenge_end_text(challenge) or '(none)'}",
            f"Title Hash: {challenge.title_hash or '(none)'}",
            f"Title Label: {challenge.title_label or '(none)'}",
            f"Title Display: {self._challenge_title_display_text(challenge)}",
            f"Title (US): {challenge.title_us or '(unresolved)'}",
            f"Title (JP): {challenge.title_jp or '(unresolved)'}",
            f"Message Hash: {challenge.message_hash or '(none)'}",
            f"Message Label: {challenge.message_label or '(none)'}",
            f"Message Display: {self._challenge_message_display_text(challenge)}",
            f"Message (US): {challenge.message_us or '(unresolved)'}",
            f"Message (JP): {challenge.message_jp or '(unresolved)'}",
        ]
        if self._has_challenge_override(challenge):
            lines.append("Edited Dates: yes")
        if len(display_item.challenges) > 1:
            lines.append("")
            lines.append("Merged sources:")
            for merged_challenge in display_item.challenges:
                lines.append(f"- {merged_challenge.source_lvst} [row {merged_challenge.row_index}]")
        return "\n".join(lines)

    def _build_event_detail_text(self, display_item: EventDisplayItem) -> str:
        event = display_item.event
        external_name = self._resolve_external_name(event)
        ranking_proxy_name = self._build_ranking_proxy_name(event)
        lines = [
            f"Event ID: {event.event_id}",
            f"Name (US): {event.event_name_us or '(unresolved)'}",
            f"Name (JP): {event.event_name_jp or '(unresolved)'}",
            f"Display Name: {display_item.display_name or '(unresolved)'}",
            f"External Name: {external_name or '(none)'}",
            f"Ranking Proxy Name: {ranking_proxy_name or '(none)'}",
            f"Name Label: {event.name_label or '(none)'}",
            f"Start: {self._event_start_text(event) or '(none)'}",
            f"End: {self._event_end_text(event) or '(none)'}",
            f"Order Value: {event.order_value if event.order_value is not None else '(none)'}",
            f"Text Hash: {event.text_hash or '(none)'}",
            f"Text Hash (JP): {event.text_hash_jp or '(unresolved)'}",
            f"Text Hash (US): {event.text_hash_us or '(unresolved)'}",
            f"Extra Value: {event.extra_value if event.extra_value is not None else '(none)'}",
        ]
        if len(display_item.events) > 1:
            lines.append(f"Edit Scope: {len(display_item.events)} merged TSS row(s)")
        if self._has_override(event):
            lines.append("Edited Dates: yes")
        if event.ranking_info is not None:
            ranking = event.ranking_info
            lines.extend(
                [
                    f"Ranking Rule Source: {ranking.source_lvst} [row {ranking.row_index}]",
                    f"Ranking Variant ID: {ranking.variant_id if ranking.variant_id is not None else '(none)'}",
                    f"Ranking Metric: {ranking.metric_value if ranking.metric_value is not None else '(none)'}",
                    f"Ranking Rule Type A: {ranking.rule_type_a if ranking.rule_type_a is not None else '(none)'}",
                    f"Ranking Rule Type B: {ranking.rule_type_b if ranking.rule_type_b is not None else '(none)'}",
                    f"Ranking Menu Hash: {ranking.menu_hash or '(none)'}",
                    f"Ranking Menu Label: {ranking.menu_label or '(unresolved)'}",
                    f"Ranking Menu External Label: {self._resolve_external_label_from_hash(ranking.menu_hash) or '(none)'}",
                    f"Ranking Menu External Text: {self._resolve_external_text_from_hash(ranking.menu_hash) or '(none)'}",
                    f"Ranking Menu (US): {ranking.menu_us or '(unresolved)'}",
                    f"Ranking Menu (JP): {ranking.menu_jp or '(unresolved)'}",
                    f"Ranking Desc Hash: {ranking.description_hash or '(none)'}",
                    f"Ranking Desc Label: {ranking.description_label or '(unresolved)'}",
                    f"Ranking Desc External Label: {self._resolve_external_label_from_hash(ranking.description_hash) or '(none)'}",
                    f"Ranking Desc External Text: {self._resolve_external_text_from_hash(ranking.description_hash) or '(none)'}",
                    f"Ranking Desc (US): {ranking.description_us or '(unresolved)'}",
                    f"Ranking Desc (JP): {ranking.description_jp or '(unresolved)'}",
                    f"Ranking Mission Hash: {ranking.mission_hash or '(none)'}",
                    f"Ranking Mission Label: {ranking.mission_label or '(unresolved)'}",
                    f"Ranking Mission External Label: {self._resolve_external_label_from_hash(ranking.mission_hash) or '(none)'}",
                    f"Ranking Mission External Text: {self._resolve_external_text_from_hash(ranking.mission_hash) or '(none)'}",
                    f"Ranking Mission (US): {ranking.mission_us or '(unresolved)'}",
                    f"Ranking Mission (JP): {ranking.mission_jp or '(unresolved)'}",
                    f"Ranking Aircraft Hash: {ranking.aircraft_hash or '(none)'}",
                    f"Ranking Aircraft Label: {ranking.aircraft_label or '(unresolved)'}",
                    f"Ranking Aircraft External Label: {self._resolve_external_label_from_hash(ranking.aircraft_hash) or '(none)'}",
                    f"Ranking Aircraft External Text: {self._resolve_external_text_from_hash(ranking.aircraft_hash) or '(none)'}",
                    f"Ranking Aircraft (US): {ranking.aircraft_us or '(unresolved)'}",
                    f"Ranking Aircraft (JP): {ranking.aircraft_jp or '(unresolved)'}",
                ]
            )
        if len(display_item.events) == 1:
            lines.insert(6, f"Source: {event.source_lvst} [row {event.row_index}]")
        else:
            merge_mode = self.merge_mode_combo.currentData()
            if merge_mode == "event_id":
                lines.insert(6, f"Effective Source: {event.source_lvst} [row {event.row_index}]")
                lines.insert(7, f"Merged Event-ID Rows: {len(display_item.events)}")
            else:
                lines.insert(6, f"Merged Rows: {len(display_item.events)}")
            lines.append("")
            lines.append("Merged sources:")
            for merged_event in display_item.events:
                lines.append(f"- {merged_event.source_lvst} [row {merged_event.row_index}]")

        challenges = []
        seen_challenges: set[tuple[str, int, str, str]] = set()
        for merged_event in display_item.events:
            for challenge in merged_event.challenges:
                key = (
                    challenge.source_lvst,
                    challenge.row_index,
                    challenge.title_hash,
                    challenge.message_hash,
                )
                if key in seen_challenges:
                    continue
                seen_challenges.add(key)
                challenges.append(challenge)
        if challenges:
            lines.append("")
            lines.append(f"Linked Challenges: {len(challenges)}")
            for index, challenge in enumerate(challenges, start=1):
                lines.append(f"[{index}] {challenge.source_lvst} row {challenge.row_index}")
                lines.append(f"Target ID: {challenge.target_id if challenge.target_id is not None else '(none)'}")
                lines.append(f"Start: {self._challenge_start_text(challenge) or '(none)'}")
                lines.append(f"End: {self._challenge_end_text(challenge) or '(none)'}")
                if self._has_challenge_override(challenge):
                    lines.append("Edited Dates: yes")
                lines.append(f"Title Hash: {challenge.title_hash or '(none)'}")
                lines.append(f"Title Label: {challenge.title_label or '(none)'}")
                lines.append(f"Title Display: {self._challenge_title_display_text(challenge)}")
                lines.append(f"Title (JP): {challenge.title_jp or '(unresolved)'}")
                lines.append(f"Title (US): {challenge.title_us or '(unresolved)'}")
                lines.append(f"Message Hash: {challenge.message_hash or '(none)'}")
                lines.append(f"Message Label: {challenge.message_label or '(none)'}")
                lines.append(f"Message Display: {self._challenge_message_display_text(challenge)}")
                lines.append(f"Message (JP): {challenge.message_jp or '(unresolved)'}")
                lines.append(f"Message (US): {challenge.message_us or '(unresolved)'}")
                lines.append("")
        return "\n".join(lines).rstrip()

    def _build_catalog_detail_text(self, display_item: CatalogDisplayItem) -> str:
        item = display_item.item
        name_label = self._catalog_label(item.name_hash, item.name_label)
        desc_label = self._catalog_label(item.desc_hash, item.desc_label)
        name_translation = self._catalog_translation(item.name_hash, item.name_label)
        desc_translation = self._catalog_translation(item.desc_hash, item.desc_label)
        lines = [
            f"Category: {self._category_text(item.category) or '(none)'}",
            f"Display Name: {display_item.name_text}",
            f"Display Description: {display_item.desc_text or '(none)'}",
            f"Effective Source: {item.source_lvst} [{item.table_kind} row {item.row_index}]",
            f"Merged Catalog Rows: {len(display_item.items)}",
            f"Table Kind: {item.table_kind}",
            f"Visible: {item.visible if item.visible is not None else '(none)'}",
            f"Sort ID: {item.sort_id if item.sort_id is not None else '(none)'}",
            f"Group ID: {item.group_id if item.group_id is not None else '(none)'}",
            f"Item ID: {item.item_id if item.item_id is not None else '(none)'}",
            f"Item ID B: {item.item_id_b if item.item_id_b is not None else '(none)'}",
            f"Content ID: {item.content_id if item.content_id is not None else '(none)'}",
            f"Packed ID: {item.packed_id if item.packed_id is not None else '(none)'}",
            f"Price A: {item.price_a if item.price_a is not None else '(none)'}",
            f"Price B: {item.price_b if item.price_b is not None else '(none)'}",
            f"Limit Flag: {item.limit_flag if item.limit_flag is not None else '(none)'}",
            f"Multiplier: {item.multiplier if item.multiplier is not None else '(none)'}",
            f"Flag: {item.flag if item.flag is not None else '(none)'}",
            "",
            f"Name Hash: {item.name_hash or '(none)'}",
            f"Name Label: {name_label or '(none)'}",
            f"Name ParaTranz: {name_translation or '(none)'}",
            f"Name (US): {item.name_us or '(unresolved)'}",
            f"Name (JP): {item.name_jp or '(unresolved)'}",
            "",
            f"Description Hash: {item.desc_hash or '(none)'}",
            f"Description Label: {desc_label or '(none)'}",
            f"Description ParaTranz: {desc_translation or '(none)'}",
            f"Description (US): {item.desc_us or '(unresolved)'}",
            f"Description (JP): {item.desc_jp or '(unresolved)'}",
        ]
        if len(display_item.items) > 1:
            lines.append("")
            lines.append("Merged sources:")
            for merged_item in display_item.items:
                lines.append(f"- {merged_item.source_lvst} [{merged_item.table_kind} row {merged_item.row_index}]")
        return "\n".join(lines).rstrip()

    def _build_drop_detail_text(self, display_item: DropDisplayItem) -> str:
        drop = display_item.drop
        lines = [
            f"Drop ID: {drop.drop_id}",
            f"Effective Source: {drop.source_lvst} [row {drop.row_index}]",
            f"Merged Drop-ID Rows: {len(display_item.drops)}",
            f"Start: {self._drop_start_text(drop) or '(none)'}",
            f"End: {self._drop_end_text(drop) or '(none)'}",
            f"Title Hash: {drop.title_hash or '(none)'}",
            f"Title Label: {drop.title_label or '(none)'}",
            f"Title Display: {display_item.title_text or '(unresolved)'}",
            f"Title (US): {drop.title_us or '(unresolved)'}",
            f"Title (JP): {drop.title_jp or '(unresolved)'}",
            f"Flag A: {drop.flag_a if drop.flag_a is not None else '(none)'}",
            f"Flag B: {drop.flag_b if drop.flag_b is not None else '(none)'}",
            f"Flag C: {drop.flag_c if drop.flag_c is not None else '(none)'}",
        ]
        if self._has_drop_override(drop):
            lines.append("Edited Dates: yes")
        if len(display_item.drops) > 1:
            lines.append("")
            lines.append("Merged sources:")
            for merged_drop in display_item.drops:
                lines.append(f"- {merged_drop.source_lvst} [row {merged_drop.row_index}]")
        return "\n".join(lines)

    def _challenge_override_key(self, challenge: GameEventChallenge) -> tuple[str, int]:
        return (_normalize_path_text(challenge.source_file), challenge.row_index)

    def _has_challenge_override(self, challenge: GameEventChallenge) -> bool:
        return self._challenge_override_key(challenge) in self.challenge_date_overrides

    def _challenge_override(self, challenge: GameEventChallenge) -> EventDateOverride | None:
        return self.challenge_date_overrides.get(self._challenge_override_key(challenge))

    def _challenge_start_date(self, challenge: GameEventChallenge) -> str:
        override = self._challenge_override(challenge)
        return override.start_date if override is not None else challenge.start_date

    def _challenge_start_time(self, challenge: GameEventChallenge) -> str:
        override = self._challenge_override(challenge)
        return override.start_time if override is not None else challenge.start_time

    def _challenge_end_date(self, challenge: GameEventChallenge) -> str:
        override = self._challenge_override(challenge)
        return override.end_date if override is not None else challenge.end_date

    def _challenge_end_time(self, challenge: GameEventChallenge) -> str:
        override = self._challenge_override(challenge)
        return override.end_time if override is not None else challenge.end_time

    def _challenge_start_text(self, challenge: GameEventChallenge) -> str:
        return _join_datetime(self._challenge_start_date(challenge), self._challenge_start_time(challenge))

    def _challenge_end_text(self, challenge: GameEventChallenge) -> str:
        return _join_datetime(self._challenge_end_date(challenge), self._challenge_end_time(challenge))

    def _validate_challenge_override(self, override: EventDateOverride) -> None:
        self._validate_date_override(override)

    def _open_event_challenges_from_item(self, item: QTableWidgetItem) -> None:
        row_index = item.data(Qt.UserRole)
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(self.filtered_display_items):
            return
        self._open_event_challenges(self.filtered_display_items[row_index])

    def _open_event_challenges(self, display_item: EventDisplayItem) -> None:
        challenges = []
        seen: set[tuple[str, int, str, str]] = set()
        for merged_event in display_item.events:
            for challenge in merged_event.challenges:
                key = (challenge.source_lvst, challenge.row_index, challenge.title_hash, challenge.message_hash)
                if key in seen:
                    continue
                seen.add(key)
                challenges.append(challenge)
        if not challenges:
            QMessageBox.information(self, "Linked Challenges", "This event has no linked challenge rows.")
            return
        dialog = ChallengeListDialog(display_item, challenges, self)
        dialog.exec_()

    def _selected_challenge_item(self) -> ChallengeDisplayItem | None:
        selected_indexes = self.challenge_table.selectionModel().selectedRows() if self.challenge_table.selectionModel() is not None else []
        if not selected_indexes:
            return None
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_challenge_items):
            return None
        return self.filtered_challenge_items[row_index]

    def _edit_selected_challenge_from_item(self, *_args) -> None:
        display_item = self._selected_challenge_item()
        if display_item is None:
            return
        self._edit_challenge_item(display_item)

    def _show_challenge_context_menu(self, position) -> None:
        item = self.challenge_table.itemAt(position)
        if item is None:
            return
        row_index = item.data(Qt.UserRole)
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(self.filtered_challenge_items):
            return
        display_item = self.filtered_challenge_items[row_index]
        self.challenge_table.selectRow(row_index)

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Date/Time")
        reset_action = menu.addAction("Reset Edited Date/Time")
        reset_action.setEnabled(any(self._has_challenge_override(challenge) for challenge in display_item.challenges))
        selected_action = menu.exec_(self.challenge_table.viewport().mapToGlobal(position))
        if selected_action == edit_action:
            self._edit_challenge_item(display_item)
        elif selected_action == reset_action:
            self._reset_challenge_item(display_item)

    def _edit_selected_drop_from_item(self, *_args) -> None:
        display_item = self._selected_drop_item()
        if display_item is None:
            return
        self._edit_drop_item(display_item)

    def _selected_drop_item(self) -> DropDisplayItem | None:
        selected_indexes = self.drop_table.selectionModel().selectedRows() if self.drop_table.selectionModel() is not None else []
        if not selected_indexes:
            return None
        row_index = selected_indexes[0].row()
        if row_index < 0 or row_index >= len(self.filtered_drop_items):
            return None
        return self.filtered_drop_items[row_index]

    def _show_drop_context_menu(self, position) -> None:
        item = self.drop_table.itemAt(position)
        if item is None:
            return
        row_index = item.data(Qt.UserRole)
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(self.filtered_drop_items):
            return
        display_item = self.filtered_drop_items[row_index]
        self.drop_table.selectRow(row_index)

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Date/Time")
        reset_action = menu.addAction("Reset Edited Date/Time")
        reset_action.setEnabled(any(self._has_drop_override(drop) for drop in display_item.drops))
        selected_action = menu.exec_(self.drop_table.viewport().mapToGlobal(position))
        if selected_action == edit_action:
            self._edit_drop_item(display_item)
        elif selected_action == reset_action:
            self._reset_drop_item(display_item)

    def _edit_drop_item(self, display_item: DropDisplayItem) -> None:
        drop = display_item.drop
        dialog = DropDateEditDialog(drop, self._drop_override(drop), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        override = dialog.values()
        try:
            self._validate_drop_override(override)
        except Exception as exc:
            QMessageBox.warning(self, "Edit Drop Dates", f"Invalid date/time value:\n{exc}")
            return

        for target_drop in display_item.drops:
            key = self._drop_override_key(target_drop)
            if (
                override.start_date == target_drop.start_date
                and override.start_time == target_drop.start_time
                and override.end_date == target_drop.end_date
                and override.end_time == target_drop.end_time
            ):
                self.drop_date_overrides.pop(key, None)
            else:
                self.drop_date_overrides[key] = override
        self._apply_drop_filter()
        self.statusBar().showMessage(
            f"Edited drop {display_item.drop.drop_id} dates across {len(display_item.drops)} row(s)"
        )

    def _reset_drop_item(self, display_item: DropDisplayItem) -> None:
        removed = False
        for drop in display_item.drops:
            removed = self.drop_date_overrides.pop(self._drop_override_key(drop), None) is not None or removed
        if not removed:
            return
        self._apply_drop_filter()
        self.statusBar().showMessage(
            f"Reset drop {display_item.drop.drop_id} dates across {len(display_item.drops)} row(s)"
        )

    def _edit_challenge_item(self, display_item: ChallengeDisplayItem) -> None:
        challenge = display_item.challenge
        dialog = ChallengeDateEditDialog(challenge, self._challenge_override(challenge), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        override = dialog.values()
        try:
            self._validate_challenge_override(override)
        except Exception as exc:
            QMessageBox.warning(self, "Edit Challenge Dates", f"Invalid date/time value:\n{exc}")
            return

        for target_challenge in display_item.challenges:
            key = self._challenge_override_key(target_challenge)
            if (
                override.start_date == target_challenge.start_date
                and override.start_time == target_challenge.start_time
                and override.end_date == target_challenge.end_date
                and override.end_time == target_challenge.end_time
            ):
                self.challenge_date_overrides.pop(key, None)
            else:
                self.challenge_date_overrides[key] = override
        self._apply_challenge_filter()
        self._sync_selected_event()
        self.statusBar().showMessage(
            f"Edited target {display_item.target_text or '(none)'} across {len(display_item.challenges)} challenge row(s)"
        )

    def _reset_challenge_item(self, display_item: ChallengeDisplayItem) -> None:
        removed = False
        for challenge in display_item.challenges:
            removed = self.challenge_date_overrides.pop(self._challenge_override_key(challenge), None) is not None or removed
        if not removed:
            return
        self._apply_challenge_filter()
        self.statusBar().showMessage(
            f"Reset target {display_item.target_text or '(none)'} across {len(display_item.challenges)} challenge row(s)"
        )

    def _event_override_key(self, event: GameEventRecord) -> tuple[str, int]:
        return (_normalize_path_text(event.source_file), event.row_index)

    def _has_override(self, event: GameEventRecord) -> bool:
        return self._event_override_key(event) in self.date_overrides

    def _event_override(self, event: GameEventRecord) -> EventDateOverride | None:
        return self.date_overrides.get(self._event_override_key(event))

    def _event_start_date(self, event: GameEventRecord) -> str:
        override = self._event_override(event)
        return override.start_date if override is not None else event.start_date

    def _event_start_time(self, event: GameEventRecord) -> str:
        override = self._event_override(event)
        return override.start_time if override is not None else event.start_time

    def _event_end_date(self, event: GameEventRecord) -> str:
        override = self._event_override(event)
        return override.end_date if override is not None else event.end_date

    def _event_end_time(self, event: GameEventRecord) -> str:
        override = self._event_override(event)
        return override.end_time if override is not None else event.end_time

    def _event_start_text(self, event: GameEventRecord) -> str:
        date_text = self._event_start_date(event)
        time_text = self._event_start_time(event)
        if date_text and time_text:
            return f"{date_text} {time_text}"
        return date_text or time_text

    def _event_end_text(self, event: GameEventRecord) -> str:
        date_text = self._event_end_date(event)
        time_text = self._event_end_time(event)
        if date_text and time_text:
            return f"{date_text} {time_text}"
        return date_text or time_text

    def _event_sort_start_date(self, event: GameEventRecord) -> str:
        return self._event_start_date(event) or ""

    def _event_sort_start_time(self, event: GameEventRecord) -> str:
        return self._event_start_time(event) or ""

    def _drop_override_key(self, drop: GameEventDrop) -> tuple[str, int]:
        return (_normalize_path_text(drop.source_file), drop.row_index)

    def _has_drop_override(self, drop: GameEventDrop) -> bool:
        return self._drop_override_key(drop) in self.drop_date_overrides

    def _drop_override(self, drop: GameEventDrop) -> EventDateOverride | None:
        return self.drop_date_overrides.get(self._drop_override_key(drop))

    def _drop_start_date(self, drop: GameEventDrop) -> str:
        override = self._drop_override(drop)
        return override.start_date if override is not None else drop.start_date

    def _drop_start_time(self, drop: GameEventDrop) -> str:
        override = self._drop_override(drop)
        return override.start_time if override is not None else drop.start_time

    def _drop_end_date(self, drop: GameEventDrop) -> str:
        override = self._drop_override(drop)
        return override.end_date if override is not None else drop.end_date

    def _drop_end_time(self, drop: GameEventDrop) -> str:
        override = self._drop_override(drop)
        return override.end_time if override is not None else drop.end_time

    def _drop_start_text(self, drop: GameEventDrop) -> str:
        return _join_datetime(self._drop_start_date(drop), self._drop_start_time(drop))

    def _drop_end_text(self, drop: GameEventDrop) -> str:
        return _join_datetime(self._drop_end_date(drop), self._drop_end_time(drop))

    def _validate_drop_override(self, override: EventDateOverride) -> None:
        self._validate_date_override(override)

    def _show_event_context_menu(self, position) -> None:
        item = self.event_table.itemAt(position)
        if item is None:
            return
        if item.column() not in {2, 3}:
            return
        row_index = item.data(Qt.UserRole)
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(self.filtered_display_items):
            return
        display_item = self.filtered_display_items[row_index]
        self.event_table.selectRow(row_index)

        menu = QMenu(self)
        challenges_action = menu.addAction("Open Linked Challenges")
        edit_action = menu.addAction("Edit Date/Time")
        reset_action = menu.addAction("Reset Edited Date/Time")
        reset_action.setEnabled(any(self._has_override(event) for event in display_item.events))
        selected_action = menu.exec_(self.event_table.viewport().mapToGlobal(position))
        if selected_action == challenges_action:
            self._open_event_challenges(display_item)
        if selected_action == edit_action:
            self._edit_event_dates(display_item)
        elif selected_action == reset_action:
            self._reset_event_dates(display_item)

    def _validate_date_override(self, override: EventDateOverride) -> None:
        if override.start_date:
            encode_date_text(override.start_date)
        if override.start_time:
            encode_time_text(override.start_time)
        if override.end_date:
            encode_date_text(override.end_date)
        if override.end_time:
            encode_time_text(override.end_time)

    def _edit_event_dates(self, display_item: EventDisplayItem) -> None:
        event = display_item.event
        target_events = list(display_item.events)
        current_override = self._event_override(event)
        base_event = event
        if current_override is not None:
            base_event = GameEventRecord(
                event_id=event.event_id,
                event_name_jp=event.event_name_jp,
                event_name_us=event.event_name_us,
                name_label=event.name_label,
                start_date=current_override.start_date,
                start_time=current_override.start_time,
                end_date=current_override.end_date,
                end_time=current_override.end_time,
                source_file=event.source_file,
                source_lvst=event.source_lvst,
                row_index=event.row_index,
                order_value=event.order_value,
                text_hash=event.text_hash,
                text_hash_jp=event.text_hash_jp,
                text_hash_us=event.text_hash_us,
                extra_value=event.extra_value,
                ranking_info=event.ranking_info,
                challenges=event.challenges,
            )
        dialog = EventDateEditDialog(base_event, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        override = dialog.values()
        try:
            self._validate_date_override(override)
        except Exception as exc:
            QMessageBox.warning(self, "Edit Event Dates", f"Invalid date/time value:\n{exc}")
            return
        if (
            override.start_date == event.start_date
            and override.start_time == event.start_time
            and override.end_date == event.end_date
            and override.end_time == event.end_time
        ):
            for target_event in target_events:
                self.date_overrides.pop(self._event_override_key(target_event), None)
        else:
            for target_event in target_events:
                self.date_overrides[self._event_override_key(target_event)] = override
        self._apply_event_filter()
        self.statusBar().showMessage(
            f"Edited event {event.event_id} dates across {len(target_events)} TSS row(s)"
        )

    def _reset_event_dates(self, display_item: EventDisplayItem) -> None:
        removed = False
        for event in display_item.events:
            if self.date_overrides.pop(self._event_override_key(event), None) is not None:
                removed = True
        if not removed:
            return
        self._apply_event_filter()
        self.statusBar().showMessage(
            f"Reset event {display_item.event.event_id} dates across {len(display_item.events)} TSS row(s)"
        )

    def _export_modified_lvst_files(self) -> None:
        if self.current_dataset is None:
            QMessageBox.warning(self, "Export Modified LVST", "Load game event data first.")
            return
        if not self.date_overrides and not self.challenge_date_overrides and not self.drop_date_overrides:
            QMessageBox.information(
                self,
                "Export Modified LVST",
                "There are no edited schedule, challenge, or drop rows to export.",
            )
            return
        output_text = self.output_dir_edit.text().strip()
        if not output_text:
            QMessageBox.warning(self, "Export Modified LVST", "Select an output directory first.")
            return

        root_dir = Path(self.current_dataset.root_dir)
        output_dir = Path(output_text)
        source_to_event: dict[tuple[str, int], GameEventRecord] = {
            self._event_override_key(event): event for event in self.current_dataset.events
        }
        source_to_challenge: dict[tuple[str, int], GameEventChallenge] = {}
        for challenge in self.current_dataset.challenges:
            source_to_challenge.setdefault(self._challenge_override_key(challenge), challenge)
        source_to_drop: dict[tuple[str, int], GameEventDrop] = {}
        for drop in self.current_dataset.drops:
            source_to_drop.setdefault(self._drop_override_key(drop), drop)

        schedule_patches_by_file: dict[str, list[tuple[int, EventDateOverride]]] = {}
        for key, override in self.date_overrides.items():
            event = source_to_event.get(key)
            if event is None:
                continue
            schedule_patches_by_file.setdefault(_normalize_path_text(event.source_file), []).append((event.row_index, override))

        challenge_patches_by_file: dict[str, list[tuple[int, EventDateOverride]]] = {}
        for key, override in self.challenge_date_overrides.items():
            challenge = source_to_challenge.get(key)
            if challenge is None:
                continue
            challenge_patches_by_file.setdefault(_normalize_path_text(challenge.source_file), []).append(
                (challenge.row_index, override)
            )

        drop_patches_by_file: dict[str, list[tuple[int, EventDateOverride]]] = {}
        for key, override in self.drop_date_overrides.items():
            drop = source_to_drop.get(key)
            if drop is None:
                continue
            drop_patches_by_file.setdefault(_normalize_path_text(drop.source_file), []).append((drop.row_index, override))

        if not schedule_patches_by_file and not challenge_patches_by_file and not drop_patches_by_file:
            QMessageBox.information(self, "Export Modified LVST", "No exportable edited rows were found.")
            return

        all_source_files = sorted(set(schedule_patches_by_file) | set(challenge_patches_by_file) | set(drop_patches_by_file))
        exported_files: list[str] = []
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.statusBar().showMessage("Exporting modified LVST files...")
            for source_file_text in all_source_files:
                source_path = Path(source_file_text)
                if not source_path.exists():
                    raise ValueError(f"Source LVST does not exist: {source_file_text}")
                relative_path = source_path.relative_to(root_dir)
                target_path = output_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)

                data = bytearray(source_path.read_bytes())
                table = parse_ace_table(source_path)
                for row_index, override in sorted(schedule_patches_by_file.get(source_file_text, []), key=lambda item: item[0]):
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        SCHEDULE_START_DATE,
                        row_index,
                        encode_date_text(override.start_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        SCHEDULE_START_TIME,
                        row_index,
                        encode_time_text(override.start_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        SCHEDULE_END_DATE,
                        row_index,
                        encode_date_text(override.end_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        SCHEDULE_END_TIME,
                        row_index,
                        encode_time_text(override.end_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                for row_index, override in sorted(challenge_patches_by_file.get(source_file_text, []), key=lambda item: item[0]):
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        CHALLENGE_START_DATE,
                        row_index,
                        encode_date_text(override.start_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        CHALLENGE_START_TIME,
                        row_index,
                        encode_time_text(override.start_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        CHALLENGE_END_DATE,
                        row_index,
                        encode_date_text(override.end_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        CHALLENGE_END_TIME,
                        row_index,
                        encode_time_text(override.end_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                for row_index, override in sorted(drop_patches_by_file.get(source_file_text, []), key=lambda item: item[0]):
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        DROP_START_DATE,
                        row_index,
                        encode_date_text(override.start_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        DROP_START_TIME,
                        row_index,
                        encode_time_text(override.start_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        DROP_END_DATE,
                        row_index,
                        encode_date_text(override.end_date),
                        allowed_types={LVSTColumnType.DATE},
                    )
                    patch_ace_table_u32_cell_in_data(
                        data,
                        table,
                        DROP_END_TIME,
                        row_index,
                        encode_time_text(override.end_time),
                        allowed_types={LVSTColumnType.TIME},
                    )
                target_path.write_bytes(bytes(data))
                exported_files.append(_normalize_path_text(target_path))
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Modified LVST", f"Failed to export modified LVST files:\n{exc}")
            self.statusBar().showMessage("Export failed")
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.statusBar().showMessage(f"Exported {len(exported_files)} modified LVST file(s)")
        preview = "\n".join(exported_files[:8])
        if len(exported_files) > 8:
            preview += f"\n... and {len(exported_files) - 8} more"
        QMessageBox.information(
            self,
            "Export Modified LVST",
            f"Exported {len(exported_files)} modified LVST file(s) to:\n{_normalize_path_text(output_dir)}\n\n{preview}",
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei"))
    window = MainWindow()
    window.show()
    return app.exec_()
