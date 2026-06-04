"""
Reusable UI Widgets — Clean Academic Style
清爽学术风组件：去边框、大留白、微阴影、柔和圆角
"""

from PyQt5.QtWidgets import (
    QWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout,
    QPushButton, QSizePolicy, QProgressBar, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath, QBrush, QPen
from PyQt5.QtSvg import QSvgWidget
from ui.styles import *

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


# ── Worker Thread ─────────────────────────────────────────────────────────────

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


# ── 阴影效果（更柔和更淡）─────────────────────────────────────────────────────

def add_shadow(widget, blur=24, offset_y=6, color="#0F172A14"):
    """柔和冷色阴影，用于卡片层次。"""
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset_y)
    c = QColor(color) if isinstance(color, str) and color.startswith("#") else QColor(15, 23, 42, 18)
    effect.setColor(c)
    widget.setGraphicsEffect(effect)
    return effect


def add_shadow_medium(widget, blur=36, offset_y=10, color="#1E293B20"):
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset_y)
    c = QColor(color) if isinstance(color, str) and color.startswith("#") else QColor(30, 41, 59, 28)
    effect.setColor(c)
    widget.setGraphicsEffect(effect)
    return effect


# ── 扁平插画 SVG（更新配色）────────────────────────────────────────────────────

ILLUSTRATION_KNOWLEDGE_TREE = """
<svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="148" rx="60" ry="8" fill="#C4B5FD" opacity="0.3"/>
  <rect x="94" y="95" width="12" height="55" rx="6" fill="#93C5FD"/>
  <circle cx="100" cy="75" r="38" fill="#2563EB" opacity="0.9"/>
  <circle cx="72" cy="88" r="22" fill="#60A5FA" opacity="0.85"/>
  <circle cx="128" cy="85" r="26" fill="#60A5FA" opacity="0.8"/>
  <circle cx="100" cy="55" r="28" fill="#C4B5FD" opacity="0.6"/>
  <circle cx="85" cy="65" r="6" fill="#7C3AED"/>
  <circle cx="112" cy="70" r="5" fill="#A78BFA"/>
  <circle cx="96" cy="82" r="4" fill="#FFFFFF" opacity="0.9"/>
  <circle cx="76" cy="82" r="4" fill="#7C3AED" opacity="0.7"/>
  <circle cx="120" cy="75" r="4" fill="#FFFFFF" opacity="0.7"/>
  <line x1="100" y1="95" x2="85" y2="65" stroke="#FFFFFF" stroke-width="1.5" opacity="0.5"/>
  <line x1="100" y1="95" x2="112" y2="70" stroke="#FFFFFF" stroke-width="1.5" opacity="0.5"/>
  <line x1="100" y1="95" x2="96" y2="82" stroke="#FFFFFF" stroke-width="1.5" opacity="0.5"/>
</svg>
"""

ILLUSTRATION_CAMPUS = """
<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="80" fill="#DBEAFE" rx="8"/>
  <ellipse cx="40" cy="25" rx="20" ry="10" fill="white" opacity="0.9"/>
  <ellipse cx="55" cy="20" rx="16" ry="9" fill="white" opacity="0.8"/>
  <ellipse cx="150" cy="30" rx="18" ry="8" fill="white" opacity="0.7"/>
  <rect y="80" width="200" height="40" fill="#BFDBFE"/>
  <rect x="70" y="35" width="60" height="55" rx="4" fill="#2563EB"/>
  <rect x="88" y="22" width="24" height="20" rx="3" fill="#1D4ED8"/>
  <rect x="88" y="63" width="24" height="27" rx="0" fill="#1D4ED8"/>
  <path d="M88 63 Q100 50 112 63" fill="#1E40AF"/>
  <rect x="76" y="44" width="10" height="12" rx="2" fill="#C4B5FD"/>
  <rect x="114" y="44" width="10" height="12" rx="2" fill="#C4B5FD"/>
  <rect x="76" y="62" width="10" height="12" rx="2" fill="#C4B5FD"/>
  <rect x="114" y="62" width="10" height="12" rx="2" fill="#C4B5FD"/>
  <rect x="20" y="55" width="40" height="35" rx="3" fill="#60A5FA"/>
  <rect x="140" y="50" width="42" height="40" rx="3" fill="#60A5FA"/>
  <rect x="50" y="78" width="4" height="12" fill="#93C5FD"/>
  <circle cx="52" cy="72" r="8" fill="#2563EB"/>
  <rect x="155" y="75" width="4" height="15" fill="#93C5FD"/>
  <circle cx="157" cy="68" r="10" fill="#2563EB"/>
  <path d="M88 90 Q100 95 112 90 L115 120 L85 120 Z" fill="#D4A373" opacity="0.4"/>
</svg>
"""

