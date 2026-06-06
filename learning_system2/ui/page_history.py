"""
Page 4: History Data Management — Warm Academic Style
历史数据管理：查看所有评阅记录、导出、清理（差距6补充）
"""

import json
import os
from typing import List, Dict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QScrollArea, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QComboBox, QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from ui.styles import *
from ui.widgets import (
    SectionHeader, SubHeader, HDivider, make_info_row, add_shadow, make_panel,
    make_svg_widget, ILLUSTRATION_CHART
)
import data_store

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

def get_chapter_name(chapter_id):
    """根据 chapter_id 从 data/courses 中读取中文章节名。"""
    if not chapter_id:
        return "-"

    try:
        course = data_store.load_course(chapter_id)
        if course:
            return course.get("chapter_title") or chapter_id
    except Exception as e:
        print(f"[HistoryPage] 读取章节名失败: {chapter_id}, {e}")

    return chapter_id


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_scores: List[Dict] = []
        self._filtered_scores: List[Dict] = []
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
        QLabel_t = QLabel("历史数据 · 记录管理")
        QLabel_t.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        QLabel_s = QLabel("查看所有评阅记录，支持按章节筛选、导出和清理")
        QLabel_s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(QLabel_t)
        title_col.addWidget(QLabel_s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        root.addLayout(hdr)

        # ── 筛选栏 ────────────────────────────────────────────────────────────
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: none;
                border-radius: {RADIUS}px;
            }}
        """)
        fl = QHBoxLayout(filter_card)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        fl.addWidget(QLabel("章节："))
        self._chapter_combo = QComboBox()
        self._chapter_combo.setStyleSheet(INPUT_STYLE)
        self._chapter_combo.setFixedWidth(200)
        self._chapter_combo.addItem("全部章节", None)
        self._chapter_combo.currentIndexChanged.connect(self._apply_filter)
        fl.addWidget(self._chapter_combo)

        fl.addWidget(QLabel("搜索："))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入姓名或学号搜索…")
        self._search_input.setStyleSheet(INPUT_STYLE)
        self._search_input.setFixedWidth(200)
        self._search_input.textChanged.connect(self._apply_filter)
        fl.addWidget(self._search_input)

        fl.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(GHOST_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: refresh_btn.setIcon(qta.icon("ri.refresh-line", color=TEXT_SEC))
            except: pass
        refresh_btn.clicked.connect(self.refresh)
        fl.addWidget(refresh_btn)

        export_all_btn = QPushButton("导出全部")
        export_all_btn.setStyleSheet(SECONDARY_BTN)
        export_all_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: export_all_btn.setIcon(qta.icon("ri.download-line", color=TEXT_SEC))
            except: pass
        export_all_btn.clicked.connect(self._export_all)
        fl.addWidget(export_all_btn)

        clear_btn = QPushButton("清除选中")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {DANGER};
                border: 1.5px solid {DANGER};
                border-radius: {RADIUS}px;
                padding: 9px 18px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: #FBEEE9; }}
        """)
        clear_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: clear_btn.setIcon(qta.icon("ri.delete-bin-line", color=DANGER))
            except: pass
        clear_btn.clicked.connect(self._delete_selected)
        fl.addWidget(clear_btn)

        root.addWidget(filter_card)
        root.addSpacing(16)

        # ── 主体分栏 ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # 左：列表表格
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 16, 0)
        ll.setSpacing(10)

        # 统计行
        self._summary_lbl = QLabel("共 0 条记录")
        self._summary_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        ll.addWidget(self._summary_lbl)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(["姓名", "学号", "章节", "总分", "交互", "知识", "提交时间"])
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: transparent;
                selection-background-color: transparent;
                color: {TEXT_PRI};
                font-size: 13px;
            }}
            QHeaderView::section {{
                background: transparent;
                color: {TEXT_SEC};
                border: none;
                padding: 8px 10px 14px 10px;
                font-weight: 800;
                font-size: 12px;
            }}
            QTableWidget::item {{
                border: none;
                padding: 0;
                background: transparent;
            }}
            QTableWidget::item:selected {{
                background: transparent;
                color: {TEXT_PRI};
            }}
        """)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.setContentsMargins(0, 0, 0, 0)
        self._table.setViewportMargins(0, 0, 0, 0)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setFixedHeight(42)
        self._table.verticalHeader().setDefaultSectionSize(68)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.ExtendedSelection)
        self._table.currentCellChanged.connect(self._show_detail)
        ll.addWidget(self._table, 1)

        # 右：详情
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 0, 0, 0)
        rl.setSpacing(12)

        rl.addWidget(SectionHeader("记录详情"))

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._detail_widget = QWidget()
        self._detail_widget.setStyleSheet("background: transparent;")
        self._detail_layout = QVBoxLayout(self._detail_widget)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(12)

        self._detail_empty = QLabel("点击左侧列表中的记录查看详情")
        self._detail_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        self._detail_empty.setAlignment(Qt.AlignCenter)
        self._detail_layout.addWidget(self._detail_empty)
        self._detail_layout.addStretch()
        detail_scroll.setWidget(self._detail_widget)
        rl.addWidget(detail_scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([600, 380])
        root.addWidget(splitter, 1)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        raw_scores = []
        seen_chapters = set()
        for fn in sorted(os.listdir(data_store.SCORES_DIR), reverse=True):
            if fn.endswith("_score.json"):
                try:
                    with open(os.path.join(data_store.SCORES_DIR, fn), 'r', encoding='utf-8') as f:
                        s = json.load(f)
                    s['_filename'] = fn
                    raw_scores.append(s)
                    cid = s.get("chapter_id", "")
                    if cid: seen_chapters.add(cid)
                except Exception:
                    continue

        # 去重：同一学生+章节只保留最新记录
        latest: dict = {}
        for s in raw_scores:
            key = (s.get("student_id", ""), s.get("chapter_id", ""))
            if key not in latest or s.get("scored_at", "") > latest[key].get("scored_at", ""):
                latest[key] = s
        self._all_scores = list(latest.values())

        # 刷新章节筛选下拉：显示中文章节名，内部仍保存 chapter_id
        chapter_map = {}
        for s in self._all_scores:
            cid = s.get("chapter_id", "")
            if cid:
                chapter_map[cid] = get_chapter_name(cid)

        self._chapter_combo.blockSignals(True)
        self._chapter_combo.clear()
        self._chapter_combo.addItem("全部章节", None)

        for cid, cname in sorted(chapter_map.items(), key=lambda item: item[1]):
            self._chapter_combo.addItem(cname, cid)

        self._chapter_combo.blockSignals(False)



        self._apply_filter()

    def _apply_filter(self):
        chapter_filter = self._chapter_combo.currentData()
        search_text = self._search_input.text().strip().lower()

        self._filtered_scores = []
        for s in self._all_scores:
            if chapter_filter and s.get("chapter_id") != chapter_filter:
                continue
            if search_text:
                name = s.get("student_name", "").lower()
                sid = s.get("student_id", "").lower()
                if search_text not in name and search_text not in sid:
                    continue
            self._filtered_scores.append(s)

        self._render_table()

    def _render_table(self):
        self._table.clearSpans()
        self._table.setRowCount(len(self._filtered_scores))
        self._summary_lbl.setText(f"共 {len(self._filtered_scores)} 条记录")
        for row, s in enumerate(self._filtered_scores):
            self._table.setRowHeight(row, 68)
            sc = s.get("scores", {})
            total = s.get("total_score", 0)
            if total >= 85: tc = SCORE_A
            elif total >= 70: tc = SCORE_B
            elif total >= 60: tc = SCORE_C
            else: tc = SCORE_F

            scored_at = s.get("scored_at", "")[:16] if s.get("scored_at") else ""
            values = [
                    s.get("student_name", ""),
                    s.get("student_id", ""),
                    get_chapter_name(s.get("chapter_id", "")),
                    str(total),
                    str(sc.get("interaction_quality", "")),
                    str(sc.get("knowledge_mastery", "")),
                    scored_at,
                ]
            for col in range(len(values)):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, col, item)
            self._table.setSpan(row, 0, 1, len(values))
            self._table.setCellWidget(row, 0, self._make_pill_row(values, row, tc))

    def _make_pill_row(self, values: list[str], row: int, total_color: str) -> QWidget:
        outer = QWidget()
        outer.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(10, 7, 10, 7)
        outer_layout.setSpacing(0)

        card = QFrame()
        card.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        bg = "#FFFFFF" if row % 2 == 0 else "#F8FBFF"
        card.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid #D9E6F3;
                border-radius: 22px;
            }}
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(18, 10, 18, 10)
        card_layout.setSpacing(0)

        stretches = [15, 14, 22, 10, 10, 10, 19]
        for idx, val in enumerate(values):
            label = QLabel(self._short_cell_text(val, 14 if idx in (2, 6) else 10))
            label.setAlignment(Qt.AlignCenter)
            label.setToolTip(val)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            color = total_color if idx == 3 else TEXT_PRI
            label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    color: {color};
                    border: none;
                    font-size: 13px;
                    font-weight: {'800' if idx in (0, 1, 2, 4, 5, 6) else '700'};
                    padding: 6px 8px;
                }}
            """)
            card_layout.addWidget(label, stretches[idx])

        outer_layout.addWidget(card)
        return outer

    def _short_cell_text(self, text: str, max_len: int = 10) -> str:
        text = str(text or "")
        return text if len(text) <= max_len else text[:max_len - 1] + "…"

    def _show_detail(self, row, _c, _pr, _pc):
        if row < 0 or row >= len(self._filtered_scores): return
        score = self._filtered_scores[row]
        self._render_detail(score)

    def _render_detail(self, score: dict):
        # 保留 _detail_empty（index 0）和尾部 stretch（最后一项），只删中间的内容 widget
        while self._detail_layout.count() > 2:
            item = self._detail_layout.takeAt(1)   # 始终取 index 1（_detail_empty 之后）
            if item and item.widget():
                item.widget().deleteLater()
        self._detail_empty.hide()

        ins = [1]   # 从 index 1 开始插入（index 0 是 _detail_empty）
        def insert(w):
            self._detail_layout.insertWidget(ins[0], w)
            ins[0] += 1

        # 基本信息
        info_panel = make_panel("基本信息")
        il = info_panel.layout()
        il.addWidget(make_info_row("姓名", score.get("student_name", "-")))
        il.addWidget(make_info_row("学号", score.get("student_id", "-")))
        #章节有中文就显示中文，没中文就退回显示章节id
        il.addWidget(make_info_row("章节",score.get("chapter_title",  get_chapter_name(score.get("chapter_id", "")))))
        il.addWidget(make_info_row("任务", str(score.get("task_id", "-"))))
        il.addWidget(make_info_row("评阅时间", score.get("scored_at", "-")[:19] if score.get("scored_at") else "-"))
        insert(info_panel)

        # 得分
        sc = score.get("scores", {})
        total = score.get("total_score", 0)
        score_panel = make_panel("评分结果")
        sl = score_panel.layout()
        total_lbl = QLabel(str(total))
        total_lbl.setStyleSheet(f"color: {SCORE_A if total >= 85 else SCORE_B if total >= 70 else SCORE_F}; "
                                 f"font-size: 38px; font-weight: 900; background: transparent;")
        total_lbl.setAlignment(Qt.AlignCenter)
        sl.addWidget(total_lbl)
        for lbl, key, mx, color in [
            ("交互质量", "interaction_quality", 50, GREEN_PRI),
            ("知识掌握", "knowledge_mastery",   25, INFO),
            ("成果表达", "presentation",        15, ORANGE_PRI),
            ("学习反思", "reflection",          10, WARNING),
        ]:
            from ui.widgets import ScoreBar
            sl.addWidget(ScoreBar(lbl, sc.get(key, 0), mx, color))
        insert(score_panel)

        # 评语
        comment_text = score.get("comment") or score.get("readable_comment", "")
        if comment_text:
            cp = make_panel("评语")
            cl = cp.layout()
            c_lbl = QLabel(comment_text[:500] + ("…" if len(comment_text) > 500 else ""))
            c_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; line-height: 160%; background: transparent;")
            c_lbl.setWordWrap(True)
            cl.addWidget(c_lbl)
            insert(cp)

        # 导出按钮
        exp_btn = QPushButton("导出此条记录 JSON")
        exp_btn.setStyleSheet(SECONDARY_BTN)
        exp_btn.clicked.connect(lambda: self._export_single(score))
        self._detail_layout.insertWidget(ins[0], exp_btn)

    def _export_single(self, score: dict):
        name = f"{score.get('student_name', 'unknown')}_{score.get('student_id', '')}_{score.get('chapter_id', '')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "导出记录", name, "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(score, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出到：{path}")

    def _export_all(self):
        if not self._filtered_scores:
            QMessageBox.information(self, "提示", "没有可导出的记录。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出全部记录", "历史评阅数据.json", "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._filtered_scores, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已导出 {len(self._filtered_scores)} 条记录到：{path}")

    def _delete_selected(self):
        selected_rows = set(item.row() for item in self._table.selectedItems())
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的记录（可多选）。")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确认删除选中的 {len(selected_rows)} 条评阅记录？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes: return
        deleted = 0
        for row in sorted(selected_rows, reverse=True):
            if row < len(self._filtered_scores):
                s = self._filtered_scores[row]
                fn = s.get("_filename", "")
                if fn:
                    try:
                        fp = os.path.join(data_store.SCORES_DIR, fn)
                        if os.path.exists(fp):
                            os.remove(fp)
                            deleted += 1
                    except Exception:
                        pass
        QMessageBox.information(self, "删除完成", f"已删除 {deleted} 条记录。")
        self.refresh()
