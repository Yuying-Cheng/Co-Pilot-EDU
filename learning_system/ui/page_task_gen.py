"""
Page 1: Course Import & Task Generation
温暖学术风格 - 支持章节标题自动识别、一键提取+生成、DOCX导出
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QScrollArea, QFrame, QMessageBox, QSplitter, QLineEdit
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import (
    Worker, SectionHeader, SubHeader, TagBadge, LoadingWidget, HDivider,
    add_shadow, make_panel, make_svg_widget,
    ILLUSTRATION_KNOWLEDGE_TREE, ILLUSTRATION_EXPLORE
)
import parser as doc_parser
import task_generator
import data_store
import session_state

try:
    from task_formatter import format_task_sheet, export_task_sheet_docx
    HAS_FORMATTER = True
except ImportError:
    HAS_FORMATTER = False

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


def _guess_chapter_title(file_path: str) -> str:
    import re
    stem = os.path.splitext(os.path.basename(file_path))[0]
    stem = re.sub(r'^[\d_\-\s]+', '', stem).strip()
    stem = re.sub(r'[\(\（].*?[\)\）]', '', stem).strip()
    return stem or os.path.splitext(os.path.basename(file_path))[0]


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
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)

        # ── 页头 ──────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 22)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        page_title = QLabel("课件导入 · 任务生成")
        page_title.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        page_sub = QLabel("上传课程材料，自动提取知识点并生成探究式课堂任务")
        page_sub.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(page_title)
        title_col.addWidget(page_sub)
        hdr.addLayout(title_col)
        hdr.addStretch()

        # 右侧小插画
        try:
            illu = make_svg_widget(ILLUSTRATION_EXPLORE, 80, 58)
            hdr.addWidget(illu)
        except Exception:
            pass

        root.addLayout(hdr)

        # ── 主体分栏 ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER_LIGHT}; }}")

        # 左栏
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 18, 0)
        ll.setSpacing(18)

        ll.addWidget(self._build_upload_card())

        ll.addWidget(SectionHeader("知识点预览"))
        kp_scroll = QScrollArea()
        kp_scroll.setWidgetResizable(True)
        kp_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                border-radius: {RADIUS_LG}px;
                background: {BG_CARD};
            }}
        """)
        self._kp_container = QWidget()
        self._kp_container.setStyleSheet(f"background: {BG_CARD};")
        self._kp_layout = QVBoxLayout(self._kp_container)
        self._kp_layout.setContentsMargins(16, 16, 16, 16)
        self._kp_layout.setSpacing(10)

        # 空态
        empty_w = QWidget()
        empty_w.setStyleSheet("background: transparent;")
        ev = QVBoxLayout(empty_w)
        ev.setAlignment(Qt.AlignCenter)
        ev.setSpacing(10)
        try:
            tree_svg = make_svg_widget(ILLUSTRATION_KNOWLEDGE_TREE, 100, 80)
            ev.addWidget(tree_svg, alignment=Qt.AlignCenter)
        except Exception:
            pass
        self._kp_empty = QLabel("上传课件后自动抽取核心知识点")
        self._kp_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._kp_empty.setAlignment(Qt.AlignCenter)
        ev.addWidget(self._kp_empty)
        self._kp_empty_widget = empty_w
        self._kp_layout.addWidget(empty_w)
        self._kp_layout.addStretch()
        kp_scroll.setWidget(self._kp_container)
        ll.addWidget(kp_scroll, 1)

        # 右栏
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 0, 0, 0)
        rl.setSpacing(16)

        rh = QHBoxLayout()
        rh.addWidget(SectionHeader("课堂探究任务书"))
        rh.addStretch()

        self._export_docx_btn = QPushButton("导出任务书 DOCX")
        self._export_docx_btn.setStyleSheet(SECONDARY_BTN)
        self._export_docx_btn.setEnabled(False)
        self._export_docx_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._export_docx_btn.setIcon(qta.icon("ri.file-word-line", color=TEXT_SEC))
            except Exception: pass
        self._export_docx_btn.clicked.connect(self._export_docx)

        self._save_btn = QPushButton("保存任务")
        self._save_btn.setStyleSheet(GREEN_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._save_btn.setIcon(qta.icon("ri.save-line", color="white"))
            except Exception: pass
        self._save_btn.clicked.connect(self._save_tasks)

        rh.addWidget(self._export_docx_btn)
        rh.addSpacing(8)
        rh.addWidget(self._save_btn)
        rl.addLayout(rh)

        task_scroll = QScrollArea()
        task_scroll.setWidgetResizable(True)
        task_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                border-radius: {RADIUS_LG}px;
                background: {BG_CARD};
            }}
        """)
        self._task_container = QWidget()
        self._task_container.setStyleSheet(f"background: {BG_CARD};")
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(18, 18, 18, 18)
        self._task_layout.setSpacing(14)

        # 任务空态
        task_empty_w = QWidget()
        task_empty_w.setStyleSheet("background: transparent;")
        tev = QVBoxLayout(task_empty_w)
        tev.setAlignment(Qt.AlignCenter)
        tev.setSpacing(10)
        try:
            chart_svg = make_svg_widget(ILLUSTRATION_CHART, 110, 70)
            tev.addWidget(chart_svg, alignment=Qt.AlignCenter)
        except Exception:
            pass
        self._task_empty = QLabel("生成任务后将展示在此\n每个任务包含探究问题、交互要求和成果说明")
        self._task_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent; line-height: 160%;")
        self._task_empty.setAlignment(Qt.AlignCenter)
        tev.addWidget(self._task_empty)
        self._task_empty_widget = task_empty_w
        self._task_layout.addWidget(task_empty_w)
        self._task_layout.addStretch()
        task_scroll.setWidget(self._task_container)
        rl.addWidget(task_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 600])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _build_upload_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1.5px dashed {BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(card, blur=10, offset_y=2)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        # 文件提示
        file_info = QHBoxLayout()
        self._file_icon_lbl = QLabel("📄")
        self._file_icon_lbl.setStyleSheet(f"font-size: 20px; background: transparent;")
        self._file_label = QLabel("请选择 PPT / PDF / DOCX / TXT 课程材料")
        self._file_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._file_label.setWordWrap(True)
        file_info.addWidget(self._file_icon_lbl)
        file_info.addWidget(self._file_label, 1)
        lay.addLayout(file_info)

        # 文件选择 + 章节标题
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        browse_btn = QPushButton("选择文件")
        browse_btn.setStyleSheet(GHOST_BTN)
        browse_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: browse_btn.setIcon(qta.icon("ri.folder-open-line", color=TEXT_SEC))
            except Exception: pass
        browse_btn.clicked.connect(self._choose_file)

        self._chapter_input = QLineEdit()
        self._chapter_input.setPlaceholderText("章节标题（选择文件后自动识别，可手动修改）")
        self._chapter_input.setStyleSheet(INPUT_STYLE)
        row1.addWidget(browse_btn)
        row1.addWidget(self._chapter_input, 1)
        lay.addLayout(row1)

        # 操作按钮
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self._extract_btn = QPushButton("仅提取知识点")
        self._extract_btn.setStyleSheet(SECONDARY_BTN)
        self._extract_btn.setEnabled(False)
        self._extract_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._extract_btn.setIcon(qta.icon("ri.search-eye-line", color=TEXT_SEC))
            except Exception: pass
        self._extract_btn.clicked.connect(self._extract_knowledge)

        self._gen_btn = QPushButton("一键提取并生成任务 ✨")
        self._gen_btn.setStyleSheet(PRIMARY_BTN)
        self._gen_btn.setEnabled(False)
        self._gen_btn.setCursor(Qt.PointingHandCursor)
        self._gen_btn.clicked.connect(self._extract_and_generate)

        row2.addWidget(self._extract_btn)
        row2.addWidget(self._gen_btn, 1)
        lay.addLayout(row2)
        return card

    # ── 文件选择 ──────────────────────────────────────────────────────────────
    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择课程材料", "",
            "课程材料 (*.pptx *.ppt *.pdf *.docx *.txt *.md)"
        )
        if path:
            self._file_path = path
            name = os.path.basename(path)
            self._file_label.setText(f"已选择：{name}")
            self._file_label.setStyleSheet(f"color: {SUCCESS}; font-size: 12px; font-weight: 600; background: transparent;")
            self._extract_btn.setEnabled(True)
            self._gen_btn.setEnabled(True)
            guessed = _guess_chapter_title(path)
            if guessed and not self._chapter_input.text().strip():
                self._chapter_input.setText(guessed)

    # ── 仅提取知识点 ──────────────────────────────────────────────────────────
    def _extract_knowledge(self):
        if not self._file_path: return
        chapter_title = self._chapter_input.text().strip() or _guess_chapter_title(self._file_path)
        self._show_loading("正在解析课件并提取知识点…")
        self._extract_btn.setEnabled(False)
        self._gen_btn.setEnabled(False)

        def do():
            text = doc_parser.parse_file(self._file_path)
            return task_generator.extract_knowledge(doc_parser.truncate_text(text), chapter_title)

        self._worker = Worker(do)
        self._worker.finished.connect(lambda k: self._on_knowledge_done(k))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_knowledge_done(self, knowledge):
        self._knowledge = knowledge
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(True)
        self._render_knowledge(knowledge)

    # ── 一键提取+生成 ─────────────────────────────────────────────────────────
    def _extract_and_generate(self):
        if not self._file_path: return
        chapter_title = self._chapter_input.text().strip() or _guess_chapter_title(self._file_path)
        self._show_loading("正在解析课件、提取知识点并生成探究任务…")
        self._extract_btn.setEnabled(False)
        self._gen_btn.setEnabled(False)

        def do():
            text = doc_parser.parse_file(self._file_path)
            knowledge = task_generator.extract_knowledge(doc_parser.truncate_text(text), chapter_title)
            tasks = task_generator.generate_tasks(knowledge)
            return knowledge, tasks

        self._worker = Worker(do)
        self._worker.finished.connect(lambda r: self._on_both_done(*r))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_both_done(self, knowledge, tasks):
        self._knowledge = knowledge
        self._tasks = tasks
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._export_docx_btn.setEnabled(HAS_FORMATTER)
        self._render_knowledge(knowledge)
        self._render_tasks(tasks)

    # ── 保存 ──────────────────────────────────────────────────────────────────
    def _save_tasks(self):
        if not self._tasks or not self._knowledge: return
        cid = data_store.save_course(self._knowledge)
        data_store.save_tasks(cid, self._tasks)
        session_state.register_chapter(cid)
        QMessageBox.information(
            self, "保存成功",
            f"✅ 章节「{self._knowledge.get('chapter_title', '')}」及 "
            f"{len(self._tasks.get('tasks', []))} 个任务已保存到本地。"
        )
        main_win = self.window()
        if hasattr(main_win, '_switch_page') and hasattr(main_win, '_pages'):
            main_win._switch_page(1)
            main_win._pages[1].jump_to_chapter(cid)

    # ── 导出 DOCX ─────────────────────────────────────────────────────────────
    def _export_docx(self):
        if not self._tasks or not HAS_FORMATTER:
            QMessageBox.warning(self, "提示", "请先生成任务，或安装 python-docx。")
            return
        chapter_title = self._tasks.get("chapter_title", "课堂探究任务")
        path, _ = QFileDialog.getSaveFileName(self, "导出任务书", f"{chapter_title}.docx", "Word 文档 (*.docx)")
        if not path: return
        if not path.lower().endswith(".docx"): path += ".docx"
        try:
            export_task_sheet_docx(self._tasks, path)
            QMessageBox.information(self, "导出成功", f"任务书已导出到：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    # ── 渲染知识点 ────────────────────────────────────────────────────────────
    def _render_knowledge(self, knowledge: dict):
        self._clear_layout(self._kp_layout, self._kp_empty_widget)
        self._kp_empty_widget.hide()
        for kp in knowledge.get("knowledge_points", []):
            card = self._make_kp_card(kp)
            self._kp_layout.insertWidget(self._kp_layout.count() - 1, card)

    def _make_kp_card(self, kp: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_INPUT};
                border: none;
                border-radius: {RADIUS}px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(5)

        row = QHBoxLayout()
        name = QLabel(kp.get("name", ""))
        name.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 12px; background: transparent;")
        name.setWordWrap(True)
        row.addWidget(name, 1)
        row.addWidget(TagBadge(kp.get("importance", ""), kp.get("importance", "default")))
        row.addSpacing(4)
        row.addWidget(TagBadge(kp.get("type", ""), kp.get("type", "default")))
        lay.addLayout(row)

        desc = QLabel(kp.get("description", ""))
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
        desc.setWordWrap(True)
        lay.addWidget(desc)
        return card

    # ── 渲染任务 ──────────────────────────────────────────────────────────────
    def _render_tasks(self, tasks: dict):
        self._clear_layout(self._task_layout, self._task_empty_widget)
        self._task_empty_widget.hide()
        for idx, task in enumerate(tasks.get("tasks", []), 1):
            card = self._make_task_card(task, idx)
            self._task_layout.insertWidget(self._task_layout.count() - 1, card)

    def _make_task_card(self, task: dict, idx: int) -> QFrame:
        diff_colors = {"基础": SUCCESS, "中等": WARNING, "挑战": DANGER}
        diff_color = diff_colors.get(task.get("difficulty", "中等"), WARNING)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: none;
                border-left: 4px solid {diff_color};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(card, blur=8, offset_y=2)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        # 标题行
        row1 = QHBoxLayout()
        num_lbl = QLabel(f"任务 {idx:02d}")
        num_lbl.setStyleSheet(f"color: {diff_color}; font-size: 11px; font-weight: 800; background: transparent;")
        row1.addWidget(num_lbl)
        row1.addSpacing(8)
        title = QLabel(task.get("title", ""))
        title.setStyleSheet(f"color: {TEXT_H1}; font-weight: 700; font-size: 13px; background: transparent;")
        title.setWordWrap(True)
        row1.addWidget(title, 1)
        row1.addWidget(TagBadge(task.get("difficulty", ""), "default"))
        lay.addLayout(row1)

        lay.addWidget(HDivider())

        # 描述
        desc = QLabel(task.get("description", ""))
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%; background: transparent;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # 成果要求（橙色高亮）
        out = task.get("output_requirements", {})
        specific = out.get("specific_output", "").strip()
        if not specific:
            req_list = out.get("required_outputs", [])
            if req_list:
                specific = "提交：" + "、".join(req_list)
        if specific:
            out_card = QFrame()
            out_card.setStyleSheet(f"""
                QFrame {{
                    background: {ORANGE_LIGHT};
                    border-left: 3px solid {ORANGE_PRI};
                    border-radius: {RADIUS_SM}px;
                    padding: 2px;
                }}
            """)
            oc_lay = QHBoxLayout(out_card)
            oc_lay.setContentsMargins(10, 6, 10, 6)
            out_lbl = QLabel(f"📋 {specific}")
            out_lbl.setStyleSheet(f"color: {ORANGE_DARK}; font-size: 11px; font-weight: 600; background: transparent;")
            out_lbl.setWordWrap(True)
            oc_lay.addWidget(out_lbl)
            lay.addWidget(out_card)

        # 底部信息
        req = task.get("interaction_requirements", {})
        bottom = QHBoxLayout()
        if req.get("need_socratic_dialogue", False):
            s_badge = QLabel("🎓 苏格拉底式")
            s_badge.setStyleSheet(f"color: {INFO}; background: #EEF4FB; border-radius: 4px; "
                                   f"padding: 2px 8px; font-size: 10px; font-weight: 700;")
            bottom.addWidget(s_badge)
            bottom.addSpacing(6)
        rounds_lbl = QLabel(f"≥ {req.get('min_rounds', 15)} 轮交互")
        rounds_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        bottom.addWidget(rounds_lbl)
        types = req.get("required_types", [])
        if types:
            bottom.addSpacing(8)
            types_lbl = QLabel(" · ".join(types))
            types_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
            types_lbl.setWordWrap(True)
            bottom.addWidget(types_lbl, 1)
        bottom.addStretch()
        lay.addLayout(bottom)
        return card

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _clear_layout(self, layout, keep_widget=None):
        items_to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and item.widget() is not keep_widget:
                items_to_remove.append(item.widget())
        for w in items_to_remove:
            layout.removeWidget(w)
            w.deleteLater()

    def _show_loading(self, text: str):
        self._loading.set_text(text)
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

    def _on_error(self, msg: str):
        self._loading.hide()
        self._extract_btn.setEnabled(bool(self._file_path))
        self._gen_btn.setEnabled(bool(self._file_path))
        QMessageBox.critical(self, "操作失败", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())
