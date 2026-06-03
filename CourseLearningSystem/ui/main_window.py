"""
Main window — Swiss minimalist sidebar navigation
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

from ui.styles import *
from ui.page_task_gen import TaskGenPage
from ui.page_eval import EvalPage
from ui.page_stats import StatsPage
from ui.page_tasks import TaskEditorPage
from ui.page_settings import SettingsPage

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

NAV_ITEMS = [
    ("ri.upload-cloud-line",   "课件导入",   "任务生成", 0),
    ("ri.edit-line",           "任务管理",   "编辑任务", 1),
    ("ri.robot-line",          "成果评阅",   "自动评分", 2),
    ("ri.bar-chart-line",      "学情统计",   "分析报告", 3),
    ("ri.settings-3-line",     "系统设置",   "",        4),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CourseAI · 探究式学习系统")
        self.resize(1320, 860)
        self.setMinimumSize(1024, 700)
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

        # Wordmark
        wm = QWidget()
        wm.setFixedHeight(64)
        wm.setStyleSheet(f"background: {BG_PANEL}; border-bottom: 1px solid {BORDER};")
        wm_lay = QVBoxLayout(wm)
        wm_lay.setContentsMargins(24, 0, 24, 0)
        wm_lay.setAlignment(Qt.AlignVCenter)

        brand = QLabel("CourseAI")
        brand.setStyleSheet(f"color: {TEXT_PRI}; font-size: 15px; font-weight: 700; letter-spacing: -0.5px;")
        sub = QLabel("探究式学习系统")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 0.5px;")
        wm_lay.addWidget(brand)
        wm_lay.addWidget(sub)
        sb.addWidget(wm)

        sb.addSpacing(16)

        # Nav section label
        nav_lbl = QLabel("导航")
        nav_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700; letter-spacing: 2px; padding: 0 24px;")
        nav_lbl.setFixedHeight(20)
        sb.addWidget(nav_lbl)
        sb.addSpacing(4)

        # Nav buttons
        for ico, label, sub_label, idx in NAV_ITEMS:
            btn = self._make_nav_btn(ico, label, sub_label, idx)
            sb.addWidget(btn)
            self._nav_btns.append(btn)

        sb.addStretch()

        # Footer
        footer = QLabel("v2.0 · 本地运行")
        footer.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; padding: 16px 24px;")
        sb.addWidget(footer)

        # ── Stack ─────────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {BG_DARK};")

        self._pages = [
            TaskGenPage(),
            TaskEditorPage(),
            EvalPage(),
            StatsPage(),
            SettingsPage(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        root.addWidget(sidebar)

        # Thin separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {BORDER};")
        root.addWidget(sep)

        root.addWidget(self._stack, 1)

    def _make_nav_btn(self, ico: str, label: str, sub: str, idx: int) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(52)
        btn.setStyleSheet(NAV_BTN_STYLE)
        btn.setProperty("active", "false")
        btn.setCursor(Qt.PointingHandCursor)

        # Layout inside button via custom widget
        w = QWidget()
        w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        if HAS_QTA:
            try:
                ico_lbl = QLabel()
                ico_lbl.setFixedSize(16, 16)
                ico_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                # store icon name for active state refresh
                btn._ico_name = ico
                btn._ico_lbl = ico_lbl
                self._set_nav_icon(btn, False)
                lay.addWidget(ico_lbl)
            except Exception:
                pass

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        lbl1 = QLabel(label)
        lbl1.setStyleSheet(f"color: inherit; font-size: 12px; font-weight: 600; background: transparent;")
        lbl1.setAttribute(Qt.WA_TransparentForMouseEvents)
        text_col.addWidget(lbl1)
        if sub:
            lbl2 = QLabel(sub)
            lbl2.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
            lbl2.setAttribute(Qt.WA_TransparentForMouseEvents)
            text_col.addWidget(lbl2)
        lay.addLayout(text_col)
        lay.addStretch()

        # Embed widget in button
        outer = QHBoxLayout(btn)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(w)

        btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
        return btn

    def _set_nav_icon(self, btn, active: bool):
        if not HAS_QTA or not hasattr(btn, '_ico_lbl'):
            return
        try:
            color = TEXT_PRI if active else TEXT_SEC
            px = qta.icon(btn._ico_name, color=color).pixmap(16, 16)
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
