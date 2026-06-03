"""
UI Theme: Swiss minimalist — stone, ivory, one precise accent
"""

# ── Palette (restricted — every color earns its place) ────────────────────────
BG_DARK    = "#F5F7FA"   # app background
BG_PANEL   = "#FFFFFF"   # sidebar white
BG_CARD    = "#FFFFFF"   # card white
BG_INPUT   = "#F0F4F8"   # input field
BORDER     = "#DDE5EE"   # hairline border
BORDER_LT  = "#B8C4D2"   # slightly stronger border

ACCENT     = "#22304A"   # primary action
ACCENT2    = "#167A5B"   # success
ACCENT3    = "#B7791F"   # warning
ACCENT4    = "#C2413A"   # danger
ACCENT5    = "#2F6EA6"   # info

TEXT_PRI   = "#172033"   # primary text
TEXT_SEC   = "#536174"   # secondary
TEXT_DIM   = "#8A97A8"   # dimmed

FONT_MAIN  = "Microsoft YaHei UI"
FONT_SIZE  = 13
SIDEBAR_W  = 220
RADIUS     = 6

# ── Global stylesheet ──────────────────────────────────────────────────────────
MAIN_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRI};
    font-family: "{FONT_MAIN}", "PingFang SC", "Segoe UI", sans-serif;
    font-size: {FONT_SIZE}px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 5px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LT}; border-radius: 2px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_LT}; border-radius: 2px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{ background: {BORDER}; }}
QToolTip {{
    background: {ACCENT}; color: white;
    border: none; padding: 5px 10px; border-radius: 4px;
    font-size: 12px;
}}
"""

SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}
"""

NAV_BTN_STYLE = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_SEC};
    border: none;
    border-radius: 0;
    padding: 0 20px;
    text-align: left;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background: {BG_DARK};
    color: {TEXT_PRI};
}}
QPushButton[active="true"] {{
    background: {BG_DARK};
    color: {ACCENT};
    font-weight: 700;
    border-left: 2px solid {ACCENT};
}}
"""

PRIMARY_BTN = f"""
QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{ background: #2D3F60; }}
QPushButton:pressed {{ background: #172033; }}
QPushButton:disabled {{ background: {BORDER_LT}; color: {TEXT_DIM}; }}
"""

SECONDARY_BTN = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_PRI};
    border: 1px solid {BORDER_LT};
    border-radius: {RADIUS}px;
    padding: 9px 20px;
    font-weight: 500;
    font-size: 12px;
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; background: {BG_DARK}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
"""

GHOST_BTN = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 8px 16px;
    font-size: 12px;
}}
QPushButton:hover {{ color: {TEXT_PRI}; border-color: {ACCENT5}; background: #F8FBFF; }}
"""

DANGER_BTN = f"""
QPushButton {{
    background: transparent;
    color: {ACCENT4};
    border: 1px solid {ACCENT4};
    border-radius: {RADIUS}px;
    padding: 9px 20px;
    font-weight: 500;
}}
QPushButton:hover {{ background: rgba(192,57,43,0.06); }}
"""

INPUT_STYLE = f"""
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 9px 12px;
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
    background: {BG_PANEL};
}}
QComboBox {{
    background: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 8px 12px;
    font-size: 13px;
}}
QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QSpinBox {{
    background: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 8px 12px;
    font-size: 13px;
}}
QSpinBox:focus {{ border: 1px solid {ACCENT}; background: {BG_PANEL}; }}
QCheckBox {{
    color: {TEXT_SEC};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER_LT};
    border-radius: 3px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 1px solid {BORDER_LT};
    color: {TEXT_PRI};
    selection-background-color: {BG_DARK};
    selection-color: {TEXT_PRI};
    outline: none;
}}
"""

CARD_STYLE = f"""
QFrame#card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
"""

TABLE_STYLE = f"""
QTableWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    gridline-color: {BORDER};
    color: {TEXT_PRI};
    font-size: 12px;
    outline: none;
}}
QTableWidget::item {{
    padding: 10px 14px;
    border: none;
}}
QTableWidget::item:selected {{
    background: {BG_DARK};
    color: {TEXT_PRI};
}}
QHeaderView::section {{
    background: {BG_CARD};
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 10px 14px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QTableWidget::item:hover {{ background: {BG_DARK}; }}
"""

TAB_STYLE = f"""
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    background: {BG_CARD};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SEC};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 20px;
    font-size: 12px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRI};
    border-bottom: 2px solid {ACCENT};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{ color: {TEXT_PRI}; }}
"""

PROGRESS_STYLE = f"""
QProgressBar {{
    background: {BORDER};
    border-radius: 3px;
    height: 4px;
    color: transparent;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}
"""

LABEL_STYLE = f"QLabel {{ color: {TEXT_PRI}; background: transparent; }}"
