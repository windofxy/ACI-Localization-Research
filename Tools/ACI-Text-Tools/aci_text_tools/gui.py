from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ace_text_builder import (
    build_ace_text_from_json,
    build_ace_text_from_paratranz_json,
    build_default_paratranz_translation_charset_path,
    export_applied_paratranz_translation_charset,
    export_applied_paratranz_translation_charset_for_templates,
    export_utf16be_charset_code_units,
    export_paratranz_translation_charset,
    export_paratranz_translation_charset_for_templates,
    build_applied_paratranz_translation_charset_code_units_partitioned,
)
from .ace_table_parser import ACETableContainer, ACETableRow, export_ace_table_json, parse_ace_table
from .ace_text_parser import (
    ACETextContainer,
    ACETextEntry,
    build_ace_text_export_entries,
    export_ace_text_json,
    export_ace_text_paratranz_json,
    export_ace_text_total_json,
    export_ace_text_total_paratranz_json,
    parse_ace_text,
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
QLineEdit, QTextEdit, QListWidget, QTableWidget {
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


class _TranslationFilterDialog(QDialog):
    def __init__(self, filters: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unique Charset Filters")
        self.resize(520, 360)
        layout = QVBoxLayout(self)

        help_label = QLabel("Patterns use wildcard matching. If a ParaTranz key matches any filter, its charset goes to Unique Charset.")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

        for pattern in filters:
            self.list_widget.addItem(pattern)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(ok_button)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        add_action = QAction("Add Filter", self)
        add_action.triggered.connect(self._add_filter)
        menu.addAction(add_action)
        current = self.list_widget.itemAt(pos)
        if current is not None:
            remove_action = QAction("Remove Filter", self)
            remove_action.triggered.connect(lambda: self._remove_filter(current))
            menu.addAction(remove_action)
        menu.exec_(self.list_widget.mapToGlobal(pos))

    def _add_filter(self) -> None:
        pattern, accepted = QInputDialog.getText(
            self,
            "Add Filter",
            "Wildcard pattern",
        )
        if not accepted:
            return
        normalized = pattern.strip()
        if not normalized:
            return
        self.list_widget.addItem(normalized)

    def _remove_filter(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row >= 0:
            self.list_widget.takeItem(row)

    def filters(self) -> list[str]:
        return [
            self.list_widget.item(index).text().strip()
            for index in range(self.list_widget.count())
            if self.list_widget.item(index).text().strip()
        ]


class ACETextUniqueCharsetItem(QWidget):
    def __init__(
        self,
        output_path: str = "",
        filters: list[str] | None = None,
        remove_callback=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.filters_list = [
            pattern.strip()
            for pattern in (filters or [])
            if isinstance(pattern, str) and pattern.strip()
        ]
        self.output_edit = QLineEdit(_normalize_path_text(output_path))
        self.filters_button = QPushButton("Filters")
        self.filters_button.clicked.connect(self._edit_filters)
        self.remove_button = QPushButton("Remove")
        if remove_callback is not None:
            self.remove_button.clicked.connect(lambda: remove_callback(self))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Unique Charset Output"))
        layout.addWidget(self.output_edit, stretch=1)
        browse_button = QPushButton("Select Output")
        browse_button.clicked.connect(self._browse_output)
        layout.addWidget(self.filters_button)
        layout.addWidget(browse_button)
        layout.addWidget(self.remove_button)

    def _browse_output(self) -> None:
        current = self.output_edit.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Unique Charset",
            current,
            "Text Files (*.txt);;All Files (*.*)",
        )
        if path:
            self.output_edit.setText(_normalize_path_text(path))

    def _edit_filters(self) -> None:
        dialog = _TranslationFilterDialog(self.filters_list, self)
        if dialog.exec_() == dialog.Accepted:
            self.filters_list = dialog.filters()

    def output_path(self) -> str:
        return self.output_edit.text().strip()

    def filters(self) -> list[str]:
        return list(self.filters_list)

    def set_default_output_path(self, output_path: str | Path) -> None:
        destination = Path(output_path)
        self.output_edit.setText(_normalize_path_text(destination.with_name(f"{destination.stem}.charset.txt")))


class ACETextTranslationSourceItem(QWidget):
    def __init__(
        self,
        source_path: str,
        output_path: str,
        remove_callback,
        description: str = "",
        unique_charset_items: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__()
        self.description_edit = QLineEdit(description)
        self.source_edit = QLineEdit(_normalize_path_text(source_path))
        self.output_edit = QLineEdit(_normalize_path_text(output_path))
        self.unique_charset_items: list[ACETextUniqueCharsetItem] = []

        layout = QVBoxLayout(self)

        description_row = QHBoxLayout()
        description_row.addWidget(QLabel("Description"))
        description_row.addWidget(self.description_edit, stretch=1)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("ACT"))
        source_row.addWidget(self.source_edit, stretch=1)
        browse_source_button = QPushButton("Select ACT")
        browse_source_button.clicked.connect(self._browse_source)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(lambda: remove_callback(self))
        source_row.addWidget(browse_source_button)
        source_row.addWidget(remove_button)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output"))
        output_row.addWidget(self.output_edit, stretch=1)
        add_unique_charset_button = QPushButton("Add Unique Charset")
        add_unique_charset_button.clicked.connect(self._add_unique_charset_item_from_button)
        output_row.addWidget(add_unique_charset_button)
        browse_output_button = QPushButton("Select Output")
        browse_output_button.clicked.connect(self._browse_output)
        output_row.addWidget(browse_output_button)

        self.unique_charset_container = QWidget()
        self.unique_charset_layout = QVBoxLayout(self.unique_charset_container)
        self.unique_charset_layout.setContentsMargins(0, 0, 0, 0)
        self.unique_charset_layout.setSpacing(6)
        self.unique_charset_layout.addStretch(1)

        layout.addLayout(description_row)
        layout.addLayout(source_row)
        layout.addLayout(output_row)
        layout.addWidget(self.unique_charset_container)

        for item in unique_charset_items or []:
            if not isinstance(item, dict):
                continue
            self._append_unique_charset_item(
                output_path=item.get("output_path", "") if isinstance(item.get("output_path"), str) else "",
                filters=item.get("filters") if isinstance(item.get("filters"), list) else None,
            )

    def _browse_source(self) -> None:
        current = self.source_edit.text().strip()
        start_dir = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACEText File",
            start_dir,
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if not path:
            return
        self.source_edit.setText(_normalize_path_text(path))
        if not self.output_edit.text().strip():
            source_path = Path(path)
            self.output_edit.setText(
                _normalize_path_text(source_path.with_name(f"{source_path.stem}.paratranz.rebuilt{source_path.suffix}"))
            )

    def _browse_output(self) -> None:
        current = self.output_edit.text().strip()
        if current:
            start_path = current
        else:
            start_path = self.source_edit.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rebuilt ACEText",
            start_path,
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if path:
            self.output_edit.setText(_normalize_path_text(path))

    def _insert_unique_charset_item(self, item: ACETextUniqueCharsetItem) -> None:
        insert_index = max(0, self.unique_charset_layout.count() - 1)
        self.unique_charset_layout.insertWidget(insert_index, item)

    def _append_unique_charset_item(
        self,
        output_path: str = "",
        filters: list[str] | None = None,
    ) -> None:
        item = ACETextUniqueCharsetItem(
            output_path=output_path,
            filters=filters,
            remove_callback=self._remove_unique_charset_item,
            parent=self,
        )
        if not item.output_path().strip():
            item.set_default_output_path(self.output_path())
        self.unique_charset_items.append(item)
        self._insert_unique_charset_item(item)

    def _add_unique_charset_item_from_button(self) -> None:
        self._append_unique_charset_item()

    def _remove_unique_charset_item(self, item: ACETextUniqueCharsetItem) -> None:
        if item in self.unique_charset_items:
            self.unique_charset_items.remove(item)
        item.setParent(None)
        item.deleteLater()

    def description(self) -> str:
        return self.description_edit.text().strip()

    def source_path(self) -> str:
        return self.source_edit.text().strip()

    def output_path(self) -> str:
        return self.output_edit.text().strip()

    def unique_charset_items_payload(self) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for item in self.unique_charset_items:
            if not item.output_path().strip() and not item.filters():
                continue
            payload.append(
                {
                    "output_path": item.output_path(),
                    "filters": item.filters(),
                }
            )
        return payload


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ACI Text Tools")
        self.resize(1320, 900)
        self.setStyleSheet(WINDOW_STYLESHEET)
        self.setAcceptDrops(True)

        self.project_root = Path(__file__).resolve().parents[1]
        self.config_dir = self.project_root / "config"
        self.translation_config_path = self.config_dir / "ace_text_translation_config.json"
        self.current_text_container: ACETextContainer | None = None
        self.filtered_text_entries: list[ACETextEntry] = []
        self.current_table_container: ACETableContainer | None = None
        self.filtered_table_rows: list[ACETableRow] = []
        self.tabs = QTabWidget()

        self.ace_text_file_edit = QLineEdit()
        self.text_entry_filter_edit = QLineEdit()
        self.text_entry_filter_edit.setPlaceholderText("Search hash label, text label, hash, or localized value")
        self.text_entry_list = QListWidget()
        self.text_entry_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.text_summary_edit = QTextEdit()
        self.text_summary_edit.setReadOnly(True)
        self.text_detail_edit = QTextEdit()
        self.text_detail_edit.setReadOnly(True)
        self.text_values_table = QTableWidget(0, 2)
        self.text_values_table.setHorizontalHeaderLabels(["Language", "Value"])
        self.text_values_table.verticalHeader().setVisible(False)
        self.text_values_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.text_values_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.text_values_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.text_values_table.setWordWrap(True)
        self.text_values_table.horizontalHeader().setStretchLastSection(True)
        self.text_values_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.text_values_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ace_text_batch_progress_label = QLabel("Batch export progress: idle")
        self.ace_text_batch_progress_bar = QProgressBar()
        self.ace_text_batch_progress_bar.setRange(0, 1)
        self.ace_text_batch_progress_bar.setValue(0)
        self.ace_text_batch_progress_bar.setTextVisible(True)
        self.ace_text_paratranz_language_combo = QComboBox()
        self.ace_text_paratranz_language_combo.setEnabled(False)
        self.translation_paratranz_file_edit = QLineEdit()
        self.translation_paratranz_language_combo = QComboBox()
        self.translation_paratranz_fallback_combo = QComboBox()
        self.translation_act_source_items: list[ACETextTranslationSourceItem] = []
        self.translation_act_sources_container = QWidget()
        self.translation_act_sources_layout = QVBoxLayout(self.translation_act_sources_container)
        self.translation_act_sources_layout.setContentsMargins(0, 0, 0, 0)
        self.translation_act_sources_layout.setSpacing(10)
        self.translation_act_sources_layout.addStretch(1)

        self.ace_table_file_edit = QLineEdit()
        self.table_row_filter_edit = QLineEdit()
        self.table_row_filter_edit.setPlaceholderText("Search row index, column hash, or cell value")
        self.table_column_list = QListWidget()
        self.table_column_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_row_list = QListWidget()
        self.table_row_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_summary_edit = QTextEdit()
        self.table_summary_edit.setReadOnly(True)
        self.table_detail_edit = QTextEdit()
        self.table_detail_edit.setReadOnly(True)
        self.table_values_table = QTableWidget(0, 3)
        self.table_values_table.setHorizontalHeaderLabels(["Column", "Type", "Value"])
        self.table_values_table.verticalHeader().setVisible(False)
        self.table_values_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_values_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_values_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_values_table.setWordWrap(True)
        self.table_values_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_values_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_values_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self._ensure_config_dir()
        self._build_ui()
        self._load_translation_page_config()
        self.statusBar().showMessage("Ready")

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_ace_text_viewer_page(), "ACEText查看")
        self.tabs.addTab(self._build_ace_table_viewer_page(), "ACETable查看")

        self.tabs.addTab(self._build_ace_text_translation_page(), "ACEText翻译")
        root_layout.addWidget(self.tabs)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar(self))

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        path = self._first_dropped_file_path(event)
        if path is not None and self._is_supported_drop_path(path):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        path = self._first_dropped_file_path(event)
        if path is not None and self._is_supported_drop_path(path):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        path = self._first_dropped_file_path(event)
        if path is None or not self._is_supported_drop_path(path):
            event.ignore()
            self.statusBar().showMessage("Dropped file is not a supported ACEText or ACETable file.")
            return

        try:
            self._open_dropped_file(path)
            event.acceptProposedAction()
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
            event.ignore()

    def _build_ace_text_viewer_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        source_group = QGroupBox("ACEText Source")
        source_layout = QGridLayout(source_group)
        browse_button = self._make_button("Select File", self._browse_ace_text_file)
        load_button = self._make_button("Load", self._load_ace_text_from_edit)
        export_button = self._make_button("Export JSON", self._export_ace_text_json)
        import_button = self._make_button("Import JSON -> ACT", self._import_ace_text_json_to_act)
        export_paratranz_button = self._make_button("Export ParaTranz", self._export_ace_text_paratranz_json)
        import_paratranz_button = self._make_button("Import ParaTranz -> ACT", self._import_ace_text_paratranz_to_act)
        batch_export_button = self._make_button("Batch Export JSON", self._batch_export_ace_text_json)
        batch_export_paratranz_button = self._make_button(
            "Batch Export ParaTranz",
            self._batch_export_ace_text_paratranz_json,
        )
        self.ace_text_file_edit.returnPressed.connect(self._load_ace_text_from_edit)
        source_layout.addWidget(QLabel("ACEText"), 0, 0)
        source_layout.addWidget(self.ace_text_file_edit, 0, 1)
        source_layout.addWidget(browse_button, 0, 2)
        source_layout.addWidget(load_button, 0, 3)
        source_layout.addWidget(export_button, 0, 4)
        source_layout.addWidget(export_paratranz_button, 0, 5)
        source_layout.addWidget(import_button, 0, 6)
        source_layout.addWidget(import_paratranz_button, 0, 7)
        source_layout.addWidget(QLabel("ParaTranz Target"), 1, 0)
        source_layout.addWidget(self.ace_text_paratranz_language_combo, 1, 1, 1, 2)
        source_layout.addWidget(batch_export_button, 1, 4)
        source_layout.addWidget(batch_export_paratranz_button, 1, 5)
        source_layout.addWidget(self.ace_text_batch_progress_label, 2, 0, 1, 2)
        source_layout.addWidget(self.ace_text_batch_progress_bar, 2, 2, 1, 6)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.addWidget(self._build_ace_text_left_panel())
        content_splitter.addWidget(self._build_ace_text_right_panel())
        content_splitter.setSizes([460, 860])

        layout.addWidget(source_group)
        layout.addWidget(content_splitter, stretch=1)
        return page

    def _build_ace_text_translation_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        config_group = QGroupBox("Translation Config")
        config_layout = QHBoxLayout(config_group)
        save_config_button = self._make_button("Save Config", self._save_translation_page_config_from_button)
        config_layout.addStretch(1)
        config_layout.addWidget(save_config_button)

        paratranz_group = QGroupBox("ParaTranz Source")
        paratranz_layout = QGridLayout(paratranz_group)
        browse_button = self._make_button("Select File", self._browse_translation_paratranz_file)
        translate_button = self._make_button("Translate", self._translate_paratranz_sources)
        paratranz_layout.addWidget(QLabel("ParaTranz"), 0, 0)
        paratranz_layout.addWidget(self.translation_paratranz_file_edit, 0, 1)
        paratranz_layout.addWidget(browse_button, 0, 2)
        paratranz_layout.addWidget(QLabel("Target"), 0, 3)
        paratranz_layout.addWidget(self.translation_paratranz_language_combo, 0, 4)
        paratranz_layout.addWidget(QLabel("Fallback"), 0, 5)
        paratranz_layout.addWidget(self.translation_paratranz_fallback_combo, 0, 6)
        paratranz_layout.addWidget(translate_button, 0, 7)

        sources_group = QGroupBox("ACEText Sources")
        sources_layout = QVBoxLayout(sources_group)
        actions_row = QHBoxLayout()
        add_act_button = self._make_button("Add ACT Files", self._add_translation_act_files)
        clear_button = self._make_button("Clear List", self._clear_translation_act_sources)
        actions_row.addWidget(add_act_button)
        actions_row.addWidget(clear_button)
        actions_row.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.translation_act_sources_container)

        sources_layout.addLayout(actions_row)
        sources_layout.addWidget(scroll)

        layout.addWidget(config_group)
        layout.addWidget(paratranz_group)
        layout.addWidget(sources_group, stretch=1)

        self._refresh_translation_language_combo()
        return page

    def _build_ace_table_viewer_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        source_group = QGroupBox("ACETable Source")
        source_layout = QGridLayout(source_group)
        browse_button = self._make_button("Select File", self._browse_ace_table_file)
        load_button = self._make_button("Load", self._load_ace_table_from_edit)
        export_button = self._make_button("Export JSON", self._export_ace_table_json)
        self.ace_table_file_edit.returnPressed.connect(self._load_ace_table_from_edit)
        source_layout.addWidget(QLabel("ACETable"), 0, 0)
        source_layout.addWidget(self.ace_table_file_edit, 0, 1)
        source_layout.addWidget(browse_button, 0, 2)
        source_layout.addWidget(load_button, 0, 3)
        source_layout.addWidget(export_button, 0, 4)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.addWidget(self._build_ace_table_left_panel())
        content_splitter.addWidget(self._build_ace_table_right_panel())
        content_splitter.setSizes([420, 900])

        layout.addWidget(source_group)
        layout.addWidget(content_splitter, stretch=1)
        return page

    def _build_ace_text_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_text_entry_panel())
        splitter.addWidget(self._build_text_summary_panel())
        splitter.setSizes([620, 220])

        layout.addWidget(splitter)
        return panel

    def _build_ace_text_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_text_detail_panel())
        splitter.addWidget(self._build_text_values_panel())
        splitter.setSizes([280, 560])

        layout.addWidget(splitter)
        return panel

    def _build_ace_table_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_table_column_panel())
        splitter.addWidget(self._build_table_summary_panel())
        splitter.setSizes([520, 260])

        layout.addWidget(splitter)
        return panel

    def _build_ace_table_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_table_row_panel())
        splitter.addWidget(self._build_table_detail_panel())
        splitter.addWidget(self._build_table_values_panel())
        splitter.setSizes([320, 220, 360])

        layout.addWidget(splitter)
        return panel

    def _build_text_entry_panel(self) -> QWidget:
        panel = QGroupBox("Entries")
        layout = QVBoxLayout(panel)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search"))
        filter_row.addWidget(self.text_entry_filter_edit, stretch=1)
        layout.addLayout(filter_row)
        self.text_entry_filter_edit.textChanged.connect(self._populate_text_entry_list)
        self.text_entry_list.currentItemChanged.connect(self._on_text_entry_changed)
        layout.addWidget(self.text_entry_list)
        return panel

    def _build_text_summary_panel(self) -> QWidget:
        panel = QGroupBox("ACEText Summary")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.text_summary_edit)
        return panel

    def _build_text_detail_panel(self) -> QWidget:
        panel = QGroupBox("Entry Details")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.text_detail_edit)
        return panel

    def _build_text_values_panel(self) -> QWidget:
        panel = QGroupBox("Localized Values")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.text_values_table)
        return panel

    def _build_table_column_panel(self) -> QWidget:
        panel = QGroupBox("Columns")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.table_column_list)
        return panel

    def _build_table_summary_panel(self) -> QWidget:
        panel = QGroupBox("ACETable Summary")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.table_summary_edit)
        return panel

    def _build_table_row_panel(self) -> QWidget:
        panel = QGroupBox("Rows")
        layout = QVBoxLayout(panel)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search"))
        filter_row.addWidget(self.table_row_filter_edit, stretch=1)
        layout.addLayout(filter_row)
        self.table_row_filter_edit.textChanged.connect(self._populate_table_row_list)
        self.table_row_list.currentItemChanged.connect(self._on_table_row_changed)
        layout.addWidget(self.table_row_list)
        return panel

    def _build_table_detail_panel(self) -> QWidget:
        panel = QGroupBox("Row Details")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.table_detail_edit)
        return panel

    def _build_table_values_panel(self) -> QWidget:
        panel = QGroupBox("Row Values")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.table_values_table)
        return panel

    def _make_button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def _default_rebuilt_ace_text_output_path(self, source_path: str | Path) -> Path:
        source = Path(source_path)
        return source.with_name(f"{source.stem}.paratranz.rebuilt{source.suffix}")

    def _default_translation_charset_output_path(self, output_path: str | Path) -> Path:
        destination = Path(output_path)
        return destination.with_name(f"{destination.stem}.charset.txt")

    def _ensure_config_dir(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_translation_page_config(self) -> None:
        path = self.translation_config_path
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self.statusBar().showMessage(f"Failed to load translation config: {path.name}")
            return

        paratranz_path = data.get("paratranz_path")
        if isinstance(paratranz_path, str):
            self.translation_paratranz_file_edit.setText(_normalize_path_text(paratranz_path))

        target_language = data.get("target_language")
        if isinstance(target_language, str):
            index = self.translation_paratranz_language_combo.findData(target_language)
            if index >= 0:
                self.translation_paratranz_language_combo.setCurrentIndex(index)

        fallback_language = data.get("fallback_language")
        if isinstance(fallback_language, str):
            index = self.translation_paratranz_fallback_combo.findData(fallback_language)
            if index >= 0:
                self.translation_paratranz_fallback_combo.setCurrentIndex(index)

        sources = data.get("sources")
        if isinstance(sources, list):
            self._clear_translation_act_sources(show_status=False)
            for source in sources:
                if not isinstance(source, dict):
                    continue
                source_path = source.get("act_path")
                output_path = source.get("output_path")
                description = source.get("description")
                unique_charset_items = source.get("unique_charset_items")
                if isinstance(source_path, str) and source_path:
                    normalized_unique_charset_items: list[dict[str, object]] | None = None
                    if isinstance(unique_charset_items, list):
                        normalized_unique_charset_items = [
                            item for item in unique_charset_items if isinstance(item, dict)
                        ]
                    else:
                        legacy_enabled = bool(source.get("unique_charset_enabled"))
                        legacy_output = source.get("unique_charset_output_path")
                        legacy_filters = source.get("unique_charset_filters")
                        if legacy_enabled:
                            normalized_unique_charset_items = [
                                {
                                    "output_path": legacy_output if isinstance(legacy_output, str) else "",
                                    "filters": legacy_filters if isinstance(legacy_filters, list) else [],
                                }
                            ]
                    self._append_translation_act_source(
                        source_path,
                        output_path if isinstance(output_path, str) else None,
                        description=description if isinstance(description, str) else "",
                        unique_charset_items=normalized_unique_charset_items,
                    )

    def _save_translation_page_config(self) -> None:
        self._ensure_config_dir()
        payload = {
            "paratranz_path": _normalize_path_text(self.translation_paratranz_file_edit.text().strip()),
            "target_language": self.translation_paratranz_language_combo.currentData(),
            "fallback_language": self.translation_paratranz_fallback_combo.currentData(),
            "sources": [
                {
                    "description": item.description(),
                    "act_path": item.source_path(),
                    "output_path": item.output_path(),
                    "unique_charset_items": item.unique_charset_items_payload(),
                }
                for item in self.translation_act_source_items
                if (
                    item.description()
                    or
                    item.source_path()
                    or item.output_path()
                    or item.unique_charset_items_payload()
                )
            ],
        }
        self.translation_config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _save_translation_page_config_from_button(self) -> None:
        try:
            self._save_translation_page_config()
        except Exception as exc:
            self._show_error(f"Failed to save translation config: {exc}")
            return
        self.statusBar().showMessage(f"Saved translation config to {self.translation_config_path.name}.")

    def _is_act_text_path(self, path: Path) -> bool:
        try:
            with path.open("rb") as stream:
                return stream.read(4) == b"ACT\x00"
        except OSError:
            return False

    def _discover_ace_text_batch_roots(self, input_root: Path) -> list[Path]:
        root_units: list[Path] = []
        direct_entries = sorted(input_root.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower()))
        direct_act_files = [path for path in direct_entries if path.is_file() and self._is_act_text_path(path)]
        if direct_act_files:
            root_units.append(input_root)
        for path in direct_entries:
            if path.is_dir():
                root_units.append(path)
        if not root_units and input_root.is_dir():
            root_units.append(input_root)
        return root_units

    def _iter_ace_text_files_for_root(self, input_root: Path, root_path: Path) -> list[Path]:
        if root_path == input_root:
            return [
                path
                for path in sorted(input_root.iterdir(), key=lambda value: value.name.lower())
                if path.is_file() and self._is_act_text_path(path)
            ]
        return [
            path
            for path in sorted(root_path.rglob("*"), key=lambda value: str(value).lower())
            if path.is_file() and self._is_act_text_path(path)
        ]

    def _build_batch_ace_text_output_path(
        self,
        input_root: Path,
        output_root: Path,
        source_path: Path,
        mode: str,
    ) -> Path:
        relative = source_path.relative_to(input_root)
        flat_name = "_".join(relative.parts)
        if mode == "paratranz":
            return output_root / f"{flat_name}.paratranz.json"
        return output_root / f"{flat_name}.json"

    def _build_batch_ace_text_total_output_path(self, output_root: Path, mode: str) -> Path:
        if mode == "paratranz":
            return output_root / "Total.paratranz.json"
        return output_root / "Total.json"

    def _set_ace_text_batch_progress(self, current: int, total: int, message: str) -> None:
        safe_total = max(1, total)
        self.ace_text_batch_progress_bar.setRange(0, safe_total)
        self.ace_text_batch_progress_bar.setValue(max(0, min(current, safe_total)))
        self.ace_text_batch_progress_label.setText(message)

    def _first_dropped_file_path(self, event) -> Path | None:
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_file():
                    return path
        return None

    def _is_supported_drop_path(self, path: Path) -> bool:
        try:
            with path.open("rb") as stream:
                magic = stream.read(4)
        except OSError:
            return False
        return magic in {b"ACT\x00", b"LVST"}

    def _open_dropped_file(self, path: Path) -> None:
        with path.open("rb") as stream:
            magic = stream.read(4)

        if magic == b"ACT\x00":
            self.tabs.setCurrentIndex(0)
            self._load_ace_text_file(str(path))
            self.statusBar().showMessage(f"Loaded ACEText from dropped file {path.name}.")
            return

        if magic == b"LVST":
            self.tabs.setCurrentIndex(1)
            self._load_ace_table_file(str(path))
            self.statusBar().showMessage(f"Loaded ACETable from dropped file {path.name}.")
            return

        raise ValueError(f"Unsupported dropped file type for {path.name}.")

    def _browse_ace_text_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACEText File",
            str(self.project_root),
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if path:
            self._load_ace_text_file(path)

    def _browse_translation_paratranz_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACEText ParaTranz JSON",
            str(self.project_root),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if path:
            self.translation_paratranz_file_edit.setText(_normalize_path_text(path))

    def _browse_ace_table_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACETable File",
            str(self.project_root),
            "ACETable Files (*.lvst *.bin);;All Files (*.*)",
        )
        if path:
            self._load_ace_table_file(path)

    def _load_ace_text_from_edit(self) -> None:
        path = self.ace_text_file_edit.text().strip()
        if path:
            self._load_ace_text_file(path)

    def _export_ace_text_json(self) -> None:
        container = self.current_text_container
        if container is None:
            self._show_error("Load an ACEText file before exporting JSON.")
            return

        source_path = Path(container.source_file)
        default_path = source_path.with_suffix(".json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ACEText JSON",
            str(default_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not path:
            return

        try:
            self.statusBar().showMessage("Exporting ACEText JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            output_path = export_ace_text_json(container, path)
            self.statusBar().showMessage(
                f"Exported ACEText JSON to {output_path.name}."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _export_ace_text_paratranz_json(self) -> None:
        container = self.current_text_container
        if container is None:
            self._show_error("Load an ACEText file before exporting ParaTranz JSON.")
            return

        source_path = Path(container.source_file)
        default_path = source_path.with_name(f"{source_path.stem}.paratranz.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ACEText ParaTranz JSON",
            str(default_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not path:
            return

        try:
            self.statusBar().showMessage("Exporting ACEText ParaTranz JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            output_path = export_ace_text_paratranz_json(container, path)
            self.statusBar().showMessage(
                f"Exported ACEText ParaTranz JSON to {output_path.name}."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _import_ace_text_json_to_act(self) -> None:
        container = self.current_text_container
        if container is None:
            self._show_error("Load an ACEText file to use as the ACT template before importing JSON.")
            return

        source_path = Path(container.source_file)
        default_json_path = source_path.with_suffix(".json")
        json_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACEText JSON",
            str(default_json_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not json_path:
            return

        default_output_path = source_path.with_name(f"{source_path.stem}.rebuilt{source_path.suffix}")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rebuilt ACEText",
            str(default_output_path),
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if not output_path:
            return

        try:
            self.statusBar().showMessage("Rebuilding ACEText from JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            built_path = build_ace_text_from_json(container, json_path, output_path)
            self.statusBar().showMessage(f"Rebuilt ACEText to {built_path.name}.")
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _import_ace_text_paratranz_to_act(self) -> None:
        container = self.current_text_container
        if container is None:
            self._show_error("Load an ACEText file to use as the ACT template before importing ParaTranz JSON.")
            return
        target_language = self.ace_text_paratranz_language_combo.currentData()
        if not isinstance(target_language, str) or not target_language:
            self._show_error("Select a target language before importing ParaTranz JSON.")
            return
        fallback_language = self.translation_paratranz_fallback_combo.currentData()
        if not isinstance(fallback_language, str):
            fallback_language = ""

        source_path = Path(container.source_file)
        default_json_path = source_path.with_name(f"{source_path.stem}.paratranz.json")
        json_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ACEText ParaTranz JSON",
            str(default_json_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not json_path:
            return

        default_output_path = source_path.with_name(f"{source_path.stem}.paratranz.rebuilt{source_path.suffix}")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rebuilt ACEText",
            str(default_output_path),
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if not output_path:
            return

        try:
            self.statusBar().showMessage("Rebuilding ACEText from ParaTranz JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            built_path = build_ace_text_from_paratranz_json(
                container,
                json_path,
                output_path,
                target_language=target_language,
                fallback_language=fallback_language or None,
            )
            charset_path = export_applied_paratranz_translation_charset(
                container,
                json_path,
                build_default_paratranz_translation_charset_path(json_path),
                target_language=target_language,
                fallback_language=fallback_language or None,
            )
            self.statusBar().showMessage(
                f"Rebuilt ACEText to {built_path.name}; exported charset to {charset_path.name}."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _refresh_translation_language_combo(self) -> None:
        previous = self.translation_paratranz_language_combo.currentData()
        previous_fallback = self.translation_paratranz_fallback_combo.currentData()
        self.translation_paratranz_language_combo.clear()
        self.translation_paratranz_fallback_combo.clear()
        languages = ["JP", "US", "FR", "IT", "GE", "SP", "RU"]
        for language in languages:
            self.translation_paratranz_language_combo.addItem(language, language)
        self.translation_paratranz_fallback_combo.addItem("(None)", "")
        for language in languages:
            self.translation_paratranz_fallback_combo.addItem(language, language)
        target = previous if isinstance(previous, str) and previous in languages else "JP"
        index = self.translation_paratranz_language_combo.findData(target)
        if index >= 0:
            self.translation_paratranz_language_combo.setCurrentIndex(index)
        fallback = previous_fallback if isinstance(previous_fallback, str) else ""
        fallback_index = self.translation_paratranz_fallback_combo.findData(fallback)
        if fallback_index >= 0:
            self.translation_paratranz_fallback_combo.setCurrentIndex(fallback_index)

    def _insert_translation_act_source_item(self, item: ACETextTranslationSourceItem) -> None:
        insert_index = max(0, self.translation_act_sources_layout.count() - 1)
        self.translation_act_sources_layout.insertWidget(insert_index, item)

    def _append_translation_act_source(
        self,
        source_path: str,
        output_path: str | None = None,
        description: str = "",
        unique_charset_items: list[dict[str, object]] | None = None,
    ) -> None:
        source = Path(source_path)
        resolved_output_path = output_path if output_path else str(self._default_rebuilt_ace_text_output_path(source))
        item = ACETextTranslationSourceItem(
            str(source),
            resolved_output_path,
            self._remove_translation_act_source_item,
            description=description,
            unique_charset_items=unique_charset_items,
        )
        self.translation_act_source_items.append(item)
        self._insert_translation_act_source_item(item)

    def _add_translation_act_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add ACEText Files",
            str(self.project_root),
            "ACEText Files (*.act *.bin);;All Files (*.*)",
        )
        if not paths:
            return
        for path in paths:
            self._append_translation_act_source(path)
        self.statusBar().showMessage(f"Added {len(paths)} ACEText source file(s) to the translation list.")

    def _remove_translation_act_source_item(self, item: ACETextTranslationSourceItem) -> None:
        if item in self.translation_act_source_items:
            self.translation_act_source_items.remove(item)
        item.setParent(None)
        item.deleteLater()
        self.statusBar().showMessage("Removed ACEText source from the translation list.")

    def _clear_translation_act_sources(self, show_status: bool = True) -> None:
        for item in list(self.translation_act_source_items):
            item.setParent(None)
            item.deleteLater()
        self.translation_act_source_items.clear()
        if show_status:
            self.statusBar().showMessage("Cleared ACEText translation source list.")

    def _translate_paratranz_sources(self) -> None:
        json_path = self.translation_paratranz_file_edit.text().strip()
        if not json_path:
            self._show_error("Select a ParaTranz JSON file first.")
            return
        target_language = self.translation_paratranz_language_combo.currentData()
        if not isinstance(target_language, str) or not target_language:
            self._show_error("Select a target language first.")
            return
        fallback_language = self.translation_paratranz_fallback_combo.currentData()
        if not isinstance(fallback_language, str):
            fallback_language = ""
        if not self.translation_act_source_items:
            self._show_error("Add at least one ACEText source file first.")
            return

        failures: list[str] = []
        translated_count = 0
        successful_total_charset_source_paths: list[str] = []
        charset_path: Path | None = None
        unique_charset_written_paths: list[Path] = []
        unique_charset_groups: dict[str, list[int]] = {}
        unique_charset_seen_by_path: dict[str, set[int]] = {}
        total_charset_code_units: list[int] = []
        total_charset_seen: set[int] = set()
        try:
            self.statusBar().showMessage("Translating ACEText files from ParaTranz JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for item in self.translation_act_source_items:
                source_path = item.source_path()
                output_path = item.output_path()
                if not source_path:
                    failures.append("A translation source entry is missing its ACT file path.")
                    continue
                if not output_path:
                    failures.append(f"{source_path}: output path is empty.")
                    continue
                unique_charset_items = item.unique_charset_items_payload()
                for unique_charset_item in unique_charset_items:
                    unique_charset_output_path = unique_charset_item.get("output_path")
                    if not isinstance(unique_charset_output_path, str) or not unique_charset_output_path.strip():
                        failures.append(f"{source_path}: a unique charset output path is empty.")
                        unique_charset_items = []
                        break
                if not unique_charset_items and any(
                    not isinstance(unique_charset_item.get("output_path"), str) or not str(unique_charset_item.get("output_path")).strip()
                    for unique_charset_item in item.unique_charset_items_payload()
                ):
                    continue
                try:
                    built_path = build_ace_text_from_paratranz_json(
                        source_path,
                        json_path,
                        output_path,
                        target_language=target_language,
                        fallback_language=fallback_language or None,
                    )
                    translated_count += 1
                    if unique_charset_items:
                        catch_all_item = next(
                            (
                                unique_charset_item
                                for unique_charset_item in unique_charset_items
                                if not [
                                    pattern.strip()
                                    for pattern in unique_charset_item.get("filters", [])
                                    if isinstance(pattern, str) and pattern.strip()
                                ]
                            ),
                            None,
                        )
                        if catch_all_item is not None:
                            unique_code_units = build_applied_paratranz_translation_charset_code_units_partitioned(
                                source_path,
                                json_path,
                                [],
                                target_language=target_language,
                                fallback_language=fallback_language or None,
                            )[0]
                            output_path_key = _normalize_path_text(str(catch_all_item["output_path"]))
                            if output_path_key not in unique_charset_groups:
                                unique_charset_groups[output_path_key] = []
                                unique_charset_seen_by_path[output_path_key] = set()
                            seen_for_path = unique_charset_seen_by_path[output_path_key]
                            for code_unit in unique_code_units:
                                if code_unit in seen_for_path:
                                    continue
                                seen_for_path.add(code_unit)
                                unique_charset_groups[output_path_key].append(code_unit)
                        else:
                            unmatched_code_units: list[int] = []
                            unmatched_seen: set[int] = set()
                            for unique_charset_item in unique_charset_items:
                                filters = [
                                    pattern.strip()
                                    for pattern in unique_charset_item.get("filters", [])
                                    if isinstance(pattern, str) and pattern.strip()
                                ]
                                unique_code_units, total_code_units = build_applied_paratranz_translation_charset_code_units_partitioned(
                                    source_path,
                                    json_path,
                                    filters,
                                    target_language=target_language,
                                    fallback_language=fallback_language or None,
                                )
                                output_path_key = _normalize_path_text(str(unique_charset_item["output_path"]))
                                if output_path_key not in unique_charset_groups:
                                    unique_charset_groups[output_path_key] = []
                                    unique_charset_seen_by_path[output_path_key] = set()
                                seen_for_path = unique_charset_seen_by_path[output_path_key]
                                for code_unit in unique_code_units:
                                    if code_unit in seen_for_path:
                                        continue
                                    seen_for_path.add(code_unit)
                                    unique_charset_groups[output_path_key].append(code_unit)
                                for code_unit in total_code_units:
                                    if code_unit in unmatched_seen:
                                        continue
                                    unmatched_seen.add(code_unit)
                                    unmatched_code_units.append(code_unit)
                            for code_unit in unmatched_code_units:
                                if code_unit in total_charset_seen:
                                    continue
                                total_charset_seen.add(code_unit)
                                total_charset_code_units.append(code_unit)
                    else:
                        successful_total_charset_source_paths.append(source_path)
                except Exception as exc:
                    failures.append(f"{source_path}: {exc}")
            if successful_total_charset_source_paths or total_charset_code_units:
                total_output_path = build_default_paratranz_translation_charset_path(json_path)
                if successful_total_charset_source_paths:
                    charset_path = export_applied_paratranz_translation_charset_for_templates(
                        successful_total_charset_source_paths,
                        json_path,
                        total_output_path,
                        target_language=target_language,
                        fallback_language=fallback_language or None,
                    )
                    if total_charset_code_units:
                        merged_existing = Path(charset_path).read_bytes()
                        existing_units = []
                        if merged_existing.startswith(b"\xFE\xFF"):
                            merged_existing = merged_existing[2:]
                        for index in range(0, len(merged_existing), 2):
                            existing_units.append(int.from_bytes(merged_existing[index:index + 2], "big", signed=False))
                        merged_seen = set()
                        merged_units: list[int] = []
                        for code_unit in existing_units + total_charset_code_units:
                            if code_unit in merged_seen:
                                continue
                            merged_seen.add(code_unit)
                            merged_units.append(code_unit)
                        charset_path = export_utf16be_charset_code_units(merged_units, total_output_path)
                else:
                    charset_path = export_utf16be_charset_code_units(total_charset_code_units, total_output_path)
            for output_path_key, code_units in unique_charset_groups.items():
                unique_charset_written_paths.append(
                    export_utf16be_charset_code_units(code_units, output_path_key)
                )
        finally:
            QApplication.restoreOverrideCursor()

        message = f"Translated {translated_count} ACEText file(s) from ParaTranz JSON."
        if failures:
            preview = "\n".join(failures[:10])
            if len(failures) > 10:
                preview += f"\n... {len(failures) - 10} more failure(s)"
            QMessageBox.warning(
                self,
                "ACI Text Tools",
                f"{message}\n\nFailures: {len(failures)}\n\n{preview}",
            )
            if charset_path is not None:
                self.statusBar().showMessage(
                    f"{message} Exported total charset to {charset_path.name}. Failures: {len(failures)}."
                )
            elif unique_charset_written_paths:
                self.statusBar().showMessage(
                    f"{message} Exported {len(unique_charset_written_paths)} unique charset file(s). Failures: {len(failures)}."
                )
            else:
                self.statusBar().showMessage(f"{message} Failures: {len(failures)}.")
            return

        try:
            self._save_translation_page_config()
        except Exception as exc:
            self._show_error(f"{message}\n\nFailed to save translation config: {exc}")
            return

        if charset_path is not None:
            self.statusBar().showMessage(
                f"{message} Exported total charset to {charset_path.name}"
                f"{'; ' if unique_charset_written_paths else '.'}"
                f"{f'exported {len(unique_charset_written_paths)} unique charset file(s).' if unique_charset_written_paths else ''}"
            )
        elif unique_charset_written_paths:
            self.statusBar().showMessage(f"{message} Exported {len(unique_charset_written_paths)} unique charset file(s).")
        else:
            self.statusBar().showMessage(message)

    def _batch_export_ace_text_json(self) -> None:
        self._batch_export_ace_text_files("json")

    def _batch_export_ace_text_paratranz_json(self) -> None:
        self._batch_export_ace_text_files("paratranz")

    def _load_ace_table_from_edit(self) -> None:
        path = self.ace_table_file_edit.text().strip()
        if path:
            self._load_ace_table_file(path)

    def _export_ace_table_json(self) -> None:
        container = self.current_table_container
        if container is None:
            self._show_error("Load an ACETable file before exporting JSON.")
            return

        source_path = Path(container.source_file)
        default_path = source_path.with_suffix(".json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ACETable JSON",
            str(default_path),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not path:
            return

        try:
            self.statusBar().showMessage("Exporting ACETable JSON...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            output_path = export_ace_table_json(container, path)
            self.statusBar().showMessage(
                f"Exported ACETable JSON to {output_path.name}."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _batch_export_ace_text_files(self, mode: str) -> None:
        input_dir = QFileDialog.getExistingDirectory(
            self,
            "Select ACEText Input Folder",
            str(self.project_root),
        )
        if not input_dir:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select ACEText Output Folder",
            str(self.project_root),
        )
        if not output_dir:
            return

        input_root = Path(input_dir)
        output_root = Path(output_dir)
        root_units = self._discover_ace_text_batch_roots(input_root)
        if not root_units:
            self.statusBar().showMessage(f"No ACEText files found under {input_root}.")
            self._set_ace_text_batch_progress(0, 1, "Batch export progress: idle")
            return

        failures: list[str] = []
        exported_count = 0
        verb = "ParaTranz JSON" if mode == "paratranz" else "JSON"
        total_roots = len(root_units)
        scanned_roots = 0
        total_entries: list[tuple[str, ACETextEntry]] = []

        try:
            self.statusBar().showMessage(f"Batch exporting ACEText {verb}...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._set_ace_text_batch_progress(0, total_roots, f"Batch export progress: 0/{total_roots} root folders")
            for root_path in root_units:
                source_paths = self._iter_ace_text_files_for_root(input_root, root_path)
                for source_path in source_paths:
                    try:
                        container = parse_ace_text(source_path)
                        total_entries.extend(build_ace_text_export_entries(container))
                        output_path = self._build_batch_ace_text_output_path(
                            input_root=input_root,
                            output_root=output_root,
                            source_path=source_path,
                            mode=mode,
                        )
                        if mode == "paratranz":
                            export_ace_text_paratranz_json(container, output_path)
                        else:
                            export_ace_text_json(container, output_path)
                        exported_count += 1
                    except Exception as exc:
                        failures.append(f"{source_path}: {exc}")
                scanned_roots += 1
                self._set_ace_text_batch_progress(
                    scanned_roots,
                    total_roots,
                    f"Batch export progress: {scanned_roots}/{total_roots} root folders",
                )
                QApplication.processEvents()
            total_output_path = self._build_batch_ace_text_total_output_path(output_root, mode)
            if mode == "paratranz":
                export_ace_text_total_paratranz_json(total_entries, total_output_path)
            else:
                export_ace_text_total_json(total_entries, total_output_path)
        finally:
            QApplication.restoreOverrideCursor()

        message = f"Batch exported {exported_count} ACEText file(s) to {output_root.name} as {verb}."
        if failures:
            preview = "\n".join(failures[:10])
            if len(failures) > 10:
                preview += f"\n... {len(failures) - 10} more failure(s)"
            QMessageBox.warning(
                self,
                "ACI Text Tools",
                f"{message}\n\nFailures: {len(failures)}\n\n{preview}",
            )
            self.statusBar().showMessage(f"{message} Failures: {len(failures)}.")
            return

        self.statusBar().showMessage(message)
        self._set_ace_text_batch_progress(
            total_roots,
            total_roots,
            f"Batch export progress: {total_roots}/{total_roots} root folders",
        )

    def _load_ace_text_file(self, path: str) -> None:
        try:
            self.ace_text_file_edit.setText(path)
            self.statusBar().showMessage("Parsing ACEText...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.current_text_container = parse_ace_text(path)
            self._refresh_ace_text_paratranz_language_combo(self.current_text_container)
            self.text_summary_edit.setPlainText(self._build_text_summary_text(self.current_text_container))
            self._populate_text_entry_list()
            self.statusBar().showMessage(
                f"Parsed {len(self.current_text_container.entries)} hash entries from {Path(path).name}."
            )
        except Exception as exc:
            self._clear_ace_text_view()
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _load_ace_table_file(self, path: str) -> None:
        try:
            self.ace_table_file_edit.setText(path)
            self.statusBar().showMessage("Parsing ACETable...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.current_table_container = parse_ace_table(path)
            self.table_summary_edit.setPlainText(self._build_table_summary_text(self.current_table_container))
            self._populate_table_column_list()
            self._populate_table_row_list()
            self.statusBar().showMessage(
                f"Parsed {self.current_table_container.row_count} rows and "
                f"{len(self.current_table_container.columns)} columns from {Path(path).name}."
            )
        except Exception as exc:
            self._clear_ace_table_view()
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _clear_ace_text_view(self) -> None:
        self.current_text_container = None
        self.filtered_text_entries = []
        self.text_entry_list.clear()
        self.text_summary_edit.clear()
        self.text_detail_edit.clear()
        self.text_values_table.setRowCount(0)
        self.ace_text_paratranz_language_combo.clear()
        self.ace_text_paratranz_language_combo.setEnabled(False)

    def _clear_ace_table_view(self) -> None:
        self.current_table_container = None
        self.filtered_table_rows = []
        self.table_column_list.clear()
        self.table_row_list.clear()
        self.table_summary_edit.clear()
        self.table_detail_edit.clear()
        self.table_values_table.setRowCount(0)

    def _populate_text_entry_list(self) -> None:
        self.text_entry_list.clear()
        self.text_detail_edit.clear()
        self.text_values_table.setRowCount(0)

        container = self.current_text_container
        if container is None:
            self.text_summary_edit.setPlainText("No ACEText file loaded.")
            return

        needle = self.text_entry_filter_edit.text().strip().lower()
        self.filtered_text_entries = []
        for entry in container.entries:
            if needle and not self._text_entry_matches_filter(entry, needle):
                continue
            self.filtered_text_entries.append(entry)

        for entry in self.filtered_text_entries:
            item = QListWidgetItem(self._format_text_entry_item_text(entry))
            item.setData(Qt.UserRole, entry)
            self.text_entry_list.addItem(item)

        if self.filtered_text_entries:
            self.text_entry_list.setCurrentRow(0)
        else:
            self.text_detail_edit.setPlainText("No entries match the current filter.")
            self.statusBar().showMessage(
                f"Parsed {len(container.entries)} entries, filter matched 0."
            )

    def _populate_table_column_list(self) -> None:
        self.table_column_list.clear()
        container = self.current_table_container
        if container is None:
            self.table_summary_edit.setPlainText("No ACETable file loaded.")
            return
        for column in container.columns:
            item = QListWidgetItem(
                f"{column.hash_name}  |  type={column.type_name}  |  rows={column.row_count}  "
                f"|  size={column.element_size}x{column.element_count}"
            )
            self.table_column_list.addItem(item)
        if self.table_column_list.count() > 0:
            self.table_column_list.setCurrentRow(0)

    def _populate_table_row_list(self) -> None:
        self.table_row_list.clear()
        self.table_detail_edit.clear()
        self.table_values_table.setRowCount(0)

        container = self.current_table_container
        if container is None:
            self.table_summary_edit.setPlainText("No ACETable file loaded.")
            return

        needle = self.table_row_filter_edit.text().strip().lower()
        self.filtered_table_rows = []
        for row in container.rows:
            if needle and not self._table_row_matches_filter(container, row, needle):
                continue
            self.filtered_table_rows.append(row)

        for row in self.filtered_table_rows:
            item = QListWidgetItem(self._format_table_row_item_text(container, row))
            item.setData(Qt.UserRole, row)
            self.table_row_list.addItem(item)

        if self.filtered_table_rows:
            self.table_row_list.setCurrentRow(0)
        else:
            self.table_detail_edit.setPlainText("No rows match the current filter.")
            self.statusBar().showMessage(
                f"Parsed {container.row_count} rows, filter matched 0."
            )

    def _text_entry_matches_filter(self, entry: ACETextEntry, needle: str) -> bool:
        if needle in entry.hash_label.lower():
            return True
        if needle in entry.text_label.lower():
            return True
        if needle in f"0x{entry.hash_value:08x}":
            return True
        return any(needle in value.lower() for value in entry.values.values())

    def _table_row_matches_filter(self, container: ACETableContainer, row: ACETableRow, needle: str) -> bool:
        if needle in str(row.index):
            return True
        for column in container.columns:
            if needle in column.hash_name.lower():
                value = row.values.get(column.hash_id)
                if value is not None:
                    return True
            value = row.values.get(column.hash_id)
            if value is not None and needle in str(value).lower():
                return True
        return False

    def _format_text_entry_item_text(self, entry: ACETextEntry) -> str:
        preview_language = ""
        preview_value = ""
        for language, value in entry.values.items():
            if value:
                preview_language = language
                preview_value = value
                break
        preview = self._truncate(preview_value.replace("\r", " ").replace("\n", " "), 48)
        preview_suffix = f"  |  {preview_language}: {preview}" if preview_language else ""
        text_label_suffix = f"  |  text='{entry.text_label}'" if entry.text_label else ""
        return (
            f"{entry.best_label}  |  hash=0x{entry.hash_value:08X}  |  idx={entry.text_index}"
            f"{text_label_suffix}{preview_suffix}"
        )

    def _format_table_row_item_text(self, container: ACETableContainer, row: ACETableRow) -> str:
        previews: list[str] = []
        for column in container.columns[:8]:
            value = row.values.get(column.hash_id)
            if value in (None, ""):
                continue
            text = str(value).replace("\r", " ").replace("\n", " ")
            previews.append(f"{column.hash_name}={self._truncate(text, 20)}")
            if len(previews) >= 3:
                break
        suffix = "  |  ".join(previews) if previews else "(empty)"
        return f"row {row.index}  |  {suffix}"

    def _on_text_entry_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if current is None:
            self.text_detail_edit.clear()
            self.text_values_table.setRowCount(0)
            return

        entry = current.data(Qt.UserRole)
        if not isinstance(entry, ACETextEntry):
            return

        self.text_detail_edit.setPlainText(self._build_text_entry_detail_text(entry))
        self._populate_text_values_table(entry)
        self.statusBar().showMessage(
            f"Selected 0x{entry.hash_value:08X} ({entry.best_label})."
        )

    def _on_table_row_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if current is None:
            self.table_detail_edit.clear()
            self.table_values_table.setRowCount(0)
            return

        row = current.data(Qt.UserRole)
        if not isinstance(row, ACETableRow):
            return

        container = self.current_table_container
        if container is None:
            return

        self.table_detail_edit.setPlainText(self._build_table_row_detail_text(container, row))
        self._populate_table_values_table(container, row)
        self.statusBar().showMessage(f"Selected ACETable row {row.index}.")

    def _populate_text_values_table(self, entry: ACETextEntry) -> None:
        rows = list(entry.values.items())
        self.text_values_table.setRowCount(len(rows))
        for row_index, (language, value) in enumerate(rows):
            self.text_values_table.setItem(row_index, 0, QTableWidgetItem(language))
            self.text_values_table.setItem(row_index, 1, QTableWidgetItem(value))
        self.text_values_table.resizeRowsToContents()

    def _populate_table_values_table(self, container: ACETableContainer, row: ACETableRow) -> None:
        self.table_values_table.setRowCount(len(container.columns))
        for row_index, column in enumerate(container.columns):
            value = row.values.get(column.hash_id)
            self.table_values_table.setItem(row_index, 0, QTableWidgetItem(column.hash_name))
            self.table_values_table.setItem(row_index, 1, QTableWidgetItem(column.type_name))
            self.table_values_table.setItem(row_index, 2, QTableWidgetItem("" if value is None else str(value)))
        self.table_values_table.resizeRowsToContents()

    def _build_text_summary_text(self, container: ACETextContainer) -> str:
        header = container.header
        language_lines = [
            f"{language.index}: {language.name or '(empty)'}"
            for language in container.languages
        ]
        unique_text_indexes = len({entry.text_index for entry in container.entries})
        orphan_texts = max(0, len(container.texts) - unique_text_indexes)
        lines = [
            f"Source: {container.source_file}",
            f"Magic: {header.magic!r}",
            f"Version: {header.version}",
            f"Data Version: {header.data_version}",
            f"Big Endian Flag: {header.is_big_endian}",
            f"Languages: {len(container.languages)}",
            f"Text Refs: {len(container.texts)}",
            f"Hash Entries: {len(container.entries)}",
            f"Referenced Text Indexes: {unique_text_indexes}",
            f"Orphan Text Refs: {orphan_texts}",
            "",
            "Language Table:",
        ]
        lines.extend(language_lines or ["(none)"])
        return "\n".join(lines)

    def _refresh_ace_text_paratranz_language_combo(self, container: ACETextContainer) -> None:
        self.ace_text_paratranz_language_combo.clear()
        preferred_index = -1
        for index, language in enumerate(container.languages):
            self.ace_text_paratranz_language_combo.addItem(language.name, language.name)
            if language.name == "JP":
                preferred_index = index
        if self.ace_text_paratranz_language_combo.count() > 0:
            if preferred_index < 0:
                preferred_index = 0
            self.ace_text_paratranz_language_combo.setCurrentIndex(preferred_index)
            self.ace_text_paratranz_language_combo.setEnabled(True)
        else:
            self.ace_text_paratranz_language_combo.setEnabled(False)

    def _build_text_entry_detail_text(self, entry: ACETextEntry) -> str:
        offset_lines = []
        for language_name, offset in zip(entry.values.keys(), entry.text_offsets):
            offset_lines.append(f"{language_name}: 0x{offset:08X}")

        lines = [
            f"Hash: 0x{entry.hash_value:08X}",
            f"Hash Label: {entry.hash_label or '(empty)'}",
            f"Hash Label Offset: 0x{entry.hash_label_offset:08X}",
            f"Text Index: {entry.text_index}",
            f"Text Label: {entry.text_label or '(empty)'}",
            f"Text Label Offset: 0x{entry.text_label_offset:08X}",
            "",
            "Text Offsets:",
        ]
        lines.extend(offset_lines or ["(none)"])
        return "\n".join(lines)

    def _build_table_summary_text(self, container: ACETableContainer) -> str:
        header = container.header
        type_counts: dict[str, int] = {}
        for column in container.columns:
            type_counts[column.type_name] = type_counts.get(column.type_name, 0) + 1
        lines = [
            f"Source: {container.source_file}",
            f"Magic: {header.magic!r}",
            f"Version: {header.version}",
            f"Reserved 1: 0x{header.reserved_1:08X}",
            f"Reserved 2: 0x{header.reserved_2:08X}",
            f"Columns: {len(container.columns)}",
            f"Rows: {container.row_count}",
            "",
            "Column Types:",
        ]
        for type_name, count in sorted(type_counts.items(), key=lambda item: item[0]):
            lines.append(f"{type_name}: {count}")
        return "\n".join(lines)

    def _build_table_row_detail_text(self, container: ACETableContainer, row: ACETableRow) -> str:
        non_empty = 0
        for column in container.columns:
            value = row.values.get(column.hash_id)
            if value not in (None, ""):
                non_empty += 1
        lines = [
            f"Row Index: {row.index}",
            f"Columns: {len(container.columns)}",
            f"Non-empty Values: {non_empty}",
            "",
            "Preview:",
        ]
        preview_lines = []
        for column in container.columns[:12]:
            value = row.values.get(column.hash_id)
            if value in (None, ""):
                continue
            preview_lines.append(f"{column.hash_name} ({column.type_name}) = {value}")
        lines.extend(preview_lines or ["(empty)"])
        return "\n".join(lines)

    def _show_error(self, message: str) -> None:
        self.statusBar().showMessage("Error")
        QMessageBox.critical(self, "ACI Text Tools", message)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()