ILLUSTRATION_EXPLORE = """
<svg viewBox="0 0 180 130" xmlns="http://www.w3.org/2000/svg">
  <circle cx="90" cy="65" r="55" fill="#DBEAFE" opacity="0.5"/>
  <rect x="45" y="70" width="55" height="38" rx="4" fill="#2563EB"/>
  <rect x="100" y="70" width="35" height="38" rx="4" fill="#60A5FA"/>
  <rect x="43" y="68" width="4" height="42" rx="2" fill="#1D4ED8"/>
  <line x1="55" y1="82" x2="88" y2="82" stroke="#C4B5FD" stroke-width="1.5"/>
  <line x1="55" y1="90" x2="88" y2="90" stroke="#C4B5FD" stroke-width="1.5"/>
  <line x1="55" y1="98" x2="75" y2="98" stroke="#C4B5FD" stroke-width="1.5"/>
  <circle cx="118" cy="52" r="22" fill="none" stroke="#7C3AED" stroke-width="4"/>
  <circle cx="118" cy="52" r="15" fill="#FEF3C7" opacity="0.8"/>
  <line x1="134" y1="68" x2="148" y2="83" stroke="#7C3AED" stroke-width="5" stroke-linecap="round"/>
  <circle cx="110" cy="46" r="4" fill="#7C3AED"/>
  <circle cx="122" cy="54" r="3" fill="#A78BFA"/>
  <circle cx="115" cy="58" r="3" fill="#7C3AED" opacity="0.6"/>
  <circle cx="65" cy="48" r="4" fill="#A78BFA"/>
  <circle cx="82" cy="38" r="3" fill="#7C3AED" opacity="0.7"/>
  <circle cx="50" cy="55" r="3" fill="#2563EB"/>
</svg>
"""

ILLUSTRATION_CHART = """
<svg viewBox="0 0 160 100" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="8" width="140" height="80" rx="8" fill="#DBEAFE"/>
  <line x1="25" y1="20" x2="140" y2="20" stroke="#BFDBFE" stroke-width="1"/>
  <line x1="25" y1="35" x2="140" y2="35" stroke="#BFDBFE" stroke-width="1"/>
  <line x1="25" y1="50" x2="140" y2="50" stroke="#BFDBFE" stroke-width="1"/>
  <line x1="25" y1="65" x2="140" y2="65" stroke="#BFDBFE" stroke-width="1"/>
  <rect x="32" y="38" width="14" height="42" rx="4" fill="#60A5FA"/>
  <rect x="54" y="28" width="14" height="52" rx="4" fill="#2563EB"/>
  <rect x="76" y="44" width="14" height="36" rx="4" fill="#60A5FA"/>
  <rect x="98" y="22" width="14" height="58" rx="4" fill="#7C3AED"/>
  <rect x="120" y="32" width="14" height="48" rx="4" fill="#2563EB"/>
  <polyline points="39,38 61,30 83,44 105,24 127,34"
    fill="none" stroke="#A78BFA" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="39" cy="38" r="3.5" fill="#A78BFA"/>
  <circle cx="61" cy="30" r="3.5" fill="#A78BFA"/>
  <circle cx="83" cy="44" r="3.5" fill="#A78BFA"/>
  <circle cx="105" cy="24" r="3.5" fill="#A78BFA"/>
  <circle cx="127" cy="34" r="3.5" fill="#A78BFA"/>
</svg>
"""

ILLUSTRATION_EMPTY = """
<svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg">
  <rect x="30" y="40" width="140" height="100" rx="12" fill="#F3F4F6" opacity="0.6"/>
  <rect x="45" y="55" width="80" height="8" rx="4" fill="#E5E7EB"/>
  <rect x="45" y="72" width="60" height="6" rx="3" fill="#E5E7EB"/>
  <rect x="45" y="85" width="100" height="6" rx="3" fill="#E5E7EB"/>
  <rect x="45" y="98" width="70" height="6" rx="3" fill="#E5E7EB"/>
  <circle cx="150" cy="50" r="25" fill="#DBEAFE" opacity="0.5"/>
  <circle cx="150" cy="50" r="15" fill="#2563EB" opacity="0.15"/>
  <circle cx="60" cy="130" r="8" fill="#FEF3C7" opacity="0.5"/>
  <circle cx="160" cy="120" r="6" fill="#DBEAFE" opacity="0.5"/>
</svg>
"""

