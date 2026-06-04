"""
Page: Task Browser & Editor — Warm Academic Style
"""

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QLineEdit, QSpinBox,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import SectionHeader, SubHeader, TagBadge, HDivider, add_shadow, make_panel
import data_store
import session_state

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

INTERACTION_TYPES_LIST = ["询问", "表达见解", "审辨", "猜想", "想象", "创新", "苏格拉底回答"]


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
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)

        # 页头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 22)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        t = QLabel("任务管理 · 编辑")
        t.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        s = QLabel("查看、修改和导出已生成的课堂探究任务")
        s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(t)
        title_col.addWidget(s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(GHOST_BTN)
        refresh_btn.clicked.connect(self._load_courses)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # 左栏：章节+任务列表
        left = QWidget()
        left.setFixedWidth(280)
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 18, 0)
        ll.setSpacing(14)

        ll.addWidget(SectionHeader("章节列表"))
        self._course_list = self._make_list()
        self._course_list.currentRowChanged.connect(self._on_course_selected)
        ll.addWidget(self._course_list, 1)

        ll.addWidget(SectionHeader("任务列表"))
        self._task_list = self._make_list()
        self._task_list.currentRowChanged.connect(self._on_task_selected)
        ll.addWidget(self._task_list, 1)

        # 右栏：编辑器
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 0, 0, 0)
        rl.setSpacing(14)

        rl.addWidget(SectionHeader("任务详情编辑"))
        rl.addWidget(self._build_editor(), 1)

        # 按钮行
        btn_row = QHBoxLayout()
        self._export_json_btn = QPushButton("导出 JSON")
        self._export_json_btn.setStyleSheet(GHOST_BTN)
        self._export_json_btn.setEnabled(False)
        self._export_json_btn.clicked.connect(self._export_task)

        self._docx_btn = QPushButton("导出任务书 DOCX")
        self._docx_btn.setStyleSheet(SECONDARY_BTN)
        self._docx_btn.setEnabled(False)
        self._docx_btn.clicked.connect(self._export_task_sheet_docx)

        self._save_btn = QPushButton("修改并保存任务")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_edit)

        btn_row.addWidget(self._export_json_btn)
        btn_row.addWidget(self._docx_btn)
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
                border: none;
                border-radius: {RADIUS}px;
                color: {TEXT_PRI};
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {BORDER_LIGHT};
            }}
            QListWidget::item:selected {{
                background: {GREEN_LIGHT};
                color: {GREEN_PRI};
                font-weight: 700;
            }}
            QListWidget::item:hover:!selected {{ background: {BG_HOVER}; }}
        """)
        return lw

    def _build_editor(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: none;
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(container, blur=10, offset_y=2)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # 标题
        lay.addWidget(SubHeader("任务标题"))
        self._edit_title = QLineEdit()
        self._edit_title.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._edit_title)

        # 类型 + 难度
        row_w = QHBoxLayout()
        tc = QVBoxLayout()
        tc.addWidget(SubHeader("任务类型"))
        self._edit_type = QComboBox()
        self._edit_type.addItems([
            "知识体系整理", "概念辨析", "方法比较",
            "案例分析", "问题推理", "批判思考",
            "苏格拉底引导", "学习反思", "算法对比", "复杂度分析"
        ])
        self._edit_type.setStyleSheet(INPUT_STYLE)
        tc.addWidget(self._edit_type)

        dc = QVBoxLayout()
        dc.addWidget(SubHeader("难度"))
        self._edit_diff = QComboBox()
        self._edit_diff.addItems(["基础", "中等", "挑战"])
        self._edit_diff.setStyleSheet(INPUT_STYLE)
        dc.addWidget(self._edit_diff)

        row_w.addLayout(tc, 2)
        row_w.addSpacing(12)
        row_w.addLayout(dc, 1)
        lay.addLayout(row_w)

        # 描述
        lay.addWidget(SubHeader("任务描述"))
        self._edit_desc = QTextEdit()
        self._edit_desc.setStyleSheet(INPUT_STYLE)
        self._edit_desc.setMinimumHeight(120)
        lay.addWidget(self._edit_desc)

        lay.addWidget(HDivider())
        lay.addWidget(SubHeader("交互要求"))

        req_row = QHBoxLayout()
        req_row.setSpacing(16)
        rl_label = QLabel("最低轮次")
        rl_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        self._edit_rounds = QSpinBox()
        self._edit_rounds.setRange(1, 50)
        self._edit_rounds.setValue(15)
        self._edit_rounds.setStyleSheet(INPUT_STYLE)
        self._edit_rounds.setFixedWidth(80)
        self._edit_followup = QCheckBox("必须追问")
        self._edit_questioning = QCheckBox("必须质疑")
        self._edit_socratic = QCheckBox("苏格拉底式")
        req_row.addWidget(rl_label)
        req_row.addWidget(self._edit_rounds)
        req_row.addWidget(self._edit_followup)
        req_row.addWidget(self._edit_questioning)
        req_row.addWidget(self._edit_socratic)
        req_row.addStretch()
        lay.addLayout(req_row)

        lay.addWidget(SubHeader("要求的交互方式"))
        types_row = QHBoxLayout()
        types_row.setSpacing(8)
        self._type_checks = {}
        for t_name in INTERACTION_TYPES_LIST:
            cb = QCheckBox(t_name)
            cb.setStyleSheet(INPUT_STYLE)
            self._type_checks[t_name] = cb
            types_row.addWidget(cb)
        types_row.addStretch()
        lay.addLayout(types_row)

        lay.addWidget(HDivider())
        lay.addWidget(SubHeader("成果要求"))
        self._edit_output = QTextEdit()
        self._edit_output.setStyleSheet(INPUT_STYLE)
        self._edit_output.setFixedHeight(80)
        self._edit_output.setPlaceholderText("具体成果说明，如：手绘推导图、对比分析报告、对话记录…")
        lay.addWidget(self._edit_output)
        lay.addStretch()

        scroll.setWidget(container)
        return scroll

    def _load_courses(self):
        self._course_list.clear()
        self._courses = data_store.list_courses()
        if not self._courses:
            item = QListWidgetItem("暂无章节，请先导入课件")
            item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(TEXT_DIM))
            self._course_list.addItem(item)
            return
        active = session_state.current_chapters()
        for c in self._courses:
            cid = c.get("chapter_id", "")
            label = c.get("chapter_title", cid)
            if active and cid in active:
                label = f"● {label}"
            self._course_list.addItem(label)

    def _on_course_selected(self, idx):
        if idx < 0 or idx >= len(self._courses): return
        cid = self._courses[idx].get("chapter_id")
        self._current_chapter_id = cid
        self._current_tasks = data_store.load_tasks(cid)
        self._task_list.clear()
        if self._current_tasks:
            for i, t in enumerate(self._current_tasks.get("tasks", []), 1):
                self._task_list.addItem(f"{i:02d}. {t.get('title', '')}")

    def _on_task_selected(self, idx):
        if not self._current_tasks or idx < 0: return
        tasks = self._current_tasks.get("tasks", [])
        if idx >= len(tasks): return
        self._current_task_idx = idx
        self._fill_editor(tasks[idx])
        self._save_btn.setEnabled(True)
        self._export_json_btn.setEnabled(True)
        self._docx_btn.setEnabled(True)

    def _fill_editor(self, task: dict):
        self._edit_title.setText(task.get("title", ""))
        self._edit_type.setCurrentText(task.get("task_type", "知识体系整理"))
        self._edit_diff.setCurrentText(task.get("difficulty", "中等"))
        self._edit_desc.setPlainText(task.get("description", ""))
        req = task.get("interaction_requirements", {})
        self._edit_rounds.setValue(int(req.get("min_rounds", 15) or 15))
        self._edit_followup.setChecked(bool(req.get("must_include_follow_up", True)))
        self._edit_questioning.setChecked(bool(req.get("must_include_questioning", True)))
        self._edit_socratic.setChecked(bool(req.get("need_socratic_dialogue", False)))
        required_types = set(req.get("required_types", []))
        for t_name, cb in self._type_checks.items():
            cb.setChecked(t_name in required_types)
        out = task.get("output_requirements", {})
        specific = out.get("specific_output", "").strip()
        if not specific:
            required = out.get("required_outputs", [])
            word_limit = out.get("word_limit", "500-800字")
            specific = f"字数要求：{word_limit}\n成果：{'、'.join(required)}" if required else f"字数要求：{word_limit}"
        self._edit_output.setPlainText(specific)

    def _save_edit(self):
        if not self._current_tasks or self._current_task_idx is None: return
        task = self._current_tasks["tasks"][self._current_task_idx]
        task["title"] = self._edit_title.text().strip()
        task["task_type"] = self._edit_type.currentText()
        task["difficulty"] = self._edit_diff.currentText()
        task["description"] = self._edit_desc.toPlainText().strip()
        req = task.setdefault("interaction_requirements", {})
        req["min_rounds"] = self._edit_rounds.value()
        req["must_include_follow_up"] = self._edit_followup.isChecked()
        req["must_include_questioning"] = self._edit_questioning.isChecked()
        req["need_socratic_dialogue"] = self._edit_socratic.isChecked()
        req["required_types"] = [t for t, cb in self._type_checks.items() if cb.isChecked()]
        data_store.save_tasks(self._current_chapter_id, self._current_tasks)
        item = self._task_list.item(self._current_task_idx)
        if item:
            item.setText(f"{self._current_task_idx+1:02d}. {task['title']}")
        QMessageBox.information(self, "已保存", f"✅ 任务「{task['title']}」已更新。")

    def _export_task(self):
        if not self._current_tasks or self._current_task_idx is None: return
        task = self._current_tasks["tasks"][self._current_task_idx]
        path, _ = QFileDialog.getSaveFileName(
            self, "导出任务", f"{task.get('title', 'task')}.json", "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出到：{path}")

    def _export_task_sheet_docx(self):
        if not self._current_tasks:
            QMessageBox.information(self, "提示", "请先选择一个章节。")
            return
        try:
            from task_formatter import export_task_sheet_docx
        except ImportError:
            QMessageBox.warning(self, "提示", "请安装 python-docx 依赖。")
            return
        default_name = f"{self._current_tasks.get('chapter_title', '课堂探究任务')}.docx"
        path, _ = QFileDialog.getSaveFileName(self, "导出任务书", default_name, "Word (*.docx)")
        if not path: return
        if not path.lower().endswith(".docx"): path += ".docx"
        try:
            export_task_sheet_docx(self._current_tasks, path)
            QMessageBox.information(self, "导出成功", f"任务书已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def jump_to_chapter(self, chapter_id: str):
        self._load_courses()
        for i, c in enumerate(self._courses):
            if c.get("chapter_id") == chapter_id:
                self._course_list.setCurrentRow(i)
                return
        if self._courses:
            self._course_list.setCurrentRow(0)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_courses()
        if self._courses:
            self._course_list.setCurrentRow(0)
