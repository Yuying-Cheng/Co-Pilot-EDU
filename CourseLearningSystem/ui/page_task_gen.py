"""Course material import and classroom task-sheet generation page."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core_pipeline import process_course_material
from data.data_manager import load_knowledge, load_task
from parser.parser import extract_text
from task_generator.task_formatter import export_task_sheet_docx, format_task_sheet
from ui.styles import *
from ui.session_state import register_chapter
from ui.widgets import LoadingWidget, SectionHeader, TagBadge, Worker

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class TaskGenPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._file_path = None
        self._knowledge = None
        self._tasks = None
        self.chapter_id = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("课件导入 · 任务生成")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: 0;")
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 24, 0)
        ll.setSpacing(16)
        ll.addWidget(SectionHeader("课程材料"))
        ll.addWidget(self._build_upload_card())
        ll.addWidget(SectionHeader("知识点"))

        kp_scroll = QScrollArea()
        kp_scroll.setWidgetResizable(True)
        kp_scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px; background: {BG_CARD}; }}")
        self._kp_container = QWidget()
        self._kp_container.setStyleSheet(f"background: {BG_CARD};")
        self._kp_layout = QVBoxLayout(self._kp_container)
        self._kp_layout.setContentsMargins(16, 16, 16, 16)
        self._kp_layout.setSpacing(8)
        self._kp_empty = QLabel("导入课件后自动抽取核心知识点")
        self._kp_empty.setAlignment(Qt.AlignCenter)
        self._kp_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._kp_layout.addWidget(self._kp_empty)
        self._kp_layout.addStretch()
        kp_scroll.setWidget(self._kp_container)
        ll.addWidget(kp_scroll, 1)

        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(24, 0, 0, 0)
        rl.setSpacing(16)

        top = QHBoxLayout()
        top.addWidget(SectionHeader("课堂探究任务书"))
        top.addStretch()
        self._export_btn = QPushButton("导出 DOCX")
        self._export_btn.setStyleSheet(SECONDARY_BTN)
        self._export_btn.setEnabled(False)
        self._export_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._export_btn.setIcon(qta.icon("ri.file-word-line", color=TEXT_PRI))
            except Exception:
                pass
        self._export_btn.clicked.connect(self._export_docx)
        top.addWidget(self._export_btn)
        rl.addLayout(top)

        self._task_preview = QTextEdit()
        self._task_preview.setReadOnly(True)
        self._task_preview.setStyleSheet(INPUT_STYLE)
        self._task_preview.setPlaceholderText("生成后的课堂探究任务书会显示在这里，可直接导出给学生。")
        rl.addWidget(self._task_preview, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([420, 760])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _build_upload_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        self._file_label = QLabel("选择 PPT / PDF / DOCX / TXT / MD 课程材料")
        self._file_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._file_label.setWordWrap(True)
        lay.addWidget(self._file_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        browse_btn = QPushButton("选择材料")
        browse_btn.setStyleSheet(GHOST_BTN)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._choose_file)
        self._chapter_input = QLineEdit()
        self._chapter_input.setPlaceholderText("章节标题，例如：贪心法")
        self._chapter_input.setStyleSheet(INPUT_STYLE)
        row.addWidget(browse_btn)
        row.addWidget(self._chapter_input, 1)
        lay.addLayout(row)

        self._generate_btn = QPushButton("抽取知识点并生成任务")
        self._generate_btn.setStyleSheet(PRIMARY_BTN)
        self._generate_btn.setEnabled(False)
        self._generate_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._generate_btn.setIcon(qta.icon("ri.magic-line", color="white"))
            except Exception:
                pass
        self._generate_btn.clicked.connect(self._generate)
        lay.addWidget(self._generate_btn)
        return card

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择课程材料",
            "",
            "课程材料 (*.pptx *.ppt *.pdf *.docx *.txt *.md)",
        )
        if path:
            self._file_path = path
            self._file_label.setText(f"已选择：{os.path.basename(path)}")
            self._file_label.setStyleSheet(f"color: {ACCENT2}; font-size: 12px;")
            self._generate_btn.setEnabled(True)

    def _generate(self):
        if not self._file_path:
            return
        chapter_title = self._chapter_input.text().strip() or os.path.splitext(os.path.basename(self._file_path))[0]
        chapter_id = "ch_" + "".join(ch for ch in chapter_title if ch.isalnum() or ch in "_-")
        self.chapter_id = chapter_id
        self._loading.set_text("正在抽取知识点并生成课堂探究任务…")
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())
        self._generate_btn.setEnabled(False)

        def do_pipeline():
            raw_text = extract_text(self._file_path)
            if not raw_text.strip():
                raise ValueError("未能从材料中解析到文本内容。")
            success = process_course_material(
                raw_text=raw_text,
                course_name="算法设计与分析",
                chapter_id=chapter_id,
                chapter_title=chapter_title,
            )
            if not success:
                raise ValueError("知识点抽取或任务生成失败，请检查 API Key 和控制台输出。")
            return chapter_id

        self._worker = Worker(do_pipeline)
        self._worker.finished.connect(self._on_generated)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_generated(self, chapter_id: str):
        self._loading.hide()
        self._generate_btn.setEnabled(True)
        self._knowledge = load_knowledge(chapter_id)
        self._tasks = load_task(chapter_id)
        register_chapter(chapter_id)
        self._render_knowledge()
        self._render_task_sheet()
        self._export_btn.setEnabled(bool(self._tasks))
        QMessageBox.information(self, "生成完成", "知识点和课堂探究任务已保存到本地。")

    def _render_knowledge(self):
        self._kp_empty.hide()
        while self._kp_layout.count() > 1:
            item = self._kp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for kp in (self._knowledge or {}).get("knowledge_points", []):
            self._kp_layout.insertWidget(self._kp_layout.count() - 1, self._make_kp_card(kp))

    def _make_kp_card(self, kp: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)
        row = QHBoxLayout()
        name = QLabel(kp.get("name", ""))
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 600; font-size: 12px; background: transparent;")
        row.addWidget(name, 1)
        row.addWidget(TagBadge(kp.get("importance", ""), kp.get("importance", "default")))
        row.addWidget(TagBadge(kp.get("type", ""), kp.get("type", "default")))
        lay.addLayout(row)
        desc = QLabel(kp.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
        lay.addWidget(desc)
        return card

    def _render_task_sheet(self):
        if not self._tasks:
            self._task_preview.clear()
            return
        self._task_preview.setPlainText(format_task_sheet(self._tasks))

    def _export_docx(self):
        if not self._tasks:
            return
        default_name = f"{self._tasks.get('chapter_title', '课堂探究任务')}.docx"
        path, _ = QFileDialog.getSaveFileName(self, "导出课堂探究任务书", default_name, "Word 文档 (*.docx)")
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            export_task_sheet_docx(self._tasks, path)
            QMessageBox.information(self, "导出成功", f"课堂探究任务书已导出到：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _on_error(self, msg: str):
        self._loading.hide()
        self._generate_btn.setEnabled(bool(self._file_path))
        QMessageBox.critical(self, "生成失败", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_loading"):
            self._loading.resize(self.size())
