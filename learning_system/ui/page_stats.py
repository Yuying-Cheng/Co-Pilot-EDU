"""
Page 3: Class Statistics — Warm Academic Style
新增：审辨/创新比例统计、群体共性问题、学情雷达图
"""

import io
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor

from ui.styles import *
from ui.widgets import (
    SectionHeader, SubHeader, StatCard, MiniStatCard, HDivider,
    make_info_row, add_shadow, make_panel, make_svg_widget, ILLUSTRATION_CHART
)
from ui.session_state_bridge import current_chapters
import os
import json
from analysis import compute_class_analysis
import data_store

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# Matplotlib 颜色主题（与 UI 一致）
MPL_BG       = "#FFFFFF"
MPL_TEXT     = "#6B7280"
MPL_GRID     = "#F3F4F6"
CHART_COLORS = [
    "#4A7C59", "#D97706", "#6DBE8C", "#F59E0B",
    "#3B82F6", "#DC2626", "#86EFAC", "#FCD34D"
]


def _mpl_base(figsize):
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    fig, ax = plt.subplots(figsize=figsize, facecolor=MPL_BG)
    ax.set_facecolor(MPL_BG)
    for spine in ax.spines.values():
        spine.set_color(MPL_GRID)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    return fig, ax


def _to_pixmap(fig) -> QPixmap:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    px = QPixmap()
    px.loadFromData(buf.read())
    return px


