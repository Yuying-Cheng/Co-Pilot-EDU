"""
Page 4: Task Browser & Editor with Export — Swiss minimalist
"""

import json, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QLineEdit, QSpinBox,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import SectionHeader, TagBadge, HDivider
import data_store

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class TaskEditorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_chapter_id = None
        self._current_tasks = None
        self._current_task_idx = None
        self._courses = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("任务管理 · 编辑")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(GHOST_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: refresh_btn.setIcon(qta.icon("ri.refresh-line", color=TEXT_SEC))
            except: pass
        refresh_btn.clicked.connect(self._load_courses)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ── Left: lists ───────────────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(260)
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 20, 0)
        ll.setSpacing(16)

        ll.addWidget(SectionHeader("章节"))
        self._course_list = self._make_list()
        self._course_list.currentRowChanged.connect(self._on_course_selected)
        ll.addWidget(self._course_list, 1)

        ll.addWidget(SectionHeader("任务"))
        self._task_list = self._make_list()
        self._task_list.currentRowChanged.connect(self._on_task_selected)
        ll.addWidget(self._task_list, 1)

        # ── Right: editor ─────────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 0, 0, 0)
        rl.setSpacing(16)

        rl.addWidget(SectionHeader("任务详情"))
        self._editor_scroll = self._build_editor()
        rl.addWidget(self._editor_scroll, 1)

        btn_row = QHBoxLayout()
        self._export_btn = QPushButton("导出 JSON")
        self._export_btn.setStyleSheet(GHOST_BTN)
        self._export_btn.setEnabled(False)
        self._export_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._export_btn.setIcon(qta.icon("ri.download-line", color=TEXT_SEC))
            except: pass
        self._export_btn.clicked.connect(self._export_task)

        # ← 在这里插入 docx_btn
        self._docx_btn = QPushButton("导出任务书 DOCX")
        self._docx_btn.setStyleSheet(SECONDARY_BTN)
        self._docx_btn.setEnabled(False)
        self._docx_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._docx_btn.setIcon(qta.icon("ri.file-word-line", color=TEXT_PRI))
            except: pass
        self._docx_btn.clicked.connect(self._export_task_sheet_docx)

        self._save_btn = QPushButton("保存修改")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._save_btn.setIcon(qta.icon("ri.save-line", color="white"))
            except: pass
        self._save_btn.clicked.connect(self._save_edit)

        btn_row.addWidget(self._export_btn)
        btn_row.addWidget(self._docx_btn)   # ← 新增
        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        rl.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        root.addWidget(splitter, 1)

        self._load_courses()

    def _make_list(self) -> QListWidget:
        lw = QListWidget()
        lw.setStyleSheet(f"""
            QListWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: {RADIUS}px;
                color: {TEXT_PRI};
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {BORDER};
                font-size: 12px;
            }}
            QListWidget::item:last {{ border-bottom: none; }}
            QListWidget::item:selected {{
                background: {BG_DARK};
                color: {TEXT_PRI};
            }}
            QListWidget::item:hover:!selected {{ background: {BG_DARK}; }}
        """)
        return lw

    def _build_editor(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        container.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        def lbl(text):
            l = QLabel(text.upper())
            l.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
            return l

        lay.addWidget(lbl("任务标题"))
        self._edit_title = QLineEdit()
        self._edit_title.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._edit_title)

        row_w = QWidget()
        row_w.setStyleSheet("background: transparent;")
        row_lay = QHBoxLayout(row_w)
        row_lay.setContentsMargins(0,0,0,0)
        row_lay.setSpacing(10)
        lay.addWidget(lbl("类型  /  难度"))

        self._edit_type = QComboBox()
        self._edit_type.addItems(["知识整理","算法对比","复杂度分析","苏格拉底引导","批判思考"])
        self._edit_type.setStyleSheet(INPUT_STYLE)

        self._edit_diff = QComboBox()
        self._edit_diff.addItems(["基础","中等","挑战"])
        self._edit_diff.setStyleSheet(INPUT_STYLE)

        row_lay.addWidget(self._edit_type, 1)
        row_lay.addWidget(self._edit_diff)
        lay.addWidget(row_w)

        lay.addWidget(lbl("任务描述"))
        self._edit_desc = QTextEdit()
        self._edit_desc.setStyleSheet(INPUT_STYLE)
        self._edit_desc.setFixedHeight(110)
        lay.addWidget(self._edit_desc)

        lay.addWidget(HDivider())
        lay.addWidget(lbl("交互要求"))

        req_w = QWidget()
        req_w.setStyleSheet("background: transparent;")
        req_lay = QHBoxLayout(req_w)
        req_lay.setContentsMargins(0,0,0,0)
        req_lay.setSpacing(20)

        rl_lbl = QLabel("最少轮次")
        rl_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        self._edit_rounds = QSpinBox()
        self._edit_rounds.setRange(1, 50)
        self._edit_rounds.setValue(10)
        self._edit_rounds.setStyleSheet(f"""
            QSpinBox {{ background: {BG_INPUT}; color: {TEXT_PRI};
                border: 1px solid {BORDER}; border-radius: {RADIUS}px;
                padding: 6px 10px; font-size: 12px; }}
        """)
        self._edit_rounds.setFixedWidth(72)

        self._edit_followup = QCheckBox("必须追问")
        self._edit_followup.setStyleSheet(f"color: {TEXT_SEC}; background: transparent; font-size: 12px;")
        self._edit_questioning = QCheckBox("必须质疑")
        self._edit_questioning.setStyleSheet(f"color: {TEXT_SEC}; background: transparent; font-size: 12px;")

        req_lay.addWidget(rl_lbl)
        req_lay.addWidget(self._edit_rounds)
        req_lay.addWidget(self._edit_followup)
        req_lay.addWidget(self._edit_questioning)
        req_lay.addStretch()
        lay.addWidget(req_w)

        lay.addWidget(lbl("要求的交互方式"))
        types_w = QWidget()
        types_w.setStyleSheet("background: transparent;")
        types_lay = QHBoxLayout(types_w)
        types_lay.setContentsMargins(0,0,0,0)
        types_lay.setSpacing(8)
        self._type_checks = {}
        for t in data_store.INTERACTION_TYPES:
            cb = QCheckBox(t)
            cb.setStyleSheet(f"color: {TEXT_SEC}; background: transparent; font-size: 11px;")
            self._type_checks[t] = cb
            types_lay.addWidget(cb)
        types_lay.addStretch()
        lay.addWidget(types_w)

        lay.addWidget(HDivider())
        lay.addWidget(lbl("成果要求"))
        self._edit_output = QTextEdit()
        self._edit_output.setStyleSheet(INPUT_STYLE)
        self._edit_output.setFixedHeight(72)
        self._edit_output.setPlaceholderText("对成果报告的具体要求…")
        lay.addWidget(self._edit_output)
        lay.addStretch()

        scroll.setWidget(container)
        return scroll

    def _load_courses(self):
        self._course_list.clear()
        self._courses = data_store.list_courses()
        if not self._courses:
            item = QListWidgetItem("暂无章节")
            item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(TEXT_DIM))
            self._course_list.addItem(item)
            return
        for c in self._courses:
            self._course_list.addItem(c.get("chapter_title", c.get("chapter_id","")))

    def _on_course_selected(self, idx):
        if idx < 0 or idx >= len(self._courses): return
        cid = self._courses[idx].get("chapter_id")
        self._current_chapter_id = cid
        self._current_tasks = data_store.load_tasks(cid)
        self._task_list.clear()
        if self._current_tasks:
            for t in self._current_tasks.get("tasks", []):
                self._task_list.addItem(t.get("title",""))

    def _on_task_selected(self, idx):
        if not self._current_tasks or idx < 0: return
        tasks = self._current_tasks.get("tasks", [])
        if idx >= len(tasks): return
        self._current_task_idx = idx
        self._fill_editor(tasks[idx])
        self._save_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._docx_btn.setEnabled(True)

    def _fill_editor(self, task: dict):
        self._edit_title.setText(task.get("title", ""))
        self._edit_type.setCurrentText(task.get("task_type", "知识整理"))
        self._edit_diff.setCurrentText(task.get("difficulty", "中等"))
        self._edit_desc.setPlainText(task.get("description", ""))
        req = task.get("interaction_requirements", {})
        self._edit_rounds.setValue(req.get("min_rounds", 15))
        self._edit_followup.setChecked(req.get("must_include_follow_up", True))
        self._edit_questioning.setChecked(req.get("must_include_questioning", True))
        required_types = req.get("required_types", [])
        for t, cb in self._type_checks.items():
            cb.setChecked(t in required_types)

        # ── 修复：优先显示 specific_output，其次拼接 required_outputs ──
        out = task.get("output_requirements", {})
        specific = out.get("specific_output", "").strip()
        if specific:
            self._edit_output.setPlainText(specific)
        else:
            required = out.get("required_outputs", [])
            word_limit = out.get("word_limit", "500-800字")
            if required:
                self._edit_output.setPlainText(
                    f"字数要求：{word_limit}\n成果：{'、'.join(required)}"
                )
            else:
                self._edit_output.setPlainText(f"字数要求：{word_limit}")

    def _save_edit(self):
        if not self._current_tasks or self._current_task_idx is None: return
        task = self._current_tasks["tasks"][self._current_task_idx]
        task["title"]     = self._edit_title.text().strip()
        task["task_type"] = self._edit_type.currentText()
        task["difficulty"]= self._edit_diff.currentText()
        task["description"]= self._edit_desc.toPlainText().strip()
        req = task.setdefault("interaction_requirements",{})
        req["min_rounds"] = self._edit_rounds.value()
        req["must_include_follow_up"]  = self._edit_followup.isChecked()
        req["must_include_questioning"]= self._edit_questioning.isChecked()
        req["required_types"] = [t for t,cb in self._type_checks.items() if cb.isChecked()]
        data_store.save_tasks(self._current_chapter_id, self._current_tasks)
        self._task_list.item(self._current_task_idx).setText(task["title"])
        QMessageBox.information(self, "已保存", f"任务「{task['title']}」已更新。")

    def _export_task(self):
        if not self._current_tasks or self._current_task_idx is None: return
        task = self._current_tasks["tasks"][self._current_task_idx]
        default_name = f"{task.get('title','task').replace(' ','_')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "导出任务", default_name, "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出到：{path}")
    
    def _export_task_sheet_docx(self):
        """导出整章任务书为 DOCX。"""
        if not self._current_tasks:
            QMessageBox.information(self, "提示", "请先选择一个章节。")
            return

        from task_formatter import export_task_sheet_docx
        default_name = f"{self._current_tasks.get('chapter_title', '课堂探究任务')}.docx"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出课堂探究任务书", default_name, "Word 文档 (*.docx)"
        )
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            export_task_sheet_docx(self._current_tasks, path)
            QMessageBox.information(self, "导出成功", f"任务书已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
    
    def jump_to_chapter(self, chapter_id: str):
        """Select a specific chapter by ID; called by TaskGenPage after saving."""
        self._load_courses()
        for i, c in enumerate(self._courses):
            if c.get("chapter_id") == chapter_id:
                self._course_list.setCurrentRow(i)
                return
        # Fallback: select first
        if self._courses:
            self._course_list.setCurrentRow(0)
    def showEvent(self, event):
        super().showEvent(event)
        self._load_courses()
        # Auto-select first (most recent after created_at sort)
        if self._courses:
            self._course_list.setCurrentRow(0)