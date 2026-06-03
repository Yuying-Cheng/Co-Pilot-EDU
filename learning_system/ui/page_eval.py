"""
Page 2: Student Evaluation — Swiss minimalist
Supports single manual entry, single PDF import, and batch PDF import.
"""

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QLineEdit, QScrollArea, QFrame,
    QMessageBox, QSplitter, QComboBox, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.styles import *
from ui.widgets import Worker, SectionHeader, ScoreBar, LoadingWidget, StatCard, make_info_row, HDivider
import evaluator, data_store, pdf_importer

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class BatchImportWorker(QThread):
    """Worker thread: parse multiple PDFs → evaluate each → collect results."""
    progress = pyqtSignal(int, int, str)   # current, total, filename
    one_done = pyqtSignal(dict)            # emitted after each successful evaluation
    finished = pyqtSignal(list)            # list of score dicts
    error = pyqtSignal(str)

    def __init__(self, pdf_paths: list, chapter_id: str, task_id: str,
                 task: dict, knowledge: dict):
        super().__init__()
        self._paths = pdf_paths
        self._chapter_id = chapter_id
        self._task_id = task_id
        self._task = task
        self._knowledge = knowledge

    def run(self):
        results = []
        total = len(self._paths)
        for i, path in enumerate(self._paths, 1):
            fname = os.path.basename(path)
            self.progress.emit(i, total, fname)
            try:
                submission = pdf_importer.parse_pdf_to_submission(
                    path,
                    chapter_id=self._chapter_id,
                    task_id=self._task_id,
                )
                score = evaluator.evaluate_submission(submission, self._task, self._knowledge)
                sid = data_store.save_submission(submission)
                score.update({
                    "submission_id": sid,
                    "student_id": submission["student_id"],
                    "student_name": submission["student_name"],
                })
                data_store.save_score(score)
                results.append(score)
                self.one_done.emit(score)
            except Exception as e:
                results.append({
                    "student_name": os.path.splitext(fname)[0],
                    "student_id": "",
                    "total_score": -1,
                    "error": str(e),
                })
        self.finished.emit(results)


class EvalPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._submission = None
        self._worker = None
        self._batch_worker = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("成果评阅 · 自动评分")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ── Left: input ───────────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 24, 0)
        ll.setSpacing(16)

        ll.addWidget(SectionHeader("学生信息"))
        ll.addWidget(self._build_info_row())

        ll.addWidget(SectionHeader("对话记录"))
        hint = QLabel("每行以「学生：」或「模型：」开头，支持直接粘贴；或使用下方按钮导入 PDF")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        ll.addWidget(hint)

        self._dialogue_edit = QTextEdit()
        self._dialogue_edit.setPlaceholderText(
            "学生：分治法的基本思想是什么？\n模型：分治法将原问题分解…\n学生：那递归结构是…"
        )
        self._dialogue_edit.setStyleSheet(INPUT_STYLE)
        ll.addWidget(self._dialogue_edit, 2)

        ll.addWidget(SectionHeader("成果报告"))
        self._report_edit = QTextEdit()
        self._report_edit.setPlaceholderText("学生最终报告…")
        self._report_edit.setStyleSheet(INPUT_STYLE)
        self._report_edit.setFixedHeight(90)
        ll.addWidget(self._report_edit)

        ll.addWidget(SectionHeader("学习反思"))
        self._reflection_edit = QTextEdit()
        self._reflection_edit.setPlaceholderText("学习反思…")
        self._reflection_edit.setStyleSheet(INPUT_STYLE)
        self._reflection_edit.setFixedHeight(70)
        ll.addWidget(self._reflection_edit)

        # Button row
        btn_row = QHBoxLayout()

        # Single PDF import
        pdf_btn = QPushButton("导入学生 PDF")
        pdf_btn.setStyleSheet(GHOST_BTN)
        pdf_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: pdf_btn.setIcon(qta.icon("ri.file-pdf-line", color=TEXT_SEC))
            except: pass
        pdf_btn.clicked.connect(self._import_pdf)

        # Batch PDF import
        batch_btn = QPushButton("批量导入 PDF")
        batch_btn.setStyleSheet(GHOST_BTN)
        batch_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: batch_btn.setIcon(qta.icon("ri.folder-open-line", color=TEXT_SEC))
            except: pass
        batch_btn.clicked.connect(self._batch_import_pdf)

        self._eval_btn = QPushButton("开始评阅")
        self._eval_btn.setStyleSheet(PRIMARY_BTN)
        self._eval_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._eval_btn.setIcon(qta.icon("ri.robot-line", color="white"))
            except: pass
        self._eval_btn.clicked.connect(self._evaluate)

        btn_row.addWidget(pdf_btn)
        btn_row.addWidget(batch_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._eval_btn)
        ll.addLayout(btn_row)

        # ── Right: results ────────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(24, 0, 0, 0)
        rl.setSpacing(16)

        rl.addWidget(SectionHeader("评阅结果"))
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._result_widget = QWidget()
        self._result_widget.setStyleSheet("background: transparent;")
        self._result_layout = QVBoxLayout(self._result_widget)
        self._result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_layout.setSpacing(12)

        self._empty_lbl = QLabel("评阅结果将在此显示")
        self._empty_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._result_layout.addWidget(self._empty_lbl)
        self._result_layout.addStretch()

        result_scroll.setWidget(self._result_widget)
        rl.addWidget(result_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([420, 480])
        root.addWidget(splitter, 1)

        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

    def _build_info_row(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._student_id = QLineEdit()
        self._student_id.setPlaceholderText("学号")
        self._student_id.setStyleSheet(INPUT_STYLE)

        self._student_name = QLineEdit()
        self._student_name.setPlaceholderText("姓名")
        self._student_name.setStyleSheet(INPUT_STYLE)

        self._task_combo = QComboBox()
        self._task_combo.setStyleSheet(INPUT_STYLE)
        self._load_tasks_to_combo()

        lay.addWidget(self._student_id)
        lay.addWidget(self._student_name)
        lay.addWidget(self._task_combo, 1)
        return w

    def _load_tasks_to_combo(self):
        self._task_combo.clear()
        self._task_combo.addItem("选择任务（可选）", None)
        for tf in data_store.list_task_files():
            for t in tf.get("tasks", []):
                self._task_combo.addItem(
                    f"{tf.get('chapter_title','')} · {t.get('title','')}", t)

    def _get_selected_task_and_knowledge(self):
        """Return (task, knowledge) from current combo selection, or (None, None)."""
        task = self._task_combo.currentData()
        knowledge = None
        if task:
            # Find the knowledge for this task's chapter
            task_files = data_store.list_task_files()
            for tf in task_files:
                if task in tf.get("tasks", []):
                    cid = tf.get("chapter_id", "")
                    knowledge = data_store.load_course(cid)
                    break
        return task, knowledge

    # ── Single PDF import ─────────────────────────────────────────────────────

    def _import_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择学生作业 PDF", "", "PDF 文件 (*.pdf)")
        if not path:
            return

        task, knowledge = self._get_selected_task_and_knowledge()
        chapter_id = knowledge.get("chapter_id", "ch01") if knowledge else "ch01"
        task_id = task.get("task_id", "task001") if task else "task001"

        self._loading.set_text(f"正在解析 PDF：{os.path.basename(path)}…")
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

        def _parse():
            return pdf_importer.parse_pdf_to_submission(
                path, chapter_id=chapter_id, task_id=task_id)

        self._worker = Worker(_parse)
        self._worker.finished.connect(self._on_pdf_parsed)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_pdf_parsed(self, submission: dict):
        self._loading.hide()
        self._student_id.setText(submission.get("student_id", ""))
        self._student_name.setText(submission.get("student_name", ""))
        lines = []
        for d in submission.get("dialogues", []):
            lines.append(f"学生：{d.get('student_input', '')}")
            lines.append(f"模型：{d.get('model_output', '')}")
        self._dialogue_edit.setPlainText("\n".join(lines))
        self._report_edit.setPlainText(submission.get("final_report", ""))
        self._reflection_edit.setPlainText(submission.get("reflection", ""))
        self._submission = submission

    # ── Batch PDF import ──────────────────────────────────────────────────────

    def _batch_import_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "批量选择学生作业 PDF（可多选）", "", "PDF 文件 (*.pdf)")
        if not paths:
            return

        task, knowledge = self._get_selected_task_and_knowledge()
        if not task or not knowledge:
            QMessageBox.warning(self, "提示", "批量导入前请先在上方选择对应任务，以便系统关联知识点进行评分。")
            return

        chapter_id = knowledge.get("chapter_id", "ch01")
        task_id = task.get("task_id", "task001")

        # Clear previous results
        self._clear_results()
        self._empty_lbl.setText(f"正在批量处理 {len(paths)} 份 PDF…")
        self._empty_lbl.show()

        self._batch_worker = BatchImportWorker(paths, chapter_id, task_id, task, knowledge)
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.one_done.connect(self._on_one_batch_done)
        self._batch_worker.finished.connect(self._on_batch_finished)
        self._batch_worker.error.connect(self._on_error)
        self._batch_worker.start()

    def _on_batch_progress(self, current: int, total: int, filename: str):
        self._empty_lbl.setText(f"[{current}/{total}] 正在处理：{filename}")

    def _on_one_batch_done(self, score: dict):
        """Render a compact result card for each completed student."""
        if score.get("total_score", -1) < 0:
            # Error card
            err_lbl = QLabel(f"✗ {score.get('student_name','')}：{score.get('error','未知错误')}")
            err_lbl.setStyleSheet(f"color: {ACCENT4}; font-size: 11px; background: transparent;")
            err_lbl.setWordWrap(True)
            self._result_layout.insertWidget(self._result_layout.count() - 1, err_lbl)
            return

        total = score.get("total_score", 0)
        total_color = ACCENT2 if total >= 85 else (ACCENT3 if total >= 70 else ACCENT4)
        card = QFrame()
        card.setStyleSheet(f"""QFrame {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-left: 3px solid {total_color};
            border-radius: {RADIUS}px;
        }}""")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(16, 10, 16, 10)
        name_lbl = QLabel(f"{score.get('student_name','')}  ·  {score.get('student_id','')}")
        name_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 12px; font-weight: 600; background: transparent;")
        score_lbl = QLabel(f"{total} 分")
        score_lbl.setStyleSheet(f"color: {total_color}; font-size: 20px; font-weight: 800; background: transparent;")
        cl.addWidget(name_lbl, 1)
        cl.addWidget(score_lbl)
        self._result_layout.insertWidget(self._result_layout.count() - 1, card)

    def _on_batch_finished(self, results: list):
        ok = sum(1 for r in results if r.get("total_score", -1) >= 0)
        self._empty_lbl.setText(f"批量评阅完成：{ok}/{len(results)} 份成功，结果已保存，可在学情统计页查看。")

    # ── Manual evaluation ─────────────────────────────────────────────────────

    def _evaluate(self):
        text = self._dialogue_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先粘贴对话记录或导入 PDF。")
            return
        dialogues = evaluator.parse_dialogue_text(text)
        if len(dialogues) < 2:
            QMessageBox.warning(self, "格式错误", "请确认对话格式：每行以「学生：」或「模型：」开头。")
            return

        self._submission = {
            "student_id":   self._student_id.text().strip() or "未知",
            "student_name": self._student_name.text().strip() or "未知",
            "dialogues":    dialogues,
            "final_report": self._report_edit.toPlainText().strip(),
            "reflection":   self._reflection_edit.toPlainText().strip(),
        }
        task, knowledge = self._get_selected_task_and_knowledge()

        self._loading.set_text(f"正在评阅 {self._submission['student_name']} 的成果…")
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

        self._worker = Worker(evaluator.evaluate_submission, self._submission, task, knowledge)
        self._worker.finished.connect(self._on_eval_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_eval_done(self, score: dict):
        self._loading.hide()
        sid = data_store.save_submission(self._submission)
        score.update({"submission_id": sid,
                      "student_id": self._submission["student_id"],
                      "student_name": self._submission["student_name"]})
        data_store.save_score(score)
        self._render_results(score)

    # ── Results rendering ─────────────────────────────────────────────────────

    def _clear_results(self):
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_lbl.show()

    def _render_results(self, score: dict):
        self._clear_results()
        self._empty_lbl.hide()

        total = score.get("total_score", 0)
        scores = score.get("scores", {})
        ia = score.get("interaction_analysis", {})
        total_color = ACCENT2 if total >= 85 else (ACCENT3 if total >= 70 else ACCENT4)
        ins = 0

        def insert(w):
            nonlocal ins
            self._result_layout.insertWidget(ins, w)
            ins += 1

        # Score header card
        hcard = QFrame()
        hcard.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-left: 3px solid {total_color};
                border-radius: {RADIUS}px;
            }}
        """)
        hc_lay = QHBoxLayout(hcard)
        hc_lay.setContentsMargins(20, 16, 20, 16)
        name_lbl = QLabel(f"{score.get('student_name','')}  ·  {score.get('student_id','')}")
        name_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 600; font-size: 13px; background: transparent;")
        total_lbl = QLabel(str(total))
        total_lbl.setStyleSheet(f"color: {total_color}; font-size: 36px; font-weight: 800; background: transparent;")
        pts = QLabel("/ 100")
        pts.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; background: transparent;")
        pts.setAlignment(Qt.AlignBottom)
        hc_lay.addWidget(name_lbl, 1)
        hc_lay.addWidget(total_lbl)
        hc_lay.addWidget(pts)
        insert(hcard)

        # Score bars
        scard = self._make_panel("分项得分")
        sl = scard.layout()
        for label, val, mx, color in [
            ("交互质量", scores.get("interaction_quality", 0), 50, ACCENT),
            ("知识掌握", scores.get("knowledge_mastery", 0), 25, ACCENT2),
            ("成果呈现", scores.get("presentation", 0), 15, ACCENT5),
            ("学习反思", scores.get("reflection", 0), 10, ACCENT3),
        ]:
            sl.addWidget(ScoreBar(label, val, mx, color))
        insert(scard)

        # Interaction analysis
        iacard = self._make_panel("交互分析")
        il = iacard.layout()
        il.addWidget(make_info_row("总轮次", str(ia.get("total_rounds", 0)), ACCENT))
        il.addWidget(make_info_row("有效轮次", str(ia.get("valid_rounds", 0))))
        il.addWidget(make_info_row("交互深度", ia.get("depth_level", "-")))
        il.addWidget(make_info_row("包含追问",
            "是" if ia.get("has_follow_up") else "否",
            ACCENT2 if ia.get("has_follow_up") else ACCENT4))
        il.addWidget(make_info_row("包含质疑",
            "是" if ia.get("has_questioning") else "否",
            ACCENT2 if ia.get("has_questioning") else ACCENT4))
        types = ia.get("interaction_types", {})
        if types:
            t_str = "  ".join(f"{k} ×{v}" for k, v in types.items() if v > 0)
            tl = QLabel(t_str)
            tl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
            tl.setWordWrap(True)
            il.addWidget(tl)
        if ia.get("interaction_quality_details"):
            dl = QLabel(ia["interaction_quality_details"])
            dl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
            dl.setWordWrap(True)
            il.addWidget(dl)
        insert(iacard)

        # Comment & suggestions
        ccard = self._make_panel("综合评语")
        cl = ccard.layout()
        comment_text = score.get("comment") or score.get("readable_comment", "")
        comment = QLabel(comment_text)
        comment.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%; background: transparent;")
        comment.setWordWrap(True)
        cl.addWidget(comment)
        suggestions = score.get("suggestions") or score.get("improvement_suggestions", [])
        for i, s in enumerate(suggestions, 1):
            sl_lbl = QLabel(f"{i}.  {s}")
            sl_lbl.setStyleSheet(f"color: {ACCENT3}; font-size: 11px; background: transparent;")
            sl_lbl.setWordWrap(True)
            cl.addWidget(sl_lbl)
        insert(ccard)

    def _make_panel(self, title: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px; }}")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        hdr = QLabel(title.upper())
        hdr.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        lay.addWidget(hdr)
        lay.addWidget(HDivider())
        return f

    def _on_error(self, msg: str):
        self._loading.hide()
        QMessageBox.critical(self, "操作失败", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())