ILLUSTRATION_SUCCESS = """
<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <circle cx="60" cy="60" r="50" fill="#DBEAFE" opacity="0.5"/>
  <circle cx="60" cy="60" r="36" fill="#2563EB"/>
  <path d="M44 62 L54 72 L76 50" fill="none" stroke="white" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


def make_svg_widget(svg_str: str, width: int, height: int) -> QLabel:
    """把 SVG 字符串渲染为 QLabel（使用 QSvgWidget 内嵌）"""
    try:
        svg_widget = QSvgWidget()
        svg_widget.load(svg_str.encode('utf-8'))
        svg_widget.setFixedSize(width, height)
        svg_widget.setStyleSheet("background: transparent;")
        return svg_widget
    except Exception:
        lbl = QLabel()
        lbl.setFixedSize(width, height)
        return lbl


# ── Section Header ────────────────────────────────────────────────────────────

class SectionHeader(QLabel):
    """小节标题，带绿色左边线装饰"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {TEXT_H1};
            font-size: 17px;
            font-weight: 900;
            padding-left: 14px;
            border-left: 5px solid {GREEN_PRI};
            background: transparent;
            letter-spacing: 0.2px;
        """)
        self.setFixedHeight(32)


class SubHeader(QLabel):
    """二级标题"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {TEXT_SEC};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            background: transparent;
            padding-bottom: 6px;
        """)
        self.setFixedHeight(24)


# ── Divider ───────────────────────────────────────────────────────────────────

class HDivider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet(f"background: {BORDER_LIGHT}; max-height: 1px; border: none;")
        self.setFixedHeight(1)


class VDivider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setStyleSheet(f"background: {BORDER_LIGHT}; max-width: 1px; border: none;")
        self.setFixedWidth(1)


# ── Stat Cards ────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """统计数字卡片，去边框，微阴影"""
    def __init__(self, label: str, value: str,
                 color: str = GREEN_PRI,
                 bg_color: str = None,
                 icon_svg: str = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("statcard")
        bg = bg_color or BG_CARD
        self.setStyleSheet(f"""
            QFrame#statcard {{
                background: {bg};
                border: 1px solid rgba(226, 232, 240, 0.62);
                border-radius: {RADIUS_LG}px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(90)
        add_shadow(self, blur=16, offset_y=3)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        top = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
        top.addWidget(lbl)
        top.addStretch()
        if icon_svg:
            try:
                ico = make_svg_widget(icon_svg, 28, 28)
                top.addWidget(ico)
            except Exception:
                pass
        lay.addLayout(top)

        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 800; background: transparent;")
        val.setObjectName("stat_value")
        lay.addWidget(val)

        # 底部装饰线（极细，仅作微妙点缀）
        bar = QFrame()
        bar.setFixedHeight(2)
        bar.setStyleSheet(f"""
            background: {color}22;
            border-radius: 1px;
        """)
        lay.addWidget(bar)

    def set_value(self, v: str):
        self.findChild(QLabel, "stat_value").setText(v)


class MiniStatCard(QFrame):
    """小型统计卡（右侧面板用）"""
    def __init__(self, label: str, value: str, color: str = GREEN_PRI, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid rgba(226, 232, 240, 0.62);
                border-radius: {RADIUS}px;
            }}
        """)
        add_shadow(self, blur=12, offset_y=2)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; background: transparent;")
        val = QLabel(value)
        val.setObjectName("mini_val")
        val.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 800; background: transparent;")
        left.addWidget(lbl)
        left.addWidget(val)
        lay.addLayout(left)
        lay.addStretch()

    def set_value(self, v: str):
        self.findChild(QLabel, "mini_val").setText(v)


# ── Score Bar ─────────────────────────────────────────────────────────────────

class ScoreBar(QWidget):
    def __init__(self, label: str, score: int, max_score: int,
                 color: str = GREEN_PRI, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 5, 0, 5)
        lay.setSpacing(14)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
        lbl.setFixedWidth(80)

        bar = QProgressBar()
        bar.setRange(0, max_score)
        bar.setValue(score)
        bar.setFixedHeight(8)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: {BG_INPUT};
                border-radius: 4px;
                border: none;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {color}AA);
                border-radius: 4px;
            }}
        """)

        val = QLabel(f"{score}/{max_score}")
        val.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px; background: transparent;")
        val.setFixedWidth(48)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(lbl)
        lay.addWidget(bar, 1)
        lay.addWidget(val)


# ── Tag Badge ─────────────────────────────────────────────────────────────────

