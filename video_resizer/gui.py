import logging
import os
import sys
import html
from typing import List, Optional

from PyQt6.QtCore import QObject, QPointF, QRectF, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .cleaner import cleanup, replace_originals
from .estimator import VideoInfo, estimate, output_path
from .logger import get_logger
from .processor import process
from .scanner import scan


# ---------------------------------------------------------------------------
# Qt logging handler
# ---------------------------------------------------------------------------

class _QtLogHandler(logging.Handler, QObject):
    log_record = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.log_record.emit(msg)


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class _ScanWorker(QObject):
    result = pyqtSignal(list)        # List[VideoInfo]
    error = pyqtSignal(str, str)     # path, error message
    finished = pyqtSignal()

    def __init__(self, directory: str, target_w: int, target_h: int, include_processed: bool = False):
        super().__init__()
        self._dir = directory
        self._tw = target_w
        self._th = target_h
        self._include_processed = include_processed
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        paths = scan(self._dir, skip_marked=not self._include_processed)
        infos: List[VideoInfo] = []
        for path in paths:
            if self._cancelled:
                break
            try:
                infos.append(estimate(path, self._tw, self._th))
            except RuntimeError as exc:
                self.error.emit(path, str(exc))
        self.result.emit(infos)
        self.finished.emit()


class _ProcessWorker(QObject):
    file_done = pyqtSignal(str, str)   # path, status ("done"|"skipped"|"error")
    file_progress = pyqtSignal(str, float, str, str)  # path, percent, fps, speed
    file_error = pyqtSignal(str, str)  # path, error message
    cleanup_done = pyqtSignal(str, str)  # original path, status
    finished = pyqtSignal()

    def __init__(self, infos: List[VideoInfo], do_cleanup: bool, do_replace_originals: bool):
        super().__init__()
        self._infos = infos
        self._do_cleanup = do_cleanup
        self._do_replace_originals = do_replace_originals
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        successful = []
        for info in self._infos:
            if self._cancelled:
                break
            status_holder = ["processing"]

            def _on_progress(s, holder=status_holder, path=info.path):
                if isinstance(s, dict) and s.get("status") == "progress":
                    self.file_progress.emit(
                        path,
                        float(s.get("percent", 0.0)),
                        str(s.get("fps", "")),
                        str(s.get("speed", "")),
                    )
                if isinstance(s, str):
                    holder[0] = s

            try:
                process(info, on_progress=_on_progress)
                final_status = status_holder[0] if status_holder[0] != "processing" else "done"
                self.file_done.emit(info.path, final_status)
                successful.append(info.path)
            except RuntimeError as exc:
                self.file_error.emit(info.path, str(exc))

        if not self._cancelled and successful:
            if self._do_replace_originals:
                result = replace_originals(successful)
                for p in result.replaced:
                    self.cleanup_done.emit(p, "replaced")
                for p in result.skipped:
                    self.cleanup_done.emit(p, "replace_skipped")
                for p in result.failed:
                    self.cleanup_done.emit(p, "replace_failed")
            elif self._do_cleanup:
                result = cleanup(successful)
                for p in result.deleted:
                    self.cleanup_done.emit(p, "deleted")
                for p in result.skipped:
                    self.cleanup_done.emit(p, "skipped_cleanup")
                for p in result.failed:
                    self.cleanup_done.emit(p, "cleanup_failed")

        self.finished.emit()


