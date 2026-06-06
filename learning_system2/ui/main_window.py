"""
Main Window — Calm Academic Style
清爽侧边栏导航 + 品牌区 + 高密度内容区
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtSvg import QSvgWidget

from ui.styles import *
from ui.widgets import (
    add_shadow, make_svg_widget,
    ILLUSTRATION_KNOWLEDGE_TREE, ILLUSTRATION_CAMPUS,
    ILLUSTRATION_EXPLORE, ILLUSTRATION_CHART
)
from ui.page_task_gen import TaskGenPage
from ui.page_eval import EvalPage
from ui.page_stats import StatsPage
from ui.page_tasks import TaskEditorPage
from ui.page_settings import SettingsPage
from ui.page_history import HistoryPage

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

NAV_ITEMS = [
    ("ri.upload-cloud-2-line",      "课件导入",  "提取知识点 · 生成任务", 0),
    ("ri.edit-box-line",            "任务管理",  "查看 · 编辑 · 导出",   1),
    ("ri.file-list-3-line",          "成果评阅",  "自动评分 · 评语生成",  2),
    ("ri.bar-chart-grouped-line",   "学情统计",  "数据分析 · 可视化",    3),
    ("ri.history-line",             "历史数据",  "查看 · 导出 · 清理",   4),
    ("ri.settings-3-line",          "系统设置",  "API · 配置",           5),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CourseAI · 探究式学习任务评估系统")
        self.resize(1400, 880)
        self.setMinimumSize(1100, 700)
        self._nav_btns = []
        self._setup_ui()
        self._switch_page(0)

    def _setup_ui(self):
        self.setStyleSheet(MAIN_STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar.setStyleSheet(SIDEBAR_STYLE)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # Brand block
        brand_w = QWidget()
        brand_w.setFixedHeight(104)
        brand_w.setStyleSheet(f"""
            background: {BG_PANEL};
            border-bottom: 1px solid {BORDER_LIGHT};
        """)
        blay = QHBoxLayout(brand_w)
        blay.setContentsMargins(20, 0, 18, 0)
        blay.setSpacing(12)

        try:
            tree_svg = make_svg_widget(ILLUSTRATION_KNOWLEDGE_TREE, 42, 34)
            blay.addWidget(tree_svg)
        except Exception:
            pass

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        name_lbl = QLabel("CourseAI")
        name_lbl.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 900; background: transparent;")
        sub_lbl = QLabel("探究式学习评估系统")
        sub_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 600; background: transparent;")
        text_col.addWidget(name_lbl)
        text_col.addWidget(sub_lbl)
        blay.addLayout(text_col)
        blay.addStretch()
        sb.addWidget(brand_w)

        sb.addSpacing(14)

        # Nav section label
        nav_lbl = QLabel("WORKSPACE")
        nav_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 900; "
                               f"letter-spacing: 1px; padding: 0 22px; background: transparent;")
        nav_lbl.setFixedHeight(22)
        sb.addWidget(nav_lbl)
        sb.addSpacing(6)

        # Nav buttons
        for ico, label, sublabel, idx in NAV_ITEMS:
            btn = self._make_nav_btn(ico, label, sublabel, idx)
            sb.addWidget(btn)
            self._nav_btns.append(btn)

        sb.addStretch()

        # Footer
        footer = QLabel("本地运行 · 数据安全 · v2.0")
        footer.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 10px;
            font-weight: 600;
            padding: 10px 20px 16px;
            background: transparent;
        """)
        sb.addWidget(footer)

        # ── Stack ─────────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        self._pages = [
            TaskGenPage(),
            TaskEditorPage(),
            EvalPage(),
            StatsPage(),
            HistoryPage(),
            SettingsPage(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        root.addWidget(sidebar)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {BORDER_LIGHT};")
        root.addWidget(sep)

        root.addWidget(self._stack, 1)

    def _make_nav_btn(self, ico: str, label: str, sub: str, idx: int) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(68)
        btn.setStyleSheet(NAV_BTN_STYLE)
        btn.setProperty("active", "false")
        btn.setCursor(Qt.PointingHandCursor)

        w = QWidget()
        w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        if HAS_QTA:
            try:
                ico_lbl = QLabel()
                ico_lbl.setFixedSize(20, 20)
                ico_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                btn._ico_name = ico
                btn._ico_lbl = ico_lbl
                self._set_nav_icon(btn, False)
                lay.addWidget(ico_lbl)
            except Exception:
                pass

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        lbl1 = QLabel(label)
        lbl1.setStyleSheet(f"color: {TEXT_H1}; font-size: 14px; font-weight: 700; background: transparent;")
        lbl1.setAttribute(Qt.WA_TransparentForMouseEvents)
        btn._title_lbl = lbl1
        text_col.addWidget(lbl1)
        if sub:
            lbl2 = QLabel(sub)
            lbl2.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-weight: 500; background: transparent;")
            lbl2.setAttribute(Qt.WA_TransparentForMouseEvents)
            btn._sub_lbl = lbl2
            text_col.addWidget(lbl2)
        lay.addLayout(text_col)
        lay.addStretch()

        outer = QHBoxLayout(btn)
        outer.setContentsMargins(8, 0, 8, 0)
        outer.addWidget(w, alignment=Qt.AlignVCenter)

        btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
        return btn

    def _set_nav_icon(self, btn, active: bool):
        if not HAS_QTA or not hasattr(btn, '_ico_lbl'):
            return
        try:
            color = GREEN_PRI if active else TEXT_DIM
            px = qta.icon(btn._ico_name, color=color).pixmap(20, 20)
            btn._ico_lbl.setPixmap(px)
        except Exception:
            pass

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            active = (i == idx)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
            self._set_nav_icon(btn, active)
            if hasattr(btn, '_title_lbl'):
                btn._title_lbl.setStyleSheet(
                    f"color: {GREEN_DARK if active else TEXT_H1}; "
                    f"font-size: 14px; font-weight: {'800' if active else '600'}; background: transparent;"
                )
            if hasattr(btn, '_sub_lbl'):
                btn._sub_lbl.setStyleSheet(
                    f"color: {TEXT_SEC if active else TEXT_DIM}; "
                    f"font-size: 11px; font-weight: 400; background: transparent;"
                )
