"""
Page 3: Class Statistics — Swiss minimalist, 4 charts
"""

import io, math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor
from ui.styles import *
from ui.widgets import SectionHeader, StatCard, HDivider, make_info_row
import os
import json
from analysis.analysis import compute_class_analysis

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

# Matplotlib style constants (light theme)
MPL_BG    = "#FFFFFF"
MPL_TEXT  = "#6B6560"
MPL_GRID  = "#E8E5DF"
MPL_SPINE = "#E8E5DF"
MPL_ACCENT = "#1A1A1A"
CHART_COLORS = ["#1A1A1A", "#4A6FA5", "#2E7D52", "#B45309", "#C0392B", "#7B5EA7", "#2A6099"]


def _mpl_base(figsize):
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)
    for spine in ax.spines.values():
        spine.set_color(MPL_SPINE)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    return fig, ax


def _to_pixmap(fig) -> QPixmap:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    px = QPixmap()
    px.loadFromData(buf.read())
    return px


class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 24)
        title = QLabel("学情统计 · 分析报告")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(SECONDARY_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: refresh_btn.setIcon(qta.icon("ri.refresh-line", color=TEXT_PRI))
            except: pass
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(0, 0, 0, 40)
        self._cl.setSpacing(24)
        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

        self._placeholder = QLabel("暂无评阅数据，请先完成学生成果评阅。")
        self._placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px;")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._cl.addWidget(self._placeholder)

    def _get_all_scores(self):
        scores = []
        scores_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scores")
        if os.path.exists(scores_dir):
            for fn in os.listdir(scores_dir):
                if fn.endswith("_score.json"):
                    with open(os.path.join(scores_dir, fn), 'r', encoding='utf-8') as f:
                        scores.append(json.load(f))
        return scores

    def showEvent(self, event):
        super().showEvent(event)
        if not self._analysis:
            self.refresh()

    def refresh(self):
        scores = self._get_all_scores()
        if not scores:
            return
        self._analysis = compute_class_analysis(scores)
        self._render(self._analysis, scores)

    def _clear(self):
        while self._cl.count():
            item = self._cl.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _render(self, data: dict, scores: list):
        self._clear()
        ss  = data.get("score_statistics", {})
        ist = data.get("interaction_statistics", {})
        sub = data.get("sub_score_averages", {})

        # ── Stat cards ────────────────────────────────────────────────────────
        cards_w = QWidget()
        cards_w.setStyleSheet("background: transparent;")
        cards_lay = QHBoxLayout(cards_w)
        cards_lay.setContentsMargins(0, 0, 0, 0)
        cards_lay.setSpacing(12)
        for label, val, color in [
            ("学生总数",   str(data["student_count"]),                        TEXT_PRI),
            ("平均分",     str(ss.get("average_score", 0)),                   ACCENT5),
            ("最高分",     str(ss.get("max_score", 0)),                       ACCENT2),
            ("最低分",     str(ss.get("min_score", 0)),                       ACCENT4),
            ("优秀率",     f"{ss.get('excellent_rate',0)*100:.0f}%",          ACCENT2),
            ("人均交互",   f"{ist.get('average_rounds',0)} 轮",
             ACCENT2 if ist.get('average_rounds', 0) >= 10 else ACCENT4),
        ]:
            cards_lay.addWidget(StatCard(label, val, color))
        self._cl.addWidget(cards_w)

        # ── Charts 2×2 ────────────────────────────────────────────────────────
        if HAS_MPL and len(scores) >= 1:
            row1 = QHBoxLayout()
            row1.setSpacing(16)
            c1 = self._chart_score_dist(ss.get("distribution", {}))
            c2 = self._chart_type_dist(ist.get("type_distribution", {}))
            c3 = self._chart_subscore(sub)
            c4 = self._chart_radar(sub, ss)
            for c in [c1, c2, c3, c4]:
                if c: row1.addWidget(c, 1)
            charts_w = QWidget()
            charts_w.setStyleSheet("background: transparent;")
            charts_w.setLayout(row1)
            self._cl.addWidget(charts_w)

        # ── Score table ───────────────────────────────────────────────────────
        self._cl.addWidget(SectionHeader("成绩明细"))
        self._cl.addWidget(self._make_table(scores))

        # ── Weak KPs ──────────────────────────────────────────────────────────
        weak = data.get("weak_knowledge_points", [])
        if weak:
            self._cl.addWidget(SectionHeader("薄弱知识点"))
            wk = QFrame()
            wk.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
            wl = QVBoxLayout(wk)
            wl.setContentsMargins(20, 16, 20, 16)
            wl.setSpacing(10)
            for i, w in enumerate(weak):
                if i > 0: wl.addWidget(HDivider())
                row = QHBoxLayout()
                kp_lbl = QLabel(w.get("knowledge_point", ""))
                kp_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 600; font-size: 12px; background: transparent;")
                cnt_lbl = QLabel(f"{w.get('affected_count',0)} 人")
                cnt_lbl.setStyleSheet(f"color: {ACCENT4}; font-size: 12px; background: transparent;")
                row.addWidget(kp_lbl)
                row.addStretch()
                row.addWidget(cnt_lbl)
                wl.addLayout(row)
            self._cl.addWidget(wk)

        # ── Summary ───────────────────────────────────────────────────────────
        self._cl.addWidget(SectionHeader("分析总结"))
        sum_card = QFrame()
        sum_card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        sl = QVBoxLayout(sum_card)
        sl.setContentsMargins(20, 16, 20, 16)
        sum_lbl = QLabel(data.get("summary", ""))
        sum_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; line-height: 180%;")
        sum_lbl.setWordWrap(True)
        sl.addWidget(sum_lbl)
        self._cl.addWidget(sum_card)
        self._cl.addStretch()

    # ── Chart builders ─────────────────────────────────────────────────────────

    def _wrap_chart(self, title: str, px: QPixmap) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        hdr = QLabel(title.upper())
        hdr.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
        hdr.setAlignment(Qt.AlignCenter)
        img = QLabel()
        img.setPixmap(px)
        img.setAlignment(Qt.AlignCenter)
        lay.addWidget(hdr)
        lay.addWidget(img)
        return f

    def _chart_score_dist(self, dist: dict):
        try:
            labels = ["A\n90+", "B\n80+", "C\n70+", "D\n60+", "F\n<60"]
            values = list(dist.values())
            fig, ax = _mpl_base((3.0, 2.6))
            bars = ax.bar(labels, values, color=[MPL_ACCENT, "#4A6FA5", "#2E7D52", "#B45309", "#C0392B"],
                          width=0.5, zorder=3)
            ax.grid(axis="y", color=MPL_GRID, linewidth=0.5, zorder=0)
            ax.set_ylabel("人数", color=MPL_TEXT, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                            str(val), ha="center", va="bottom", color=MPL_TEXT, fontsize=8)
            return self._wrap_chart("分数段分布", _to_pixmap(fig))
        except Exception:
            return None

    def _chart_type_dist(self, type_dist: dict):
        try:
            abbr = {"询问":"Ask","表达见解":"Express","审辨":"Critique",
                    "猜想":"Guess","想象":"Imagine","创新":"Create","苏格拉底回答":"Socratic"}
            valid = {abbr.get(k,k): v for k,v in type_dist.items() if v > 0}
            if not valid: return None
            fig, ax = _mpl_base((3.0, 2.6))
            wedges, _, autotexts = ax.pie(
                list(valid.values()), labels=None,
                autopct="%1.0f%%", colors=CHART_COLORS[:len(valid)],
                startangle=90, pctdistance=0.78,
                wedgeprops={"linewidth": 1, "edgecolor": "white"}
            )
            for at in autotexts:
                at.set_fontsize(7)
                at.set_color("white")
            ax.legend(list(valid.keys()), loc="lower center", bbox_to_anchor=(0.5, -0.22),
                      ncol=4, fontsize=7, frameon=False, labelcolor=MPL_TEXT)
            ax.axis("off")
            return self._wrap_chart("交互方式分布", _to_pixmap(fig))
        except Exception:
            return None

    def _chart_subscore(self, sub: dict):
        try:
            keys   = ["interaction_quality","knowledge_mastery","presentation","reflection"]
            labels = ["Interaction\n/50","Knowledge\n/25","Presentation\n/15","Reflection\n/10"]
            maxes  = [50, 25, 15, 10]
            vals   = [sub.get(k,0) for k in keys]
            pcts   = [v/m*100 for v,m in zip(vals,maxes)]
            fig, ax = _mpl_base((3.0, 2.6))
            bars = ax.barh(labels, pcts, color=CHART_COLORS[:4], height=0.45)
            ax.set_xlim(0, 115)
            ax.set_xlabel("得分率 %", color=MPL_TEXT, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(axis="x", color=MPL_GRID, linewidth=0.5)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
                        f"{val:.1f}", va="center", color=MPL_TEXT, fontsize=8)
            return self._wrap_chart("各维度得分率", _to_pixmap(fig))
        except Exception:
            return None

    def _chart_radar(self, sub: dict, ss: dict):
        try:
            categories = ["交互质量", "知识掌握", "成果呈现", "学习反思", "及格率"]
            raw = [
                sub.get("interaction_quality", 0) / 50 * 100,
                sub.get("knowledge_mastery", 0) / 25 * 100,
                sub.get("presentation", 0) / 15 * 100,
                sub.get("reflection", 0) / 10 * 100,
                ss.get("pass_rate", 0) * 100,
            ]
            N = len(categories)
            angles = [n / N * 2 * math.pi for n in range(N)]
            angles += angles[:1]
            vals = raw + raw[:1]

            fig = plt.figure(figsize=(3.0, 2.6), facecolor=MPL_BG)
            ax = fig.add_subplot(111, polar=True)
            ax.set_facecolor(MPL_BG)
            ax.plot(angles, vals, color=MPL_ACCENT, linewidth=1.5)
            ax.fill(angles, vals, color=MPL_ACCENT, alpha=0.10)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=8, color=MPL_TEXT)
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_yticklabels(["25", "50", "75", "100"], size=7, color=MPL_TEXT)
            ax.grid(color=MPL_GRID, linewidth=0.5)
            ax.spines["polar"].set_color(MPL_SPINE)
            return self._wrap_chart("学情雷达图", _to_pixmap(fig))
        except Exception:
            return None

    def _make_table(self, scores: list) -> QTableWidget:
        cols = ["姓名", "学号", "总分", "交互质量", "知识掌握", "成果呈现", "学习反思", "交互轮次", "深度"]
        table = QTableWidget(len(scores), len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setStyleSheet(TABLE_STYLE)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setMaximumHeight(260)
        table.setAlternatingRowColors(False)

        for row, s in enumerate(scores):
            sc = s.get("scores", {})
            ia = s.get("interaction_analysis", {})
            total = s.get("total_score", 0)
            total_color = ACCENT2 if total >= 85 else (ACCENT3 if total >= 70 else ACCENT4)
            for col, val in enumerate([
                s.get("student_name",""), s.get("student_id",""), str(total),
                str(sc.get("interaction_quality",0)), str(sc.get("knowledge_mastery",0)),
                str(sc.get("presentation",0)), str(sc.get("reflection",0)),
                str(ia.get("total_rounds",0)), ia.get("depth_level","-")
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(total_color))
                table.setItem(row, col, item)
        return table
