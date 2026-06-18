from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .atlas_generator import AtlasResult, build_ascii_charset, generate_atlas, save_result
from .nut_tools import load_nut_image
from .uifont_builder import (
    UIFontBuildConfig,
    UIFontBuildResult,
    _is_cjk_or_kana_codepoint,
    build_uifont_package,
    save_uifont_package,
)


def _is_cjk_or_cyrillic_codepoint(codepoint: int) -> bool:
    if _is_cjk_or_kana_codepoint(codepoint):
        return True
    return (
        0x0400 <= codepoint <= 0x04FF
        or 0x0500 <= codepoint <= 0x052F
        or 0x2DE0 <= codepoint <= 0x2DFF
        or 0xA640 <= codepoint <= 0xA69F
        or 0x1C80 <= codepoint <= 0x1C8F
    )
from .uifont_parser import UIFontBlock, UIFontContainer, UIFontGlyph, parse_uifont


def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class AtlasPreviewLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._empty_text = text
        self._source_pixmap: QPixmap | None = None
        self._highlight_rect: tuple[int, int, int, int] | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 640)
        self.setStyleSheet("background: #1f2228; color: #d7dde8;")

    def set_preview_pixmap(self, pixmap: QPixmap | None) -> None:
        self._source_pixmap = pixmap
        if pixmap is None:
            self.clear()
            self.setText(self._empty_text)
            self._highlight_rect = None
            return
        self._update_scaled_pixmap()

    def set_highlight_rect(self, rect: tuple[int, int, int, int] | None) -> None:
        self._highlight_rect = rect
        self._update_scaled_pixmap()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._source_pixmap is None:
            return

        scaled = self._source_pixmap.scaled(
            max(1, self.width()),
            max(1, self.height()),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        canvas = QPixmap(max(1, self.width()), max(1, self.height()))
        canvas.fill(QColor("#1f2228"))

        offset_x = (canvas.width() - scaled.width()) // 2
        offset_y = (canvas.height() - scaled.height()) // 2

        painter = QPainter(canvas)
        painter.drawPixmap(offset_x, offset_y, scaled)

        if self._highlight_rect is not None and self._source_pixmap.width() > 0 and self._source_pixmap.height() > 0:
            atlas_x, atlas_y, rect_w, rect_h = self._highlight_rect
            scale_x = scaled.width() / self._source_pixmap.width()
            scale_y = scaled.height() / self._source_pixmap.height()
            draw_x = offset_x + atlas_x * scale_x
            draw_y = offset_y + atlas_y * scale_y
            draw_w = max(1.0, rect_w * scale_x)
            draw_h = max(1.0, rect_h * scale_y)

            pen = QPen(QColor("#ff5a36"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(round(draw_x), round(draw_y), max(1, round(draw_w)), max(1, round(draw_h)))

        painter.end()

        super().setPixmap(canvas)
        self.setText("")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ACI Font Tools")
        self.resize(1320, 900)
        self.project_root = Path(__file__).resolve().parents[1]
        self.config_dir = self.project_root / "config"
        self.creation_config_path = self.config_dir / "uifont_creation_config.json"

        self.last_result: AtlasResult | None = None
        self.last_uifont_build_result: UIFontBuildResult | None = None
        self.current_preview: QPixmap | None = None
        self.template_container: UIFontContainer | None = None
        self.template_font_configs: dict[int, UIFontBuildConfig] = {}
        self.template_selected_block_index: int | None = None
        self.template_form_sync_lock = False
        self.creation_presets: list[dict[str, object]] = []
        self.creation_current_preset_index: int | None = None
        self.creation_preset_sync_lock = False
        self.uifont_blocks: list[UIFontBlock] = []
        self.uifont_fonts_by_name: dict[str, list[UIFontBlock]] = {}
        self.uifont_atlas_cache: dict[str, QPixmap] = {}
        self.uifont_selected_glyph: UIFontGlyph | None = None
        self.uifont_preview_mode = "atlas"

        self.font_path_edit = QLineEdit()
        self.template_uifont_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        self.base_name_edit = QLineEdit("Default")
        self.output_dir_edit.setText(str(self.project_root / "output"))
        self.creation_preset_list = QListWidget()
        self.template_font_list = QListWidget()
        self.pixel_size_spin = QSpinBox()
        self.pixel_size_spin.setRange(1, 512)
        self.pixel_size_spin.setValue(32)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 64)
        self.padding_spin.setValue(1)

        self.atlas_width_spin = QSpinBox()
        self.atlas_width_spin.setRange(32, 16384)
        self.atlas_width_spin.setValue(1024)

        self.atlas_height_spin = QSpinBox()
        self.atlas_height_spin.setRange(32, 16384)
        self.atlas_height_spin.setValue(1024)

        self.standalone_charset_codepoints = [ord(char) for char in build_ascii_charset()]
        self.codepoint_input_edit = QLineEdit()
        self.codepoint_input_edit.setPlaceholderText("U+4E00 U+4E01 or 4E00,4E01")
        self.charset_codepoint_list = QListWidget()
        self.charset_codepoint_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.summary_edit = QTextEdit()
        self.summary_edit.setReadOnly(True)
        self.generate_progress_bar = QProgressBar()
        self.generate_progress_bar.setRange(0, 1)
        self.generate_progress_bar.setValue(0)
        self.generate_progress_bar.setTextVisible(True)
        self.generate_progress_bar.hide()
        self.generate_progress_label = QLabel("Ready")

        self.preview_label = AtlasPreviewLabel("No atlas generated yet.")
        self.uifont_file_edit = QLineEdit()
        self.uifont_font_list = QListWidget()
        self.uifont_glyph_list = QListWidget()
        self.uifont_summary_edit = QTextEdit()
        self.uifont_summary_edit.setReadOnly(True)
        self.uifont_atlas_path_edit = QLineEdit()
        self.uifont_atlas_path_edit.setReadOnly(True)
        self.uifont_full_view_button = QPushButton("整体视图")
        self.uifont_full_view_button.setCheckable(True)
        self.uifont_crop_view_button = QPushButton("切字视图")
        self.uifont_crop_view_button.setCheckable(True)
        self.uifont_atlas_preview = AtlasPreviewLabel("No atlas selected yet.")

        self._ensure_config_dir()
        self._build_ui()
        self._load_creation_page_config()
        self.statusBar().showMessage("Ready")

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_font_creation_page(), "UIFont Create")
        tabs.addTab(self._build_uifont_viewer_page(), "UIFont View")

        root_layout.addWidget(tabs)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar(self))

    def _build_font_creation_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_controls_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.setSizes([420, 880])

        page_layout.addWidget(splitter)
        return page

    def _build_uifont_viewer_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        source_group = QGroupBox("UIFONT Source")
        source_layout = QGridLayout(source_group)
        browse_button = QPushButton("Select File")
        browse_button.clicked.connect(self._browse_uifont_file)
        source_layout.addWidget(QLabel("UIFONT"), 0, 0)
        source_layout.addWidget(self.uifont_file_edit, 0, 1)
        source_layout.addWidget(browse_button, 0, 2)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.addWidget(self._build_uifont_left_panel())
        content_splitter.addWidget(self._build_uifont_atlas_panel())
        content_splitter.setSizes([420, 900])

        layout.addWidget(source_group)
        layout.addWidget(content_splitter, stretch=1)
        return page

    def _build_uifont_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        lists_splitter = QSplitter(Qt.Vertical)
        lists_splitter.addWidget(self._build_uifont_font_panel())
        lists_splitter.addWidget(self._build_uifont_glyph_panel())
        lists_splitter.addWidget(self._build_uifont_summary_panel())
        lists_splitter.setSizes([220, 420, 220])

        layout.addWidget(lists_splitter)
        return panel

    def _build_uifont_font_panel(self) -> QWidget:
        panel = QGroupBox("Font Names")
        layout = QVBoxLayout(panel)
        self.uifont_font_list.currentItemChanged.connect(self._on_uifont_font_changed)
        layout.addWidget(self.uifont_font_list)
        return panel

    def _build_uifont_glyph_panel(self) -> QWidget:
        panel = QGroupBox("Glyphs")
        layout = QVBoxLayout(panel)
        self.uifont_glyph_list.currentItemChanged.connect(self._on_uifont_glyph_changed)
        layout.addWidget(self.uifont_glyph_list)
        return panel

    def _build_uifont_summary_panel(self) -> QWidget:
        panel = QGroupBox("UIFONT Summary")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.uifont_summary_edit)
        return panel

    def _build_uifont_atlas_panel(self) -> QWidget:
        panel = QGroupBox("Atlas Preview")
        layout = QVBoxLayout(panel)
        button_row = QHBoxLayout()
        self.uifont_full_view_button.clicked.connect(lambda: self._set_uifont_preview_mode("atlas"))
        self.uifont_crop_view_button.clicked.connect(lambda: self._set_uifont_preview_mode("glyph"))
        button_row.addWidget(self.uifont_full_view_button)
        button_row.addWidget(self.uifont_crop_view_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addWidget(self.uifont_atlas_path_edit)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setBackgroundRole(self.uifont_atlas_preview.backgroundRole())
        scroll.setWidget(self.uifont_atlas_preview)
        layout.addWidget(scroll, stretch=1)
        self._sync_uifont_preview_mode_buttons()
        return panel

    def _build_controls_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout(preset_group)
        preset_button_row = QHBoxLayout()
        new_preset_button = QPushButton("New Preset")
        new_preset_button.clicked.connect(self._create_creation_preset)
        delete_preset_button = QPushButton("Delete Preset")
        delete_preset_button.clicked.connect(self._delete_creation_preset)
        preset_button_row.addWidget(new_preset_button)
        preset_button_row.addWidget(delete_preset_button)
        preset_layout.addLayout(preset_button_row)
        self.creation_preset_list.currentItemChanged.connect(self._on_creation_preset_changed)
        preset_layout.addWidget(self.creation_preset_list)

        template_group = QGroupBox("Template UIFONT")
        template_layout = QGridLayout(template_group)
        template_browse_button = QPushButton("Browse UIFONT")
        template_browse_button.clicked.connect(self._browse_template_uifont)
        template_layout.addWidget(QLabel("Template"), 0, 0)
        template_layout.addWidget(self.template_uifont_edit, 0, 1)
        template_layout.addWidget(template_browse_button, 0, 2)

        output_browse_button = QPushButton("Browse Output")
        output_browse_button.clicked.connect(self._browse_output_dir)
        template_layout.addWidget(QLabel("Output Dir"), 1, 0)
        template_layout.addWidget(self.output_dir_edit, 1, 1)
        template_layout.addWidget(output_browse_button, 1, 2)

        self.base_name_edit.textChanged.connect(self._on_creation_preset_name_changed)
        template_layout.addWidget(QLabel("Preset Name"), 2, 0)
        template_layout.addWidget(self.base_name_edit, 2, 1, 1, 2)

        template_font_group = QGroupBox("Template Fonts")
        template_font_layout = QVBoxLayout(template_font_group)
        self.template_font_list.currentItemChanged.connect(self._on_template_font_changed)
        template_font_layout.addWidget(self.template_font_list)

        source_group = QGroupBox("Selected Font")
        source_layout = QGridLayout(source_group)
        font_browse_button = QPushButton("Browse Font")
        font_browse_button.clicked.connect(self._browse_font)
        apply_all_button = QPushButton("Apply To All Fonts")
        apply_all_button.clicked.connect(self._apply_selected_font_to_all_template_fonts)
        source_layout.addWidget(QLabel("Font File"), 0, 0)
        source_layout.addWidget(self.font_path_edit, 0, 1)
        source_layout.addWidget(font_browse_button, 0, 2)
        source_layout.addWidget(apply_all_button, 1, 1, 1, 2)

        settings_group = QGroupBox("Atlas Settings")
        settings_layout = QFormLayout(settings_group)
        settings_layout.addRow("Pixel Size", self.pixel_size_spin)
        settings_layout.addRow("Padding", self.padding_spin)
        settings_layout.addRow("Max Width", self.atlas_width_spin)
        settings_layout.addRow("Max Height", self.atlas_height_spin)

        charset_group = QGroupBox("Codepoint Editor")
        charset_layout = QVBoxLayout(charset_group)
        codepoint_input_row = QHBoxLayout()
        add_codepoint_button = QPushButton("Add Codepoints")
        add_codepoint_button.clicked.connect(self._add_codepoints_from_input)
        replace_codepoint_button = QPushButton("Replace Selected")
        replace_codepoint_button.clicked.connect(self._replace_selected_codepoint_from_input)
        remove_button = QPushButton("Remove Input Codepoints")
        remove_button.clicked.connect(self._remove_selected_codepoints)
        remove_all_cjk_codepoints_button = QPushButton("Remove All CJK+Cyrillic Codepoints")
        remove_all_cjk_codepoints_button.clicked.connect(self._remove_all_cjk_codepoints)
        codepoint_input_row.addWidget(QLabel("Codepoints"))
        codepoint_input_row.addWidget(self.codepoint_input_edit, stretch=1)
        codepoint_input_row.addWidget(add_codepoint_button)
        codepoint_input_row.addWidget(replace_codepoint_button)
        codepoint_input_row.addWidget(remove_button)
        codepoint_input_row.addWidget(remove_all_cjk_codepoints_button)
        charset_layout.addLayout(codepoint_input_row)

        charset_button_row = QHBoxLayout()
        import_button = QPushButton("Import UTF-16BE Charset")
        import_button.clicked.connect(self._import_charset_file)
        import_replace_cjk_button = QPushButton("Import UTF-16BE Charset (Replace CJK+Cyrillic)")
        import_replace_cjk_button.clicked.connect(self._import_charset_file_replace_cjk)
        ascii_button = QPushButton("Load ASCII 32-126")
        ascii_button.clicked.connect(self._load_ascii_charset)
        reset_button = QPushButton("Reset Current")
        reset_button.clicked.connect(self._reset_current_charset)
        charset_button_row.addWidget(import_button)
        charset_button_row.addWidget(import_replace_cjk_button)
        charset_button_row.addWidget(ascii_button)
        charset_button_row.addWidget(reset_button)
        charset_layout.addLayout(charset_button_row)
        charset_layout.addWidget(self.charset_codepoint_list)

        actions_row = QHBoxLayout()
        generate_button = QPushButton("Generate Preview")
        generate_button.clicked.connect(self._generate)
        save_button = QPushButton("Save Output")
        save_button.clicked.connect(self._save_result)
        actions_row.addWidget(generate_button)
        actions_row.addWidget(save_button)

        progress_group = QGroupBox("Generation Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.addWidget(self.generate_progress_label)
        progress_layout.addWidget(self.generate_progress_bar)

        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(self.summary_edit)

        layout.addWidget(preset_group)
        layout.addWidget(template_group)
        layout.addWidget(template_font_group, stretch=1)
        layout.addWidget(source_group)
        layout.addWidget(settings_group)
        layout.addWidget(charset_group, stretch=1)
        layout.addLayout(actions_row)
        layout.addWidget(progress_group)
        layout.addWidget(summary_group, stretch=1)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setBackgroundRole(self.preview_label.backgroundRole())
        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)
        self._refresh_charset_codepoint_list(self.standalone_charset_codepoints)
        return panel

    def _ensure_config_dir(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _default_creation_preset(self, preset_name: str = "Default") -> dict[str, object]:
        return {
            "preset_name": preset_name,
            "template_uifont_path": "",
            "output_dir": str(self.project_root / "output"),
            "selected_font_path": "",
            "max_width": self.atlas_width_spin.value(),
            "max_height": self.atlas_height_spin.value(),
            "pixel_size": self.pixel_size_spin.value(),
            "padding": self.padding_spin.value(),
            "selected_block_index": None,
            "standalone_charset_codepoints": [ord(char) for char in build_ascii_charset()],
            "template_font_configs": [],
        }

    def _normalize_creation_preset_name(self, value: object, fallback: str) -> str:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
        return fallback

    def _serialize_template_font_configs(self) -> list[dict[str, object]]:
        serialized: list[dict[str, object]] = []
        for block_index in sorted(self.template_font_configs):
            config = self.template_font_configs[block_index]
            serialized.append(
                {
                    "block_index": config.block_index,
                    "font_name": config.font_name,
                    "font_path": config.font_path,
                    "pixel_size": config.pixel_size,
                    "charset_codepoints": list(config.charset_codepoints),
                }
            )
        return serialized

    def _deserialize_template_font_configs(self, payload: object) -> dict[int, UIFontBuildConfig]:
        restored: dict[int, UIFontBuildConfig] = {}
        if not isinstance(payload, list):
            return restored

        for entry in payload:
            if not isinstance(entry, dict):
                continue
            block_index = entry.get("block_index")
            font_name = entry.get("font_name")
            font_path = entry.get("font_path")
            pixel_size = entry.get("pixel_size")
            charset_codepoints = entry.get("charset_codepoints")
            if not isinstance(block_index, int):
                continue
            if not isinstance(font_name, str):
                font_name = ""
            if not isinstance(font_path, str):
                font_path = ""
            if not isinstance(pixel_size, int):
                pixel_size = self.pixel_size_spin.value()
            if not isinstance(charset_codepoints, list):
                charset_codepoints = []
            normalized_codepoints = [value for value in charset_codepoints if isinstance(value, int)]
            restored[block_index] = UIFontBuildConfig(
                block_index=block_index,
                font_name=font_name,
                font_path=font_path,
                pixel_size=max(1, pixel_size),
                charset_codepoints=normalized_codepoints,
            )
        return restored

    def _capture_current_creation_preset(self) -> dict[str, object]:
        self._save_current_template_font_config()
        return {
            "preset_name": self.base_name_edit.text().strip() or "Default",
            "template_uifont_path": self.template_uifont_edit.text().strip(),
            "output_dir": self.output_dir_edit.text().strip(),
            "selected_font_path": self.font_path_edit.text().strip(),
            "max_width": self.atlas_width_spin.value(),
            "max_height": self.atlas_height_spin.value(),
            "pixel_size": self.pixel_size_spin.value(),
            "padding": self.padding_spin.value(),
            "selected_block_index": self.template_selected_block_index,
            "standalone_charset_codepoints": list(self.standalone_charset_codepoints),
            "template_font_configs": self._serialize_template_font_configs(),
        }

    def _clear_template_uifont_state(self) -> None:
        self.template_container = None
        self.template_font_configs = {}
        self.template_selected_block_index = None
        self.template_font_list.clear()
        self.last_uifont_build_result = None
        self.last_result = None
        self.current_preview = None
        self.preview_label.set_preview_pixmap(None)
        self._refresh_charset_codepoint_list(self.standalone_charset_codepoints)
        self.summary_edit.setPlainText("Load a template .uifont file to start template-driven UIFont creation.")

    def _store_current_creation_preset(self) -> None:
        if self.creation_preset_sync_lock:
            return
        if self.creation_current_preset_index is None:
            return
        if not (0 <= self.creation_current_preset_index < len(self.creation_presets)):
            return
        self.creation_presets[self.creation_current_preset_index] = self._capture_current_creation_preset()

    def _refresh_creation_preset_list(self) -> None:
        current_index = self.creation_current_preset_index
        self.creation_preset_sync_lock = True
        self.creation_preset_list.clear()
        for index, preset in enumerate(self.creation_presets):
            preset_name = self._normalize_creation_preset_name(preset.get("preset_name"), f"Preset {index + 1}")
            item = QListWidgetItem(preset_name)
            item.setData(Qt.UserRole, index)
            self.creation_preset_list.addItem(item)
        self.creation_preset_sync_lock = False
        if not self.creation_presets:
            self.creation_current_preset_index = None
            return
        if current_index is None or not (0 <= current_index < len(self.creation_presets)):
            current_index = 0
        self.creation_current_preset_index = current_index
        self.creation_preset_sync_lock = True
        self.creation_preset_list.setCurrentRow(current_index)
        self.creation_preset_sync_lock = False

    def _apply_creation_preset(self, preset_index: int) -> None:
        if not (0 <= preset_index < len(self.creation_presets)):
            return

        preset = self.creation_presets[preset_index]
        template_path = preset.get("template_uifont_path")
        output_dir = preset.get("output_dir")
        selected_font_path = preset.get("selected_font_path")
        max_width = preset.get("max_width")
        max_height = preset.get("max_height")
        pixel_size = preset.get("pixel_size")
        padding = preset.get("padding")
        selected_block_index = preset.get("selected_block_index")
        standalone_charset_codepoints = preset.get("standalone_charset_codepoints")

        self.creation_preset_sync_lock = True
        self.base_name_edit.setText(self._normalize_creation_preset_name(preset.get("preset_name"), "Default"))
        self.template_uifont_edit.setText(template_path if isinstance(template_path, str) else "")
        self.output_dir_edit.setText(
            output_dir if isinstance(output_dir, str) and output_dir.strip() else str(self.project_root / "output")
        )
        self.font_path_edit.setText(selected_font_path if isinstance(selected_font_path, str) else "")
        if isinstance(max_width, int):
            self.atlas_width_spin.setValue(
                max(self.atlas_width_spin.minimum(), min(max_width, self.atlas_width_spin.maximum()))
            )
        if isinstance(max_height, int):
            self.atlas_height_spin.setValue(
                max(self.atlas_height_spin.minimum(), min(max_height, self.atlas_height_spin.maximum()))
            )
        if isinstance(pixel_size, int):
            self.pixel_size_spin.setValue(
                max(self.pixel_size_spin.minimum(), min(pixel_size, self.pixel_size_spin.maximum()))
            )
        if isinstance(padding, int):
            self.padding_spin.setValue(
                max(self.padding_spin.minimum(), min(padding, self.padding_spin.maximum()))
            )
        if isinstance(standalone_charset_codepoints, list):
            self.standalone_charset_codepoints = [value for value in standalone_charset_codepoints if isinstance(value, int)]
        self.creation_preset_sync_lock = False

        template_path_str = template_path if isinstance(template_path, str) else ""
        saved_configs = self._deserialize_template_font_configs(preset.get("template_font_configs"))
        if template_path_str and Path(template_path_str).is_file():
            preferred_block_index = selected_block_index if isinstance(selected_block_index, int) else None
            self._load_template_uifont(
                template_path_str,
                saved_configs=saved_configs,
                preferred_block_index=preferred_block_index,
            )
        else:
            self._clear_template_uifont_state()

        self.creation_current_preset_index = preset_index

    def _create_creation_preset(self) -> None:
        base_index = self.creation_current_preset_index
        if base_index is not None:
            self._store_current_creation_preset()

        default_name = f"Preset {len(self.creation_presets) + 1}"
        preset_name, accepted = QInputDialog.getText(self, "New Preset", "Preset name:", text=default_name)
        if not accepted:
            return

        normalized_name = self._normalize_creation_preset_name(preset_name, default_name)
        new_preset = (
            dict(self._capture_current_creation_preset())
            if base_index is not None and 0 <= base_index < len(self.creation_presets)
            else self._default_creation_preset(normalized_name)
        )
        new_preset["preset_name"] = normalized_name
        self.creation_presets.append(new_preset)
        self.creation_current_preset_index = len(self.creation_presets) - 1
        self._refresh_creation_preset_list()
        self._apply_creation_preset(self.creation_current_preset_index)
        self._save_creation_page_config()
        self.statusBar().showMessage(f"Created preset '{normalized_name}'.")

    def _delete_creation_preset(self) -> None:
        current_index = self.creation_current_preset_index
        if current_index is None or not (0 <= current_index < len(self.creation_presets)):
            self._show_error("Select a preset to delete.")
            return
        if len(self.creation_presets) <= 1:
            self._show_error("Keep at least one preset.")
            return

        preset_name = self._normalize_creation_preset_name(
            self.creation_presets[current_index].get("preset_name"),
            f"Preset {current_index + 1}",
        )
        del self.creation_presets[current_index]
        self.creation_current_preset_index = min(current_index, len(self.creation_presets) - 1)
        self._refresh_creation_preset_list()
        self._apply_creation_preset(self.creation_current_preset_index)
        self._save_creation_page_config()
        self.statusBar().showMessage(f"Deleted preset '{preset_name}'.")

    def _on_creation_preset_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        if self.creation_preset_sync_lock:
            return
        self._store_current_creation_preset()
        if current is None:
            self.creation_current_preset_index = None
            return

        preset_index = current.data(Qt.UserRole)
        if not isinstance(preset_index, int):
            return
        self._apply_creation_preset(preset_index)

    def _on_creation_preset_name_changed(self, text: str) -> None:
        if self.creation_preset_sync_lock:
            return
        current_index = self.creation_current_preset_index
        if current_index is None or not (0 <= current_index < len(self.creation_presets)):
            return

        normalized_name = self._normalize_creation_preset_name(text, f"Preset {current_index + 1}")
        self.creation_presets[current_index]["preset_name"] = normalized_name
        item = self.creation_preset_list.item(current_index)
        if item is not None and item.text() != normalized_name:
            item.setText(normalized_name)

    def _load_creation_page_config(self) -> None:
        path = self.creation_config_path
        if not path.is_file():
            self.creation_presets = [self._default_creation_preset()]
            self.creation_current_preset_index = 0
            self._refresh_creation_preset_list()
            return

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self.statusBar().showMessage(f"Failed to load creation config: {path.name}")
            self.creation_presets = [self._default_creation_preset()]
            self.creation_current_preset_index = 0
            self._refresh_creation_preset_list()
            return

        presets_payload = payload.get("presets") if isinstance(payload, dict) else None
        selected_preset = payload.get("selected_preset") if isinstance(payload, dict) else None

        if isinstance(presets_payload, list) and presets_payload:
            self.creation_presets = []
            for index, entry in enumerate(presets_payload):
                if not isinstance(entry, dict):
                    continue
                preset = self._default_creation_preset(f"Preset {index + 1}")
                preset.update(entry)
                preset["preset_name"] = self._normalize_creation_preset_name(
                    preset.get("preset_name"),
                    f"Preset {index + 1}",
                )
                self.creation_presets.append(preset)
            if not self.creation_presets:
                self.creation_presets = [self._default_creation_preset()]
            if not isinstance(selected_preset, int):
                selected_preset = 0
        else:
            preset_name = self._normalize_creation_preset_name(payload.get("export_folder"), "Default")
            migrated = self._default_creation_preset(preset_name)
            migrated["template_uifont_path"] = payload.get("template_uifont_path", "")
            migrated["output_dir"] = payload.get("output_dir", str(self.project_root / "output"))
            migrated["selected_font_path"] = payload.get("selected_font_path", "")
            migrated["max_width"] = payload.get("max_width", self.atlas_width_spin.value())
            migrated["max_height"] = payload.get("max_height", self.atlas_height_spin.value())
            self.creation_presets = [migrated]
            selected_preset = 0

        self.creation_current_preset_index = (
            selected_preset if isinstance(selected_preset, int) and 0 <= selected_preset < len(self.creation_presets) else 0
        )
        self._refresh_creation_preset_list()
        if self.creation_current_preset_index is not None:
            self._apply_creation_preset(self.creation_current_preset_index)

    def _save_creation_page_config(self) -> None:
        self._ensure_config_dir()
        if not self.creation_presets:
            self.creation_presets = [self._default_creation_preset()]
            self.creation_current_preset_index = 0
        self._store_current_creation_preset()
        payload = {
            "version": 2,
            "selected_preset": self.creation_current_preset_index if self.creation_current_preset_index is not None else 0,
            "presets": self.creation_presets,
        }
        self.creation_config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _browse_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Font",
            str(self.project_root),
            "Font Files (*.ttf *.otf *.ttc);;All Files (*.*)",
        )
        if path:
            self.font_path_edit.setText(path)
            self._save_current_template_font_config()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir_edit.text())
        if path:
            self.output_dir_edit.setText(path)

    def _browse_template_uifont(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template UIFONT",
            str(self.project_root),
            "UIFONT Files (*.uifont);;All Files (*.*)",
        )
        if not path:
            return

        self.template_uifont_edit.setText(path)
        self._load_template_uifont(path)

    def _browse_uifont_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select UIFONT",
            self.uifont_file_edit.text() or str(self.project_root),
            "UIFONT Files (*.uifont);;All Files (*.*)",
        )
        if not path:
            return

        self.uifont_file_edit.setText(path)
        self._load_uifont_file(path)

    def _resolve_export_root(self) -> Path:
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            raise ValueError("Please select an output directory first.")
        return Path(output_dir)

    def _reset_generate_progress(self) -> None:
        self.generate_progress_bar.setRange(0, 1)
        self.generate_progress_bar.setValue(0)
        self.generate_progress_bar.hide()
        self.generate_progress_label.setText("Ready")

    def _update_generate_progress(self, current: int, total: int, message: str) -> None:
        safe_total = max(1, total)
        safe_current = max(0, min(current, safe_total))
        self.generate_progress_bar.show()
        self.generate_progress_bar.setRange(0, safe_total)
        self.generate_progress_bar.setValue(safe_current)
        self.generate_progress_label.setText(message)
        self.statusBar().showMessage(message)
        QApplication.processEvents()

    def _load_ascii_charset(self) -> None:
        self._set_current_charset_codepoints([ord(char) for char in build_ascii_charset()])

    def _format_codepoint_item_text(self, codepoint: int) -> str:
        char = chr(codepoint)
        if char == " ":
            display = "SPACE"
        elif char == "\t":
            display = "\\t"
        elif char == "\n":
            display = "\\n"
        elif char == "\r":
            display = "\\r"
        elif char.isprintable() and not char.isspace():
            display = char
        else:
            display = "."
        return f"U+{codepoint:04X}  {display}"

    def _refresh_charset_codepoint_list(self, codepoints: list[int]) -> None:
        self.charset_codepoint_list.clear()
        for codepoint in codepoints:
            item = QListWidgetItem(self._format_codepoint_item_text(codepoint))
            item.setData(Qt.UserRole, codepoint)
            self.charset_codepoint_list.addItem(item)

    def _normalize_codepoints(self, codepoints: list[int]) -> list[int]:
        seen: set[int] = set()
        normalized: list[int] = []
        for codepoint in codepoints:
            if codepoint in seen:
                continue
            seen.add(codepoint)
            normalized.append(codepoint)
        return normalized

    def _parse_codepoint_input(self, text: str) -> list[int]:
        tokens = [token for token in re.split(r"[\s,;]+", text.strip()) if token]
        if not tokens:
            raise ValueError("Enter one or more codepoints first.")

        codepoints: list[int] = []
        for token in tokens:
            normalized = token.upper()
            if normalized.startswith("U+"):
                normalized = normalized[2:]
            elif normalized.startswith("0X"):
                normalized = normalized[2:]

            if not normalized or any(char not in "0123456789ABCDEF" for char in normalized):
                raise ValueError(
                    f"Invalid codepoint token '{token}'. Use formats like U+4E00, 0x4E00, or 4E00."
                )

            codepoint = int(normalized, 16)
            if codepoint < 0 or codepoint > 0xFFFF:
                raise ValueError(
                    f"UIFONT stores codepoints as a single UTF-16BE code unit; {token} is out of range."
                )
            codepoints.append(codepoint)

        return codepoints

    def _current_charset_codepoints(self) -> list[int]:
        if self.template_container is not None and self.template_selected_block_index is not None:
            config = self.template_font_configs.get(self.template_selected_block_index)
            if config is not None:
                return list(config.charset_codepoints)
        return list(self.standalone_charset_codepoints)

    def _current_template_block(self) -> UIFontBlock | None:
        if self.template_container is None or self.template_selected_block_index is None:
            return None
        return next(
            (value for value in self.template_container.blocks if value.block_index == self.template_selected_block_index),
            None,
        )

    def _set_current_charset_codepoints(self, codepoints: list[int]) -> None:
        normalized = self._normalize_codepoints(codepoints)
        if self.template_container is not None and self.template_selected_block_index is not None:
            block_index = self.template_selected_block_index
            config = self.template_font_configs.get(block_index)
            if config is None:
                block = next(
                    (value for value in self.template_container.blocks if value.block_index == block_index),
                    None,
                )
                if block is None:
                    return
                config = UIFontBuildConfig(
                    block_index=block.block_index,
                    font_name=block.name,
                    font_path=self.font_path_edit.text().strip(),
                    pixel_size=self.pixel_size_spin.value(),
                    charset_codepoints=normalized,
                )
            else:
                config.charset_codepoints = normalized
            self.template_font_configs[block_index] = config
        else:
            self.standalone_charset_codepoints = normalized

        self._refresh_charset_codepoint_list(normalized)
        self._refresh_template_selection_summary()

    def _add_codepoints_from_input(self) -> None:
        existing = self._current_charset_codepoints()
        try:
            additions = self._parse_codepoint_input(self.codepoint_input_edit.text())
            self._set_current_charset_codepoints(existing + additions)
            self.codepoint_input_edit.clear()
            self.statusBar().showMessage(f"Added {len(additions)} codepoint(s).")
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")

    def _replace_selected_codepoint_from_input(self) -> None:
        selected_items = self.charset_codepoint_list.selectedItems()
        if len(selected_items) != 1:
            self._show_error("Select exactly one codepoint to replace.")
            return

        try:
            replacements = self._parse_codepoint_input(self.codepoint_input_edit.text())
            if len(replacements) != 1:
                raise ValueError("Replace Selected expects exactly one codepoint input.")

            row = self.charset_codepoint_list.row(selected_items[0])
            updated = self._current_charset_codepoints()
            updated[row] = replacements[0]
            self._set_current_charset_codepoints(updated)
            if row < self.charset_codepoint_list.count():
                self.charset_codepoint_list.setCurrentRow(row)
            self.codepoint_input_edit.clear()
            self.statusBar().showMessage("Replaced selected codepoint.")
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")

    def _import_charset_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import UTF-16BE Charset",
            str(self.project_root),
            "Text Files (*.txt *.utf16 *.utf-16be);;All Files (*.*)",
        )
        if not path:
            return

        self._import_charset_from_path(path)

    def _import_charset_file_replace_cjk(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import UTF-16BE Charset (Replace CJK+Cyrillic)",
            str(self.project_root),
            "Text Files (*.txt *.utf16 *.utf-16be);;All Files (*.*)",
        )
        if not path:
            return

        self._import_charset_from_path(path, replace_cjk_only=True)

    def _remove_all_cjk_codepoints(self) -> None:
        updated = [
            codepoint
            for index, codepoint in enumerate(self._current_charset_codepoints())
            if not _is_cjk_or_cyrillic_codepoint(codepoint)
        ]
        
        self._set_current_charset_codepoints(updated)

    def _read_charset_text(self, source_path: Path) -> str:
        text = source_path.read_text(encoding="utf-16-be")
        if text.startswith("\ufeff"):
            text = text[1:]
        return text

    def _text_to_codepoints(self, text: str, source_name: str) -> tuple[list[int], int]:
        codepoints: list[int] = []
        skipped_private_use = 0
        for index, char in enumerate(text):
            codepoint = ord(char)
            if codepoint > 0xFFFF:
                raise ValueError(
                    f"UIFONT stores codepoints as a single UTF-16BE code unit; "
                    f"{source_name} contains unsupported U+{codepoint:04X} at character {index + 1}."
                )
            if 0xE000 <= codepoint <= 0xF8FF:
                skipped_private_use += 1
                continue
            codepoints.append(codepoint)
        return codepoints, skipped_private_use

    def _build_cjk_replaced_charset(self, current: list[int], imported: list[int], source_name: str) -> tuple[list[int], int]:
        normalized_current = self._normalize_codepoints(current)
        normalized_imported = self._normalize_codepoints(imported)
        imported_set = set(normalized_imported)
        current_set = set(normalized_current)
        missing_imported = [codepoint for codepoint in normalized_imported if codepoint not in current_set]
        replaceable_indices = [
            index
            for index, codepoint in enumerate(normalized_current)
            if _is_cjk_or_cyrillic_codepoint(codepoint) and codepoint not in imported_set
        ]

        if len(missing_imported) > len(replaceable_indices):
            raise ValueError(
                f"{source_name} needs {len(missing_imported)} replacement slot(s), "
                f"but only {len(replaceable_indices)} replaceable CJK+Cyrillic codepoint(s) are available in the current charset."
            )

        updated = list(normalized_current)
        for index, replacement in zip(replaceable_indices, missing_imported):
            updated[index] = replacement
        return updated, len(missing_imported)

    def _import_charset_from_path(self, path: str, replace_cjk_only: bool = False) -> None:
        source_path = Path(path)

        previous = self._current_charset_codepoints()
        try:
            text = self._read_charset_text(source_path)
            imported, skipped_private_use = self._text_to_codepoints(text, source_path.name)
            if replace_cjk_only:
                updated, replaced_count = self._build_cjk_replaced_charset(previous, imported, source_path.name)
                self._set_current_charset_codepoints(updated)
                message = (
                    f"Imported {source_path.name}: replaced {replaced_count} CJK+Cyrillic codepoint(s) without growing the charset."
                )
                if skipped_private_use:
                    message += f" Skipped {skipped_private_use} private-use codepoint(s)."
                self.statusBar().showMessage(message)
            elif self.template_container is not None and self.template_selected_block_index is not None:
                updated = previous + imported
                self._set_current_charset_codepoints(updated)
                normalized_previous = self._normalize_codepoints(previous)
                normalized_current = self._current_charset_codepoints()
                appended = [codepoint for codepoint in normalized_current if codepoint not in normalized_previous]
                block = self._current_template_block()
                template_existing = {glyph.codepoint for glyph in block.glyphs} if block is not None else set()
                appended_beyond_template = [
                    codepoint for codepoint in appended if codepoint not in template_existing
                ]
                message = (
                    f"Imported {source_path.name}: appended {len(appended)} codepoint(s) to the current template block."
                )
                if appended_beyond_template:
                    preview = ", ".join(f"U+{codepoint:04X}" for codepoint in appended_beyond_template[:8])
                    if len(appended_beyond_template) > 8:
                        preview += ", ..."
                    message += (
                        f" New beyond template: {len(appended_beyond_template)} ({preview})."
                    )
                if skipped_private_use:
                    message += f" Skipped {skipped_private_use} private-use codepoint(s)."
                self.statusBar().showMessage(message)
            else:
                self._set_current_charset_codepoints(imported)
                message = f"Imported {len(self._current_charset_codepoints())} codepoints from {source_path.name}"
                if skipped_private_use:
                    message += f" Skipped {skipped_private_use} private-use codepoint(s)."
                self.statusBar().showMessage(message)
        except Exception as exc:
            self._refresh_charset_codepoint_list(previous)
            if self.template_container is not None and self.template_selected_block_index is not None:
                config = self.template_font_configs.get(self.template_selected_block_index)
                if config is not None:
                    config.charset_codepoints = previous
                    self.template_font_configs[self.template_selected_block_index] = config
            else:
                self.standalone_charset_codepoints = previous
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")

    def _remove_selected_codepoints(self) -> None:
        try:
            removals = set(self._parse_codepoint_input(self.codepoint_input_edit.text()))
            current = self._current_charset_codepoints()
            updated = [codepoint for codepoint in current if codepoint not in removals]
            removed_count = len(current) - len(updated)
            self._set_current_charset_codepoints(updated)
            self.codepoint_input_edit.clear()
            self.statusBar().showMessage(f"Removed {removed_count} matching codepoint(s).")
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")

    def _reset_current_charset(self) -> None:
        if self.template_container is not None and self.template_selected_block_index is not None:
            block = next(
                (value for value in self.template_container.blocks if value.block_index == self.template_selected_block_index),
                None,
            )
            if block is None:
                return
            self._set_current_charset_codepoints([glyph.codepoint for glyph in block.glyphs])
            self.statusBar().showMessage("Reset current template block charset to template defaults.")
            return

        self._set_current_charset_codepoints([ord(char) for char in build_ascii_charset()])
        self.statusBar().showMessage("Reset standalone charset to ASCII 32-126.")

    def _load_template_uifont(
        self,
        path: str,
        saved_configs: dict[int, UIFontBuildConfig] | None = None,
        preferred_block_index: int | None = None,
    ) -> None:
        try:
            self.statusBar().showMessage("Loading template UIFONT...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._save_current_template_font_config()
            self.template_container = parse_uifont(path)
            self.template_font_configs = dict(saved_configs or {})
            self.template_selected_block_index = None
            self.last_uifont_build_result = None
            self.last_result = None
            self.current_preview = None
            self.preview_label.set_preview_pixmap(None)
            self._populate_template_font_list(preferred_block_index)
            self.statusBar().showMessage(
                f"Loaded template with {len(self.template_container.blocks)} font blocks."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_template_font_list(self, preferred_block_index: int | None = None) -> None:
        self.template_font_list.clear()

        container = self.template_container
        if container is None:
            self.summary_edit.setPlainText("Load a template .uifont file to start template-driven UIFont creation.")
            return

        seed_font_path = self.font_path_edit.text().strip()
        for block in container.blocks:
            config = self.template_font_configs.get(block.block_index)
            if config is None:
                config = UIFontBuildConfig(
                    block_index=block.block_index,
                    font_name=block.name,
                    font_path=seed_font_path,
                    pixel_size=self._infer_template_pixel_size(block),
                    charset_codepoints=[glyph.codepoint for glyph in block.glyphs],
                )
                self.template_font_configs[block.block_index] = config

            kind = "embedded" if block.has_embedded_glyphs else "reference"
            item = QListWidgetItem(
                f"[{block.block_index:02d}] {block.name}  |  {kind}  |  glyphs={len(block.glyphs)}"
            )
            item.setData(Qt.UserRole, block.block_index)
            self.template_font_list.addItem(item)

        if self.template_font_list.count() > 0:
            if preferred_block_index is not None:
                for row in range(self.template_font_list.count()):
                    item = self.template_font_list.item(row)
                    if item.data(Qt.UserRole) == preferred_block_index:
                        self.template_font_list.setCurrentRow(row)
                        return
            self.template_font_list.setCurrentRow(0)

    def _infer_template_pixel_size(self, block: UIFontBlock) -> int:
        suffix_digits = []
        for char in reversed(block.name):
            if not char.isdigit():
                break
            suffix_digits.append(char)
        if suffix_digits:
            return max(1, int("".join(reversed(suffix_digits))))

        if len(block.metrics_raw) >= 4 and block.metrics_raw[3] > 0:
            return max(1, round(block.metrics_raw[3] / 64.0))
        return self.pixel_size_spin.value()

    def _save_current_template_font_config(self) -> None:
        if self.template_form_sync_lock:
            return

        block_index = self.template_selected_block_index
        container = self.template_container
        if block_index is None or container is None:
            return

        block = next((value for value in container.blocks if value.block_index == block_index), None)
        if block is None:
            return

        existing = self.template_font_configs.get(block_index)
        charset_codepoints = list(existing.charset_codepoints) if existing is not None else [glyph.codepoint for glyph in block.glyphs]

        self.template_font_configs[block_index] = UIFontBuildConfig(
            block_index=block_index,
            font_name=block.name,
            font_path=self.font_path_edit.text().strip(),
            pixel_size=self.pixel_size_spin.value(),
            charset_codepoints=charset_codepoints,
        )

    def _apply_selected_font_to_all_template_fonts(self) -> None:
        container = self.template_container
        font_path = self.font_path_edit.text().strip()
        if container is None:
            self._show_error("Load a template .uifont file first.")
            return
        if not font_path:
            self._show_error("Please select a font file first.")
            return

        self._save_current_template_font_config()
        for block in container.blocks:
            config = self.template_font_configs.get(block.block_index)
            if config is None:
                config = UIFontBuildConfig(
                    block_index=block.block_index,
                    font_name=block.name,
                    font_path=font_path,
                    pixel_size=self._infer_template_pixel_size(block),
                    charset_codepoints=[glyph.codepoint for glyph in block.glyphs],
                )
            else:
                config.font_path = font_path
            self.template_font_configs[block.block_index] = config

        if self.template_selected_block_index is not None:
            self._load_template_font_into_form(self.template_selected_block_index)
        self.statusBar().showMessage("Applied selected font file to all template fonts.")

    def _load_template_font_into_form(self, block_index: int) -> None:
        container = self.template_container
        if container is None:
            return

        config = self.template_font_configs.get(block_index)
        if config is None:
            return

        self.template_form_sync_lock = True
        self.font_path_edit.setText(config.font_path)
        self.pixel_size_spin.setValue(config.pixel_size)
        self._refresh_charset_codepoint_list(config.charset_codepoints)
        self.template_form_sync_lock = False
        self._refresh_template_selection_summary()

    def _count_replaceable_cjk_slots(self, codepoints: list[int]) -> int:
        return sum(1 for codepoint in codepoints if _is_cjk_or_cyrillic_codepoint(codepoint))

    def _refresh_template_selection_summary(self) -> None:
        container = self.template_container
        block = self._current_template_block()
        if container is None or block is None:
            return

        config = self.template_font_configs.get(block.block_index)
        if config is None:
            return

        lines = [
            f"Template file: {container.source_file}",
            f"Selected block: [{block.block_index:02d}] {block.name}",
            f"Embedded glyphs: {len(block.glyphs)}",
            f"Current charset size: {len(config.charset_codepoints)}",
            (
                "Import UTF-16BE Charset (Replace CJK+Cyrillic) slots: "
                f"{self._count_replaceable_cjk_slots(config.charset_codepoints)}"
            ),
            f"Atlas template: {container.atlas_path or '(none)'}",
            f"UITX template: {container.uitx_path or '(none)'}",
            f"NUT template: {container.nut1_path or '(none)'}",
            "",
            "Notes:",
            "- UTF-16BE charset import reads raw characters verbatim; spaces and line breaks also become codepoints.",
            "- Appending codepoints that are not already present in the template block will create synthetic glyph records.",
            "- DDS drives the generated NUT size and pixel payload; template NUT metadata is only used as an optional seed.",
            "- Output writes 0.uifont, 1/0.uitx, and one or more 1/1/<page>/{0,1}.nut files using template-relative names.",
        ]
        self.summary_edit.setPlainText("\n".join(lines))

    def _on_template_font_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        self._save_current_template_font_config()
        if current is None:
            self.template_selected_block_index = None
            return

        block_index = current.data(Qt.UserRole)
        if not isinstance(block_index, int):
            return

        self.template_selected_block_index = block_index
        self._load_template_font_into_form(block_index)

    def _generate(self) -> None:
        try:
            self.statusBar().showMessage("Generating atlas...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._update_generate_progress(0, 1, "Starting atlas generation...")
            if self.template_container is not None:
                self._save_current_template_font_config()
                export_root = self._resolve_export_root()

                result = build_uifont_package(
                    template=self.template_container,
                    font_configs=self.template_font_configs,
                    output_root=export_root,
                    atlas_width=self.atlas_width_spin.value(),
                    atlas_height=self.atlas_height_spin.value(),
                    padding=self.padding_spin.value(),
                    progress_callback=self._update_generate_progress,
                )
                self.last_uifont_build_result = result
                self.last_result = None
                self._update_preview_image(result.atlas_image)
                self._update_template_build_summary(result)
                self._save_creation_page_config()
                self._update_generate_progress(1, 1, "Template atlas preview ready.")
                self.statusBar().showMessage("Template UIFont preview generated.")
                return

            font_path = self.font_path_edit.text().strip()
            charset = "".join(chr(codepoint) for codepoint in self.standalone_charset_codepoints)
            if not font_path:
                self._show_error("Please select a font file first.")
                return

            result = generate_atlas(
                font_path=font_path,
                charset=charset,
                pixel_size=self.pixel_size_spin.value(),
                max_width=self.atlas_width_spin.value(),
                max_height=self.atlas_height_spin.value(),
                padding=self.padding_spin.value(),
                progress_callback=self._update_generate_progress,
            )
            self.last_result = result
            self.last_uifont_build_result = None
            self._update_preview(result)
            self._update_summary(result)
            self._save_creation_page_config()
            self._update_generate_progress(1, 1, "Atlas preview ready.")
            self.statusBar().showMessage("Atlas generated.")
        except Exception as exc:
            self._reset_generate_progress()
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _save_result(self) -> None:
        if self.template_container is not None:
            if self.last_uifont_build_result is None:
                self._show_error("Generate a template preview before saving output.")
                return

            try:
                self.last_uifont_build_result.output_root = str(self._resolve_export_root())
                paths = save_uifont_package(self.last_uifont_build_result)
                nut_page_count = len(paths.get("nut1_pages", []))
                message = (
                    f"Saved UIFONT package to {paths['uifont'].parent}: "
                    f"{paths['uifont'].name}, {paths['uitx'].name}"
                )
                if "nut0" in paths and "nut1" in paths:
                    message += f", {paths['nut0'].name}, {paths['nut1'].name}"
                if nut_page_count > 1:
                    message += f" (+ {nut_page_count - 1} more atlas pages)"
                self.statusBar().showMessage(message)
            except Exception as exc:
                self._show_error(f"{exc}\n\n{traceback.format_exc()}")
            return

        if self.last_result is None:
            self._show_error("Generate an atlas before saving.")
            return

        try:
            export_root = self._resolve_export_root()
            paths = save_result(self.last_result, export_root)
            self.statusBar().showMessage(
                f"Saved atlas output to {paths['nut0'].parent}: "
                f"{paths['nut0'].name}, {paths['nut1'].name}"
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")

    def _load_uifont_file(self, path: str) -> None:
        try:
            self.uifont_file_edit.setText(path)
            self.statusBar().showMessage("Parsing UIFONT...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            blocks = parse_uifont(path).blocks
            self.uifont_blocks = blocks

            grouped: dict[str, list[UIFontBlock]] = {}
            for block in blocks:
                grouped.setdefault(block.name, []).append(block)

            self.uifont_fonts_by_name = dict(sorted(grouped.items(), key=lambda item: item[0].lower()))
            self._populate_uifont_font_list()
            self.statusBar().showMessage(
                f"Parsed {len(blocks)} blocks and {len(self.uifont_fonts_by_name)} font names from {Path(path).name}."
            )
        except Exception as exc:
            self._show_error(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_uifont_font_list(self) -> None:
        self.uifont_font_list.clear()
        self.uifont_glyph_list.clear()
        self.uifont_summary_edit.clear()
        self.uifont_selected_glyph = None
        self.uifont_atlas_path_edit.clear()
        self.uifont_atlas_preview.set_preview_pixmap(None)

        if not self.uifont_fonts_by_name:
            self.uifont_summary_edit.setPlainText("未找到 .uifont 文件或字体块。")
            return

        for font_name, blocks in self.uifont_fonts_by_name.items():
            glyph_total = sum(len(block.glyphs) for block in blocks)
            file_total = len({block.source_file for block in blocks})
            item = QListWidgetItem(
                f"{font_name}  |  blocks={len(blocks)}  glyphs={glyph_total}  files={file_total}"
            )
            item.setData(Qt.UserRole, font_name)
            self.uifont_font_list.addItem(item)

        self.uifont_font_list.setCurrentRow(0)

    def _on_uifont_font_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        self.uifont_glyph_list.clear()
        self.uifont_selected_glyph = None
        self.uifont_atlas_path_edit.clear()
        self.uifont_atlas_preview.set_preview_pixmap(None)
        if current is None:
            return

        font_name = current.data(Qt.UserRole)
        if not isinstance(font_name, str):
            return

        blocks = self.uifont_fonts_by_name.get(font_name, [])
        glyphs: list[UIFontGlyph] = []
        for block in blocks:
            glyphs.extend(block.glyphs)

        glyphs.sort(key=lambda glyph: (glyph.codepoint, glyph.glyph_index, glyph.source_file))
        for glyph in glyphs:
            item = QListWidgetItem(
                f"U+{glyph.codepoint:04X} '{glyph.display_char}'  "
                f"idx={glyph.glyph_index}  "
                f"page={glyph.atlas_page_index}  "
                f"atlas=({glyph.atlas_x},{glyph.atlas_y})  "
                f"ink={glyph.ink_width_px}x{glyph.ink_height_px}  "
                f"advance={glyph.advance_x_px:.3f}  "
                f"class=0x{glyph.class_byte:02X}"
            )
            item.setData(Qt.UserRole, glyph)
            self.uifont_glyph_list.addItem(item)

        files = sorted({Path(block.source_file).name for block in blocks})
        preview_sources = sorted({
            source_path
            for block in blocks
            for source_path in ([*block.nut1_paths.values(), *block.atlas_paths.values()] or [block.nut1_path or block.atlas_path])
            if source_path
        })
        atlas_pages = sorted({
            page_index
            for block in blocks
            for page_index in set(block.nut1_paths) | set(block.atlas_paths)
        })
        summary_lines = [
            f"Font Name: {font_name}",
            f"Blocks: {len(blocks)}",
            f"Glyph entries: {len(glyphs)}",
            f"Files: {len(files)}",
            f"Atlas pages: {len(atlas_pages)}",
            f"Atlas sources: {len(preview_sources)}",
            "",
            "Source files:",
        ]
        summary_lines.extend(files[:20])
        if len(files) > 20:
            summary_lines.append(f"... {len(files) - 20} more")
        if preview_sources:
            summary_lines.append("")
            summary_lines.append("Atlas source paths:")
            summary_lines.extend(preview_sources[:5])
            if len(preview_sources) > 5:
                summary_lines.append(f"... {len(preview_sources) - 5} more")
        self.uifont_summary_edit.setPlainText("\n".join(summary_lines))

        if self.uifont_glyph_list.count() > 0:
            self.uifont_glyph_list.setCurrentRow(self._find_default_uifont_glyph_row())

    def _find_default_uifont_glyph_row(self) -> int:
        for row in range(self.uifont_glyph_list.count()):
            item = self.uifont_glyph_list.item(row)
            glyph = item.data(Qt.UserRole)
            if isinstance(glyph, UIFontGlyph) and glyph.ink_width_px > 0 and glyph.ink_height_px > 0:
                return row
        return 0

    def _on_uifont_glyph_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if current is None:
            self.uifont_selected_glyph = None
            self.uifont_atlas_path_edit.clear()
            self.uifont_atlas_preview.set_highlight_rect(None)
            self.uifont_atlas_preview.set_preview_pixmap(None)
            return

        glyph = current.data(Qt.UserRole)
        if not isinstance(glyph, UIFontGlyph):
            return

        self.uifont_selected_glyph = glyph
        preview_source_path = self._get_uifont_preview_source_path(glyph)
        if preview_source_path:
            self.uifont_atlas_path_edit.setText(f"[page {glyph.atlas_page_index}] {preview_source_path}")
        else:
            self.uifont_atlas_path_edit.setText("(no atlas found)")
        self._refresh_uifont_preview()

    def _get_uifont_preview_source_path(self, glyph: UIFontGlyph) -> str:
        if glyph.nut1_path:
            return glyph.nut1_path
        if glyph.atlas_path:
            return glyph.atlas_path
        if glyph.atlas_page_index in glyph.nut1_paths:
            return glyph.nut1_paths[glyph.atlas_page_index]
        if glyph.atlas_page_index in glyph.atlas_paths:
            return glyph.atlas_paths[glyph.atlas_page_index]
        if glyph.nut1_paths:
            return glyph.nut1_paths[sorted(glyph.nut1_paths)[0]]
        if glyph.atlas_paths:
            return glyph.atlas_paths[sorted(glyph.atlas_paths)[0]]
        return ""

    def _load_uifont_preview_pixmap(self, source_path: str) -> QPixmap | None:
        pixmap = self.uifont_atlas_cache.get(source_path)
        if pixmap is not None:
            return pixmap

        source = Path(source_path)
        try:
            if source.suffix.lower() == ".nut":
                pixmap = pil_image_to_qpixmap(load_nut_image(source))
            else:
                pixmap = QPixmap(source_path)
                if pixmap.isNull():
                    pixmap = pil_image_to_qpixmap(Image.open(source))
        except Exception:
            return None

        if pixmap.isNull():
            return None

        self.uifont_atlas_cache[source_path] = pixmap
        return pixmap

    def _show_uifont_glyph_on_atlas(self, glyph: UIFontGlyph) -> None:
        source_path = self._get_uifont_preview_source_path(glyph)
        if not source_path:
            self.uifont_atlas_preview.set_preview_pixmap(None)
            return

        pixmap = self._load_uifont_preview_pixmap(source_path)
        if pixmap is None:
            self.uifont_atlas_preview.set_preview_pixmap(None)
            return

        if self.uifont_preview_mode == "glyph":
            crop_x = glyph.atlas_x
            crop_y = glyph.atlas_y
            crop_w = max(1, glyph.ink_width_px)
            crop_h = max(1, glyph.ink_height_px)
            cropped = pixmap.copy(crop_x, crop_y, crop_w, crop_h)
            self.uifont_atlas_preview.set_preview_pixmap(cropped)
            self.uifont_atlas_preview.set_highlight_rect(None)
            return

        self.uifont_atlas_preview.set_preview_pixmap(pixmap)
        self.uifont_atlas_preview.set_highlight_rect(
            (
                glyph.atlas_x,
                glyph.atlas_y,
                max(1, glyph.ink_width_px),
                max(1, glyph.ink_height_px),
            )
        )

    def _set_uifont_preview_mode(self, mode: str) -> None:
        self.uifont_preview_mode = mode
        self._sync_uifont_preview_mode_buttons()
        self._refresh_uifont_preview()

    def _sync_uifont_preview_mode_buttons(self) -> None:
        self.uifont_full_view_button.setChecked(self.uifont_preview_mode == "atlas")
        self.uifont_crop_view_button.setChecked(self.uifont_preview_mode == "glyph")

    def _refresh_uifont_preview(self) -> None:
        glyph = self.uifont_selected_glyph
        if glyph is None:
            self.uifont_atlas_preview.set_preview_pixmap(None)
            return
        self._show_uifont_glyph_on_atlas(glyph)

    def _update_preview_image(self, image: Image.Image) -> None:
        pixmap = pil_image_to_qpixmap(image)
        self.current_preview = pixmap
        self.preview_label.set_preview_pixmap(pixmap)

    def _update_preview(self, result: AtlasResult) -> None:
        self._update_preview_image(result.atlas_image)

    def _update_summary(self, result: AtlasResult) -> None:
        lines = [
            f"Font: {result.font_path}",
            f"Pixel size: {result.pixel_size}",
            f"Atlas: {result.atlas_width} x {result.atlas_height}",
            f"Used bounds: {result.used_width} x {result.used_height}",
            f"Ascent: {result.ascent:.3f}",
            f"Descent: {result.descent:.3f}",
            f"Line height: {result.line_height:.3f}",
            f"Padding: {result.padding}",
            f"Glyph count: {len(result.glyphs)}",
            "Packing mode: atlas",
            "",
            "First glyphs:",
        ]
        for glyph in result.glyphs[:20]:
            lines.append(
                f"U+{glyph.codepoint:04X} '{glyph.char}' "
                f"pos=({glyph.atlas_x},{glyph.atlas_y}) "
                f"size={glyph.width}x{glyph.height} "
                f"bearing=({glyph.bearing_x},{glyph.bearing_y}) "
                f"advance={glyph.advance_x:.3f}"
            )
        self.summary_edit.setPlainText("\n".join(lines))

    def _update_template_build_summary(self, result: UIFontBuildResult) -> None:
        page_entries = result.debug_metadata.get("pages", [])
        selected_block = self._current_template_block()
        selected_config = (
            self.template_font_configs.get(selected_block.block_index)
            if selected_block is not None
            else None
        )
        lines = [
            f"Template: {result.template_path}",
            f"Preview Atlas: {result.atlas_width} x {result.atlas_height}",
            f"Used bounds: {result.used_width} x {result.used_height}",
            f"Atlas pages: {len(page_entries)}",
            f"Packing mode: {result.debug_metadata.get('packing_mode', 'unknown')}",
            f"Fallback glyphs: {result.debug_metadata.get('fallback_glyph_count', 0)}",
            f"UIFONT output: {result.uifont_relative_path}",
            f"UITX output: {result.uitx_relative_path}",
            f"0.nut output: {result.nut0_relative_path}",
            f"1.nut output: {result.nut1_relative_path}",
        ]
        if selected_block is not None and selected_config is not None:
            lines.extend(
                [
                    f"Selected block: [{selected_block.block_index:02d}] {selected_block.name}",
                    f"Selected charset size: {len(selected_config.charset_codepoints)}",
                    (
                        "Import UTF-16BE Charset (Replace CJK+Cyrillic) slots: "
                        f"{self._count_replaceable_cjk_slots(selected_config.charset_codepoints)}"
                    ),
                ]
            )
        lines.extend([
            "",
            "Pages:",
        ])
        for page in page_entries[:20]:
            lines.append(
                f"[page {page['page_index']}] {page['width']}x{page['height']}  "
                f"used={page['used_width']}x{page['used_height']}  "
                f"glyphs={page['glyph_count']}  "
                f"0.nut={page['nut0_path']}  "
                f"1.nut={page['nut1_path']}"
            )
        lines.extend([
            "",
            "Fonts:",
        ])
        for entry in result.debug_metadata.get("fonts", [])[:20]:
            lines.append(
                    f"[{entry['block_index']:02d}] {entry['name']}  "
                    f"glyphs={entry['glyph_count']}  "
                    f"fallback={entry.get('fallback_glyph_count', 0)}  "
                    f"size={entry['pixel_size']}  "
                    f"font={Path(entry['font_path']).name if entry['font_path'] else '(unset)'}"
                )
        self.summary_edit.setPlainText("\n".join(lines))

    def _show_error(self, message: str) -> None:
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "ACI Font Tools", message)
        self.statusBar().showMessage("Error")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self._save_creation_page_config()
        except Exception:
            pass
        super().closeEvent(event)


def main() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec_()
