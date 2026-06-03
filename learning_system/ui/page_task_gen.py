"""
Page 1: Course Import & Task Generation — Swiss minimalist
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QLineEdit, QScrollArea, QFrame,
    QMessageBox, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import Worker, SectionHeader, TagBadge, LoadingWidget, HDivider
import parser as doc_parser
import task_generator
import data_store

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class TaskGenPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._knowledge = None
        self._tasks = None
        self._worker = None
        self._file_path = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        # Page header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("课件导入 · 任务生成")
        title.setStyleSheet(
            f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;"
        )
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        # ── Left panel ────────────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 24, 0)
        ll.setSpacing(20)

        ll.addWidget(SectionHeader("上传材料"))
        ll.addWidget(self._build_upload_card())

        ll.addWidget(SectionHeader("知识点"))
        kp_scroll = QScrollArea()
        kp_scroll.setWidgetResizable(True)
        kp_scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px;"
            f" background: {BG_CARD}; }}"
        )
        self._kp_container = QWidget()
        self._kp_container.setStyleSheet(f"background: {BG_CARD};")
        self._kp_layout = QVBoxLayout(self._kp_container)
        self._kp_layout.setContentsMargins(16, 16, 16, 16)
        self._kp_layout.setSpacing(8)

        self._kp_empty = QLabel("上传课件后自动提取")
        self._kp_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._kp_empty.setAlignment(Qt.AlignCenter)
        self._kp_layout.addWidget(self._kp_empty)
        self._kp_layout.addStretch()
        kp_scroll.setWidget(self._kp_container)
        ll.addWidget(kp_scroll, 1)

        # ── Right panel ───────────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(24, 0, 0, 0)
        rl.setSpacing(20)

        rh = QHBoxLayout()
        rh.addWidget(SectionHeader("探究任务"))
        rh.addStretch()

        self._gen_btn = QPushButton("生成任务")
        self._gen_btn.setStyleSheet(PRIMARY_BTN)
        self._gen_btn.setEnabled(False)
        self._gen_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._gen_btn.setIcon(qta.icon("ri.flashlight-line", color="white"))
            except Exception:
                pass
        self._gen_btn.clicked.connect(self._generate_tasks)

        self._save_btn = QPushButton("保存")
        self._save_btn.setStyleSheet(SECONDARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._save_btn.setIcon(qta.icon("ri.save-line", color=TEXT_PRI))
            except Exception:
                pass
        self._save_btn.clicked.connect(self._save_tasks)

        rh.addWidget(self._gen_btn)
        rh.addWidget(self._save_btn)
        rl.addLayout(rh)

        task_scroll = QScrollArea()
        task_scroll.setWidgetResizable(True)
        task_scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px;"
            f" background: {BG_CARD}; }}"
        )
        self._task_container = QWidget()
        self._task_container.setStyleSheet(f"background: {BG_CARD};")
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(16, 16, 16, 16)
        self._task_layout.setSpacing(12)

        self._task_empty = QLabel("生成任务后显示在此")
        self._task_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._task_empty.setAlignment(Qt.AlignCenter)
        self._task_layout.addWidget(self._task_empty)
        self._task_layout.addStretch()
        task_scroll.setWidget(self._task_container)
        rl.addWidget(task_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 560])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _build_upload_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {BG_CARD}; border: 1px dashed {BORDER_LT};"
            f" border-radius: {RADIUS}px; }}"
        )
        card.setFixedHeight(140)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        self._file_label = QLabel("选择 PPT / PDF / TXT / DOCX 文件")
        self._file_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._file_label.setAlignment(Qt.AlignCenter)

        row = QHBoxLayout()
        row.setSpacing(8)

        browse_btn = QPushButton("浏览文件")
        browse_btn.setStyleSheet(GHOST_BTN)
        browse_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                browse_btn.setIcon(qta.icon("ri.folder-open-line", color=TEXT_SEC))
            except Exception:
                pass
        browse_btn.clicked.connect(self._choose_file)

        self._chapter_input = QLineEdit()
        self._chapter_input.setPlaceholderText("章节标题（可选）")
        self._chapter_input.setStyleSheet(INPUT_STYLE)

        self._extract_btn = QPushButton("提取知识点")
        self._extract_btn.setStyleSheet(PRIMARY_BTN)
        self._extract_btn.setEnabled(False)
        self._extract_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._extract_btn.setIcon(qta.icon("ri.search-line", color="white"))
            except Exception:
                pass
        self._extract_btn.clicked.connect(self._extract_knowledge)

        row.addWidget(browse_btn)
        row.addWidget(self._chapter_input, 1)
        row.addWidget(self._extract_btn)

        lay.addWidget(self._file_label)
        lay.addLayout(row)
        return card

    # ── File chooser ──────────────────────────────────────────────────────────

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择课程材料", "",
            "课程材料 (*.pptx *.ppt *.pdf *.txt *.md *.docx)"
        )
        if path:
            self._file_path = path
            name = os.path.basename(path)
            self._file_label.setText(f"已选择：{name}")
            self._file_label.setStyleSheet(f"color: {ACCENT2}; font-size: 12px;")
            self._extract_btn.setEnabled(True)

    # ── Knowledge extraction ──────────────────────────────────────────────────

    def _extract_knowledge(self):
        if not self._file_path:
            return
        self._show_loading("正在解析课件并提取知识点…")
        self._extract_btn.setEnabled(False)

        def do():
            text = doc_parser.parse_file(self._file_path)
            text = doc_parser.truncate_text(text)
            return task_generator.extract_knowledge(
                text, self._chapter_input.text().strip()
            ), text

        self._worker = Worker(do)
        self._worker.finished.connect(self._on_knowledge_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_knowledge_done(self, result):
        knowledge, _ = result
        self._knowledge = knowledge
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(True)
        self._render_knowledge(knowledge)

    # ── Task generation ───────────────────────────────────────────────────────

    def _generate_tasks(self):
        if not self._knowledge:
            return
        self._show_loading("正在生成探究式学习任务…")
        self._gen_btn.setEnabled(False)
        self._worker = Worker(task_generator.generate_tasks, self._knowledge)
        self._worker.finished.connect(self._on_tasks_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_tasks_done(self, tasks: dict):
        self._tasks = tasks
        self._loading.hide()
        self._gen_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._render_tasks(tasks)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_tasks(self):
        if not self._tasks or not self._knowledge:
            return
        cid = data_store.save_course(self._knowledge)
        data_store.save_tasks(cid, self._tasks)

        # 注册到 session，评阅页和统计页联动
        try:
            import session_state
            session_state.register_chapter(cid)
        except ImportError:
            pass

        QMessageBox.information(
            self, "已保存",
            f"章节「{self._knowledge.get('chapter_title', '')}」及 "
            f"{len(self._tasks.get('tasks', []))} 个任务已保存。"
        )
        main_win = self.window()
        if hasattr(main_win, '_switch_page') and hasattr(main_win, '_pages'):
            main_win._switch_page(1)
            main_win._pages[1].jump_to_chapter(cid)

    # ── Render: knowledge points ──────────────────────────────────────────────

    def _render_knowledge(self, knowledge: dict):
        # 只删除非 _kp_empty 的 widget
        items_to_remove = []
        for i in range(self._kp_layout.count()):
            item = self._kp_layout.itemAt(i)
            if item and item.widget() and item.widget() is not self._kp_empty:
                items_to_remove.append(item.widget())
        for w in items_to_remove:
            self._kp_layout.removeWidget(w)
            w.deleteLater()

        self._kp_empty.hide()

        for kp in knowledge.get("knowledge_points", []):
            self._kp_layout.insertWidget(
                self._kp_layout.count() - 1,
                self._make_kp_card(kp)
            )

    def _make_kp_card(self, kp: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {BG_INPUT}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS}px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        row = QHBoxLayout()
        name = QLabel(kp.get("name", ""))
        name.setStyleSheet(
            f"color: {TEXT_PRI}; font-weight: 600; font-size: 12px; background: transparent;"
        )
        row.addWidget(name)
        row.addStretch()
        row.addWidget(TagBadge(kp.get("importance", ""), kp.get("importance", "default")))
        row.addWidget(TagBadge(kp.get("type", ""), kp.get("type", "default")))
        lay.addLayout(row)

        desc = QLabel(kp.get("description", ""))
        desc.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)
        return card

    # ── Render: tasks ─────────────────────────────────────────────────────────

    def _render_tasks(self, tasks: dict):
        # 只删除非 _task_empty 的 widget，避免 C++ 对象已删除的错误
        items_to_remove = []
        for i in range(self._task_layout.count()):
            item = self._task_layout.itemAt(i)
            if item and item.widget() and item.widget() is not self._task_empty:
                items_to_remove.append(item.widget())
        for w in items_to_remove:
            self._task_layout.removeWidget(w)
            w.deleteLater()

        self._task_empty.hide()

        for task in tasks.get("tasks", []):
            self._task_layout.insertWidget(
                self._task_layout.count() - 1,
                self._make_task_card(task)
            )

    def _make_task_card(self, task: dict) -> QFrame:
        diff_colors = {"基础": ACCENT2, "中等": ACCENT3, "挑战": ACCENT4}
        diff_color = diff_colors.get(task.get("difficulty", "中等"), ACCENT3)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-left: 4px solid {diff_color}; border-radius: {RADIUS}px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # ── 标题行 ──────────────────────────────────────────────────────────
        row1 = QHBoxLayout()
        title = QLabel(task.get("title", ""))
        title.setStyleSheet(
            f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px; background: transparent;"
        )
        title.setWordWrap(True)
        row1.addWidget(title, 1)
        row1.addWidget(TagBadge(task.get("difficulty", ""), "default"))
        type_lbl = QLabel(task.get("task_type", ""))
        type_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
        )
        row1.addWidget(type_lbl)
        lay.addLayout(row1)

        lay.addWidget(HDivider())

        # ── 任务描述 ────────────────────────────────────────────────────────
        desc_header = QLabel("任务描述")
        desc_header.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700;"
            f" letter-spacing: 1px; background: transparent;"
        )
        lay.addWidget(desc_header)

        desc = QLabel(task.get("description", ""))
        desc.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%; background: transparent;"
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # ── 成果要求（高亮显示）────────────────────────────────────────────
        out = task.get("output_requirements", {})
        specific = out.get("specific_output", "").strip()
        if not specific:
            # 降级：拼接 required_outputs
            required = out.get("required_outputs", [])
            if required:
                specific = "提交：" + "、".join(required)

        if specific:
            out_header = QLabel("成果要求")
            out_header.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700;"
                f" letter-spacing: 1px; background: transparent;"
            )
            lay.addWidget(out_header)

            out_val = QLabel(specific)
            out_val.setStyleSheet(
                f"color: {ACCENT3}; font-size: 11px; background: #FEF3C7;"
                f" border-radius: 4px; padding: 6px 10px;"
            )
            out_val.setWordWrap(True)
            lay.addWidget(out_val)

        # ── 底部信息行 ──────────────────────────────────────────────────────
        req = task.get("interaction_requirements", {})
        bottom = QHBoxLayout()

        # 苏格拉底标签
        if req.get("need_socratic_dialogue", False):
            s_badge = QLabel("苏格拉底式")
            s_badge.setStyleSheet(
                f"color: {ACCENT5}; background: #EFF6FF; border-radius: 3px;"
                f" padding: 1px 6px; font-size: 10px; font-weight: 600;"
            )
            bottom.addWidget(s_badge)

        rounds_lbl = QLabel(f"≥ {req.get('min_rounds', 15)} 轮")
        rounds_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
        )
        bottom.addWidget(rounds_lbl)

        types = req.get("required_types", [])
        if types:
            bottom.addSpacing(8)
            types_lbl = QLabel("  ·  ".join(types))
            types_lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
            )
            bottom.addWidget(types_lbl)

        bottom.addStretch()
        lay.addLayout(bottom)

        return card

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show_loading(self, text: str):
        self._loading.set_text(text)
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

    def _on_error(self, msg: str):
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(bool(self._knowledge))
        QMessageBox.critical(self, "错误", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())