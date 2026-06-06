"""
Page 2: Student Evaluation — Warm Parchment Style
重新设计：
- 左栏：任务选择 + 批量/单份导入 → 学生列表
- 右栏：选中学生的对话/报告预览 + 手动触发「开始评阅」
- 评阅结果在右下方展示
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QLineEdit, QScrollArea, QFrame,
    QMessageBox, QSplitter, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy
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

# ── 小工具 ────────────────────────────────────────────────────────────────────

def _split_keywords(text: str) -> List[str]:
    return [p for p in re.split(r"[\s·：:，,、（）()《》\-]+", text or "") if len(p) >= 2]


def _match_task_score(text: str, chapter_title: str, task: Dict) -> int:
    score = 0
    title = str(task.get("title", ""))
    task_id = str(task.get("task_id", ""))
    if title and title in text:
        score += 100
    if chapter_title and chapter_title in text:
        score += 10
    cn_map = {"task001": "任务一", "task002": "任务二", "task003": "任务三",
              "task004": "任务四", "task005": "任务五"}
    if cn_map.get(task_id, "") in text:
        score += 80
    for point in task.get("inquiry_points", []):
        if point and str(point)[:12] in text:
            score += 5
    for word in _split_keywords(title):
        if word in text:
            score += 3
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
    if best:
        return best
    if bundle:
        cid, knowledge, task_data = bundle[0]
        first = task_data.get("tasks", [{}])[0]
        return cid, first.get("task_id", "task001"), knowledge, task_data
    raise ValueError("没有可用的课堂任务，请先在「课件导入」页面生成并保存任务。")


# ── PDF 批量解析（只解析，不评阅）────────────────────────────────────────────

class BatchParseWorker(QThread):
    progress   = pyqtSignal(int, int, str)      # current, total, filename
    one_parsed = pyqtSignal(dict)               # parsed submission dict
    finished   = pyqtSignal(list)               # all parsed submissions
    error      = pyqtSignal(str)

    def __init__(self, pdf_paths):
        super().__init__()
        self._paths = pdf_paths

    def run(self):
        results = []
        total = len(self._paths)
        for i, path in enumerate(self._paths, 1):
            fname = os.path.basename(path)
            self.progress.emit(i, total, fname)
            try:
                sub = pdf_importer.parse_pdf_to_submission(path, fallback_index=i)
                sub["_source_path"] = path
                sub["_parse_error"] = ""
                results.append(sub)
                self.one_parsed.emit(sub)
            except Exception as e:
                err_sub = {
                    "_source_path": path,
                    "_parse_error": str(e),
                    "student_name": os.path.splitext(fname)[0],
                    "student_id":   "",
                    "dialogues":    [],
                    "final_report": "",
                    "reflection":   "",
                }
                results.append(err_sub)
                self.one_parsed.emit(err_sub)
        self.finished.emit(results)


class SingleEvalWorker(QThread):
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, submission, bundle, selected_task):
        super().__init__()
        self._sub      = submission
        self._bundle   = bundle
        self._selected = selected_task

    def run(self):
        try:
            sub = dict(self._sub)
            if self._bundle:
                cid, tid, knowledge, task_data = _resolve_task(sub, self._bundle, self._selected)
                sub["chapter_id"] = cid
                sub["task_id"]    = tid
                task = next((t for t in task_data.get("tasks", []) if t.get("task_id") == tid), None)
            else:
                knowledge, task = None, None

            score = evaluator.evaluate_submission(sub, task, knowledge)
            sid = data_store.save_submission(sub)

            # ✅ 关键修改在这里
            score.update({
                "submission_id": sid,
                "student_id": sub.get("student_id", ""),
                "student_name": sub.get("student_name", ""),
                "chapter_id": sub.get("chapter_id", ""),
                "chapter_title": knowledge.get("chapter_title") if knowledge else sub.get("chapter_id", ""),
                "task_id": sub.get("task_id", "")
            })

            data_store.save_score(score)
            self.finished.emit(score)
        except Exception as e:
            self.error.emit(str(e))


# ── 主页面 ─────────────────────────────────────────────────────────────────────

class EvalPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parsed_submissions: List[Dict]  = []
        self._scores: Dict[int, Dict]         = {}
        self._current_idx: Optional[int]      = None
        self._parse_worker                    = None
        self._eval_worker                     = None
        # 缓存已有评阅记录的学号集合（跨会话去重提示）
        self._existing_student_ids: set = set()
        self._setup_ui()

    def _refresh_existing_ids(self):
        """刷新数据库中已评阅学生的学号缓存。"""
        try:
            scores = data_store.list_scores()
            self._existing_student_ids = {
                s.get("student_id", "") for s in scores if s.get("student_id")
            }
        except Exception:
            self._existing_student_ids = set()

    # ─────────────────────────── UI 构建 ──────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # 页头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 18)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        t = QLabel("成果评阅 · 自动评分")
        t.setStyleSheet(f"color: {TEXT_H1}; font-size: 19px; font-weight: 800; background: transparent;")
        s = QLabel("导入学生对话记录，选择学生后手动触发 AI 评阅")
        s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(t)
        title_col.addWidget(s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        root.addLayout(hdr)

        # 主体：三栏分割
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)

        # ── 左栏：导入控制 + 学生列表 ─────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(220)
        left.setMaximumWidth(340)
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 10, 0)
        ll.setSpacing(12)

        # 任务选择
        ll.addWidget(SectionHeader("任务选择"))
        task_hint = QLabel("选择指定任务，或留「自动匹配」")
        task_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        ll.addWidget(task_hint)
        self._task_combo = QComboBox()
        self._task_combo.setStyleSheet(INPUT_STYLE)
        self._load_tasks_to_combo()
        ll.addWidget(self._task_combo)

        # 导入按钮
        ll.addWidget(SectionHeader("导入学生作业"))
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        pdf_btn = QPushButton("导入单份 PDF")
        pdf_btn.setStyleSheet(GHOST_BTN)
        pdf_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                pdf_btn.setIcon(qta.icon("ri.file-pdf-line", color=TEXT_SEC))
            except Exception:
                pass
        pdf_btn.clicked.connect(self._import_single_pdf)
        btn_row1.addWidget(pdf_btn)
        ll.addLayout(btn_row1)

        batch_btn = QPushButton("批量导入 PDF（选择多份）")
        batch_btn.setStyleSheet(PRIMARY_BTN)
        batch_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                batch_btn.setIcon(qta.icon("ri.folder-upload-line", color="white"))
            except Exception:
                pass
        batch_btn.clicked.connect(self._batch_import_pdf)
        ll.addWidget(batch_btn)

        manual_btn = QPushButton("手动输入对话（粘贴）")
        manual_btn.setStyleSheet(SECONDARY_BTN)
        manual_btn.setCursor(Qt.PointingHandCursor)
        manual_btn.clicked.connect(self._open_manual_input)
        ll.addWidget(manual_btn)

        # 进度标签
        self._import_status = QLabel("")
        self._import_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        self._import_status.setWordWrap(True)
        ll.addWidget(self._import_status)

        # 学生列表
        ll.addWidget(SectionHeader("已导入学生"))
        self._student_list = QListWidget()
        self._student_list.setStyleSheet(f"""
            QListWidget {{
                background: {BG_CARD};
                border: 1.5px solid {BORDER};
                border-radius: {RADIUS}px;
                outline: none;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                margin: 2px;
                border-radius: {RADIUS_SM}px;
                color: {TEXT_PRI};
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background: {GREEN_LIGHT};
                color: {GREEN_DARK};
                font-weight: 700;
            }}
            QListWidget::item:hover:!selected {{ background: {BG_HOVER}; }}
        """)
        self._student_list.currentRowChanged.connect(self._on_student_selected)
        ll.addWidget(self._student_list, 1)

        # 清空按钮
        clear_btn = QPushButton("清空列表")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {DANGER};
                border: 1px solid {DANGER};
                border-radius: {RADIUS_SM}px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #FEE2E2; }}
        """)
        clear_btn.clicked.connect(self._clear_all)
        ll.addWidget(clear_btn)

        # 批量评阅所有学生
        self._batch_eval_btn = QPushButton("批量评阅全部学生 →")
        self._batch_eval_btn.setStyleSheet(PRIMARY_BTN)
        self._batch_eval_btn.setCursor(Qt.PointingHandCursor)
        self._batch_eval_btn.setEnabled(False)
        self._batch_eval_btn.clicked.connect(self._batch_eval_all)
        ll.addWidget(self._batch_eval_btn)

        # ── 中栏：学生详情预览 ────────────────────────────────────────────────
        mid = QWidget()
        mid.setMinimumWidth(300)
        mid.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(10, 0, 10, 0)
        ml.setSpacing(12)

        ml.addWidget(SectionHeader("学生作业预览"))

        # 学生信息编辑区
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        self._student_id_edit   = QLineEdit()
        self._student_id_edit.setPlaceholderText("学号")
        self._student_id_edit.setStyleSheet(INPUT_STYLE)
        self._student_name_edit = QLineEdit()
        self._student_name_edit.setPlaceholderText("姓名")
        self._student_name_edit.setStyleSheet(INPUT_STYLE)
        info_row.addWidget(self._student_id_edit)
        info_row.addWidget(self._student_name_edit)
        ml.addLayout(info_row)

        preview_splitter = QSplitter(Qt.Vertical)
        preview_splitter.setHandleWidth(6)
        preview_splitter.setChildrenCollapsible(False)
        preview_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {BORDER_LIGHT};
                border-radius: 3px;
            }}
            QSplitter::handle:hover {{ background: {BORDER}; }}
        """)

        dialogue_box = QWidget()
        dialogue_box.setStyleSheet("background: transparent;")
        dialogue_layout = QVBoxLayout(dialogue_box)
        dialogue_layout.setContentsMargins(0, 0, 0, 0)
        dialogue_layout.setSpacing(8)
        dialogue_layout.addWidget(SubHeader("对话记录"))
        self._dialogue_preview = QTextEdit()
        self._dialogue_preview.setReadOnly(False)
        self._dialogue_preview.setMinimumHeight(120)
        self._dialogue_preview.setPlaceholderText(
            "导入学生 PDF 后，此处显示解析出的对话记录。\n"
            "也可直接粘贴（格式：每行以「学生：」或「模型：」开头）。"
        )
        self._dialogue_preview.setStyleSheet(INPUT_STYLE)
        dialogue_layout.addWidget(self._dialogue_preview, 1)
        preview_splitter.addWidget(dialogue_box)

        report_reflection_splitter = QSplitter(Qt.Horizontal)
        report_reflection_splitter.setHandleWidth(6)
        report_reflection_splitter.setChildrenCollapsible(False)
        report_reflection_splitter.setStyleSheet(preview_splitter.styleSheet())

        rc = QWidget()
        rc.setStyleSheet("background: transparent;")
        rc_layout = QVBoxLayout(rc)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        rc_layout.setSpacing(8)
        rc_layout.addWidget(SubHeader("最终报告"))
        self._report_edit = QTextEdit()
        self._report_edit.setPlaceholderText("最终成果报告…")
        self._report_edit.setStyleSheet(INPUT_STYLE)
        self._report_edit.setMinimumSize(130, 70)
        rc_layout.addWidget(self._report_edit, 1)

        refc = QWidget()
        refc.setStyleSheet("background: transparent;")
        refc_layout = QVBoxLayout(refc)
        refc_layout.setContentsMargins(0, 0, 0, 0)
        refc_layout.setSpacing(8)
        refc_layout.addWidget(SubHeader("学习反思"))
        self._reflection_edit = QTextEdit()
        self._reflection_edit.setPlaceholderText("学习反思和心得…")
        self._reflection_edit.setStyleSheet(INPUT_STYLE)
        self._reflection_edit.setMinimumSize(130, 70)
        refc_layout.addWidget(self._reflection_edit, 1)

        report_reflection_splitter.addWidget(rc)
        report_reflection_splitter.addWidget(refc)
        report_reflection_splitter.setSizes([1, 1])
        preview_splitter.addWidget(report_reflection_splitter)
        preview_splitter.setSizes([360, 130])
        ml.addWidget(preview_splitter, 1)

        # 评阅按钮（核心：手动触发）
        eval_row = QHBoxLayout()
        eval_row.setSpacing(10)
        self._eval_btn = QPushButton("开始评阅当前学生 →")
        self._eval_btn.setStyleSheet(PRIMARY_BTN)
        self._eval_btn.setCursor(Qt.PointingHandCursor)
        self._eval_btn.setEnabled(False)
        self._eval_btn.setFixedHeight(42)
        self._eval_btn.clicked.connect(self._evaluate_current)
        eval_row.addWidget(self._eval_btn)
        self._eval_status = QLabel("")
        self._eval_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        eval_row.addWidget(self._eval_status, 1)
        ml.addLayout(eval_row)

        # ── 右栏：评阅结果 ────────────────────────────────────────────────────
        right = QWidget()
        right.setMinimumWidth(260)
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 0, 0, 0)
        rl.setSpacing(12)

        top_r = QHBoxLayout()
        top_r.addWidget(SectionHeader("评阅结果"))
        top_r.addStretch()
        export_btn = QPushButton("导出 JSON")
        export_btn.setStyleSheet(SECONDARY_BTN)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_scores)
        top_r.addWidget(export_btn)
        rl.addLayout(top_r)

        # 结果滚动区
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._result_widget = QWidget()
        self._result_widget.setStyleSheet("background: transparent;")
        self._result_layout = QVBoxLayout(self._result_widget)
        self._result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_layout.setSpacing(12)
        self._result_layout.setAlignment(Qt.AlignTop)

        self._result_placeholder = QLabel("选择学生并点击「开始评阅」后，评语和得分将在此显示")
        self._result_placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._result_placeholder.setAlignment(Qt.AlignCenter)
        self._result_placeholder.setWordWrap(True)
        self._result_layout.addWidget(self._result_placeholder)

        result_scroll.setWidget(self._result_widget)
        rl.addWidget(result_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(mid)
        splitter.addWidget(right)
        splitter.setSizes([260, 400, 360])
        root.addWidget(splitter, 1)

        # Loading overlay
        self._loading = LoadingWidget(parent=self)
        self._loading.hide()

        # 手动输入窗口（延迟创建）
        self._manual_dialog = None

    # ─────────────────────────── 任务下拉 ────────────────────────────────────

    def _load_tasks_to_combo(self):
        self._task_combo.clear()
        self._task_combo.addItem("🔍 自动匹配任务（推荐批量使用）", None)
        active = session_state.current_chapters()
        for tf in data_store.list_task_files():
            cid = tf.get("chapter_id", "")
            if active and cid not in active:
                continue
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
            if active and cid not in active:
                continue
            knowledge = data_store.load_course(cid)
            if knowledge and tf.get("tasks"):
                bundle.append((cid, knowledge, tf))
        return bundle

    # ─────────────────────────── 导入逻辑 ────────────────────────────────────

    def _import_single_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择学生作业 PDF", "", "PDF (*.pdf)")
        if not path:
            return
        self._import_status.setText(f"正在解析：{os.path.basename(path)}…")
        self._loading.set_text(f"正在解析：{os.path.basename(path)}")
        self._loading.show()
        self._loading.raise_()
        self._loading.resize(self.size())

        def do():
            fallback_index = len(self._parsed_submissions) + 1
            return pdf_importer.parse_pdf_to_submission(path, fallback_index=fallback_index)

        self._parse_worker = Worker(do)
        self._parse_worker.finished.connect(self._on_single_parsed)
        self._parse_worker.error.connect(self._on_parse_error)
        self._parse_worker.start()

    def _on_single_parsed(self, sub: dict):
        self._loading.hide()
        sub["_source_path"] = sub.get("_source_path", "")
        sub["_parse_error"] = ""
        self._add_parsed_submission(sub)
        # 自动选中
        idx = len(self._parsed_submissions) - 1
        self._student_list.setCurrentRow(idx)
        self._import_status.setText(f"已导入 {len(self._parsed_submissions)} 位学生")

    def _batch_import_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "批量选择学生作业 PDF", "", "PDF (*.pdf)"
        )
        if not paths:
            return
        self._import_status.setText(f"正在批量解析 {len(paths)} 份 PDF…")
        self._parse_worker = BatchParseWorker(paths)
        self._parse_worker.progress.connect(
            lambda c, t, f: self._import_status.setText(f"[{c}/{t}] 解析：{f}")
        )
        self._parse_worker.one_parsed.connect(self._add_parsed_submission)
        self._parse_worker.finished.connect(self._on_batch_parsed)
        self._parse_worker.error.connect(self._on_parse_error)
        self._parse_worker.start()

    def _on_batch_parsed(self, results: list):
        ok = sum(1 for r in results if not r.get("_parse_error"))
        fail = len(results) - ok
        msg = f"✅ 已解析 {ok} 份"
        if fail:
            msg += f"，{fail} 份失败"
        msg += "。请在列表中选择学生，再点击「开始评阅」。"
        self._import_status.setText(msg)

    def _on_parse_error(self, msg: str):
        self._loading.hide()
        self._import_status.setText(f"❌ 解析失败：{msg}")

    def _add_parsed_submission(self, sub: dict):
        """把解析好的学生提交加入列表（不评阅），并检测重复导入。"""
        sid  = (sub.get("student_id") or "").strip()
        name = sub.get("student_name", "")

        # ── 会话内重复检测 ─────────────────────────────────────────────────
        if sid:
            for i, existing in enumerate(self._parsed_submissions):
                if (existing.get("student_id") or "").strip() == sid:
                    reply = QMessageBox.question(
                        self, "重复导入",
                        f"学生 {name or sid}（学号：{sid}）已在列表中。\n"
                        "是否覆盖原有记录？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if reply == QMessageBox.Yes:
                        self._parsed_submissions[i] = sub
                        n = len(sub.get("dialogues", []))
                        lbl = f"👤  {name or f'学生{i+1}'}"
                        if sid: lbl += f"  {sid}"
                        lbl += f"  |  {n} 轮"
                        self._student_list.item(i).setText(lbl)
                    # 无论覆盖还是跳过，都不再追加新行
                    return

        self._parsed_submissions.append(sub)
        idx = len(self._parsed_submissions) - 1
        n_rounds = len(sub.get("dialogues", []))

        if sub.get("_parse_error"):
            label = f"❌  {name or f'学生{idx+1}'}（解析失败）"
        else:
            has_record = bool(sid and sid in self._existing_student_ids)
            prefix = "⚠️" if has_record else "👤"
            label = f"{prefix}  {name or f'学生{idx+1}'}"
            if sid:
                label += f"  {sid}"
            label += f"  |  {n_rounds} 轮"
            if has_record:
                label += "  [已有评阅记录]"

        self._student_list.addItem(QListWidgetItem(label))
        self._batch_eval_btn.setEnabled(True)

    def _open_manual_input(self):
        """弹出手动输入对话框"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("手动输入对话记录")
        dlg.setMinimumSize(560, 420)
        dlg.setStyleSheet(f"background: {BG_APP};")
        ly = QVBoxLayout(dlg)
        ly.setContentsMargins(20, 18, 20, 18)
        ly.setSpacing(12)

        ly.addWidget(SubHeader("学生信息"))
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        sid_edit  = QLineEdit()
        sid_edit.setPlaceholderText("学号")
        sid_edit.setStyleSheet(INPUT_STYLE)
        sname_edit = QLineEdit()
        sname_edit.setPlaceholderText("姓名")
        sname_edit.setStyleSheet(INPUT_STYLE)
        info_row.addWidget(sid_edit)
        info_row.addWidget(sname_edit)
        ly.addLayout(info_row)

        ly.addWidget(SubHeader("对话记录（每行以「学生：」或「模型：」开头）"))
        text_edit = QTextEdit()
        text_edit.setStyleSheet(INPUT_STYLE)
        text_edit.setPlaceholderText(
            "学生：分治法的基本思想是什么？\n模型：分治法将原问题分解为...\n学生：我理解分治就是大事化小，对吗？"
        )
        ly.addWidget(text_edit, 1)

        ly.addWidget(SubHeader("最终报告（选填）"))
        report_edit = QTextEdit()
        report_edit.setStyleSheet(INPUT_STYLE)
        report_edit.setFixedHeight(60)
        ly.addWidget(report_edit)

        ly.addWidget(SubHeader("学习反思（选填）"))
        ref_edit = QTextEdit()
        ref_edit.setStyleSheet(INPUT_STYLE)
        ref_edit.setFixedHeight(60)
        ly.addWidget(ref_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("添加到列表")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet(PRIMARY_BTN)
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet(GHOST_BTN)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        ly.addWidget(btn_box)

        if dlg.exec_() == QDialog.Accepted:
            raw = text_edit.toPlainText().strip()
            if not raw:
                return
            try:
                from evaluator import parse_dialogue_text
            except Exception:
                from evaluator.io_utils import parse_dialogue_text
            dialogues = parse_dialogue_text(raw)
            if len(dialogues) < 1:
                QMessageBox.warning(self, "格式错误",
                                    "请确认格式：每行以「学生：」或「模型：」开头。")
                return
            sub = {
                "student_id":   sid_edit.text().strip() or "manual",
                "student_name": sname_edit.text().strip() or "手动输入",
                "dialogues":    dialogues,
                "final_report": report_edit.toPlainText().strip(),
                "reflection":   ref_edit.toPlainText().strip(),
                "_source_path": "",
                "_parse_error": "",
            }
            self._add_parsed_submission(sub)
            idx = len(self._parsed_submissions) - 1
            self._student_list.setCurrentRow(idx)

    # ─────────────────────────── 学生选择 ────────────────────────────────────

    def _on_student_selected(self, row: int):
        if row < 0 or row >= len(self._parsed_submissions):
            return
        self._current_idx = row
        sub = self._parsed_submissions[row]

        # 填充预览区
        self._student_id_edit.setText(sub.get("student_id", ""))
        self._student_name_edit.setText(sub.get("student_name", ""))

        lines = []
        for d in sub.get("dialogues", []):
            lines.append(f"学生：{d.get('student_input', '')}")
            lines.append(f"模型：{d.get('model_output', '')}")
        self._dialogue_preview.setPlainText("\n".join(lines))
        self._report_edit.setPlainText(sub.get("final_report", ""))
        self._reflection_edit.setPlainText(sub.get("reflection", ""))

        # 如果已评阅，显示已有结果；否则清空结果区
        if row in self._scores:
            self._clear_result()
            self._render_score(self._scores[row])
            self._eval_btn.setText("重新评阅 →")
        else:
            self._clear_result()
            self._eval_btn.setText("开始评阅当前学生 →")

        self._eval_btn.setEnabled(not bool(sub.get("_parse_error")))
        self._eval_status.setText("")

    # ─────────────────────────── 评阅逻辑 ────────────────────────────────────

    def _collect_current_submission(self) -> Optional[Dict]:
        """从预览区收集最新内容（用户可能手动修改过）"""
        if self._current_idx is None:
            return None
        raw_text = self._dialogue_preview.toPlainText().strip()
        if not raw_text:
            return None

        try:
            from evaluator import parse_dialogue_text
        except Exception:
            from evaluator.io_utils import parse_dialogue_text

        dialogues = parse_dialogue_text(raw_text)

        sub = dict(self._parsed_submissions[self._current_idx])
        sub["student_id"]   = self._student_id_edit.text().strip() or sub.get("student_id", "unknown")
        sub["student_name"] = self._student_name_edit.text().strip() or sub.get("student_name", "未知")
        sub["dialogues"]    = dialogues
        sub["final_report"] = self._report_edit.toPlainText().strip()
        sub["reflection"]   = self._reflection_edit.toPlainText().strip()
        return sub

    def _evaluate_current(self):
        sub = self._collect_current_submission()
        if not sub:
            QMessageBox.warning(self, "提示", "当前学生无有效对话记录，请检查。")
            return
        if len(sub.get("dialogues", [])) < 2:
            QMessageBox.warning(self, "格式错误",
                                "对话记录需至少 2 轮。\n请确认格式：每行以「学生：」或「模型：」开头。")
            return

        self._eval_btn.setEnabled(False)
        self._eval_status.setText("评阅中…")
        bundle = self._load_bundle()
        selected = self._task_combo.currentData()

        self._eval_worker = SingleEvalWorker(sub, bundle, selected)
        self._eval_worker.finished.connect(self._on_eval_done)
        self._eval_worker.error.connect(self._on_eval_error)
        self._eval_worker.start()

    def _batch_eval_all(self):
        """依次评阅所有未评阅学生"""
        pending = [i for i in range(len(self._parsed_submissions))
                   if i not in self._scores and not self._parsed_submissions[i].get("_parse_error")]
        if not pending:
            QMessageBox.information(self, "提示", "所有学生均已评阅。")
            return
        reply = QMessageBox.question(
            self, "批量评阅",
            f"将依次评阅 {len(pending)} 位未评阅学生，这可能需要较长时间（每位约 15-40 秒）。\n确认继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        # 选中第一个pending学生，开始链式评阅
        self._pending_queue = pending
        self._eval_next_in_queue()

    def _eval_next_in_queue(self):
        if not hasattr(self, '_pending_queue') or not self._pending_queue:
            QMessageBox.information(self, "批量完成",
                                    f"批量评阅完成，共评阅 {len(self._scores)} 位学生。")
            return
        idx = self._pending_queue.pop(0)
        self._student_list.setCurrentRow(idx)
        # 短暂延迟后触发评阅
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(300, self._evaluate_current)

    def _on_eval_done(self, score: dict):
        self._eval_btn.setEnabled(True)
        self._eval_btn.setText("重新评阅 →")
        self._eval_status.setText(f"✅ 评阅完成  总分：{score.get('total_score', 0)}")

        if self._current_idx is not None:
            self._scores[self._current_idx] = score
            # 更新列表项标记
            item = self._student_list.item(self._current_idx)
            if item:
                sub   = self._parsed_submissions[self._current_idx]
                name  = sub.get("student_name", "")
                total = score.get("total_score", 0)
                item.setText(f"✅  {name}  →  {total} 分")
                item.setForeground(QColor(SCORE_A if total >= 85 else SCORE_B if total >= 70 else SCORE_F))

        self._clear_result()
        self._render_score(score)

        # 如果是批量模式，继续下一个
        if hasattr(self, '_pending_queue') and self._pending_queue:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self._eval_next_in_queue)

    def _on_eval_error(self, msg: str):
        self._eval_btn.setEnabled(True)
        self._eval_status.setText(f"❌ 评阅失败：{msg[:60]}")
        QMessageBox.critical(self, "评阅失败", msg)

        if hasattr(self, '_pending_queue') and self._pending_queue:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self._eval_next_in_queue)

    # ─────────────────────────── 结果渲染 ────────────────────────────────────

    def _clear_result(self):
        while self._result_layout.count():
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._result_placeholder = QLabel("评阅中…")
        self._result_placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._result_placeholder.setAlignment(Qt.AlignCenter)
        self._result_layout.addWidget(self._result_placeholder)

    def _render_score(self, score: dict):
        # 先移除placeholder
        while self._result_layout.count():
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total  = score.get("total_score", 0)
        scores = score.get("scores", {})
        ia     = score.get("interaction_analysis", {})

        if total >= 85:   tc = SCORE_A
        elif total >= 70: tc = SCORE_B
        elif total >= 60: tc = SCORE_C
        else:             tc = SCORE_F

        def insert(w):
            self._result_layout.addWidget(w)

        # 总分卡
        hcard = QFrame()
        hcard.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        add_shadow(hcard, blur=10, offset_y=3)
        hlay = QHBoxLayout(hcard)
        hlay.setContentsMargins(16, 14, 16, 14)
        name_lbl = QLabel(f"{score.get('student_name', '')}  ·  {score.get('student_id', '')}")
        name_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px; background: transparent;")
        score_lbl = QLabel(str(total))
        score_lbl.setStyleSheet(f"color: {tc}; font-size: 38px; font-weight: 900; background: transparent;")
        pts = QLabel("/ 100")
        pts.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; background: transparent;")
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
            ("知识掌握", scores.get("knowledge_mastery", 0),   25, INFO),
            ("成果表达", scores.get("presentation", 0),        15, ORANGE_PRI),
            ("学习反思", scores.get("reflection", 0),          10, WARNING),
        ]:
            sl.addWidget(ScoreBar(lbl, val, mx, color))
        insert(sp)

        # 交互行为
        ia_panel = make_panel("交互分析")
        il = ia_panel.layout()
        il.addWidget(make_info_row("总轮次",   str(ia.get("total_rounds", 0)), GREEN_PRI))
        il.addWidget(make_info_row("有效轮次", str(ia.get("valid_rounds", 0))))
        il.addWidget(make_info_row("交互深度", ia.get("depth_level", "-")))
        il.addWidget(make_info_row(
            "包含追问",
            "✅ 是" if ia.get("has_follow_up") else "❌ 否",
            SCORE_A if ia.get("has_follow_up") else SCORE_F
        ))
        il.addWidget(make_info_row(
            "包含质疑",
            "✅ 是" if ia.get("has_questioning") else "❌ 否",
            SCORE_A if ia.get("has_questioning") else SCORE_F
        ))
        types = ia.get("interaction_types", {})
        if types:
            used = [f"{k}×{v}" for k, v in types.items() if v > 0]
            tl = QLabel("  ".join(used))
            tl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
            tl.setWordWrap(True)
            il.addWidget(tl)
        insert(ia_panel)

        # 评语与建议
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
            for i, s_text in enumerate(suggestions, 1):
                rw = QHBoxLayout()
                num = QLabel(str(i))
                num.setStyleSheet(f"""
                    color: white; background: {GREEN_PRI};
                    border-radius: 9px; font-size: 10px;
                    font-weight: 800; padding: 1px 6px;
                """)
                num.setFixedSize(18, 18)
                num.setAlignment(Qt.AlignCenter)
                s_lbl = QLabel(s_text)
                s_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; background: transparent;")
                s_lbl.setWordWrap(True)
                rw.addWidget(num, alignment=Qt.AlignTop)
                rw.addWidget(s_lbl, 1)
                cl.addLayout(rw)
        insert(cp)

    # ─────────────────────────── 工具 ────────────────────────────────────────

    def _clear_all(self):
        if not self._parsed_submissions:
            return
        reply = QMessageBox.question(
            self, "确认清空",
            "清空所有已导入学生？（已保存的评阅结果不受影响）",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._parsed_submissions.clear()
        self._scores.clear()
        self._current_idx = None
        self._student_list.clear()
        self._batch_eval_btn.setEnabled(False)
        self._eval_btn.setEnabled(False)
        self._dialogue_preview.clear()
        self._report_edit.clear()
        self._reflection_edit.clear()
        self._student_id_edit.clear()
        self._student_name_edit.clear()
        self._import_status.setText("")
        self._clear_result()

    def _export_scores(self):
        data = list(self._scores.values())
        if not data:
            QMessageBox.information(self, "提示", "暂无评阅结果。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出结果", "评阅结果.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出 {len(data)} 条结果到：{path}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_loading"):
            self._loading.resize(self.size())

    def showEvent(self, event):
        super().showEvent(event)
        self._load_tasks_to_combo()
        self._refresh_existing_ids()