class TagBadge(QLabel):
    STYLES = {
        "core":        (GREEN_DARK,   "#DBEAFE"),
        "important":   (ORANGE_DARK,  ORANGE_LIGHT),
        "extended":    (TEXT_SEC,     BG_INPUT),
        "concept":     (INFO,         "#DBEAFE"),
        "algorithm":   (GREEN_PRI,    GREEN_LIGHT),
        "difficulty":  (DANGER,       "#FEE2E2"),
        "application": (INFO,         "#DBEAFE"),
        "default":     (TEXT_SEC,     BG_INPUT),
    }

    def __init__(self, text: str, kind: str = "default", parent=None):
        super().__init__(text, parent)
        color, bg = self.STYLES.get(kind, self.STYLES["default"])
        self.setStyleSheet(f"""
            color: {color};
            background: {bg};
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        self.setFixedHeight(24)


# ── Info Row ──────────────────────────────────────────────────────────────────

def make_info_row(label: str, value: str, val_color: str = TEXT_PRI) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; background: transparent;")
    val = QLabel(value)
    val.setStyleSheet(f"color: {val_color}; font-size: 13px; font-weight: 700; background: transparent;")
    lay.addWidget(lbl)
    lay.addStretch()
    lay.addWidget(val)
    return w


# ── Loading Overlay ───────────────────────────────────────────────────────────

class LoadingWidget(QWidget):
    def __init__(self, text="处理中，请稍候…", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            background: rgba(245, 247, 251, 0.94);
            border: 1px solid rgba(226, 232, 240, 0.62);
            border-radius: {RADIUS_LG}px;
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(18)

        # 插画装饰
        try:
            svg_w = make_svg_widget(ILLUSTRATION_EXPLORE, 100, 72)
            lay.addWidget(svg_w, alignment=Qt.AlignCenter)
        except Exception:
            pass

        msg = QLabel(text)
        msg.setObjectName("loading_msg")
        msg.setStyleSheet(f"color: {TEXT_H1}; font-size: 16px; font-weight: 700; background: transparent;")
        msg.setAlignment(Qt.AlignCenter)

        sub = QLabel("正在调用大模型分析，约需 15–40 秒")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; background: transparent;")
        sub.setAlignment(Qt.AlignCenter)

        # 进度指示点
        dots = QLabel("●  ●  ●")
        dots.setStyleSheet(f"color: {GREEN_MUTED}; font-size: 10px; letter-spacing: 8px; background: transparent;")
        dots.setAlignment(Qt.AlignCenter)

        lay.addWidget(msg)
        lay.addWidget(dots)
        lay.addWidget(sub)

    def set_text(self, text: str):
        self.findChild(QLabel, "loading_msg").setText(text)


# ── Panel Helper ──────────────────────────────────────────────────────────────

def make_panel(title: str = "", with_shadow: bool = True) -> QFrame:
    """创建标准内容面板（去边框，微阴影）"""
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {BG_CARD};
            border: none;
            border-radius: {RADIUS_LG}px;
        }}
    """)
    if with_shadow:
        add_shadow(f, blur=14, offset_y=3)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(22, 20, 22, 20)
    lay.setSpacing(14)
    if title:
        lay.addWidget(SubHeader(title))
        lay.addWidget(HDivider())
    return f


# ── 装饰性背景插画 Label ───────────────────────────────────────────────────────

class IllustrationLabel(QLabel):
    """在页面空白区展示扁平插画，半透明装饰"""
    def __init__(self, svg_str: str, width: int = 120, height: int = 90, parent=None):
        super().__init__(parent)
        try:
            svg_w = make_svg_widget(svg_str, width, height)
            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(svg_w)
        except Exception:
            pass
        self.setStyleSheet("background: transparent;")


# ── 空状态组件 ────────────────────────────────────────────────────────────────

class EmptyStateWidget(QWidget):
    """空状态提示组件"""
    def __init__(self, title: str = "暂无数据", subtitle: str = "",
                 icon_svg: str = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(14)

        svg = icon_svg or ILLUSTRATION_EMPTY
        try:
            ico = make_svg_widget(svg, 140, 110)
            lay.addWidget(ico, alignment=Qt.AlignCenter)
        except Exception:
            pass

        t = QLabel(title)
        t.setStyleSheet(f"color: {TEXT_SEC}; font-size: 15px; font-weight: 700; background: transparent;")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; background: transparent;")
            s.setAlignment(Qt.AlignCenter)
            s.setWordWrap(True)
            lay.addWidget(s)
