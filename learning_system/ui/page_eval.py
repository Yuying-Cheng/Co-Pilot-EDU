"""
Page 2: Student Evaluation — Warm Academic Style
- 批量PDF导入后自动匹配任务
- 任务下拉联动章节
- 批量结果表格 + 点击查看详情
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QLineEdit, QScrollArea, QFrame,
    QMessageBox, QSplitter, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ui.styles import *
from ui.widgets import (
    Worker, SectionHeader, SubHeader, ScoreBar, LoadingWidget,
    make_info_row, HDivider, add_shadow, make_panel,
    make_svg_widget, ILLUSTRATION_EXPLORE
)
import evaluator
import data_store
import pdf_importer
import session_state

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


def _split_keywords(text: str) -> List[str]:
    return [p for p in re.split(r"[\s·：:，,、（）()《》\-]+", text or "") if len(p) >= 2]


def _match_task_score(text: str, chapter_title: str, task: Dict) -> int:
    score = 0
    title = str(task.get("title", ""))
    task_id = str(task.get("task_id", ""))
    if title and title in text: score += 100
    if chapter_title and chapter_title in text: score += 10
    cn_map = {"task001": "任务一", "task002": "任务二", "task003": "任务三",
              "task004": "任务四", "task005": "任务五"}
    if cn_map.get(task_id, "") in text: score += 80
    for point in task.get("inquiry_points", []):
        if point and str(point)[:12] in text: score += 5
    for word in _split_keywords(title):
        if word in text: score += 3
    return score


def _resolve_task(sub, bundle, selected_task=None):
    if selected_task and isinstance(selected_task, dict):
        chapter_id = selected_task.get("chapter_id", "")
        task_id = selected_task.get("task_id", "task001")
        for cid, knowledge, task_data in bundle:
            if cid == chapter_id:
                return chapter_id, task_id, knowledge, task_data
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
            s = _match_task_score(text, chapter_title, task)
            if s > best_score:
                best_score = s
                best = (chapter_id, task.get("task_id", "task001"), knowledge, task_data)
    if best: return best
    if bundle:
        cid, knowledge, task_data = bundle[0]
        first = task_data.get("tasks", [{}])[0]
        return cid, first.get("task_id", "task001"), knowledge, task_data
    raise ValueError("没有可用的课堂任务，请先在「课件导入」页面生成并保存任务。")


class BatchEvalWorker(QThread):
    progress = pyqtSignal(int, int, str)
    one_done = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, pdf_paths, bundle, selected_task):
        super().__init__()
        self._paths = pdf_paths
        self._bundle = bundle
        self._selected_task = selected_task

    def run(self):
        results = []
        total = len(self._paths)
        for i, path in enumerate(self._paths, 1):
            fname = os.path.basename(path)
            self.progress.emit(i, total, fname)
            try:
                sub = pdf_importer.parse_pdf_to_submission(path)
                cid, tid, knowledge, task_data = _resolve_task(sub, self._bundle, self._selected_task)
                sub["chapter_id"] = cid
                sub["task_id"] = tid
                task = next((t for t in task_data.get("tasks", []) if t.get("task_id") == tid), None)
                score = evaluator.evaluate_submission(sub, task, knowledge)
                sid = data_store.save_submission(sub)
                score.update({"submission_id": sid,
                               "student_id": sub.get("student_id", ""),
                               "student_name": sub.get("student_name", ""),
                               "matched_chapter": cid, "matched_task": tid})
                data_store.save_score(score)
                results.append(score)
                self.one_done.emit(score)
            except Exception as e:
                err = {"student_name": os.path.splitext(fname)[0],
                       "student_id": "", "total_score": -1, "error": str(e)}
                results.append(err)
                self.one_done.emit(err)
        self.finished.emit(results)


class EvalPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._submission = None
        self._worker = None
        self._batch_worker = None
        self._scores: List[Dict] = []
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
        QLabel_title = QLabel("成果评阅 · 自动评分")
        QLabel_title.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        QLabel_sub = QLabel("导入学生对话记录，AI 自动评分并生成评语和改进建议")
        QLabel_sub.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(QLabel_title)
        title_col.addWidget(QLabel_sub)
        hdr.addLayout(title_col)
        hdr.addStretch()
        try:
            illu = make_svg_widget(ILLUSTRATION_EXPLORE, 80, 58)
            hdr.addWidget(illu)
        except Exception: pass
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ── 左栏：输入 ────────────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 18, 0)
        ll.setSpacing(14)

        # 任务选择
        ll.addWidget(SectionHeader("任务选择"))
        task_hint = QLabel("选择指定任务，或留「自动匹配」（批量时自动识别每位学生的任务）")
        task_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        task_hint.setWordWrap(True)
        ll.addWidget(task_hint)
        self._task_combo = QComboBox()
        self._task_combo.setStyleSheet(INPUT_STYLE)
        self._load_tasks_to_combo()
        ll.addWidget(self._task_combo)

        # 学生信息
        ll.addWidget(SectionHeader("学生信息"))
        info_row = QHBoxLayout()
        info_row.setSpacing(10)
        self._student_id = QLineEdit()
        self._student_id.setPlaceholderText("学号")
        self._student_id.setStyleSheet(INPUT_STYLE)
        self._student_name = QLineEdit()
        self._student_name.setPlaceholderText("姓名")
        self._student_name.setStyleSheet(INPUT_STYLE)
        info_row.addWidget(self._student_id)
        info_row.addWidget(self._student_name)
        ll.addLayout(info_row)

        # 对话记录
        ll.addWidget(SectionHeader("对话记录"))
        dialogue_hint = QLabel("每行以「学生：」或「模型：」开头粘贴；或用下方按钮导入 PDF")
        dialogue_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        ll.addWidget(dialogue_hint)
        self._dialogue_edit = QTextEdit()
        self._dialogue_edit.setPlaceholderText(
            "学生：分治法的基本思想是什么？\n模型：分治法将原问题分解为...\n学生：我理解分治就是大事化小，对吗？"
        )
        self._dialogue_edit.setStyleSheet(INPUT_STYLE)
        ll.addWidget(self._dialogue_edit, 2)

        # 报告 & 反思
        rep_ref = QHBoxLayout()
        rep_ref.setSpacing(10)
        rep_col = QVBoxLayout()
        rep_col.addWidget(SubHeader("最终报告"))
        self._report_edit = QTextEdit()
        self._report_edit.setPlaceholderText("学生最终成果报告…")
        self._report_edit.setStyleSheet(INPUT_STYLE)
        self._report_edit.setFixedHeight(80)
        rep_col.addWidget(self._report_edit)

        ref_col = QVBoxLayout()
        ref_col.addWidget(SubHeader("学习反思"))
        self._reflection_edit = QTextEdit()
        self._reflection_edit.setPlaceholderText("学习反思和心得…")
        self._reflection_edit.setStyleSheet(INPUT_STYLE)
        self._reflection_edit.setFixedHeight(80)
        ref_col.addWidget(self._reflection_edit)

        rep_ref.addLayout(rep_col)
        rep_ref.addLayout(ref_col)
        ll.addLayout(rep_ref)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        pdf_btn = QPushButton("导入单份 PDF")
        pdf_btn.setStyleSheet(GHOST_BTN)
        pdf_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: pdf_btn.setIcon(qta.icon("ri.file-pdf-line", color=TEXT_SEC))
            except: pass
        pdf_btn.clicked.connect(self._import_pdf)

        batch_btn = QPushButton("批量导入 PDF")
        batch_btn.setStyleSheet(GHOST_BTN)
        batch_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: batch_btn.setIcon(qta.icon("ri.folder-upload-line", color=TEXT_SEC))
            except: pass
        batch_btn.clicked.connect(self._batch_import_pdf)

        self._eval_btn = QPushButton("开始评阅 →")
        self._eval_btn.setStyleSheet(PRIMARY_BTN)
        self._eval_btn.setCursor(Qt.PointingHandCursor)
        self._eval_btn.clicked.connect(self._evaluate)

        btn_row.addWidget(pdf_btn)
        btn_row.addWidget(batch_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._eval_btn)
        ll.addLayout(btn_row)

        # ── 右栏：结果 ────────────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 0, 0, 0)
        rl.setSpacing(14)

        top_r = QHBoxLayout()
        top_r.addWidget(SectionHeader("评阅结果"))
        top_r.addStretch()
        export_btn = QPushButton("导出结果 JSON")
        export_btn.setStyleSheet(SECONDARY_BTN)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_scores)
        top_r.addWidget(export_btn)
        rl.addLayout(top_r)

        # 批量结果表格
        self._result_table = QTableWidget(0, 7)
        self._result_table.setHorizontalHeaderLabels(["姓名", "学号", "总分", "交互", "知识", "表达", "反思"])
        self._result_table.setStyleSheet(TABLE_STYLE)
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._result_table.verticalHeader().setVisible(False)
        self._result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._result_table.setMaximumHeight(200)
        self._result_table.currentCellChanged.connect(self._show_score_detail)
        rl.addWidget(self._result_table)

        # 单份详情
        rl.addWidget(SubHeader("学生详情"))
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._result_widget = QWidget()
        self._result_widget.setStyleSheet("background: transparent;")
        self._result_layout = QVBoxLayout(self._result_widget)
        self._result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_layout.setSpacing(12)

        self._empty_lbl = QLabel("评阅完成后，点击表格中的学生查看详细评语和建议")
        self._empty_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._result_layout.addWidget(self._empty_lbl)
        self._result_layout.addStretch()
        result_scroll.setWidget(self._result_widget)
        rl.addWidget(result_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([430, 500])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    # ── 任务下拉 ──────────────────────────────────────────────────────────────
    def _load_tasks_to_combo(self):
        self._task_combo.clear()
        self._task_combo.addItem("🔍 自动匹配任务（推荐批量使用）", None)
        active = session_state.current_chapters()
        for tf in data_store.list_task_files():
            cid = tf.get("chapter_id", "")
            if active and cid not in active: continue
            for t in tf.get("tasks", []):
                label = f"📖 {tf.get('chapter_title', cid)} · {t.get('title', '')}"
                item = dict(t)
                item["chapter_id"] = cid
                self._task_combo.addItem(label, item)

    def _load_bundle(self):
        bundle = []
        active = session_state.current_chapters()
        for tf in data_store.list_task_files():
            cid = tf.get("chapter_id", "")
            if active and cid not in active: continue
            knowledge = data_store.load_course(cid)
            if knowledge and tf.get("tasks"):
                bundle.append((cid, knowledge, tf))
        return bundle

    # ── PDF 导入 ──────────────────────────────────────────────────────────────
    def _import_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择学生作业 PDF", "", "PDF (*.pdf)")
        if not path: return
        self._loading.set_text(f"正在解析：{os.path.basename(path)}")
        self._loading.show(); self._loading.raise_(); self._loading.resize(self.size())
        self._worker = Worker(pdf_importer.parse_pdf_to_submission, path)
        self._worker.finished.connect(self._on_pdf_parsed)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_pdf_parsed(self, sub):
        self._loading.hide()
        self._student_id.setText(sub.get("student_id", ""))
        self._student_name.setText(sub.get("student_name", ""))
        lines = []
        for d in sub.get("dialogues", []):
            lines.append(f"学生：{d.get('student_input', '')}")
            lines.append(f"模型：{d.get('model_output', '')}")
        self._dialogue_edit.setPlainText("\n".join(lines))
        self._report_edit.setPlainText(sub.get("final_report", ""))
        self._reflection_edit.setPlainText(sub.get("reflection", ""))
        self._submission = sub

    # ── 批量 ──────────────────────────────────────────────────────────────────
    def _batch_import_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "批量选择学生作业 PDF", "", "PDF (*.pdf)")
        if not paths: return
        bundle = self._load_bundle()
        if not bundle:
            QMessageBox.warning(self, "提示", "请先在「课件导入」页面生成并保存任务。")
            return
        selected = self._task_combo.currentData()
        self._clear_results()
        self._result_table.setRowCount(0)
        self._scores = []
        self._empty_lbl.setText(f"正在批量处理 {len(paths)} 份 PDF…")
        self._empty_lbl.show()
        self._batch_worker = BatchEvalWorker(paths, bundle, selected)
        self._batch_worker.progress.connect(lambda c, t, f: self._empty_lbl.setText(f"[{c}/{t}] 正在处理：{f}"))
        self._batch_worker.one_done.connect(self._on_one_done)
        self._batch_worker.finished.connect(
            lambda r: self._empty_lbl.setText(
                f"批量评阅完成：{sum(1 for x in r if x.get('total_score', -1) >= 0)}/{len(r)} 份成功。点击学生查看详情。"
            )
        )
        self._batch_worker.error.connect(self._on_error)
        self._batch_worker.start()

    # ── 手动评阅 ──────────────────────────────────────────────────────────────
    def _evaluate(self):
        text = self._dialogue_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先粘贴对话记录或导入 PDF。")
            return
        try:
            from evaluator import parse_dialogue_text
        except Exception:
            try:
                from evaluator.io_utils import parse_dialogue_text
            except Exception:
                import importlib.util, os
                root_eval_path = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "evaluator.py"))
                spec = importlib.util.spec_from_file_location("root_evaluator", root_eval_path)
                root_eval = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(root_eval)
                parse_dialogue_text = getattr(root_eval, "parse_dialogue_text")

        dialogues = parse_dialogue_text(text)
        if len(dialogues) < 2:
            QMessageBox.warning(self, "格式错误", "请确认格式：每行以「学生：」或「模型：」开头。")
            return
        self._submission = {
            "student_id": self._student_id.text().strip() or "未知",
            "student_name": self._student_name.text().strip() or "未知",
            "dialogues": dialogues,
            "final_report": self._report_edit.toPlainText().strip(),
            "reflection": self._reflection_edit.toPlainText().strip(),
        }
        bundle = self._load_bundle()
        selected = self._task_combo.currentData()
        self._loading.set_text(f"正在评阅 {self._submission['student_name']}…")
        self._loading.show(); self._loading.raise_(); self._loading.resize(self.size())

        def do():
            if bundle:
                cid, tid, knowledge, task_data = _resolve_task(self._submission, bundle, selected)
                self._submission["chapter_id"] = cid
                self._submission["task_id"] = tid
                task = next((t for t in task_data.get("tasks", []) if t.get("task_id") == tid), None)
            else:
                knowledge, task = None, None
            return evaluator.evaluate_submission(self._submission, task, knowledge)

        self._worker = Worker(do)
        self._worker.finished.connect(self._on_eval_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_eval_done(self, score):
        self._loading.hide()
        sid = data_store.save_submission(self._submission)
        score.update({"submission_id": sid,
                       "student_id": self._submission["student_id"],
                       "student_name": self._submission["student_name"]})
        data_store.save_score(score)
        self._on_one_done(score)
        # 选中刚添加的行
        row = self._result_table.rowCount() - 1
        if row >= 0:
            self._result_table.setCurrentCell(row, 0)

    # ── 结果渲染 ──────────────────────────────────────────────────────────────
    def _on_one_done(self, score: dict):
        self._scores.append(score)
        row = self._result_table.rowCount()
        self._result_table.insertRow(row)
        total = int(score.get("total_score", -1))
        sc = score.get("scores", {})
        if total >= 85: total_color = SCORE_A
        elif total >= 70: total_color = SCORE_B
        elif total >= 60: total_color = SCORE_C
        else: total_color = SCORE_F
        values = [
            score.get("student_name", ""),
            score.get("student_id", ""),
            str(total) if total >= 0 else "错误",
            str(sc.get("interaction_quality", "")),
            str(sc.get("knowledge_mastery", "")),
            str(sc.get("presentation", "")),
            str(sc.get("reflection", "")),
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 2 and total >= 0:
                item.setForeground(QColor(total_color))
            self._result_table.setItem(row, col, item)

    def _show_score_detail(self, row, _c, _pr, _pc):
        if row < 0 or row >= len(self._scores): return
        score = self._scores[row]
        if score.get("total_score", -1) < 0: return
        self._clear_results()
        self._empty_lbl.hide()
        self._render_detail(score)

    def _render_detail(self, score: dict):
        ins = [0]
        def insert(w):
            self._result_layout.insertWidget(ins[0], w)
            ins[0] += 1

        total = score.get("total_score", 0)
        scores = score.get("scores", {})
        ia = score.get("interaction_analysis", {})
        if total >= 85: tc = SCORE_A
        elif total >= 70: tc = SCORE_B
        elif total >= 60: tc = SCORE_C
        else: tc = SCORE_F

        # 总分卡
        hcard = QFrame()
        hcard.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: none;
                border-left: 5px solid {tc};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(hcard)
        hlay = QHBoxLayout(hcard)
        hlay.setContentsMargins(20, 16, 20, 16)
        name_lbl = QLabel(f"{score.get('student_name', '')}  ·  {score.get('student_id', '')}")
        name_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 14px; background: transparent;")
        score_lbl = QLabel(str(total))
        score_lbl.setStyleSheet(f"color: {tc}; font-size: 42px; font-weight: 900; background: transparent;")
        pts = QLabel("/ 100")
        pts.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; background: transparent;")
        pts.setAlignment(Qt.AlignBottom)
        hlay.addWidget(name_lbl, 1)
        hlay.addWidget(score_lbl)
        hlay.addWidget(pts)
        insert(hcard)

        # 分项得分
        sp = make_panel("分项得分")
        sl = sp.layout()
        for lbl, val, mx, color in [
            ("交互质量", scores.get("interaction_quality", 0), 50, GREEN_PRI),
            ("知识掌握", scores.get("knowledge_mastery", 0), 25, INFO),
            ("成果表达", scores.get("presentation", 0), 15, ORANGE_PRI),
            ("学习反思", scores.get("reflection", 0), 10, WARNING),
        ]:
            sl.addWidget(ScoreBar(lbl, val, mx, color))
        insert(sp)

        # 交互行为
        ia_panel = make_panel("交互行为分析")
        il = ia_panel.layout()
        il.addWidget(make_info_row("总轮次", str(ia.get("total_rounds", 0)), GREEN_PRI))
        il.addWidget(make_info_row("有效轮次", str(ia.get("valid_rounds", 0))))
        il.addWidget(make_info_row("交互深度", ia.get("depth_level", "-")))
        il.addWidget(make_info_row(
            "包含追问", "✅ 是" if ia.get("has_follow_up") else "❌ 否",
            SCORE_A if ia.get("has_follow_up") else SCORE_F
        ))
        il.addWidget(make_info_row(
            "包含质疑", "✅ 是" if ia.get("has_questioning") else "❌ 否",
            SCORE_A if ia.get("has_questioning") else SCORE_F
        ))
        types = ia.get("interaction_types", {})
        if types:
            used_types = [f"{k}×{v}" for k, v in types.items() if v > 0]
            tl = QLabel("  ".join(used_types))
            tl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
            tl.setWordWrap(True)
            il.addWidget(tl)
        insert(ia_panel)

        # 评语
        cp = make_panel("综合评语与建议")
        cl = cp.layout()
        comment_text = score.get("comment") or score.get("readable_comment", "")
        comment = QLabel(comment_text)
        comment.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 170%; background: transparent;")
        comment.setWordWrap(True)
        cl.addWidget(comment)
        suggestions = score.get("suggestions") or score.get("improvement_suggestions", [])
        if suggestions:
            cl.addWidget(HDivider())
            for i, s in enumerate(suggestions, 1):
                row_w = QHBoxLayout()
                num = QLabel(f"{i}")
                num.setStyleSheet(f"color: white; background: {ORANGE_PRI}; border-radius: 9px; "
                                   f"font-size: 10px; font-weight: 800; padding: 1px 6px;")
                num.setFixedSize(18, 18)
                num.setAlignment(Qt.AlignCenter)
                sl_lbl = QLabel(s)
                sl_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
                sl_lbl.setWordWrap(True)
                row_w.addWidget(num, alignment=Qt.AlignTop)
                row_w.addWidget(sl_lbl, 1)
                cl.addLayout(row_w)
        insert(cp)

    def _clear_results(self):
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._empty_lbl.show()

    def _export_scores(self):
        if not self._scores:
            QMessageBox.information(self, "提示", "暂无评阅结果。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出结果", "评阅结果.json", "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._scores, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出到：{path}")

    def _on_error(self, msg: str):
        self._loading.hide()
        QMessageBox.critical(self, "操作失败", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())

    def showEvent(self, event):
        super().showEvent(event)
        self._load_tasks_to_combo()
