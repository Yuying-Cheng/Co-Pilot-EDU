"""
UI Theme: Calm Academic
清爽、克制的教学工具风格：浅灰底、白色工作区、蓝绿主色和少量暖色点缀。
"""

# ── Palette ────────────────────────────────────────────────────────────────────
BG_APP       = "#F5F7FA"
BG_PANEL     = "#FFFFFF"
BG_CARD      = "#FFFFFF"
BG_INPUT     = "#F8FAFC"
BG_HOVER     = "#EDF6F9"

# 主色：沉稳蓝绿，适合数据和教学场景
GREEN_PRI    = "#2F80ED"
GREEN_DARK   = "#1D5FBF"
GREEN_LIGHT  = "#E8F2FF"
GREEN_MUTED  = "#8CBFF4"

# 副色：薄荷绿，降低蓝紫单调感
ORANGE_PRI   = "#20B486"
ORANGE_DARK  = "#138461"
ORANGE_LIGHT = "#E6F7F1"
ORANGE_MUTED = "#91D9C2"

BORDER       = "#DDE5EE"
BORDER_LIGHT = "#EAF0F6"

TEXT_H1      = "#18233A"
TEXT_PRI     = "#26364D"
TEXT_SEC     = "#627086"
TEXT_DIM     = "#96A3B6"

SUCCESS      = "#22A05B"
WARNING      = "#D4920A"
DANGER       = "#D94F4F"
INFO         = "#168AAD"

SCORE_A      = "#22A05B"
SCORE_B      = "#4AB87A"
SCORE_C      = "#D4920A"
SCORE_D      = "#E07040"
SCORE_F      = "#D94F4F"

# 图表色板（保留暖橙系给图表，避免图表也变蓝而单调）
CHART_WARM = [
    "#2F80ED",
    "#20B486",
    "#F59E0B",
    "#8B5CF6",
    "#EF6F6C",
    "#168AAD",
    "#64748B",
]

FONT_MAIN    = "Microsoft YaHei"
FONT_SIZE    = 14
SIDEBAR_W    = 248
RADIUS       = 10
RADIUS_SM    = 8
RADIUS_LG    = 14

# ── 全局样式 ──────────────────────────────────────────────────────────────────
MAIN_STYLE = f"""
QMainWindow {{
    background: {BG_APP};
}}
QWidget {{
    color: {TEXT_PRI};
    font-family: "{FONT_MAIN}", "PingFang SC", "Segoe UI", sans-serif;
    font-size: {FONT_SIZE}px;
}}
QLabel {{
    background: transparent;
    border: none;
}}
QMainWindow {{
    background: {BG_APP};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    border-radius: 4px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: #C9D5E4;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {GREEN_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #C9D5E4;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{ background: {GREEN_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:hover {{ background: {GREEN_MUTED}; }}
QToolTip {{
    background: {TEXT_H1};
    color: #FFFFFF;
    border: none;
    padding: 7px 12px;
    border-radius: {RADIUS_SM}px;
    font-size: 12px;
}}
QDialog {{
    background: {BG_APP};
    color: {TEXT_PRI};
}}
QDialog QLabel {{
    color: {TEXT_PRI};
    background: {BG_APP};
}}
QMessageBox {{
    background: {BG_CARD};
    color: {TEXT_PRI};
}}
QMessageBox QLabel {{
    color: {TEXT_PRI};
    background: {BG_CARD};
}}
QMessageBox QPushButton, QDialogButtonBox QPushButton {{
    background: {BG_CARD};
    color: {TEXT_H1};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 7px 22px;
    font-weight: 600;
    font-size: 13px;
    min-width: 72px;
}}
QMessageBox QPushButton:focus, QDialogButtonBox QPushButton:focus {{
    background: {GREEN_LIGHT};
    color: {TEXT_H1};
    border-color: {GREEN_PRI};
}}
QMessageBox QPushButton:hover, QDialogButtonBox QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {GREEN_MUTED};
    color: {GREEN_DARK};
}}
QMessageBox QPushButton:default, QDialogButtonBox QPushButton:default {{
    background: {GREEN_LIGHT};
    color: {TEXT_H1};
    border-color: {GREEN_PRI};
    font-weight: 700;
}}
QMessageBox QPushButton:default:hover, QDialogButtonBox QPushButton:default:hover {{
    background: #DCEBFF;
    color: {GREEN_DARK};
    border-color: {GREEN_DARK};
}}
"""

# ── 侧边栏（保留暖米色）──────────────────────────────────────────────────────
SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background: #FFFFFF;
    border-right: 1px solid {BORDER};
}}
"""

# ── 导航按钮 ─────────────────────────────────────────────────────────────────
NAV_BTN_STYLE = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_SEC};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 0 10px;
    margin: 3px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: #F4F8FC;
    border-color: #E4ECF5;
    color: {TEXT_H1};
}}
QPushButton[active="true"] {{
    background: {GREEN_LIGHT};
    border: 1px solid #CFE2FA;
    color: {GREEN_DARK};
    font-weight: 700;
}}
"""

# ── 主要按钮 ──────────────────────────────────────────────────────────────────
PRIMARY_BTN = f"""
QPushButton {{
    background: {GREEN_PRI};
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 10px 22px;
    font-weight: 800;
    font-size: 14px;
}}
QPushButton:hover {{
    background: {GREEN_DARK};
}}
QPushButton:pressed {{ background: {GREEN_DARK}; }}
QPushButton:disabled {{
    background: #D0D8EE;
    color: {TEXT_DIM};
}}
"""