def _wrap_chart(title: str, px: QPixmap) -> QFrame:
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {BG_CARD};
            border: none;
            border-radius: {RADIUS_LG}px;
        }}
    """)
    add_shadow(f, blur=10, offset_y=2)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(0)
    img = QLabel()
    img.setPixmap(px)
    img.setAlignment(Qt.AlignCenter)
    img.setStyleSheet("background: transparent;")
    lay.addWidget(img)
    return f


class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis = None
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
        QLabel_t = QLabel("学情统计 · 分析报告")
        QLabel_t.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        QLabel_s = QLabel("汇总班级成绩分布、交互行为特征及薄弱知识点，辅助教学调整")
        QLabel_s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
        title_col.addWidget(QLabel_t)
        title_col.addWidget(QLabel_s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        try:
            chart_svg = make_svg_widget(ILLUSTRATION_CHART, 80, 50)
            hdr.addWidget(chart_svg)
        except Exception: pass

        refresh_btn = QPushButton("刷新数据")
        refresh_btn.setStyleSheet(GREEN_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: refresh_btn.setIcon(qta.icon("ri.refresh-line", color="white"))
            except: pass
        refresh_btn.clicked.connect(self.refresh)
        hdr.addSpacing(12)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(0, 0, 0, 40)
        self._cl.setSpacing(22)
        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

        # 空态
        empty_w = QWidget()
        empty_w.setStyleSheet("background: transparent;")
        ev = QVBoxLayout(empty_w)
        ev.setAlignment(Qt.AlignCenter)
        ev.setSpacing(12)
        try:
            c_svg = make_svg_widget(ILLUSTRATION_CHART, 120, 80)
            ev.addWidget(c_svg, alignment=Qt.AlignCenter)
        except Exception: pass
        self._placeholder = QLabel("暂无评阅数据\n请先完成学生成果评阅，然后点击「刷新数据」")
        self._placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; background: transparent;")
        self._placeholder.setAlignment(Qt.AlignCenter)
        ev.addWidget(self._placeholder)
        self._cl.addWidget(empty_w)

    def _get_scores(self):
        scores = []
        active = current_chapters()
        for fn in sorted(os.listdir(data_store.SCORES_DIR)):
            if fn.endswith("_score.json"):
                try:
                    with open(os.path.join(data_store.SCORES_DIR, fn), 'r', encoding='utf-8') as f:
                        s = json.load(f)
                    if not active or s.get("chapter_id") in active:
                        scores.append(s)
                except Exception:
                    continue
        return scores

    def showEvent(self, event):
        super().showEvent(event)
        if not self._analysis:
            self.refresh()

    def refresh(self):
        scores = self._get_scores()
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

        # ── 统计卡片（2行3列网格，避免横向过宽）───────────────────────────────
        cards_w = QWidget()
        cards_w.setStyleSheet("background: transparent;")
        cards_lay = QGridLayout(cards_w)
        cards_lay.setContentsMargins(0, 0, 0, 0)
        cards_lay.setSpacing(12)
        card_data = [
            ("学生总数",  str(data["student_count"]),             TEXT_PRI),
            ("班级平均分", str(ss.get("average_score", 0)),       INFO),
            ("最高分",    str(ss.get("max_score", 0)),            SCORE_A),
            ("最低分",    str(ss.get("min_score", 0)),            SCORE_F),
            ("优秀率",    f"{ss.get('excellent_rate', 0)*100:.0f}%", SCORE_A),
            ("人均交互",  f"{ist.get('average_rounds', 0)} 轮",
             SCORE_A if ist.get('average_rounds', 0) >= 10 else SCORE_F),
        ]
        for i, (lbl, val, color) in enumerate(card_data):
            card = StatCard(lbl, val, color)
            cards_lay.addWidget(card, i // 3, i % 3)
        self._cl.addWidget(cards_w)

        # ── 审辨/创新专项统计（2+3网格）─────────────────────────────────────────
        type_dist = ist.get("type_distribution", {})
        total_stu = data["student_count"]
        if type_dist and total_stu > 0:
            self._cl.addWidget(SectionHeader("交互方式专项统计"))
            behavior_w = QWidget()
            behavior_w.setStyleSheet("background: transparent;")
            bl = QGridLayout(behavior_w)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(12)
            behavior_data = [
                ("审辨",   DANGER,      "质疑/评判/辨析"),
                ("创新",   INFO,        "改进/变体/迁移"),
                ("猜想",   WARNING,     "推测/假设/验证"),
                ("苏格拉底回答", GREEN_PRI, "引导式问答"),
                ("表达见解", ORANGE_PRI, "陈述/分享/确认"),
            ]
            for i, (type_name, color, desc) in enumerate(behavior_data):
                cnt = type_dist.get(type_name, 0)
                ratio = f"{cnt / total_stu:.1f}" if total_stu > 0 else "0"
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background: {BG_CARD};
                        border: none;
                        border-radius: {RADIUS}px;
                    }}
                """)
                add_shadow(card, blur=8, offset_y=2)
                cl2 = QVBoxLayout(card)
                cl2.setContentsMargins(18, 16, 18, 16)
                cl2.setSpacing(8)

                top = QHBoxLayout()
                color_dot = QLabel("●")
                color_dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
                color_dot.setFixedWidth(16)
                name_lbl = QLabel(type_name)
                name_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; font-weight: 600; background: transparent;")
                top.addWidget(color_dot)
                top.addWidget(name_lbl)
                top.addStretch()
                cl2.addLayout(top)

                val_lbl = QLabel(f"{cnt} 次")
                val_lbl.setStyleSheet(f"color: {TEXT_H1}; font-size: 24px; font-weight: 800; background: transparent;")
                cl2.addWidget(val_lbl)

                avg_lbl = QLabel(f"人均 {ratio} 次  ·  {desc}")
                avg_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
                cl2.addWidget(avg_lbl)
                bl.addWidget(card, i // 3, i % 3)
            self._cl.addWidget(behavior_w)

        # ── 图表（2x2网格）─────────────────────────────────────────────────────
        if HAS_MPL and len(scores) >= 1:
            self._cl.addWidget(SectionHeader("可视化分析"))
            charts_grid = QGridLayout()
            charts_grid.setContentsMargins(0, 0, 0, 0)
            charts_grid.setSpacing(14)
            chart_widgets = [
                self._chart_score_dist(ss.get("distribution", {})),
                self._chart_type_dist(type_dist),
                self._chart_subscore(sub),
                self._chart_radar(sub, ss),
            ]
            positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
            for c, (r, cidx) in zip(chart_widgets, positions):
                if c:
                    charts_grid.addWidget(c, r, cidx)
            cw = QWidget()
            cw.setStyleSheet("background: transparent;")
            cw.setLayout(charts_grid)
            self._cl.addWidget(cw)

        # ── 成绩明细表 ────────────────────────────────────────────────────────
        self._cl.addWidget(SectionHeader("成绩明细"))
        self._cl.addWidget(self._make_table(scores))

        # ── 薄弱知识点 ────────────────────────────────────────────────────────
        weak = data.get("weak_knowledge_points", [])
        if weak:
            self._cl.addWidget(SectionHeader("群体薄弱知识点"))
            wk = make_panel()
            wl = wk.layout()
            for i, w in enumerate(weak):
                if i > 0: wl.addWidget(HDivider())
                row_w = QHBoxLayout()
                kp_lbl = QLabel(w.get("knowledge_point", ""))
                kp_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px; background: transparent;")
                cnt_lbl = QLabel(f"{w.get('affected_count', 0)} 人")
                cnt_lbl.setStyleSheet(f"color: {DANGER}; font-size: 13px; font-weight: 700; background: transparent;")
                row_w.addWidget(kp_lbl)
                row_w.addStretch()
                row_w.addWidget(cnt_lbl)
                wl.addLayout(row_w)
            self._cl.addWidget(wk)

        # ── 群体共性问题 ──────────────────────────────────────────────────────
        self._cl.addWidget(SectionHeader("群体共性问题"))
        problems_panel = make_panel()
        pl = problems_panel.layout()
        problems = self._compute_common_problems(scores)
        if problems:
            for i, prob in enumerate(problems):
                if i > 0: pl.addWidget(HDivider())
                row_w = QHBoxLayout()
                icon = QLabel("⚠️")
                icon.setStyleSheet("background: transparent; font-size: 14px;")
                icon.setFixedWidth(24)
                prob_lbl = QLabel(prob["desc"])
                prob_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
                prob_lbl.setWordWrap(True)
                ratio_lbl = QLabel(f"{prob['ratio']:.0%} 学生")
                ratio_lbl.setStyleSheet(f"color: {WARNING}; font-size: 13px; font-weight: 700; background: transparent;")
                row_w.addWidget(icon)
                row_w.addWidget(prob_lbl, 1)
                row_w.addWidget(ratio_lbl)
                pl.addLayout(row_w)
        else:
            pl.addWidget(QLabel("暂无明显共性问题 🎉"))
        self._cl.addWidget(problems_panel)

        # ── 分析总结 ──────────────────────────────────────────────────────────
        self._cl.addWidget(SectionHeader("分析总结"))
        sum_panel = make_panel()
        sl = sum_panel.layout()
        sum_lbl = QLabel(data.get("summary", ""))
        sum_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; line-height: 180%; background: transparent;")
        sum_lbl.setWordWrap(True)
        sl.addWidget(sum_lbl)
        self._cl.addWidget(sum_panel)
        self._cl.addStretch()

    # ── 群体共性问题计算 ──────────────────────────────────────────────────────
    def _compute_common_problems(self, scores: list) -> list:
        problems = []
        total = len(scores)
        if total == 0: return problems
        # 刷轮数比例
        brushing = sum(1 for s in scores
                       if s.get("interaction_analysis", {}).get("depth_level") == "较浅"
                       and s.get("interaction_analysis", {}).get("valid_rounds", 0) >= 8)
        if brushing / total >= 0.3:
            problems.append({"desc": "多数学生交互轮次达标但深度不足，存在刷轮数倾向（单轮均为简单提问）", "ratio": brushing / total})
        # 缺少追问
        no_followup = sum(1 for s in scores if not s.get("interaction_analysis", {}).get("has_follow_up"))
        if no_followup / total >= 0.4:
            problems.append({"desc": "超过40%学生未出现基于上一轮回答的连续追问，交互缺乏连贯性", "ratio": no_followup / total})
        # 缺少质疑
        no_q = sum(1 for s in scores if not s.get("interaction_analysis", {}).get("has_questioning"))
        if no_q / total >= 0.5:
            problems.append({"desc": "超过50%学生缺少对模型结论的质疑或审辨行为，批判性思维有待培养", "ratio": no_q / total})
        # 反思为空
        no_ref = sum(1 for s in scores if (s.get("scores", {}).get("reflection", 0) or 0) == 0)
        if no_ref / total >= 0.3:
            problems.append({"desc": "较多学生未提交学习反思或反思内容过于简短", "ratio": no_ref / total})
        return problems

    # ── 图表 ──────────────────────────────────────────────────────────────────
    def _chart_score_dist(self, dist: dict):
        try:
            labels = ["A\n90+", "B\n80+", "C\n70+", "D\n60+", "F\n<60"]
            values = list(dist.values())
            colors = [SCORE_A, SCORE_B, SCORE_C, SCORE_D, SCORE_F]
            fig, ax = _mpl_base((3.2, 2.6))
            bars = ax.bar(labels, values, color=colors, width=0.5, zorder=3, edgecolor="white", linewidth=1.5)
            ax.grid(axis="y", color=MPL_GRID, linewidth=0.7, zorder=0)
            ax.set_ylabel("人数", color=MPL_TEXT, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_title("分数段分布", color=MPL_TEXT, fontsize=9, pad=8)
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                            str(val), ha="center", va="bottom", color=MPL_TEXT, fontsize=9, fontweight="bold")
            return _wrap_chart("分数段分布", _to_pixmap(fig))
        except Exception: return None

    def _chart_type_dist(self, type_dist: dict):
        try:
            abbr = {"询问": "询问", "表达见解": "表达", "审辨": "审辨",
                    "猜想": "猜想", "想象": "想象", "创新": "创新", "苏格拉底回答": "苏格拉底"}
            valid = {abbr.get(k, k): v for k, v in type_dist.items() if v > 0}
            if not valid: return None
            fig, ax = _mpl_base((3.2, 2.6))
            wedges, _, autotexts = ax.pie(
                list(valid.values()), labels=None,
                autopct="%1.0f%%", colors=CHART_COLORS[:len(valid)],
                startangle=90, pctdistance=0.78,
                wedgeprops={"linewidth": 2, "edgecolor": "white"}
            )
            for at in autotexts:
                at.set_fontsize(7)
                at.set_color("white")
                at.set_fontweight("bold")
            ax.legend(list(valid.keys()), loc="lower center", bbox_to_anchor=(0.5, -0.22),
                      ncol=4, fontsize=7, frameon=False, labelcolor=MPL_TEXT)
            ax.axis("off")
            ax.set_title("交互方式分布", color=MPL_TEXT, fontsize=9, pad=4)
            return _wrap_chart("交互方式分布", _to_pixmap(fig))
        except Exception: return None

    def _chart_subscore(self, sub: dict):
        try:
            keys   = ["interaction_quality", "knowledge_mastery", "presentation", "reflection"]
            labels = ["交互质量\n/50", "知识掌握\n/25", "成果表达\n/15", "学习反思\n/10"]
            maxes  = [50, 25, 15, 10]
            vals   = [sub.get(k, 0) for k in keys]
            pcts   = [v/m*100 for v, m in zip(vals, maxes)]
            fig, ax = _mpl_base((3.2, 2.6))
            colors = [GREEN_PRI, INFO, ORANGE_PRI, WARNING]
            bars = ax.barh(labels, pcts, color=colors, height=0.42, edgecolor="white", linewidth=1.5)
            ax.set_xlim(0, 118)
            ax.set_xlabel("得分率 %", color=MPL_TEXT, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(axis="x", color=MPL_GRID, linewidth=0.7)
            ax.set_title("各维度平均得分率", color=MPL_TEXT, fontsize=9, pad=8)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2,
                        f"{val:.1f}", va="center", color=MPL_TEXT, fontsize=8, fontweight="bold")
            return _wrap_chart("各维度得分率", _to_pixmap(fig))
        except Exception: return None

    def _chart_radar(self, sub: dict, ss: dict):
        try:
            categories = ["交互质量", "知识掌握", "成果表达", "学习反思", "及格率"]
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
            fig = plt.figure(figsize=(3.2, 2.6), facecolor=MPL_BG)
            ax = fig.add_subplot(111, polar=True)
            ax.set_facecolor(MPL_BG)
            ax.plot(angles, vals, color=GREEN_PRI, linewidth=2)
            ax.fill(angles, vals, color=GREEN_PRI, alpha=0.15)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=8, color=MPL_TEXT)
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_yticklabels(["25", "50", "75", "100"], size=7, color=MPL_TEXT)
            ax.grid(color=MPL_GRID, linewidth=0.7)
            ax.spines["polar"].set_color(MPL_GRID)
            ax.set_title("学情雷达图", color=MPL_TEXT, fontsize=9, pad=12)
            return _wrap_chart("学情雷达图", _to_pixmap(fig))
        except Exception: return None

    def _make_table(self, scores: list) -> QTableWidget:
        cols = ["姓名", "学号", "总分", "交互质量", "知识掌握", "成果表达", "学习反思", "交互轮次", "深度"]
        table = QTableWidget(len(scores), len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setStyleSheet(TABLE_STYLE)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setMaximumHeight(280)
        for row, s in enumerate(scores):
            sc = s.get("scores", {})
            ia = s.get("interaction_analysis", {})
            total = s.get("total_score", 0)
            if total >= 85: tc = SCORE_A
            elif total >= 70: tc = SCORE_B
            elif total >= 60: tc = SCORE_C
            else: tc = SCORE_F
            for col, val in enumerate([
                s.get("student_name", ""), s.get("student_id", ""), str(total),
                str(sc.get("interaction_quality", 0)), str(sc.get("knowledge_mastery", 0)),
                str(sc.get("presentation", 0)), str(sc.get("reflection", 0)),
                str(ia.get("total_rounds", 0)), ia.get("depth_level", "-")
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(tc))
                table.setItem(row, col, item)
        return table
