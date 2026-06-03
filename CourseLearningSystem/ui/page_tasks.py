"""Teacher-facing task browser, editor, and task-sheet exporter."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from data.data_manager import load_task, save_task
from task_generator.task_formatter import export_task_sheet_docx
from ui.styles import *
from ui.session_state import current_chapters
from ui.widgets import HDivider, SectionHeader

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
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("任务管理 · 教师编辑")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: 0;")
        hdr.addWidget(title)
        hdr.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(GHOST_BTN)
        refresh_btn.clicked.connect(self._load_courses)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        left = QWidget()
        left.setFixedWidth(300)
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
        ll.addWidget(self._task_list, 2)

        export_sheet_btn = QPushButton("导出整章任务书 DOCX")
        export_sheet_btn.setStyleSheet(SECONDARY_BTN)
        export_sheet_btn.clicked.connect(self._export_sheet)
        ll.addWidget(export_sheet_btn)

        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 0, 0, 0)
        rl.setSpacing(16)
        rl.addWidget(SectionHeader("任务内容"))
        rl.addWidget(self._build_editor(), 1)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("保存修改")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_edit)
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
            QListWidget::item:selected {{
                background: {BG_INPUT};
                color: {TEXT_PRI};
            }}
        """)
        return lw

    def _build_editor(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QFrame()
        container.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(QLabel("任务标题"))
        self._edit_title = QLineEdit()
        self._edit_title.setStyleSheet(INPUT_STYLE)
        lay.addWidget(self._edit_title)

        row = QHBoxLayout()
        self._edit_type = QComboBox()
        self._edit_type.addItems(["知识体系整理", "算法对比", "复杂度分析", "案例推演", "苏格拉底引导", "审辨创新", "学习反思"])
        self._edit_type.setStyleSheet(INPUT_STYLE)
        self._edit_diff = QComboBox()
        self._edit_diff.addItems(["基础", "中等", "挑战"])
        self._edit_diff.setStyleSheet(INPUT_STYLE)
        row.addWidget(self._edit_type, 1)
        row.addWidget(self._edit_diff)
        lay.addLayout(row)

        lay.addWidget(QLabel("任务描述"))
        self._edit_desc = QTextEdit()
        self._edit_desc.setStyleSheet(INPUT_STYLE)
        self._edit_desc.setMinimumHeight(140)
        lay.addWidget(self._edit_desc)

        lay.addWidget(QLabel("探究问题（每行一个）"))
        self._edit_inquiry = QTextEdit()
        self._edit_inquiry.setStyleSheet(INPUT_STYLE)
        self._edit_inquiry.setFixedHeight(100)
        lay.addWidget(self._edit_inquiry)

        lay.addWidget(QLabel("提示（每行一个）"))
        self._edit_hints = QTextEdit()
        self._edit_hints.setStyleSheet(INPUT_STYLE)
        self._edit_hints.setFixedHeight(86)
        lay.addWidget(self._edit_hints)

        lay.addWidget(HDivider())
        req = QHBoxLayout()
        req.addWidget(QLabel("最低轮次"))
        self._edit_rounds = QSpinBox()
        self._edit_rounds.setRange(1, 50)
        self._edit_rounds.setValue(10)
        self._edit_rounds.setStyleSheet(INPUT_STYLE)
        req.addWidget(self._edit_rounds)
        self._edit_followup = QCheckBox("要求追问")
        self._edit_questioning = QCheckBox("要求质疑/审辨")
        self._edit_socratic = QCheckBox("苏格拉底式")
        req.addWidget(self._edit_followup)
        req.addWidget(self._edit_questioning)
        req.addWidget(self._edit_socratic)
        req.addStretch()
        lay.addLayout(req)

        types = QHBoxLayout()
        self._type_checks = {}
        for name in INTERACTION_TYPES_LIST:
            cb = QCheckBox(name)
            self._type_checks[name] = cb
            types.addWidget(cb)
        types.addStretch()
        lay.addLayout(types)

        lay.addWidget(QLabel("成果要求"))
        self._edit_output = QTextEdit()
        self._edit_output.setStyleSheet(INPUT_STYLE)
        self._edit_output.setFixedHeight(90)
        lay.addWidget(self._edit_output)
        lay.addStretch()
        scroll.setWidget(container)
        return scroll

    def _load_courses(self):
        self._course_list.clear()
        self._task_list.clear()
        tasks_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks")
        if not os.path.exists(tasks_dir):
            return
        active = current_chapters()
        if not active:
            self._clear_editor()
            return
        for filename in os.listdir(tasks_dir):
            if not filename.endswith("_task.json"):
                continue
            chapter_id = filename.replace("_task.json", "")
            if chapter_id not in active:
                continue
            data = load_task(chapter_id)
            if data:
                item = QListWidgetItem(data.get("chapter_title", chapter_id))
                item.setData(Qt.UserRole, chapter_id)
                self._course_list.addItem(item)

    def _on_course_selected(self, row):
        item = self._course_list.item(row)
        self._task_list.clear()
        self._clear_editor()
        if item is None:
            self._current_chapter_id = None
            self._current_tasks = None
            return
        self._current_chapter_id = item.data(Qt.UserRole)
        self._current_tasks = load_task(self._current_chapter_id)
        for index, task in enumerate((self._current_tasks or {}).get("tasks", [])):
            li = QListWidgetItem(task.get("title", f"任务{index + 1}"))
            li.setData(Qt.UserRole, index)
            self._task_list.addItem(li)

    def _on_task_selected(self, row):
        if not self._current_tasks or row < 0:
            return
        tasks = self._current_tasks.get("tasks", [])
        if row >= len(tasks):
            return
        self._current_task_idx = row
        self._fill_editor(tasks[row])
        self._save_btn.setEnabled(True)

    def _fill_editor(self, task):
        self._edit_title.setText(task.get("title", ""))
        self._edit_type.setCurrentText(task.get("task_type", "知识体系整理"))
        self._edit_diff.setCurrentText(task.get("difficulty", "中等"))
        self._edit_desc.setPlainText(task.get("description", ""))
        self._edit_inquiry.setPlainText("\n".join(task.get("inquiry_points", [])))
        hints = task.get("hints", [])
        self._edit_hints.setPlainText("\n".join(hints if isinstance(hints, list) else [str(hints)]))
        req = task.get("interaction_requirements", {})
        self._edit_rounds.setValue(int(req.get("min_rounds", 10) or 10))
        self._edit_followup.setChecked(bool(req.get("must_include_follow_up", True)))
        self._edit_questioning.setChecked(bool(req.get("must_include_questioning", True)))
        self._edit_socratic.setChecked(bool(req.get("need_socratic_dialogue", False)))
        required = set(req.get("required_types", []))
        for name, cb in self._type_checks.items():
            cb.setChecked(name in required)
        out = task.get("output_requirements", {})
        self._edit_output.setPlainText("\n".join(out.get("required_outputs", [])) or "探究报告\n交互记录\n学习反思")

    def _clear_editor(self):
        self._current_task_idx = None
        self._edit_title.clear()
        self._edit_desc.clear()
        self._edit_inquiry.clear()
        self._edit_hints.clear()
        self._edit_output.clear()
        self._edit_rounds.setValue(10)
        self._edit_followup.setChecked(True)
        self._edit_questioning.setChecked(True)
        self._edit_socratic.setChecked(False)
        for cb in self._type_checks.values():
            cb.setChecked(False)
        self._save_btn.setEnabled(False)

    def _save_edit(self):
        if self._current_task_idx is None or not self._current_tasks:
            return
        task = self._current_tasks["tasks"][self._current_task_idx]
        task["title"] = self._edit_title.text().strip()
        task["task_type"] = self._edit_type.currentText()
        task["difficulty"] = self._edit_diff.currentText()
        task["description"] = self._edit_desc.toPlainText().strip()
        task["inquiry_points"] = [line.strip() for line in self._edit_inquiry.toPlainText().splitlines() if line.strip()]
        task["hints"] = [line.strip() for line in self._edit_hints.toPlainText().splitlines() if line.strip()]
        req = task.setdefault("interaction_requirements", {})
        req["min_rounds"] = self._edit_rounds.value()
        req["required_types"] = [name for name, cb in self._type_checks.items() if cb.isChecked()]
        req["must_include_follow_up"] = self._edit_followup.isChecked()
        req["must_include_questioning"] = self._edit_questioning.isChecked()
        req["need_socratic_dialogue"] = self._edit_socratic.isChecked()
        out = task.setdefault("output_requirements", {})
        out["required_outputs"] = [line.strip() for line in self._edit_output.toPlainText().splitlines() if line.strip()]
        save_task(self._current_chapter_id, self._current_tasks)
        self._task_list.item(self._current_task_idx).setText(task["title"])
        QMessageBox.information(self, "已保存", "任务修改已保存。")

    def _export_sheet(self):
        if not self._current_tasks:
            QMessageBox.information(self, "提示", "请先选择一个章节。")
            return
        default_name = f"{self._current_tasks.get('chapter_title', '课堂探究任务')}.docx"
        path, _ = QFileDialog.getSaveFileName(self, "导出课堂探究任务书", default_name, "Word 文档 (*.docx)")
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        export_task_sheet_docx(self._current_tasks, path)
        QMessageBox.information(self, "导出成功", f"任务书已导出到：{path}")

    def showEvent(self, event):
        super().showEvent(event)
        self._load_courses()