GREEN_BTN = f"""
QPushButton {{
    background: {GREEN_PRI};
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 10px 20px;
    font-weight: 800;
    font-size: 14px;
}}
QPushButton:hover {{ background: {GREEN_DARK}; }}
QPushButton:pressed {{ background: {GREEN_DARK}; }}
QPushButton:disabled {{
    background: #D0D8EE;
    color: {TEXT_DIM};
}}
"""

SECONDARY_BTN = f"""
QPushButton {{
    background: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 9px 18px;
    font-weight: 700;
    font-size: 14px;
}}
QPushButton:hover {{
    border-color: {GREEN_PRI};
    color: {GREEN_DARK};
    background: {GREEN_LIGHT};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {BORDER_LIGHT};
    background: {BG_INPUT};
}}
"""

GHOST_BTN = f"""
QPushButton {{
    background: {BG_INPUT};
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {GREEN_LIGHT};
    color: {GREEN_DARK};
    border-color: {GREEN_MUTED};
}}
"""

DANGER_BTN = f"""
QPushButton {{
    background: {DANGER};
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 10px 20px;
    font-weight: 800;
    font-size: 14px;
}}
QPushButton:hover {{ background: #BB3838; }}
"""

# ── 输入控件 ───────────────────────────────────────────────────────────────────
INPUT_STYLE = f"""
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 160%;
    selection-background-color: {GREEN_LIGHT};
    selection-color: {GREEN_DARK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {GREEN_PRI};
    background: #FAFCFF;
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border: 1px solid {GREEN_MUTED};
}}
QComboBox {{
    background: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 10px 16px;
    font-size: 14px;
    min-height: 32px;
}}
QComboBox:focus {{ border: 1px solid {GREEN_PRI}; }}
QComboBox:hover {{ border: 1px solid {GREEN_MUTED}; }}
QComboBox::drop-down {{ border: none; width: 36px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    color: {TEXT_PRI};
    selection-background-color: {GREEN_LIGHT};
    selection-color: {GREEN_DARK};
    outline: none;
    padding: 6px;
    font-size: 14px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 36px;
    padding: 6px 12px;
    border-radius: 6px;
}}
QSpinBox {{
    background: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 9px 14px;
    font-size: 14px;
}}
QSpinBox:focus {{ border: 1px solid {GREEN_PRI}; }}
QCheckBox {{
    color: {TEXT_SEC};
    spacing: 8px;
    background: transparent;
    font-size: 14px;
}}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1px solid #BCC8E4;
    border-radius: 5px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background: {GREEN_PRI};
    border-color: {GREEN_PRI};
}}
QCheckBox::indicator:hover {{ border-color: {GREEN_MUTED}; }}
"""

# ── 表格 ──────────────────────────────────────────────────────────────────────
TABLE_STYLE = f"""
QTableWidget {{
    background: {BG_CARD};
    border: none;
    border-radius: {RADIUS}px;
    gridline-color: {BORDER_LIGHT};
    color: {TEXT_PRI};
    font-size: 13px;
    outline: none;
    alternate-background-color: {BG_INPUT};
}}
QTableWidget::item {{
    padding: 11px 14px;
    border: none;
    border-bottom: 1px solid {BORDER_LIGHT};
}}
QTableWidget::item:selected {{
    background: {GREEN_LIGHT};
    color: {GREEN_DARK};
}}
QTableWidget::item:hover {{ background: {BG_HOVER}; }}
QHeaderView::section {{
    background: {BG_INPUT};
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 11px 14px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.5px;
}}
QHeaderView::section:hover {{ background: {GREEN_LIGHT}; color: {GREEN_DARK}; }}
"""

# ── 列表 ──────────────────────────────────────────────────────────────────────
LIST_STYLE = f"""
QListWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    outline: none;
    padding: 4px;
}}
QListWidget::item {{
    border-radius: {RADIUS_SM}px;
    padding: 10px 12px;
    margin: 2px 3px;
    color: {TEXT_PRI};
}}
QListWidget::item:selected {{
    background: {GREEN_LIGHT};
    color: {GREEN_DARK};
    font-weight: 700;
}}
QListWidget::item:hover {{ background: {BG_HOVER}; }}
"""

CARD_STYLE = f"""
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
"""

PROGRESS_STYLE = f"""
QProgressBar {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    border: none;
    color: transparent;
    height: 8px;
}}
QProgressBar::chunk {{
    background: {GREEN_PRI};
    border-radius: 4px;
}}
"""

TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    background: {BG_CARD};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SEC};
    border: none;
    border-bottom: 2.5px solid transparent;
    padding: 12px 20px;
    font-weight: 700;
    font-size: 14px;
}}
QTabBar::tab:hover {{ color: {TEXT_H1}; }}
QTabBar::tab:selected {{
    color: {GREEN_PRI};
    border-bottom: 2.5px solid {GREEN_PRI};
}}
"""

MENU_STYLE = f"""
QMenu {{
    background: {BG_CARD};
    border: 1.5px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 6px;
    color: {TEXT_PRI};
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 6px;
    color: {TEXT_PRI};
}}
QMenu::item:selected {{
    background: {GREEN_LIGHT};
    color: {GREEN_DARK};
}}
"""
