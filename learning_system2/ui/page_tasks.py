"""
Page: Task Browser & Editor — Warm Parchment Style
修复：分割栏可自由拖拽（移除 setFixedWidth 改用 setMinimumWidth + setSizes）
"""

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QLineEdit, QSpinBox,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QCheckBox, QFileDialog, QGridLayout
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


class TileCheckBox(QCheckBox):
    """让整块复选框区域都可点击，而不只限于文字/小方框。"""
    def hitButton(self, pos):
        return self.rect().contains(pos)


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
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # 页头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 20)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        t = QLabel("任务管理 · 编辑")
        t.setStyleSheet(f"color: {TEXT_H1}; font-size: 19px; font-weight: 800; background: transparent;")
        s = QLabel("查看、修改和导出已生成的课堂探究任务（拖拽分割线调整各栏宽度）")
        s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(t)
        title_col.addWidget(s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(GHOST_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_courses)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        # 主分割器（关键：setChildrenCollapsible(False) 防止塌陷）
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)          # 加宽手柄，更易拖拽
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {BORDER};
                border-radius: 3px;
            }}
            QSplitter::handle:hover {{
                background: {GREEN_MUTED};
            }}
            QSplitter::handle:pressed {{
                background: {GREEN_PRI};
            }}
        """)

        # ── 左栏：章节列表 ────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(160)
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(12)

        ll.addWidget(SectionHeader("章节列表"))
        self._course_list = self._make_list()
        self._course_list.currentRowChanged.connect(self._on_course_selected)
        ll.addWidget(self._course_list, 1)

        ll.addWidget(SectionHeader("任务列表"))
        self._task_list = self._make_list()
        self._task_list.currentRowChanged.connect(self._on_task_selected)
        ll.addWidget(self._task_list, 1)

        # ── 中栏任务详情编辑 ──────────────────────────────────────────────────
        mid = QWidget()
        mid.setMinimumWidth(280)
        mid.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(8, 0, 8, 0)
        ml.setSpacing(12)

        ml.addWidget(SectionHeader("任务详情编辑"))
        ml.addWidget(self._build_editor(), 1)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._export_json_btn = QPushButton("导出 JSON")
        self._export_json_btn.setStyleSheet(GHOST_BTN)
        self._export_json_btn.setEnabled(False)
        self._export_json_btn.clicked.connect(self._export_task)

        self._docx_btn = QPushButton("导出任务书 DOCX")
        self._docx_btn.setStyleSheet(SECONDARY_BTN)
        self._docx_btn.setEnabled(False)
        self._docx_btn.clicked.connect(self._export_task_sheet_docx)

        self._save_btn = QPushButton("保存修改")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_edit)

        btn_row.addWidget(self._export_json_btn)
        btn_row.addWidget(self._docx_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        ml.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(mid)
        splitter.setSizes([220, 700])       # 初始比例：列表窄，编辑区宽

        root.addWidget(splitter, 1)
        self._load_courses()

    def _make_list(self) -> QListWidget:
        lw = QListWidget()
        lw.setStyleSheet(f"""
            QListWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 10px;
                color: {TEXT_PRI};
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 11px 14px;
                border-bottom: 1px solid {BORDER_LIGHT};
            }}
            QListWidget::item:selected {{
                background: {GREEN_LIGHT};
                color: {GREEN_DARK};
                font-weight: 700;
            }}
            QListWidget::item:hover:!selected {{ background: {BG_HOVER}; }}
        """)
        return lw

    def _build_editor(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 编辑器卡片（统一控件尺寸，减少嵌套边框）
        EDIT_LINE_STYLE = f"""
            QLineEdit {{
                background: {BG_INPUT};
                color: {TEXT_PRI};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 0 12px;
                min-height: 38px;
                font-size: 13px;
            }}
            QLineEdit:hover {{ border-color: {GREEN_MUTED}; background: #FFFFFF; }}
            QLineEdit:focus {{ border-color: {GREEN_PRI}; background: #FFFFFF; }}
        """
        EDIT_TEXT_STYLE = f"""
            QTextEdit {{
                background: {BG_INPUT};
                color: {TEXT_PRI};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                line-height: 160%;
                selection-background-color: {GREEN_LIGHT};
                selection-color: {GREEN_DARK};
            }}
            QTextEdit:hover {{ border-color: {GREEN_MUTED}; background: #FFFFFF; }}
            QTextEdit:focus {{ border-color: {GREEN_PRI}; background: #FFFFFF; }}
        """
        COMBO_STYLE = f"""
            QComboBox {{
                background: {BG_INPUT};
                color: {TEXT_PRI};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                min-height: 38px;
            }}
            QComboBox:focus {{ border: 1px solid {GREEN_PRI}; background: #FFFFFF; }}
            QComboBox:hover {{ border: 1px solid {GREEN_MUTED}; background: #FFFFFF; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {TEXT_DIM};
                width: 0; height: 0;
            }}
            QComboBox QAbstractItemView {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                color: {TEXT_PRI};
                selection-background-color: {GREEN_LIGHT};
                selection-color: {GREEN_DARK};
                padding: 4px;
                font-size: 13px;
            }}
        """
        SPIN_STYLE = f"""
            QSpinBox {{
                background: {BG_INPUT};
                color: {TEXT_H1};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 0 10px;
                min-height: 34px;
                font-size: 14px;
                font-weight: 700;
            }}
            QSpinBox:hover {{ border-color: {GREEN_MUTED}; background: #FFFFFF; }}
            QSpinBox:focus {{ border-color: {GREEN_PRI}; background: #FFFFFF; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 0px;
                height: 0px;
                border: none;
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                width: 0px;
                height: 0px;
                image: none;
            }}
        """
        CB_STYLE = f"""
            QCheckBox {{
                color: {TEXT_PRI};
                font-size: 13px;
                spacing: 8px;
                background: {BG_INPUT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 7px 11px;
                min-height: 20px;
            }}
            QCheckBox:hover {{
                border-color: {GREEN_MUTED};
                background: #FFFFFF;
            }}
            QCheckBox:checked {{
                color: {GREEN_DARK};
                background: {GREEN_LIGHT};
                border-color: #CFE2FA;
                font-weight: 700;
            }}
            QCheckBox::indicator {{
                width: 15px; height: 15px;
                border: 2px solid #B9C6D8;
                border-radius: 4px;
                background: #FFFFFF;
            }}
            QCheckBox::indicator:checked {{
                background: {GREEN_PRI};
                border-color: {GREEN_PRI};
            }}
        """
        SECTION_LBL = (
            f"color: {TEXT_SEC}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 0.8px; background: transparent; border: none;"
        )

        container = QFrame()
        container.setObjectName("taskEditorCard")
        container.setStyleSheet(f"""
            QFrame#taskEditorCard {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        add_shadow(container, blur=10, offset_y=2)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(12)

        # ── 标题 + 类型 + 难度 一行 ──────────────────────────────────────
        row_top = QHBoxLayout()
        row_top.setSpacing(8)
        self._edit_title = QLineEdit()
        self._edit_title.setStyleSheet(EDIT_LINE_STYLE)
        self._edit_title.setPlaceholderText("任务标题")
        self._edit_title.setFixedHeight(40)
        row_top.addWidget(self._edit_title, 3)

        self._edit_type = QComboBox()
        self._edit_type.addItems([
            "知识体系整理", "概念辨析", "方法比较",
            "案例分析", "问题推理", "批判思考",
            "苏格拉底引导", "学习反思", "算法对比", "复杂度分析"
        ])
        self._edit_type.setStyleSheet(COMBO_STYLE)
        self._edit_type.setFixedHeight(40)
        row_top.addWidget(self._edit_type, 2)

        self._edit_diff = QComboBox()
        self._edit_diff.addItems(["基础", "中等", "挑战"])
        self._edit_diff.setStyleSheet(COMBO_STYLE)
        self._edit_diff.setFixedHeight(40)
        row_top.addWidget(self._edit_diff, 1)
        lay.addLayout(row_top)

        # ── 任务描述 ─────────────────────────────────────────────────────
        desc_hdr = QLabel("任务描述")
        desc_hdr.setStyleSheet(SECTION_LBL)
        lay.addWidget(desc_hdr)
        self._edit_desc = QTextEdit()
        self._edit_desc.setStyleSheet(EDIT_TEXT_STYLE)
        self._edit_desc.setMinimumHeight(116)
        lay.addWidget(self._edit_desc)

        lay.addSpacing(2)

        # ── 交互要求 ─────────────────────────────────────────────────────
        req_hdr = QLabel("交互要求")
        req_hdr.setStyleSheet(SECTION_LBL)
        lay.addWidget(req_hdr)

        req_row = QHBoxLayout()
        req_row.setSpacing(10)
        rl_label = QLabel("最低轮次")
        rl_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent; border: none;")
        self._edit_rounds = QSpinBox()
        self._edit_rounds.setRange(1, 50)
        self._edit_rounds.setValue(15)
        self._edit_rounds.setButtonSymbols(QSpinBox.NoButtons)
        self._edit_rounds.setStyleSheet(SPIN_STYLE)
        self._edit_rounds.setFixedSize(68, 36)
        self._edit_followup   = TileCheckBox("必须追问")
        self._edit_questioning = TileCheckBox("必须质疑")
        self._edit_socratic   = TileCheckBox("苏格拉底式")
        for cb in [self._edit_followup, self._edit_questioning, self._edit_socratic]:
            cb.setStyleSheet(CB_STYLE)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setFixedHeight(36)
        req_row.addWidget(rl_label)
        req_row.addWidget(self._edit_rounds)
        req_row.addWidget(self._edit_followup)
        req_row.addWidget(self._edit_questioning)
        req_row.addWidget(self._edit_socratic)
        req_row.addStretch()
        lay.addLayout(req_row)

        # ── 交互方式复选框 ─────────────────────────────────────────────────
        types_hdr = QLabel("要求的交互方式")
        types_hdr.setStyleSheet(SECTION_LBL)
        lay.addWidget(types_hdr)
        types_grid = QGridLayout()
        types_grid.setHorizontalSpacing(8)
        types_grid.setVerticalSpacing(8)
        self._type_checks = {}
        for i, t_name in enumerate(INTERACTION_TYPES_LIST):
            cb = TileCheckBox(t_name)
            cb.setStyleSheet(CB_STYLE)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setFixedHeight(36)
            self._type_checks[t_name] = cb
            types_grid.addWidget(cb, i // 4, i % 4)
        lay.addLayout(types_grid)

        lay.addSpacing(2)

        # ── 成果要求 ─────────────────────────────────────────────────────
        out_hdr = QLabel("成果要求")
        out_hdr.setStyleSheet(SECTION_LBL)
        lay.addWidget(out_hdr)
        self._edit_output = QTextEdit()
        self._edit_output.setStyleSheet(EDIT_TEXT_STYLE)
        self._edit_output.setFixedHeight(86)
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
            from PyQt5.QtGui import QColor
            item.setForeground(QColor(TEXT_DIM))
            self._course_list.addItem(item)
            return
        active = session_state.current_chapters()
        for c in self._courses:
            cid   = c.get("chapter_id", "")
            label = c.get("chapter_title", cid)
            if active and cid in active:
                label = f"● {label}"
            self._course_list.addItem(label)

    def _on_course_selected(self, idx):
        if idx < 0 or idx >= len(self._courses):
            return
        cid = self._courses[idx].get("chapter_id")
        self._current_chapter_id = cid
        self._current_tasks = data_store.load_tasks(cid)
        self._task_list.clear()
        if self._current_tasks:
            for i, t in enumerate(self._current_tasks.get("tasks", []), 1):
                self._task_list.addItem(f"{i:02d}. {t.get('title', '')}")

    def _on_task_selected(self, idx):
        if not self._current_tasks or idx < 0:
            return
        tasks = self._current_tasks.get("tasks", [])
        if idx >= len(tasks):
            return
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
            required   = out.get("required_outputs", [])
            word_limit = out.get("word_limit", "500-800字")
            specific   = f"字数要求：{word_limit}\n成果：{'、'.join(required)}" if required else f"字数要求：{word_limit}"
        self._edit_output.setPlainText(specific)

    def _save_edit(self):
        if not self._current_tasks or self._current_task_idx is None:
            return
        task = self._current_tasks["tasks"][self._current_task_idx]
        task["title"]     = self._edit_title.text().strip()
        task["task_type"] = self._edit_type.currentText()
        task["difficulty"] = self._edit_diff.currentText()
        task["description"] = self._edit_desc.toPlainText().strip()
        req = task.setdefault("interaction_requirements", {})
        req["min_rounds"]              = self._edit_rounds.value()
        req["must_include_follow_up"]  = self._edit_followup.isChecked()
        req["must_include_questioning"] = self._edit_questioning.isChecked()
        req["need_socratic_dialogue"]  = self._edit_socratic.isChecked()
        req["required_types"] = [t for t, cb in self._type_checks.items() if cb.isChecked()]
        data_store.save_tasks(self._current_chapter_id, self._current_tasks)
        item = self._task_list.item(self._current_task_idx)
        if item:
            item.setText(f"{self._current_task_idx + 1:02d}. {task['title']}")
        QMessageBox.information(self, "保存成功", f"任务「{task['title']}」已更新。")

    def _export_task(self):
        if not self._current_tasks or self._current_task_idx is None:
            return
        task = self._current_tasks["tasks"][self._current_task_idx]
        path, _ = QFileDialog.getSaveFileName(
            self, "导出任务", f"{task.get('title', 'task')}.json", "JSON (*.json)")
        if not path:
            return
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
