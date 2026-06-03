"""
Reusable UI widgets — Swiss minimalist edition
"""

from PyQt5.QtWidgets import (
    QWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout,
    QPushButton, QSizePolicy, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from ui.styles import *
try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


# ── Icon helper ───────────────────────────────────────────────────────────────

def icon(name: str, color: str = TEXT_SEC, size: int = 16):
    """Return a QIcon from qtawesome, or None."""
    if HAS_QTA:
        try:
            return qta.icon(name, color=color, scale_factor=1.0)
        except Exception:
            pass
    return None


def icon_btn(ico_name: str, text: str, style: str, ico_color: str = "white") -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(style)
    if HAS_QTA:
        try:
            btn.setIcon(qta.icon(ico_name, color=ico_color))
        except Exception:
            pass
    return btn


# ── Worker thread ─────────────────────────────────────────────────────────────

class Worker(QThread):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.finished.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            self.error.emit(str(e))


# ── Stat card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str = TEXT_PRI, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: {RADIUS}px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(88)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-weight: 600; letter-spacing: 1px;")

        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")
        val.setObjectName("stat_value")

        lay.addWidget(lbl)
        lay.addWidget(val)

    def set_value(self, value: str):
        self.findChild(QLabel, "stat_value").setText(value)


# ── Section header ────────────────────────────────────────────────────────────

class SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding-bottom: 6px;
        """)
        self.setFixedHeight(28)


# ── Score bar ─────────────────────────────────────────────────────────────────

class ScoreBar(QWidget):
    def __init__(self, label: str, score: int, max_score: int,
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(12)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px;")
        lbl.setFixedWidth(80)

        bar = QProgressBar()
        bar.setRange(0, max_score)
        bar.setValue(score)
        bar.setFixedHeight(4)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: {BORDER}; border-radius: 2px; color: transparent; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}
        """)

        val = QLabel(f"{score}/{max_score}")
        val.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 600; font-size: 12px;")
        val.setFixedWidth(48)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(lbl)
        lay.addWidget(bar, 1)
        lay.addWidget(val)


# ── Loading overlay ───────────────────────────────────────────────────────────

class LoadingWidget(QWidget):
    def __init__(self, text="处理中，请稍候…", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: rgba(248,247,245,0.92); border-radius: {RADIUS}px;")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(12)

        msg = QLabel(text)
        msg.setObjectName("loading_msg")
        msg.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
        msg.setAlignment(Qt.AlignCenter)

        sub = QLabel("这可能需要10-30秒")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        sub.setAlignment(Qt.AlignCenter)

        lay.addWidget(msg)
        lay.addWidget(sub)

    def set_text(self, text: str):
        self.findChild(QLabel, "loading_msg").setText(text)


# ── Divider ───────────────────────────────────────────────────────────────────

class HDivider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px;")
        self.setFixedHeight(1)


# ── Info row ──────────────────────────────────────────────────────────────────

def make_info_row(label: str, value: str, val_color: str = TEXT_PRI) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px;")
    val = QLabel(value)
    val.setStyleSheet(f"color: {val_color}; font-size: 12px; font-weight: 600;")
    lay.addWidget(lbl)
    lay.addStretch()
    lay.addWidget(val)
    return w


# ── Tag badge ─────────────────────────────────────────────────────────────────

class TagBadge(QLabel):
    COLORS = {
        "core":        (TEXT_PRI,  BG_DARK),
        "important":   (ACCENT3,   "#FEF3C7"),
        "extended":    (TEXT_SEC,  BG_INPUT),
        "concept":     (ACCENT5,   "#EFF6FF"),
        "algorithm":   (ACCENT2,   "#F0FDF4"),
        "difficulty":  (ACCENT4,   "#FEF2F2"),
        "application": (ACCENT5,   "#EFF6FF"),
        "default":     (TEXT_SEC,  BG_INPUT),
    }

    def __init__(self, text: str, kind: str = "default", parent=None):
        super().__init__(text, parent)
        color, bg = self.COLORS.get(kind, self.COLORS["default"])
        self.setStyleSheet(f"""
            color: {color};
            background: {bg};
            border: 1px solid {BORDER};
            border-radius: 3px;
            padding: 1px 7px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.3px;
        """)
        self.setFixedHeight(18)
