"""
Page 3: Class Statistics — Calm Academic Style
图表配色与全局蓝绿主题保持一致，并保留少量暖色用于强调。
"""

import io
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar
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
    # 模块级别统一设置中文字体，避免 CJK glyph missing 警告
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "PingFang SC", "SimHei",
                            "Arial Unicode MS", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
    })
    HAS_MPL = True
    try:
        from matplotlib.figure import Figure as _MplFigure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as _FigureCanvasQT
        HAS_MPL_QT = True
    except Exception:
        HAS_MPL_QT = False
except ImportError:
    HAS_MPL = False
    HAS_MPL_QT = False

# ── Matplotlib 主题 ───────────────────────────────────────────────────────────
MPL_BG       = "#FFFFFF"
MPL_PANEL    = "#F5F7FA"
MPL_TEXT     = "#627086"
MPL_GRID     = "#EAF0F6"
MPL_TICK     = "#96A3B6"

# 图表色板（蓝绿主色 + 暖色强调）
CHART_INDIGO = [
    "#2F80ED",   # primary blue
    "#20B486",   # mint green
    "#65A9F4",   # lighter blue
    "#F59E0B",   # warm amber
    "#1D5FBF",   # deeper blue
    "#138461",   # deeper green
    "#8CBFF4",   # pale blue
]

BAR_DARK  = "#2F80ED"   # 主色蓝
BAR_LIGHT = "#8CBFF4"   # 浅蓝

# 分数段语义色（保留 A=绿 F=红，其余跟随主题）
SCORE_BAR_COLORS = ["#22A05B", "#4AB87A", "#2F80ED", "#F59E0B", "#D94F4F"]


def _setup_mpl():
    plt.rcParams.update({
        'font.sans-serif': ['PingFang SC', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'font.size': 9,
    })


def _mpl_base(figsize, facecolor=MPL_BG):
    _setup_mpl()
    fig, ax = plt.subplots(figsize=figsize, facecolor=facecolor)
    ax.set_facecolor(facecolor)
    for spine in ax.spines.values():
        spine.set_color(MPL_GRID)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=MPL_TICK, labelsize=8.5)
    return fig, ax


def _to_pixmap(fig) -> QPixmap:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    px = QPixmap()
    px.loadFromData(buf.read())
    return px


def _make_chart_frame(title: str = "") -> tuple:
    """返回 (QFrame, QVBoxLayout)，可选在卡片顶部插入标题标签。"""
    f = QFrame()
    f.setObjectName("chartFrame")
    f.setStyleSheet(f"""
        QFrame#chartFrame {{
            background: {BG_CARD};
            border: 1px solid {BORDER_LIGHT};
            border-radius: 10px;
        }}
    """)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 16, 18, 14)
    lay.setSpacing(10)
    if title:
        t = QLabel(title)
        t.setStyleSheet(
            f"color: {TEXT_H1}; font-size: 13px; font-weight: 800;"
            f" background: transparent; min-height: 24px; padding: 0;"
        )
        t.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(t)
    return f, lay



