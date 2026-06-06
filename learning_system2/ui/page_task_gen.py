"""
Page 1: Course Import & Task Generation
简洁学术风 — 减少边框视觉噪音，任务卡参考学情统计的轻量卡片风格
"""

import hashlib
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QScrollArea, QFrame, QMessageBox, QSplitter, QLineEdit,
    QInputDialog
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


def _content_fingerprint(text: str) -> str:
    normalized = "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_name(text: str) -> str:
    import re
    stem = os.path.splitext(os.path.basename(text or ""))[0]
    stem = re.sub(r"\s+", "", stem)
    stem = re.sub(r"[()（）【】\[\]_\-·.。]", "", stem)
    return stem.lower()


class TaskGenPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._knowledge = None
        self._tasks = None
        self._worker = None
        self._file_path = None
        self._source_meta = {}
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # 页头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 20)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        page_title = QLabel("课件导入 · 任务生成")
        page_title.setStyleSheet(f"color: {TEXT_H1}; font-size: 19px; font-weight: 800; background: transparent;")
        page_sub = QLabel("上传课程材料，自动提取知识点并生成探究式课堂任务")
        page_sub.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(page_title)
        title_col.addWidget(page_sub)
        hdr.addLayout(title_col)
        hdr.addStretch()
        root.addLayout(hdr)

        # 主体分栏
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {BORDER}; }}
            QSplitter::handle:hover {{ background: {GREEN_MUTED}; }}
        """)

        # ── 左栏 ──────────────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(240)
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 14, 0)
        ll.setSpacing(16)

        ll.addWidget(self._build_upload_card())

        ll.addWidget(SectionHeader("知识点预览"))
        kp_scroll = QScrollArea()
        kp_scroll.setWidgetResizable(True)
        kp_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {BG_CARD};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        self._kp_container = QWidget()
        self._kp_container.setStyleSheet(f"background: {BG_CARD};")
        self._kp_layout = QVBoxLayout(self._kp_container)
        self._kp_layout.setContentsMargins(14, 14, 14, 14)
        self._kp_layout.setSpacing(8)

        self._kp_empty = QLabel("上传课件后自动抽取核心知识点")
        self._kp_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._kp_empty.setAlignment(Qt.AlignCenter)
        self._kp_layout.addWidget(self._kp_empty)
        self._kp_layout.addStretch()
        kp_scroll.setWidget(self._kp_container)
        ll.addWidget(kp_scroll, 1)

        # ── 右栏 ──────────────────────────────────────────────────────────────
        right = QWidget()
        right.setMinimumWidth(320)
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 0, 0, 0)
        rl.setSpacing(14)

        rh = QHBoxLayout()
        rh.addWidget(SectionHeader("课堂探究任务书"))
        rh.addStretch()

        self._export_docx_btn = QPushButton("导出 DOCX")
        self._export_docx_btn.setStyleSheet(SECONDARY_BTN)
        self._export_docx_btn.setEnabled(False)
        self._export_docx_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._export_docx_btn.setIcon(qta.icon("ri.file-word-line", color=TEXT_SEC))
            except Exception:
                pass
        self._export_docx_btn.clicked.connect(self._export_docx)

        self._save_btn = QPushButton("保存任务")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._save_btn.setIcon(qta.icon("ri.save-line", color="white"))
            except Exception:
                pass
        self._save_btn.clicked.connect(self._save_tasks)

        rh.addWidget(self._export_docx_btn)
        rh.addSpacing(8)
        rh.addWidget(self._save_btn)
        rl.addLayout(rh)

        task_scroll = QScrollArea()
        task_scroll.setWidgetResizable(True)
        task_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._task_container = QWidget()
        self._task_container.setStyleSheet("background: transparent;")
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(0, 0, 0, 0)
        self._task_layout.setSpacing(10)

        self._task_empty = QLabel("生成任务后将展示在此\n每个任务包含探究问题、交互要求和成果说明")
        self._task_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent; line-height: 160%;")
        self._task_empty.setAlignment(Qt.AlignCenter)
        self._task_layout.addWidget(self._task_empty)
        self._task_layout.addStretch()
        task_scroll.setWidget(self._task_container)
        rl.addWidget(task_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _build_upload_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1.5px solid {BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(card, blur=12, offset_y=3)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        file_info = QHBoxLayout()
        self._file_icon_lbl = QLabel("📄")
        self._file_icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        self._file_label = QLabel("请选择 PPT / PDF / DOCX / TXT 课程材料")
        self._file_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._file_label.setWordWrap(True)
        file_info.addWidget(self._file_icon_lbl)
        file_info.addWidget(self._file_label, 1)
        lay.addLayout(file_info)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        browse_btn = QPushButton("选择文件")
        browse_btn.setStyleSheet(GHOST_BTN)
        browse_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                browse_btn.setIcon(qta.icon("ri.folder-open-line", color=TEXT_SEC))
            except Exception:
                pass
        browse_btn.clicked.connect(self._choose_file)

        self._chapter_input = QLineEdit()
        self._chapter_input.setPlaceholderText("章节标题（选文件后自动识别）")
        self._chapter_input.setStyleSheet(INPUT_STYLE)
        row1.addWidget(browse_btn)
        row1.addWidget(self._chapter_input, 1)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self._extract_btn = QPushButton("仅提取知识点")
        self._extract_btn.setStyleSheet(SECONDARY_BTN)
        self._extract_btn.setEnabled(False)
        self._extract_btn.setCursor(Qt.PointingHandCursor)
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

    def _extract_knowledge(self):
        if not self._file_path:
            return
        chapter_title = self._chapter_input.text().strip() or _guess_chapter_title(self._file_path)
        self._show_loading("正在解析课件并提取知识点…")
        self._extract_btn.setEnabled(False)
        self._gen_btn.setEnabled(False)

        def do():
            text = doc_parser.parse_file(self._file_path)
            knowledge = task_generator.extract_knowledge(doc_parser.truncate_text(text), chapter_title)
            return knowledge, {
                "source_file_name": os.path.basename(self._file_path),
                "source_content_hash": _content_fingerprint(text),
            }

        self._worker = Worker(do)
        self._worker.finished.connect(lambda r: self._on_knowledge_done(*r))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_knowledge_done(self, knowledge, source_meta=None):
        self._source_meta = source_meta or {}
        knowledge.update(self._source_meta)
        self._knowledge = knowledge
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(True)
        self._render_knowledge(knowledge)

    def _extract_and_generate(self):
        if not self._file_path:
            return
        chapter_title = self._chapter_input.text().strip() or _guess_chapter_title(self._file_path)
        self._show_loading("正在解析课件、提取知识点并生成探究任务…")
        self._extract_btn.setEnabled(False)
        self._gen_btn.setEnabled(False)

        def do():
            text = doc_parser.parse_file(self._file_path)
            knowledge = task_generator.extract_knowledge(doc_parser.truncate_text(text), chapter_title)
            tasks = task_generator.generate_tasks(knowledge)
            return knowledge, tasks, {
                "source_file_name": os.path.basename(self._file_path),
                "source_content_hash": _content_fingerprint(text),
            }

        self._worker = Worker(do)
        self._worker.finished.connect(lambda r: self._on_both_done(*r))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_both_done(self, knowledge, tasks, source_meta=None):
        self._source_meta = source_meta or {}
        knowledge.update(self._source_meta)
        tasks.update(self._source_meta)
        self._knowledge = knowledge
        self._tasks = tasks
        self._loading.hide()
        self._extract_btn.setEnabled(True)
        self._gen_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._export_docx_btn.setEnabled(HAS_FORMATTER)
        self._render_knowledge(knowledge)
        self._render_tasks(tasks)

    def _same_title_courses(self, title: str):
        normalized = (title or "").strip()
        return [
            c for c in data_store.list_courses()
            if (c.get("chapter_title") or "").strip() == normalized
        ]

    def _find_existing_course(self, title: str, source_meta: dict):
        courses = data_store.list_courses()
        current_hash = source_meta.get("source_content_hash", "")
        current_file = source_meta.get("source_file_name", "")
        title_keys = {
            _normalize_name(title),
            _normalize_name(self._chapter_input.text()),
            _normalize_name(current_file),
        }
        title_keys.discard("")

        if current_hash:
            for course in courses:
                if course.get("source_content_hash") == current_hash:
                    return course, "same_content"

        for course in courses:
            course_keys = {
                _normalize_name(course.get("chapter_title", "")),
                _normalize_name(course.get("source_file_name", "")),
            }
            if title_keys & course_keys:
                return course, "same_name"

        return None, ""

    def _unique_chapter_title(self, base_title: str) -> str:
        existing_titles = {
            (c.get("chapter_title") or "").strip()
            for c in data_store.list_courses()
        }
        base = (base_title or "未命名章节").strip()
        if base not in existing_titles:
            return base
        idx = 2
        while f"{base}_{idx}" in existing_titles:
            idx += 1
        return f"{base}_{idx}"

    def _resolve_save_target(self):
        title = (self._knowledge.get("chapter_title") or self._chapter_input.text() or "").strip()
        existing, match_kind = self._find_existing_course(title, self._source_meta)
        if not existing:
            return None, title, "new"

        existing_title = (existing.get("chapter_title") or title).strip()
        if match_kind == "same_content":
            return existing.get("chapter_id"), existing_title, "same"

        msg = QMessageBox(self)
        msg.setWindowTitle("同名课件已存在")
        msg.setText(f"课件「{existing_title}」已经上传过。")
        msg.setInformativeText("请选择覆盖原章节，或重命名为一个新的章节。")
        overwrite_btn = msg.addButton("覆盖原章节", QMessageBox.AcceptRole)
        rename_btn = msg.addButton("重命名保存", QMessageBox.ActionRole)
        msg.addButton("取消", QMessageBox.RejectRole)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == overwrite_btn:
            return existing.get("chapter_id"), title, "overwrite"
        if clicked != rename_btn:
            return None, "", "cancel"

        suggested = self._unique_chapter_title(title)
        new_title, ok = QInputDialog.getText(
            self,
            "重命名章节",
            "请输入新的章节名称：",
            text=suggested,
        )
        if not ok:
            return None, "", "cancel"
        new_title = (new_title or "").strip()
        if not new_title:
            QMessageBox.warning(self, "提示", "章节名称不能为空。")
            return None, "", "cancel"
        if self._same_title_courses(new_title):
            new_title = self._unique_chapter_title(new_title)
        return None, new_title, "rename"

    def _save_tasks(self):
        if not self._tasks or not self._knowledge:
            return
        cid, chapter_title, action = self._resolve_save_target()
        if action == "cancel":
            return
        if chapter_title:
            self._knowledge["chapter_title"] = chapter_title
            self._tasks["chapter_title"] = chapter_title
            self._chapter_input.setText(chapter_title)
        self._knowledge.update(self._source_meta)
        self._tasks.update(self._source_meta)
        if cid:
            self._knowledge["chapter_id"] = cid
            self._tasks["chapter_id"] = cid
        cid = data_store.save_course(self._knowledge)
        data_store.save_tasks(cid, self._tasks)
        session_state.register_chapter(cid)
        if action == "same":
            save_msg = "检测到同名且内容相同，已复用原章节并更新任务。"
        elif action == "overwrite":
            save_msg = "已覆盖原同名章节。"
        elif action == "rename":
            save_msg = "已重命名为新章节保存。"
        else:
            save_msg = "已保存为新章节。"
        QMessageBox.information(
            self, "保存成功",
            f"章节「{self._knowledge.get('chapter_title', '')}」及 "
            f"{len(self._tasks.get('tasks', []))} 个任务已保存。\n{save_msg}"
        )
        main_win = self.window()
        if hasattr(main_win, '_switch_page') and hasattr(main_win, '_pages'):
            main_win._switch_page(1)
            main_win._pages[1].jump_to_chapter(cid)

    def _export_docx(self):
        if not self._tasks or not HAS_FORMATTER:
            QMessageBox.warning(self, "提示", "请先生成任务，或安装 python-docx。")
            return
        chapter_title = self._tasks.get("chapter_title", "课堂探究任务")
        path, _ = QFileDialog.getSaveFileName(self, "导出任务书", f"{chapter_title}.docx", "Word (*.docx)")
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            export_task_sheet_docx(self._tasks, path)
            QMessageBox.information(self, "导出成功", f"任务书已导出到：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    # ── 渲染知识点（极简标签风格）──────────────────────────────────────────────
    def _render_knowledge(self, knowledge: dict):
        self._clear_layout(self._kp_layout)
        for kp in knowledge.get("knowledge_points", []):
            card = self._make_kp_card(kp)
            self._kp_layout.insertWidget(self._kp_layout.count() - 1, card)

    def _make_kp_card(self, kp: dict) -> QWidget:
        """知识点行：无边框，仅底部分隔线，如学情统计表格行"""
        w = QWidget()
        w.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border-bottom: 1px solid {BORDER_LIGHT};
            }}
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(4)

        row = QHBoxLayout()
        name = QLabel(kp.get("name", ""))
        name.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px; background: transparent;")
        name.setWordWrap(True)
        row.addWidget(name, 1)
        row.addWidget(TagBadge(kp.get("importance", ""), kp.get("importance", "default")))
        row.addSpacing(4)
        row.addWidget(TagBadge(kp.get("type", ""), kp.get("type", "default")))
        lay.addLayout(row)

        desc = kp.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
            desc_lbl.setWordWrap(True)
            lay.addWidget(desc_lbl)
        return w

    # ── 渲染任务（简洁卡片：阴影+左色条，无繁杂边框）──────────────────────────
    def _render_tasks(self, tasks: dict):
        self._clear_layout(self._task_layout)

        # 任务说明（纯文字，无边框）
        instr = tasks.get("task_instruction", "")
        if instr:
            lbl = QLabel(instr[:180] + ("…" if len(instr) > 180 else ""))
            lbl.setStyleSheet(
                f"color: {TEXT_SEC}; font-size: 11px; line-height: 160%;"
                f" padding: 0 2px 8px 2px;"
            )
            lbl.setWordWrap(True)
            self._task_layout.insertWidget(self._task_layout.count() - 1, lbl)

        for idx, task in enumerate(tasks.get("tasks", []), 1):
            card = self._make_task_card(task, idx)
            self._task_layout.insertWidget(self._task_layout.count() - 1, card)

    def _make_task_card(self, task: dict, idx: int) -> QFrame:
        diff_colors = {"基础": SUCCESS, "中等": WARNING, "挑战": DANGER}
        diff_color = diff_colors.get(task.get("difficulty", "中等"), WARNING)

        card = QFrame()
        card.setObjectName("generatedTaskCard")
        card.setStyleSheet(f"""
            QFrame#generatedTaskCard {{
                background: {BG_CARD};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(9)

        # 标题行
        row1 = QHBoxLayout()
        num_lbl = QLabel(f"任务 {idx:02d}")
        num_lbl.setStyleSheet(f"""
            color: {diff_color};
            background: transparent;
            font-size: 11px;
            font-weight: 900;
        """)
        num_lbl.setFixedWidth(52)
        title = QLabel(task.get("title", ""))
        title.setStyleSheet(f"color: {TEXT_H1}; font-weight: 800; font-size: 13px; background: transparent;")
        title.setWordWrap(True)
        row1.addWidget(num_lbl)
        row1.addWidget(title, 1)
        diff_tag = TagBadge(task.get("difficulty", ""), "default")
        row1.addWidget(diff_tag)
        if task.get("interaction_requirements", {}).get("need_socratic_dialogue"):
            s_tag = QLabel("苏格拉底")
            s_tag.setStyleSheet(f"""
                color: {INFO}; background: #E8F4FB;
                border-radius: 5px; padding: 2px 7px;
                font-size: 10px; font-weight: 700;
            """)
            row1.addWidget(s_tag)
        lay.addLayout(row1)

        # 描述（不超过 3 行，保持紧凑）
        desc = task.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 155%; background: transparent;")
            desc_lbl.setWordWrap(True)
            lay.addWidget(desc_lbl)

        # 成果要求（纯文字，主色小图标前缀）
        out = task.get("output_requirements", {})
        specific = out.get("specific_output", "").strip()
        if not specific:
            req_list = out.get("required_outputs", [])
            if req_list:
                specific = "、".join(req_list)
        if specific:
            out_lbl = QLabel(specific)
            out_lbl.setStyleSheet(
                f"color: {GREEN_DARK}; font-size: 11px; font-weight: 600;"
                f" background: {GREEN_LIGHT}; border-radius: 7px;"
                f" padding: 7px 10px;"
            )
            out_lbl.setWordWrap(True)
            lay.addWidget(out_lbl)

        # 底部 meta 信息（无边框，纯文字）
        req = task.get("interaction_requirements", {})
        types = req.get("required_types", [])
        meta_parts = [f"≥ {req.get('min_rounds', 15)} 轮"]
        if types:
            meta_parts.append(" · ".join(types[:4]))
        meta_lbl = QLabel("  |  ".join(meta_parts))
        meta_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(meta_lbl)

        return card

    def _clear_layout(self, layout):
        items_to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
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