# ---------------------------------------------------------------------------
# Column indices
# ---------------------------------------------------------------------------
_COL_FILE = 0
_COL_ORIG_SIZE = 1
_COL_ORIG_RES = 2
_COL_NEW_RES = 3
_COL_EST_SIZE = 4
_COL_STATUS = 5
_NUM_COLS = 6


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Resizer")
        self.resize(1100, 750)
        self.setWindowIcon(self._build_app_icon())

        self._infos: List[VideoInfo] = []
        self._path_to_row: dict = {}
        self._scan_thread: Optional[QThread] = None
        self._proc_thread: Optional[QThread] = None

        # --- Qt log handler ---
        self._log_handler = _QtLogHandler()
        self._log_handler.log_record.connect(self._append_log)
        get_logger().addHandler(self._log_handler)

        self._build_ui()
        self._apply_modern_theme()

        self._full_screen_shortcut = QShortcut(QKeySequence("F11"), self)
        self._full_screen_shortcut.activated.connect(self._toggle_fullscreen)
        self._exit_full_screen_shortcut = QShortcut(QKeySequence("Escape"), self)
        self._exit_full_screen_shortcut.activated.connect(self._exit_fullscreen_if_needed)

    @staticmethod
    def _build_app_icon() -> QIcon:
        """Create a custom multi-size app icon to avoid default Qt icon."""
        icon = QIcon()

        for size in (16, 24, 32, 48, 64, 128, 256):
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)

            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            rect = QRectF(1, 1, size - 2, size - 2)
            radius = size * 0.22
            bg = QPainterPath()
            bg.addRoundedRect(rect, radius, radius)

            grad = QLinearGradient(0, 0, size, size)
            grad.setColorAt(0.0, QColor("#2f6d99"))
            grad.setColorAt(1.0, QColor("#2f9f5f"))
            p.fillPath(bg, grad)

            p.setPen(QPen(QColor(255, 255, 255, 90), max(1.0, size * 0.03)))
            p.drawPath(bg)

            # Center play glyph to suggest video processing.
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ffffff"))
            tri = QPainterPath()
            tri.moveTo(QPointF(size * 0.40, size * 0.30))
            tri.lineTo(QPointF(size * 0.72, size * 0.50))
            tri.lineTo(QPointF(size * 0.40, size * 0.70))
            tri.closeSubpath()
            p.drawPath(tri)

            # Subtle VR badge text.
            p.setPen(QColor(255, 255, 255, 215))
            f = QFont("Segoe UI", max(6, int(size * 0.12)))
            f.setBold(True)
            p.setFont(f)
            p.drawText(QRectF(0, size * 0.72, size, size * 0.22), Qt.AlignmentFlag.AlignHCenter, "VR")

            p.end()
            icon.addPixmap(pix)

        return icon

    def _set_bar_color(self, bar: QProgressBar, chunk_color: str) -> None:
        bar.setStyleSheet(
            "QProgressBar {"
            "border: 1px solid #bcd0df;"
            "border-radius: 4px;"
            "background: #edf3f8;"
            "color: #15354e;"
            "text-align: center;"
            "}"
            f"QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 3px; }}"
        )

    def _refresh_totals_label(self) -> None:
        if not self._infos:
            self._totals_label.setText("")
            return

        total_orig = sum(info.orig_size_bytes for info in self._infos)
        total_out = 0
        actual_count = 0
        for info in self._infos:
            out = output_path(info.path)
            if os.path.exists(out):
                total_out += os.path.getsize(out)
                actual_count += 1
            else:
                total_out += info.est_size_bytes

        self._totals_label.setText(
            f"Total original: {_fmt_bytes(total_orig)}   "
            f"Output: {_fmt_bytes(total_out)} "
            f"(actual {actual_count}/{len(self._infos)})"
        )

    def _update_actual_size_cell(self, path: str) -> None:
        row = self._path_to_row.get(path)
        if row is None:
            return
        out = output_path(path)
        if not os.path.exists(out):
            return

        item = QTableWidgetItem(_fmt_bytes(os.path.getsize(out)))
        item.setToolTip("Actual output size")
        self._table.setItem(row, _COL_EST_SIZE, item)
        self._refresh_totals_label()

    def _make_status_bar(self, value: int = 0, text: str = "pending", color: str = "#2e9f52") -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(max(0, min(100, value)))
        bar.setFormat(text)
        bar.setTextVisible(True)
        bar.setMinimumWidth(280)
        self._set_bar_color(bar, color)
        return bar

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --- Hero header ---
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(2)
        title = QLabel("Video Resizer Studio")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Fast batch conversion with validation, cleanup, and replace-originals pass")
        subtitle.setObjectName("heroSubtitle")
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        # --- Top bar ---
        top = QHBoxLayout()
        top.setSpacing(8)
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("Select input directory…")
        self._dir_edit.setReadOnly(True)
        self._dir_edit.setMinimumHeight(34)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        self._res_edit = QLineEdit("1280x720")
        self._res_edit.setFixedWidth(100)
        self._res_edit.setMinimumHeight(34)
        self._res_edit.setToolTip("Target resolution (WxH)")
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setMinimumHeight(34)
        self._scan_btn.clicked.connect(self._start_scan)
        self._include_processed_check = QCheckBox("Include already processed")
        top.addWidget(QLabel("Directory:"))
        top.addWidget(self._dir_edit, stretch=1)
        top.addWidget(browse_btn)
        top.addWidget(QLabel("Resolution:"))
        top.addWidget(self._res_edit)
        top.addWidget(self._include_processed_check)
        top.addWidget(self._scan_btn)
        root.addLayout(top)

        # --- Splitter: table + log ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        # File table
        table_widget = QWidget()
        tv = QVBoxLayout(table_widget)
        tv.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, _NUM_COLS)
        self._table.setHorizontalHeaderLabels(
            ["File", "Orig Size", "Orig Res", "New Res", "Out Size", "Status"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, _COL_STATUS):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_STATUS, 320)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tv.addWidget(self._table)

        # Totals label
        self._totals_label = QLabel("")
        tv.addWidget(self._totals_label)

        splitter.addWidget(table_widget)

        # Log panel
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText("Processing logs will appear here…")
        splitter.addWidget(self._log_edit)
        splitter.setSizes([500, 200])

        root.addWidget(splitter, stretch=1)

        # --- Bottom controls ---
        bottom = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setMinimumHeight(26)
        self._start_btn = QPushButton("Start")
        self._start_btn.setMinimumHeight(34)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_processing)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setMinimumHeight(34)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        self._cleanup_check = QCheckBox("Delete originals after processing")
        self._replace_check = QCheckBox("Second pass: replace originals with resized")
        self._cleanup_check.toggled.connect(self._on_cleanup_toggled)
        self._replace_check.toggled.connect(self._on_replace_toggled)
        self._manual_btn = QPushButton("Quick Manual")
        self._manual_btn.setMinimumHeight(34)
        self._manual_btn.clicked.connect(self._show_quick_manual)
        self._fullscreen_btn = QPushButton("Full Screen")
        self._fullscreen_btn.setMinimumHeight(34)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        bottom.addWidget(self._progress, stretch=1)
        bottom.addWidget(self._cleanup_check)
        bottom.addWidget(self._replace_check)
        bottom.addWidget(self._manual_btn)
        bottom.addWidget(self._fullscreen_btn)
        bottom.addWidget(self._start_btn)
        bottom.addWidget(self._cancel_btn)
        root.addLayout(bottom)

    def _apply_modern_theme(self):
        self.setStyleSheet(
            "QWidget#root {"
            "background: #f3f7fb;"
            "color: #173042;"
            "}"
            "QFrame#hero {"
            "border: 1px solid #8fb5d3;"
            "border-radius: 12px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "stop:0 #d7ebff, stop:1 #d7f6ee);"
            "}"
            "QLabel#heroTitle {"
            "font-size: 22px;"
            "font-weight: 700;"
            "color: #0f3e63;"
            "}"
            "QLabel#heroSubtitle {"
            "font-size: 12px;"
            "color: #2f5d7f;"
            "}"
            "QLabel {"
            "color: #173042;"
            "}"
            "QLineEdit, QTextEdit, QTableWidget {"
            "background: #ffffff;"
            "color: #1a2f3f;"
            "border: 1px solid #c8d9e8;"
            "border-radius: 8px;"
            "padding: 6px 8px;"
            "selection-background-color: #c8e7ff;"
            "selection-color: #12324a;"
            "}"
            "QTableWidget::item { color: #1a2f3f; }"
            "QHeaderView::section {"
            "background: #e6f0f8;"
            "color: #12324a;"
            "padding: 6px;"
            "border: none;"
            "border-right: 1px solid #c8d9e8;"
            "font-weight: 600;"
            "}"
            "QTableWidget {"
            "alternate-background-color: #f7fbff;"
            "gridline-color: #dce8f2;"
            "}"
            "QPushButton {"
            "background: #2f6d99;"
            "color: #ffffff;"
            "border: 1px solid #2a6288;"
            "border-radius: 8px;"
            "padding: 6px 12px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "background: #377caa;"
            "}"
            "QPushButton:pressed {"
            "background: #285b80;"
            "}"
            "QPushButton:disabled {"
            "background: #d4dee8;"
            "color: #6f8395;"
            "border-color: #c1ceda;"
            "}"
            "QCheckBox {"
            "spacing: 8px;"
            "color: #173042;"
            "}"
            "QCheckBox::indicator {"
            "width: 16px;"
            "height: 16px;"
            "border-radius: 4px;"
            "border: 1px solid #7ea2bf;"
            "background: #ffffff;"
            "}"
            "QCheckBox::indicator:checked {"
            "background: #2f6d99;"
            "border-color: #2f6d99;"
            "}"
            "QProgressBar {"
            "background: #e7eff6;"
            "border: 1px solid #bdd1e0;"
            "border-radius: 6px;"
            "text-align: center;"
            "color: #15354e;"
            "font-weight: 600;"
            "}"
            "QProgressBar::chunk {"
            "background: #2f9f5f;"
            "border-radius: 5px;"
            "}"
            "QSplitter::handle {"
            "background: #cfdeea;"
            "}"
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select video directory")
        if path:
            self._dir_edit.setText(path)

    def _parse_resolution(self):
        text = self._res_edit.text().strip().lower()
        try:
            w, h = text.split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            QMessageBox.warning(
                self, "Invalid resolution",
                f"Resolution must be in WxH format (e.g. 1280x720).\nGot: {text!r}"
            )
            return None

    def _start_scan(self):
        directory = self._dir_edit.text().strip()
        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, "No directory", "Please select a valid input directory.")
            return
        res = self._parse_resolution()
        if res is None:
            return
        target_w, target_h = res

        self._table.setRowCount(0)
        self._path_to_row.clear()
        self._infos.clear()
        self._totals_label.setText("")
        self._start_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        worker = _ScanWorker(
            directory,
            target_w,
            target_h,
            include_processed=self._include_processed_check.isChecked(),
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result.connect(self._on_scan_result)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_finished)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_scan_result(self, infos: List[VideoInfo]):
        self._infos = infos
        self._table.setRowCount(len(infos))
        total_orig = 0
        total_est = 0
        for row, info in enumerate(infos):
            self._path_to_row[info.path] = row
            self._table.setItem(row, _COL_FILE, QTableWidgetItem(info.path))
            self._table.setItem(row, _COL_ORIG_SIZE, QTableWidgetItem(_fmt_bytes(info.orig_size_bytes)))
            self._table.setItem(row, _COL_ORIG_RES, QTableWidgetItem(f"{info.orig_width}x{info.orig_height}"))
            self._table.setItem(row, _COL_NEW_RES, QTableWidgetItem(f"{info.new_width}x{info.new_height}"))
            self._table.setItem(row, _COL_EST_SIZE, QTableWidgetItem(_fmt_bytes(info.est_size_bytes)))
            bar = self._make_status_bar(0, "pending", "#4a4a4a")
            self._table.setCellWidget(row, _COL_STATUS, bar)
            total_orig += info.orig_size_bytes
            total_est += info.est_size_bytes

        if infos:
            self._totals_label.setText(
                f"Total original: {_fmt_bytes(total_orig)}   "
                f"Estimated output: {_fmt_bytes(total_est)}"
            )

    def _on_scan_error(self, path: str, msg: str):
        get_logger().error("Scan/estimate error for '%s': %s", path, msg)

    def _on_scan_finished(self):
        self._scan_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._start_btn.setEnabled(bool(self._infos))

    def _start_processing(self):
        if not self._infos:
            return
        self._progress.setMaximum(len(self._infos))
        self._progress.setValue(0)
        self._start_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        do_cleanup = self._cleanup_check.isChecked()
        do_replace_originals = self._replace_check.isChecked()
        worker = _ProcessWorker(self._infos, do_cleanup, do_replace_originals)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.file_progress.connect(self._on_file_progress)
        worker.file_done.connect(self._on_file_done)
        worker.file_error.connect(self._on_file_error)
        worker.cleanup_done.connect(self._on_cleanup_done)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_processing_finished)
        self._proc_thread = thread
        self._proc_worker = worker
        thread.start()

    def _on_file_progress(self, path: str, percent: float, fps: str, speed: str):
        row = self._path_to_row.get(path)
        if row is None:
            return
        bar = self._table.cellWidget(row, _COL_STATUS)
        if not isinstance(bar, QProgressBar):
            bar = self._make_status_bar(0, "pending", "#4a4a4a")
            self._table.setCellWidget(row, _COL_STATUS, bar)

        pct = max(0, min(100, int(percent * 100)))
        extras = []
        if fps:
            extras.append(f"fps={fps}")
        if speed:
            extras.append(f"speed={speed}")
        suffix = f" ({', '.join(extras)})" if extras else ""
        bar.setValue(pct)
        bar.setFormat(f"processing {pct}%{suffix}")
        self._set_bar_color(bar, "#2e9f52")

    def _on_file_done(self, path: str, status: str):
        row = self._path_to_row.get(path)
        if row is not None:
            bar = self._table.cellWidget(row, _COL_STATUS)
            if not isinstance(bar, QProgressBar):
                bar = self._make_status_bar(0, "pending", "#4a4a4a")
                self._table.setCellWidget(row, _COL_STATUS, bar)

            if status == "skipped":
                bar.setValue(100)
                bar.setFormat("skipped (validated)")
                self._set_bar_color(bar, "#d9a300")
            else:
                bar.setValue(100)
                bar.setFormat("done")
                self._set_bar_color(bar, "#2e9f52")
        self._update_actual_size_cell(path)
        self._progress.setValue(self._progress.value() + 1)

    def _on_file_error(self, path: str, msg: str):
        row = self._path_to_row.get(path)
        if row is not None:
            bar = self._table.cellWidget(row, _COL_STATUS)
            if not isinstance(bar, QProgressBar):
                bar = self._make_status_bar(0, "pending", "#4a4a4a")
                self._table.setCellWidget(row, _COL_STATUS, bar)
            bar.setValue(100)
            bar.setFormat("error")
            self._set_bar_color(bar, "#d9534f")
            for col in range(_NUM_COLS):
                cell = self._table.item(row, col)
                if cell:
                    cell.setBackground(QColor("#ffcccc"))
        self._progress.setValue(self._progress.value() + 1)
        get_logger().error("Processing error for '%s': %s", path, msg)

    def _on_cleanup_done(self, path: str, status: str):
        row = self._path_to_row.get(path)
        if row is not None:
            label_map = {
                "deleted": "original deleted",
                "skipped_cleanup": "cleanup skipped",
                "cleanup_failed": "cleanup failed",
                "replaced": "replaced original",
                "replace_skipped": "replace skipped",
                "replace_failed": "replace failed",
            }
            label = label_map.get(status, status)
            bar = self._table.cellWidget(row, _COL_STATUS)
            if not isinstance(bar, QProgressBar):
                bar = self._make_status_bar(0, "pending", "#4a4a4a")
                self._table.setCellWidget(row, _COL_STATUS, bar)

            bar.setValue(100)
            bar.setFormat(label)
            if status in {"cleanup_failed", "replace_failed"}:
                self._set_bar_color(bar, "#d9534f")
            elif status in {"deleted", "replaced"}:
                self._set_bar_color(bar, "#2e9f52")
            else:
                self._set_bar_color(bar, "#4a4a4a")

            if status == "replaced" and os.path.exists(path):
                item = QTableWidgetItem(_fmt_bytes(os.path.getsize(path)))
                item.setToolTip("Actual output size (renamed to original)")
                self._table.setItem(row, _COL_EST_SIZE, item)
                self._refresh_totals_label()

    def _on_cleanup_toggled(self, checked: bool):
        if checked and self._replace_check.isChecked():
            self._replace_check.setChecked(False)

    def _on_replace_toggled(self, checked: bool):
        if checked and self._cleanup_check.isChecked():
            self._cleanup_check.setChecked(False)

    def _on_processing_finished(self):
        self._scan_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._start_btn.setEnabled(True)

    def _show_quick_manual(self):
        text = (
            "How it works:\n\n"
            "1) Scan is recursive. The selected folder and all subdirectories are scanned for videos.\n\n"
            "2) Processed-file detection uses metadata. Converted files get marker video_resizer_processed=1. "
            "By default, files with this marker are skipped. Enable 'Include already processed' to rescan them.\n\n"
            "3) Delete originals after processing: keeps *_resized output files and removes original files after health checks.\n\n"
            "4) Second pass: replace originals with resized: validates output, deletes original, then renames resized file to the original filename.\n\n"
            "Tip: Use replace mode when you want final files to keep original names."
        )
        QMessageBox.information(self, "Quick Manual", text)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
            self._fullscreen_btn.setText("Full Screen")
        else:
            self.showFullScreen()
            self._fullscreen_btn.setText("Windowed")

    def _exit_fullscreen_if_needed(self):
        if self.isFullScreen():
            self._toggle_fullscreen()

    def _cancel(self):
        if hasattr(self, "_scan_worker"):
            self._scan_worker.cancel()
        if hasattr(self, "_proc_worker"):
            self._proc_worker.cancel()
        self._cancel_btn.setEnabled(False)

    def _append_log(self, msg: str):
        level = "INFO"
        body = msg
        if ":" in msg:
            maybe_level, maybe_body = msg.split(":", 1)
            maybe_level = maybe_level.strip().upper()
            if maybe_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
                level = maybe_level
                body = maybe_body.strip()

        color_map = {
            "DEBUG": "#5f7a91",
            "INFO": "#1f7a46",
            "WARNING": "#a46d00",
            "ERROR": "#b4232f",
            "CRITICAL": "#7a1022",
        }
        level_color = color_map.get(level, "#2b4a62")
        safe_body = html.escape(body)
        html_line = (
            f"<span style='font-weight:700;color:{level_color};'>{level}</span>"
            f"<span style='color:#2b465c;'>: {safe_body}</span>"
        )
        self._log_edit.append(html_line)

    def closeEvent(self, event):
        self._cancel()
        get_logger().removeHandler(self._log_handler)
        super().closeEvent(event)


def run_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    app.setWindowIcon(window.windowIcon())
    window.showMaximized()
    sys.exit(app.exec())