class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis = None
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
        QLabel_t = QLabel("学情统计 · 分析报告")
        QLabel_t.setStyleSheet(f"color: {TEXT_H1}; font-size: 19px; font-weight: 800; background: transparent;")
        QLabel_s = QLabel("汇总班级成绩分布、交互行为特征及薄弱知识点，辅助教学调整")
        QLabel_s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(QLabel_t)
        title_col.addWidget(QLabel_s)
        hdr.addLayout(title_col)
        hdr.addStretch()

        refresh_btn = QPushButton("刷新数据")
        refresh_btn.setStyleSheet(PRIMARY_BTN)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(38)
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(0, 0, 0, 40)
        self._cl.setSpacing(20)
        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

        # 空态
        empty_w = QWidget()
        empty_w.setStyleSheet("background: transparent;")
        ev = QVBoxLayout(empty_w)
        ev.setAlignment(Qt.AlignCenter)
        ev.setSpacing(14)
        self._placeholder = QLabel("暂无评阅数据\n请先完成学生成果评阅，然后点击「刷新数据」")
        self._placeholder.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; background: transparent;")
        self._placeholder.setAlignment(Qt.AlignCenter)
        ev.addWidget(self._placeholder)
        self._cl.addWidget(empty_w)

    def _get_scores(self):
        raw = []
        active = current_chapters()
        for fn in sorted(os.listdir(data_store.SCORES_DIR)):
            if fn.endswith("_score.json"):
                try:
                    with open(os.path.join(data_store.SCORES_DIR, fn), 'r', encoding='utf-8') as f:
                        s = json.load(f)
                    if not active or s.get("chapter_id") in active:
                        raw.append(s)
                except Exception:
                    continue
        # 去重：同一学生+章节仅保留最新记录
        latest: dict = {}
        for s in raw:
            key = (s.get("student_id", ""), s.get("chapter_id", ""))
            if key not in latest or s.get("scored_at", "") > latest[key].get("scored_at", ""):
                latest[key] = s
        return list(latest.values())

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
            if item.widget():
                item.widget().deleteLater()

    def _render(self, data: dict, scores: list):
        self._clear()
        ss  = data.get("score_statistics", {})
        ist = data.get("interaction_statistics", {})
        sub = data.get("sub_score_averages", {})

        # ── 顶部统计卡片 ──────────────────────────────────────────────────────
        cards_w = QWidget()
        cards_w.setStyleSheet("background: transparent;")
        cards_lay = QGridLayout(cards_w)
        cards_lay.setContentsMargins(0, 0, 0, 0)
        cards_lay.setSpacing(10)

        avg_rounds = ist.get('average_rounds', 0)
        card_data = [
            ("学生总数",   str(data["student_count"]),                                           TEXT_H1),
            ("班级平均分", str(ss.get("average_score", 0)),                                       INFO),
            ("最高分",     str(ss.get("max_score", 0)),                                           SCORE_A),
            ("最低分",     str(ss.get("min_score", 0)),                                           SCORE_F),
            ("优秀率",     f"{ss.get('excellent_rate', 0)*100:.0f}%",                             SCORE_A),
            ("人均交互",   f"{avg_rounds} 轮",   SCORE_A if avg_rounds >= 10 else WARNING),
        ]
        for i, (lbl, val, color) in enumerate(card_data):
            card = StatCard(lbl, val, color)
            cards_lay.addWidget(card, i // 3, i % 3)
        self._cl.addWidget(cards_w)

        # ── 图表区（2×2，参考图1/图2风格）─────────────────────────────────────
        if HAS_MPL and scores:
            self._cl.addWidget(SectionHeader("可视化分析"))
            type_dist = ist.get("type_distribution", {})

            charts_grid = QGridLayout()
            charts_grid.setContentsMargins(0, 0, 0, 0)
            charts_grid.setSpacing(12)

            charts = [
                self._chart_score_dist(ss.get("distribution", {})),
                self._chart_type_donut(type_dist),         # 甜甜圈，参考图1
                self._chart_monthly_bar(scores),            # 柱状图，参考图2风格
                self._chart_radar(sub, ss),
            ]
            for idx, c in enumerate(charts):
                if c:
                    charts_grid.addWidget(c, idx // 2, idx % 2)

            cw = QWidget()
            cw.setStyleSheet("background: transparent;")
            cw.setLayout(charts_grid)
            self._cl.addWidget(cw)

        # ── 交互方式专项统计 ──────────────────────────────────────────────────
        type_dist = ist.get("type_distribution", {})
        total_stu = data["student_count"]
        if type_dist and total_stu > 0:
            self._cl.addWidget(SectionHeader("交互方式分析"))
            self._cl.addWidget(self._make_behavior_grid(type_dist, total_stu))

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
                if i > 0:
                    wl.addWidget(HDivider())
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

    # ── 交互方式卡片网格 ──────────────────────────────────────────────────────
    def _make_behavior_grid(self, type_dist: dict, total_stu: int) -> QWidget:
        behavior_w = QFrame()
        behavior_w.setObjectName("behaviorPanel")
        behavior_w.setStyleSheet(f"""
            QFrame#behaviorPanel {{
                background: {BG_CARD};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 10px;
            }}
        """)
        bl = QGridLayout(behavior_w)
        bl.setContentsMargins(18, 16, 18, 16)
        bl.setHorizontalSpacing(24)
        bl.setVerticalSpacing(14)
        behavior_data = [
            ("审辨",         DANGER,      "质疑/评判/辨析"),
            ("创新",         INFO,        "改进/变体/迁移"),
            ("猜想",         WARNING,     "推测/假设/验证"),
            ("苏格拉底回答",  GREEN_PRI,  "引导式问答"),
            ("表达见解",      ORANGE_PRI, "陈述/分享/确认"),
        ]
        max_cnt = max([type_dist.get(name, 0) for name, _, _ in behavior_data] + [1])
        for i, (type_name, color, desc) in enumerate(behavior_data):
            cnt = type_dist.get(type_name, 0)
            ratio = f"{cnt / total_stu:.1f}" if total_stu > 0 else "0.0"

            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(7)

            top = QHBoxLayout()
            top.setSpacing(8)
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"QFrame {{ background: {color}; border-radius: 4px; border: none; }}"
            )
            name_lbl = QLabel(type_name)
            name_lbl.setStyleSheet(
                f"color: {TEXT_H1}; font-size: 13px; font-weight: 800;"
                f" background: transparent; border: none;"
            )
            val_lbl = QLabel(f"{cnt} 次")
            val_lbl.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: 900;"
                f" background: transparent; border: none;"
            )
            top.addWidget(dot, 0, Qt.AlignVCenter)
            top.addWidget(name_lbl)
            top.addStretch()
            top.addWidget(val_lbl)
            rl.addLayout(top)

            bar = QProgressBar()
            bar.setRange(0, max_cnt)
            bar.setValue(cnt)
            bar.setFixedHeight(7)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background: {BG_INPUT};
                    border: none;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: {color};
                    border-radius: 3px;
                }}
            """)
            rl.addWidget(bar)

            avg_lbl = QLabel(f"人均 {ratio} 次  ·  {desc}")
            avg_lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 11px;"
                f" background: transparent; border: none;"
            )
            rl.addWidget(avg_lbl)

            bl.addWidget(row, i // 2, i % 2)
        return behavior_w

    # ─────────────────────────── 图表方法 ────────────────────────────────────

    def _chart_score_dist(self, dist: dict):
        """分数段柱状图 — 蓝紫语义色 + 悬浮提示"""
        try:
            labels = ["A\n90+", "B\n80+", "C\n70+", "D\n60+", "F\n<60"]
            grade_names = ["A级 (90+)", "B级 (80+)", "C级 (70+)", "D级 (60+)", "F级 (<60)"]
            values = list(dist.values())
            frame, fl = _make_chart_frame("分数段分布")

            if HAS_MPL_QT:
                fig = _MplFigure(figsize=(3.8, 2.8), facecolor=MPL_BG)
                canvas = _FigureCanvasQT(fig)
                canvas.setMinimumHeight(210)
                canvas.setStyleSheet(f"background: {MPL_BG};")
                ax = fig.add_subplot(111)
                ax.set_facecolor(MPL_BG)
                for sp in ax.spines.values():
                    sp.set_color(MPL_GRID); sp.set_linewidth(0.8)
                ax.tick_params(colors=MPL_TICK, labelsize=8.5)
            else:
                fig, ax = _mpl_base((3.8, 2.8))
                canvas = None

            bars = ax.bar(labels, values, color=SCORE_BAR_COLORS, width=0.52,
                          zorder=3, edgecolor="white", linewidth=2)
            ax.grid(axis="y", color=MPL_GRID, linewidth=0.8, zorder=0)
            ax.set_ylabel("人数", color=MPL_TICK, fontsize=8.5)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(MPL_GRID)
            # Y 轴整数刻度
            from matplotlib.ticker import MaxNLocator
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.05, str(val),
                            ha="center", va="bottom", color=MPL_TEXT,
                            fontsize=9.5, fontweight="bold")

            if canvas is not None:
                annot = ax.annotate("", xy=(0, 0), xytext=(0, 16),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.45", fc="#1A2340", ec="none", alpha=0.88),
                    color="white", fontsize=9, fontweight="bold", ha="center")
                annot.set_visible(False)

                def _hover(event, _ax=ax, _an=annot, _cv=canvas,
                           _bars=bars, _gn=grade_names):
                    if event.inaxes != _ax:
                        if _an.get_visible():
                            _an.set_visible(False); _cv.draw_idle()
                        return
                    found = False
                    for i, bar in enumerate(_bars):
                        if bar.contains(event)[0]:
                            _an.xy = (bar.get_x() + bar.get_width() / 2, bar.get_height())
                            _an.set_text(f"{_gn[i]}: {int(bar.get_height())} 人")
                            _an.set_visible(True); _cv.draw_idle()
                            found = True; break
                    if not found and _an.get_visible():
                        _an.set_visible(False); _cv.draw_idle()

                canvas.mpl_connect("motion_notify_event", _hover)
                fig.tight_layout(pad=1.2)
                fl.addWidget(canvas)
            else:
                fig.tight_layout(pad=1.2)
                img = QLabel()
                img.setPixmap(_to_pixmap(fig))
                img.setAlignment(Qt.AlignCenter)
                img.setStyleSheet("background: transparent; padding: 4px;")
                fl.addWidget(img)
            return frame
        except Exception as e:
            print(f"[chart_score_dist] {e}")
            return None

    def _chart_type_donut(self, type_dist: dict):
        """交互方式甜甜圈图 — 蓝绿系、无缝分区 + 悬浮提示"""
        try:
            abbr = {
                "询问": "询问", "表达见解": "表达见解", "审辨": "审辨",
                "猜想": "猜想", "想象": "想象", "创新": "创新", "苏格拉底回答": "苏格拉底"
            }
            valid = {abbr.get(k, k): v for k, v in type_dist.items() if v > 0}
            if not valid:
                return None

            labels = list(valid.keys())
            values = list(valid.values())
            total = sum(values)
            harmony_palette = ["#3478E5", "#2FB58A", "#69A7F0", "#7BC8A4", "#9CC7F7", "#B8E2D0", "#D8E9FB"]
            colors_used = harmony_palette[:len(valid)]

            frame, fl = _make_chart_frame("交互方式分布")

            if HAS_MPL_QT:
                fig = _MplFigure(figsize=(3.9, 2.8), facecolor=MPL_BG)
                canvas = _FigureCanvasQT(fig)
                canvas.setMinimumHeight(225)
                canvas.setStyleSheet(f"background: {MPL_BG};")
                ax = fig.add_subplot(111, aspect="equal")
                ax.set_facecolor(MPL_BG)
            else:
                _setup_mpl()
                fig = plt.figure(figsize=(3.9, 2.8), facecolor=MPL_BG)
                ax = fig.add_subplot(111, aspect="equal")
                ax.set_facecolor(MPL_BG)
                canvas = None

            wedges, _ = ax.pie(
                values, labels=None, colors=colors_used, startangle=90,
                counterclock=False,
                wedgeprops={"linewidth": 0, "edgecolor": "none"},
            )
            # 中心镂空
            import matplotlib.patches as _mp
            centre = _mp.Circle((0, 0), 0.56, color=MPL_BG)
            ax.add_artist(centre)

            # 图例
            legend_patches = [mpatches.Patch(color=c, label=l)
                               for c, l in zip(colors_used, labels)]
            ax.legend(handles=legend_patches, loc="lower center",
                      bbox_to_anchor=(0.5, -0.17), ncol=min(4, len(labels)), fontsize=7.8,
                      frameon=False, labelcolor=MPL_TEXT,
                      handlelength=1.8, handleheight=0.9, columnspacing=1.2, handletextpad=0.5)

            if canvas is not None:
                annot = ax.annotate("", xy=(0, 0), xytext=(30, 20),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.5", fc="#1A2340", ec="none", alpha=0.90),
                    color="white", fontsize=9, fontweight="bold", ha="left")
                annot.set_visible(False)

                def _hover_donut(event, _ax=ax, _an=annot, _cv=canvas,
                                 _wedges=wedges, _labels=labels,
                                 _values=values, _tot=total):
                    import math as _m
                    if event.inaxes != _ax:
                        if _an.get_visible():
                            _an.set_visible(False); _cv.draw_idle()
                        return
                    found = False
                    for i, w in enumerate(_wedges):
                        if w.contains(event)[0]:
                            t1, t2 = w.theta1, w.theta2
                            t_mid = (t1 + t2) / 2 * _m.pi / 180
                            xc = 0.82 * _m.cos(t_mid)
                            yc = 0.82 * _m.sin(t_mid)
                            _an.xy = (xc, yc)
                            pct = _values[i] / _tot * 100 if _tot > 0 else 0
                            _an.set_text(f"{_labels[i]}\n{_values[i]}次 ({pct:.0f}%)")
                            _an.set_visible(True); _cv.draw_idle()
                            found = True; break
                    if not found and _an.get_visible():
                        _an.set_visible(False); _cv.draw_idle()

                canvas.mpl_connect("motion_notify_event", _hover_donut)
                fig.tight_layout(pad=0.9)
                fl.addWidget(canvas)
            else:
                fig.tight_layout(pad=0.9)
                img = QLabel()
                img.setPixmap(_to_pixmap(fig))
                img.setAlignment(Qt.AlignCenter)
                img.setStyleSheet("background: transparent; padding: 4px;")
                fl.addWidget(img)
            return frame
        except Exception as e:
            print(f"[chart_type_donut] {e}")
            return None

    def _chart_monthly_bar(self, scores: list):
        """交互轮次横向柱状图 — 展示总交互轮次与有效轮次"""
        try:
            total_rounds = 0
            valid_rounds = 0
            for s in scores:
                ia = s.get("interaction_analysis", {})
                total_rounds += int(ia.get("total_rounds", 0) or 0)
                valid_rounds += int(ia.get("valid_rounds", 0) or 0)

            if total_rounds <= 0 and valid_rounds <= 0:
                return None

            labels = ["总交互轮次", "有效轮次"]
            values = [total_rounds, valid_rounds]
            colors = ["#2F80ED", "#6EC3A5"]
            max_value = max(values + [1])

            _setup_mpl()
            frame, fl = _make_chart_frame("交互轮次统计")

            if HAS_MPL_QT:
                fig = _MplFigure(figsize=(4.4, 2.75), facecolor=MPL_BG)
                canvas = _FigureCanvasQT(fig)
                canvas.setMinimumHeight(220)
                canvas.setStyleSheet(f"background: {MPL_BG};")
                ax = fig.add_subplot(111)
                ax.set_facecolor(MPL_BG)
            else:
                fig, ax = _mpl_base((4.4, 2.75))
                canvas = None

            ax.set_xlim(0, max_value * 1.18)
            ax.set_ylim(-0.5, len(labels) - 0.5)
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=10, color=TEXT_H1, fontweight="700")
            ax.invert_yaxis()
            ax.set_xticks([])
            ax.tick_params(axis="y", length=0, pad=12)
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_visible(False)

            bar_height = 0.34
            bars = []
            for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
                track = mpatches.FancyBboxPatch(
                    (0, idx - bar_height / 2),
                    max_value * 1.02,
                    bar_height,
                    boxstyle="round,pad=0.02,rounding_size=0.14",
                    linewidth=0,
                    facecolor="#ECF3FB",
                    zorder=1,
                )
                ax.add_patch(track)
                bar = mpatches.FancyBboxPatch(
                    (0, idx - bar_height / 2),
                    value,
                    bar_height,
                    boxstyle="round,pad=0.02,rounding_size=0.14",
                    linewidth=0,
                    facecolor=color,
                    zorder=3,
                )
                ax.add_patch(bar)
                ax.text(
                    max_value * 1.045, idx, str(int(value)),
                    va="center", ha="left",
                    fontsize=10.5, fontweight="800", color=MPL_TEXT, zorder=4
                )
                bars.append((bar, label, value))

            if canvas is not None:
                annot = ax.annotate(
                    "", xy=(0, 0), xytext=(12, 0),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.45", fc="#1A2340", ec="none", alpha=0.88),
                    color="white", fontsize=9, fontweight="bold", ha="left",
                    annotation_clip=False,
                    zorder=20
                )
                annot.set_clip_on(False)
                annot.set_visible(False)

                def _on_hover(event, _ax=ax, _annot=annot, _cv=canvas, _bars=bars):
                    if event.inaxes != _ax:
                        if _annot.get_visible():
                            _annot.set_visible(False)
                            _cv.draw_idle()
                        return
                    found = False
                    for bar, label, value in _bars:
                        if bar.contains(event)[0]:
                            _annot.xy = (value, bar.get_y() + bar.get_height() / 2)
                            _annot.set_text(f"{label}\n{int(value)}")
                            _annot.set_visible(True)
                            _cv.draw_idle()
                            found = True
                            break
                    if not found and _annot.get_visible():
                        _annot.set_visible(False)
                        _cv.draw_idle()

                canvas.mpl_connect("motion_notify_event", _on_hover)
                fig.tight_layout(pad=0.8)
                fl.addWidget(canvas)
            else:
                fig.tight_layout(pad=0.8)
                px = _to_pixmap(fig)
                img = QLabel()
                img.setPixmap(px)
                img.setAlignment(Qt.AlignCenter)
                img.setStyleSheet("background: transparent; padding: 4px;")
                fl.addWidget(img)

            return frame
        except Exception as e:
            print(f"[chart_monthly_bar] {e}")
            return None

    def _chart_radar(self, sub: dict, ss: dict):
        """学情雷达图 — 多边形网格 + 无内部刻度数字 + 主色统一 + 悬浮提示"""
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

            frame, fl = _make_chart_frame("学情雷达图")

            if HAS_MPL_QT:
                _setup_mpl()
                fig = _MplFigure(figsize=(4.2, 3.4), facecolor=MPL_BG)
                canvas = _FigureCanvasQT(fig)
                canvas.setMinimumHeight(240)
                canvas.setStyleSheet(f"background: {MPL_BG};")
                ax = fig.add_subplot(111, polar=True)
            else:
                _setup_mpl()
                fig = plt.figure(figsize=(4.2, 3.4), facecolor=MPL_BG)
                ax = fig.add_subplot(111, polar=True)
                canvas = None

            ax.set_facecolor("#F8FBFF")

            # ── 多边形背景色带（从外到内叠加）──────────────────────────────
            ring_colors = [
                (100, "#F0F7FF"),
                (75,  "#E8F4FF"),
                (50,  "#DFF0FF"),
                (25,  "#D6ECFF"),
            ]
            for lvl, clr in ring_colors:
                pts = [lvl] * (N + 1)
                ax.fill(angles, pts, color=clr, zorder=0, alpha=1.0)

            # ── 多边形网格线（替代默认圆形网格）──────────────────────────────
            GRID_CLR = "#C6D5E8"
            ax.grid(False)                          # 关闭默认圆形网格
            ax.yaxis.set_visible(False)             # 不显示 r 轴
            ax.spines["polar"].set_visible(False)   # 关闭外圆框
            for lvl in [25, 50, 75, 100]:
                pts = [lvl] * (N + 1)
                ax.plot(angles, pts, color=GRID_CLR, linewidth=0.9, zorder=1)
            for a in angles[:-1]:
                ax.plot([a, a], [0, 100], color=GRID_CLR, linewidth=0.9, zorder=1)

            # ── 数据区域 ────────────────────────────────────────────────────
            ax.fill(angles, vals, color=GREEN_PRI, alpha=0.18, zorder=2)
            ax.plot(angles, vals, color=GREEN_PRI, linewidth=2.2, zorder=3)

            # ── 顶点标记（单一主色，较小）────────────────────────────────────
            for a, v in zip(angles[:-1], raw):
                ax.plot(a, v, "o", color=GREEN_PRI, markersize=5, zorder=5,
                        markeredgecolor="white", markeredgewidth=1.5)

            # ── 分类标签（向外推出，不进入图内）──────────────────────────────
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=9, color=TEXT_H1, fontweight="600")
            ax.tick_params(axis="x", pad=18)

            ax.set_ylim(0, 100)
            ax.set_yticks([])                       # 不显示内部 25/50/75/100
            # 标题已在卡片外部 QLabel 显示，不再在 matplotlib 内画标题

            if canvas is not None:
                annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.5", fc="#1A2340",
                              ec="none", alpha=0.90),
                    color="white", fontsize=9, fontweight="bold", ha="center")
                annot.set_visible(False)
                _ang = angles[:-1]
                _raw = raw[:]
                _cats = categories[:]

                def _hover_radar(event, _ax=ax, _an=annot, _cv=canvas,
                                 _angles=_ang, _vals=_raw, _cats=_cats):
                    if event.inaxes != _ax:
                        if _an.get_visible():
                            _an.set_visible(False); _cv.draw_idle()
                        return
                    try:
                        theta = event.xdata; r = event.ydata
                        if theta is None or r is None: return
                        min_d = float("inf"); best = 0
                        for i, (a, v) in enumerate(zip(_angles, _vals)):
                            d_t = abs(a - theta) % (2 * math.pi)
                            if d_t > math.pi: d_t = 2 * math.pi - d_t
                            dist = d_t * 22 + abs(v - r)
                            if dist < min_d: min_d = dist; best = i
                        if min_d < 22:
                            _an.xy = (_angles[best], _vals[best])
                            _an.set_text(f"{_cats[best]}\n{_vals[best]:.1f} 分")
                            _an.set_visible(True); _cv.draw_idle()
                        elif _an.get_visible():
                            _an.set_visible(False); _cv.draw_idle()
                    except Exception:
                        pass

                canvas.mpl_connect("motion_notify_event", _hover_radar)
                fig.tight_layout(pad=0.6)
                fl.addWidget(canvas)
            else:
                fig.tight_layout(pad=0.6)
                img = QLabel()
                img.setPixmap(_to_pixmap(fig))
                img.setAlignment(Qt.AlignCenter)
                img.setStyleSheet("background: transparent; padding: 4px;")
                fl.addWidget(img)
            return frame
        except Exception as e:
            print(f"[chart_radar] {e}")
            return None

    # ── 成绩表 ────────────────────────────────────────────────────────────────
    def _make_table(self, scores: list) -> QTableWidget:
        cols = ["姓名", "学号", "总分", "交互质量", "知识掌握", "成果表达", "学习反思", "交互轮次", "深度"]
        table = QTableWidget(len(scores), len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setStyleSheet(TABLE_STYLE)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setMaximumHeight(300)

        for row, s in enumerate(scores):
            sc = s.get("scores", {})
            ia = s.get("interaction_analysis", {})
            total = s.get("total_score", 0)
            if total >= 85:   tc = SCORE_A
            elif total >= 70: tc = SCORE_B
            elif total >= 60: tc = SCORE_C
            else:             tc = SCORE_F

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
