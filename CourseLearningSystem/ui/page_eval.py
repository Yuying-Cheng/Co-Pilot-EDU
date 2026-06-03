"""Batch student evaluation page for teacher workflow."""

import json
import os
import re
from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QHeaderView,
)
from PyQt5.QtGui import QColor

from data.data_manager import load_knowledge, load_task, save_report, save_score
from evaluator.evaluator_v2 import evaluate_submission_v2
from parser.submission_parser import iter_submission_files, parse_submission_file
from ui.styles import *
from ui.session_state import current_chapters
from ui.widgets import HDivider, LoadingWidget, ScoreBar, SectionHeader, Worker, make_info_row

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


def re_split_keywords(text: str):
    return [part for part in re.split(r"[\s·：:，,、（）()《》\-]+", text or "") if len(part) >= 2]


class EvalPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._submissions: List[Dict[str, Any]] = []
        self._scores: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("成果评阅 · 批量评分")
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

        ll.addWidget(SectionHeader("评阅任务"))
        self._task_combo = QComboBox()
        self._task_combo.setStyleSheet(INPUT_STYLE)
        self._load_tasks_to_combo()
        ll.addWidget(self._task_combo)

        import_card = QFrame()
        import_card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        ic_lay = QVBoxLayout(import_card)
        ic_lay.setContentsMargins(18, 16, 18, 16)
        ic_lay.setSpacing(12)
        hint = QLabel("选择学生提交文件或文件夹。支持 JSON、TXT、MD、DOCX、PDF；文件名可包含学号和姓名。")
        hint.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%;")
        hint.setWordWrap(True)
        ic_lay.addWidget(hint)
        btn_row = QHBoxLayout()
        file_btn = QPushButton("导入文件")
        file_btn.setStyleSheet(GHOST_BTN)
        file_btn.setCursor(Qt.PointingHandCursor)
        folder_btn = QPushButton("导入文件夹")
        folder_btn.setStyleSheet(GHOST_BTN)
        folder_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                file_btn.setIcon(qta.icon("ri.file-upload-line", color=TEXT_SEC))
                folder_btn.setIcon(qta.icon("ri.folder-upload-line", color=TEXT_SEC))
            except Exception:
                pass
        file_btn.clicked.connect(self._import_files)
        folder_btn.clicked.connect(self._import_folder)
        btn_row.addWidget(file_btn)
        btn_row.addWidget(folder_btn)
        ic_lay.addLayout(btn_row)
        ll.addWidget(import_card)

        ll.addWidget(SectionHeader("待评阅学生"))
        self._submission_table = QTableWidget(0, 4)
        self._submission_table.setHorizontalHeaderLabels(["姓名", "学号", "轮次", "来源"])
        self._submission_table.setStyleSheet(TABLE_STYLE)
        self._submission_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._submission_table.verticalHeader().setVisible(False)
        self._submission_table.setEditTriggers(QTableWidget.NoEditTriggers)
        ll.addWidget(self._submission_table, 1)

        self._eval_btn = QPushButton("批量评阅")
        self._eval_btn.setStyleSheet(PRIMARY_BTN)
        self._eval_btn.setEnabled(False)
        self._eval_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._eval_btn.setIcon(qta.icon("ri.robot-line", color="white"))
            except Exception:
                pass
        self._eval_btn.clicked.connect(self._evaluate_batch)
        ll.addWidget(self._eval_btn)

        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(24, 0, 0, 0)
        rl.setSpacing(16)

        top = QHBoxLayout()
        top.addWidget(SectionHeader("评阅结果"))
        top.addStretch()
        export_btn = QPushButton("导出结果")
        export_btn.setStyleSheet(SECONDARY_BTN)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_scores)
        top.addWidget(export_btn)
        rl.addLayout(top)

        self._result_table = QTableWidget(0, 8)
        self._result_table.setHorizontalHeaderLabels(["姓名", "学号", "总分", "交互", "知识", "表达", "反思", "有效轮次"])
        self._result_table.setStyleSheet(TABLE_STYLE)
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._result_table.verticalHeader().setVisible(False)
        self._result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._result_table.currentCellChanged.connect(self._show_score_detail)
        rl.addWidget(self._result_table, 1)

        rl.addWidget(SectionHeader("学生详情"))
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._detail = QWidget()
        self._detail.setStyleSheet("background: transparent;")
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(10)
        self._detail_empty = QLabel("评阅完成后，点击表格中的学生查看评语和改进建议。")
        self._detail_empty.setAlignment(Qt.AlignCenter)
        self._detail_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._detail_layout.addWidget(self._detail_empty)
        self._detail_layout.addStretch()
        detail_scroll.setWidget(self._detail)
        rl.addWidget(detail_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([440, 720])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _load_tasks_to_combo(self):
        self._task_combo.clear()
        self._task_combo.addItem("自动识别学生选择的任务", "AUTO")
        tasks_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks")
        if not os.path.exists(tasks_dir):
            return
        active = current_chapters()
        if not active:
            return
        for filename in os.listdir(tasks_dir):
            if not filename.endswith("_task.json"):
                continue
            chapter_id = filename.replace("_task.json", "")
            if chapter_id not in active:
                continue
            try:
                with open(os.path.join(tasks_dir, filename), "r", encoding="utf-8") as f:
                    task_data = json.load(f)
                for task in task_data.get("tasks", []):
                    task = dict(task)
                    task["chapter_id"] = chapter_id
                    label = f"{task_data.get('chapter_title', chapter_id)} · {task.get('title', task.get('task_id', '任务'))}"
                    self._task_combo.addItem(label, task)
            except Exception:
                continue

    def _current_task(self) -> Dict[str, Any] | None:
        task = self._task_combo.currentData()
        return task if isinstance(task, dict) else None

    def _import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择学生提交文件",
            "",
            "学生提交 (*.json *.txt *.md *.docx *.pdf)",
        )
        if paths:
            self._load_submission_paths(paths)

    def _import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择学生提交文件夹")
        if folder:
            self._load_submission_paths(iter_submission_files(folder))

    def _load_submission_paths(self, paths: List[str]):
        task = self._current_task()
        chapter_id = task.get("chapter_id", "AUTO") if task else "AUTO"
        task_id = task.get("task_id", "AUTO") if task else "AUTO"
        loaded: List[Dict[str, Any]] = []
        errors: List[str] = []
        for path in paths:
            try:
                loaded.append(parse_submission_file(path, chapter_id, task_id))
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}：{exc}")
        self._submissions = loaded
        self._render_submissions()
        self._eval_btn.setEnabled(bool(self._submissions))
        if errors:
            QMessageBox.warning(self, "部分文件未导入", "\n".join(errors[:8]))

    def _render_submissions(self):
        self._submission_table.setRowCount(len(self._submissions))
        for row, sub in enumerate(self._submissions):
            values = [
                sub.get("student_name", ""),
                sub.get("student_id", ""),
                str(len(sub.get("dialogues", []))),
                os.path.basename(sub.get("source_file", "")),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if col != 3 else Qt.AlignLeft | Qt.AlignVCenter)
                self._submission_table.setItem(row, col, item)

    def _evaluate_batch(self):
        if not self._submissions:
            return
        self._loading.set_text(f"正在批量评阅 {len(self._submissions)} 份学生提交…")
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

        def do_eval():
            selected_task = self._current_task()
            task_bundle = self._load_task_bundle()
            if not task_bundle:
                raise ValueError("当前没有可用于评阅的课堂任务。请先导入课件并生成任务。")
            results = []
            for sub in self._submissions:
                chapter_id, task_id, knowledge, task_data = self._resolve_submission_task(sub, task_bundle, selected_task)
                sub["chapter_id"] = chapter_id
                sub["task_id"] = task_id
                save_report(sub["student_id"], chapter_id, sub)
                score = evaluate_submission_v2(knowledge=knowledge, task_data=task_data, submission=sub, use_llm=True)
                save_score(sub["student_id"], chapter_id, score)
                results.append(score)
            return results

        self._worker = Worker(do_eval)
        self._worker.finished.connect(self._on_batch_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _load_task_bundle(self):
        bundle = []
        active = current_chapters()
        for chapter_id in active:
            knowledge = load_knowledge(chapter_id)
            task_data = load_task(chapter_id)
            if knowledge and task_data:
                bundle.append((chapter_id, knowledge, task_data))
        return bundle

    def _resolve_submission_task(self, sub, bundle, selected_task):
        if selected_task:
            chapter_id = selected_task.get("chapter_id")
            knowledge = load_knowledge(chapter_id)
            task_data = load_task(chapter_id)
            return chapter_id, selected_task.get("task_id", "task001"), knowledge, task_data

        text = "\n".join([
            str(sub.get("raw_text", "")),
            str(sub.get("final_report", "")),
            " ".join(d.get("student_input", "") for d in sub.get("dialogues", [])),
        ])
        best = None
        best_score = -1
        for chapter_id, knowledge, task_data in bundle:
            chapter_title = str(task_data.get("chapter_title", ""))
            for task in task_data.get("tasks", []):
                score = self._match_task_score(text, chapter_title, task)
                if score > best_score:
                    best_score = score
                    best = (chapter_id, task.get("task_id", "task001"), knowledge, task_data)
        if not best:
            chapter_id, knowledge, task_data = bundle[0]
            first = task_data.get("tasks", [{}])[0]
            best = (chapter_id, first.get("task_id", "task001"), knowledge, task_data)
        return best

    def _match_task_score(self, text: str, chapter_title: str, task: Dict[str, Any]) -> int:
        score = 0
        title = str(task.get("title", ""))
        task_id = str(task.get("task_id", ""))
        if title and title in text:
            score += 100
        if chapter_title and chapter_title in text:
            score += 10
        cn_map = {"task001": "任务一", "task002": "任务二", "task003": "任务三", "task004": "任务四", "task005": "任务五", "task006": "任务六"}
        if cn_map.get(task_id, "") in text:
            score += 80
        for point in task.get("inquiry_points", []):
            if point and str(point)[:12] in text:
                score += 5
        for kp in task.get("related_knowledge_points", []):
            if str(kp) in text:
                score += 1
        for word in re_split_keywords(title):
            if word in text:
                score += 3
        return score

    def _on_batch_done(self, scores: List[Dict[str, Any]]):
        self._loading.hide()
        self._scores = scores
        self._render_scores()

    def _render_scores(self):
        self._result_table.setRowCount(len(self._scores))
        for row, score in enumerate(self._scores):
            sc = score.get("scores", {})
            ia = score.get("interaction_analysis", {})
            values = [
                score.get("student_name", ""),
                score.get("student_id", ""),
                str(score.get("total_score", 0)),
                str(sc.get("interaction_quality", 0)),
                str(sc.get("knowledge_mastery", 0)),
                str(sc.get("presentation", 0)),
                str(sc.get("reflection", 0)),
                str(ia.get("valid_rounds", 0)),
            ]
            total = int(score.get("total_score", 0) or 0)
            total_color = ACCENT2 if total >= 85 else ACCENT3 if total >= 70 else ACCENT4
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(total_color))
                self._result_table.setItem(row, col, item)
        if self._scores:
            self._result_table.setCurrentCell(0, 0)

    def _show_score_detail(self, row: int, _col: int, _prev_row: int, _prev_col: int):
        if row < 0 or row >= len(self._scores):
            return
        score = self._scores[row]
        while self._detail_layout.count() > 1:
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._detail_empty.hide()
        self._detail_layout.insertWidget(0, self._make_score_card(score))
        self._detail_layout.insertWidget(1, self._make_interaction_card(score))
        self._detail_layout.insertWidget(2, self._make_comment_card(score))

    def _panel(self, title: str) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        lay.addWidget(SectionHeader(title))
        lay.addWidget(HDivider())
        return panel

    def _make_score_card(self, score: Dict[str, Any]) -> QFrame:
        panel = self._panel("分项得分")
        lay = panel.layout()
        scores = score.get("scores", {})
        for label, val, mx, color in [
            ("交互质量", scores.get("interaction_quality", 0), 50, ACCENT),
            ("知识掌握", scores.get("knowledge_mastery", 0), 25, ACCENT2),
            ("成果表达", scores.get("presentation", 0), 15, ACCENT5),
            ("学习反思", scores.get("reflection", 0), 10, ACCENT3),
        ]:
            lay.addWidget(ScoreBar(label, val, mx, color))
        return panel

    def _make_interaction_card(self, score: Dict[str, Any]) -> QFrame:
        panel = self._panel("交互行为")
        lay = panel.layout()
        ia = score.get("interaction_analysis", {})
        lay.addWidget(make_info_row("总轮次", str(ia.get("total_rounds", 0)), ACCENT))
        lay.addWidget(make_info_row("有效轮次", str(ia.get("valid_rounds", 0))))
        lay.addWidget(make_info_row("交互深度", str(ia.get("depth_level", "-"))))
        types = ia.get("interaction_types", {})
        used = "  ".join(f"{k} x{v}" for k, v in types.items() if v)
        if used:
            label = QLabel(used)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
            lay.addWidget(label)
        return panel

    def _make_comment_card(self, score: Dict[str, Any]) -> QFrame:
        panel = self._panel("评语与建议")
        lay = panel.layout()
        comment = QLabel(score.get("comment") or score.get("readable_comment", ""))
        comment.setWordWrap(True)
        comment.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%; background: transparent;")
        lay.addWidget(comment)
        for index, suggestion in enumerate(score.get("improvement_suggestions", []), start=1):
            item = QLabel(f"{index}. {suggestion}")
            item.setWordWrap(True)
            item.setStyleSheet(f"color: {ACCENT3}; font-size: 11px; background: transparent;")
            lay.addWidget(item)
        return panel

    def _export_scores(self):
        if not self._scores:
            QMessageBox.information(self, "提示", "暂无可导出的评阅结果。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出评阅结果", "评阅结果.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._scores, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"评阅结果已导出到：{path}")

    def _on_error(self, msg: str):
        self._loading.hide()
        QMessageBox.critical(self, "评阅失败", msg)

    def showEvent(self, event):
        super().showEvent(event)
        current = self._task_combo.currentData()
        self._load_tasks_to_combo()
        if isinstance(current, dict):
            for i in range(self._task_combo.count()):
                data = self._task_combo.itemData(i)
                if isinstance(data, dict) and data.get("task_id") == current.get("task_id") and data.get("chapter_id") == current.get("chapter_id"):
                    self._task_combo.setCurrentIndex(i)
                    break

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_loading"):
            self._loading.resize(self.size())
