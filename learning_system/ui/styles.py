"""
UI Theme: Aurora Academic — Pearl White + Indigo Blue + Violet Accent
现代学术风：柔和冷白背景、蓝紫主色、玻璃感卡片、精致圆角和轻阴影。
"""

# ── Palette ────────────────────────────────────────────────────────────────────
BG_APP       = "#F5F7FB"
BG_PANEL     = "#FFFFFF"
BG_CARD      = "#FFFFFF"
BG_INPUT     = "#F8FAFC"
BG_HOVER     = "#EEF4FF"

GREEN_PRI    = "#2563EB"
GREEN_DARK   = "#1D4ED8"
GREEN_LIGHT  = "#DBEAFE"
GREEN_MUTED  = "#93C5FD"

ORANGE_PRI   = "#7C3AED"
ORANGE_DARK  = "#6D28D9"
ORANGE_LIGHT = "#F3E8FF"
ORANGE_MUTED = "#C4B5FD"

BORDER       = "#E2E8F0"
BORDER_LIGHT = "#EEF2F7"

TEXT_H1      = "#0F172A"
TEXT_PRI     = "#334155"
TEXT_SEC     = "#64748B"
TEXT_DIM     = "#94A3B8"

SUCCESS      = "#10B981"
WARNING      = "#F59E0B"
DANGER       = "#EF4444"
INFO         = "#0EA5E9"

SCORE_A      = "#10B981"
SCORE_B      = "#22C55E"
SCORE_C      = "#F59E0B"
SCORE_D      = "#F97316"
SCORE_F      = "#EF4444"

FONT_MAIN    = "Microsoft YaHei"
FONT_SIZE    = 14
SIDEBAR_W    = 246
RADIUS       = 14
RADIUS_SM    = 10
RADIUS_LG    = 20

# ── 全局样式 ──────────────────────────────────────────────────────────────────
MAIN_STYLE = f"""
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #F8FBFF, stop:0.45 {BG_APP}, stop:1 #F4F0FF);
}}
QWidget {{
    color: {TEXT_PRI};
    font-family: "{FONT_MAIN}", "PingFang SC", "Segoe UI", sans-serif;
    font-size: {FONT_SIZE}px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 6px 2px 6px 0;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: {GREEN_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border-radius: 4px;
    margin: 0 6px 2px 6px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {GREEN_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{
    background: rgba(148, 163, 184, 0.22);
    border-radius: 1px;
}}
QSplitter::handle:hover {{ background: {GREEN_MUTED}; }}
QToolTip {{
    background: {TEXT_H1};
    color: white;
    border: 1px solid rgba(255,255,255,0.12);
    padding: 9px 14px;
    border-radius: {RADIUS_SM}px;
    font-size: 12px;
}}
QMessageBox {{
    background: {BG_CARD};
}}
QMessageBox QLabel {{
    color: {TEXT_PRI};
    background: transparent;
}}
QMessageBox QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GREEN_PRI}, stop:1 {ORANGE_PRI});
    color: white;
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: 9px 22px;
    font-weight: 700;
    min-width: 88px;
}}
QMessageBox QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GREEN_DARK}, stop:1 {ORANGE_DARK});
}}
"""

# ── 侧边栏 ───────────────────────────────────────────────────────────────────
SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.52 #F8FBFF, stop:1 #F4F7FF);
    border-right: 1px solid rgba(226, 232, 240, 0.85);
}}
"""

# ── 导航按钮 ─────────────────────────────────────────────────────────────────
NAV_BTN_STYLE = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_SEC};
    border: 1px solid transparent;
    border-radius: 16px;
    padding: 0 10px;
    margin: 4px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: rgba(37, 99, 235, 0.06);
    border-color: rgba(37, 99, 235, 0.08);
    color: {TEXT_H1};
}}
QPushButton[active="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(37, 99, 235, 0.10), stop:1 rgba(124, 58, 237, 0.08));
    border: 1px solid rgba(37, 99, 235, 0.16);
    color: {GREEN_DARK};
    font-weight: 600;
}}
"""

# ── 按钮样式 ───────────────────────────────────────────────────────────────────
PRIMARY_BTN = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {GREEN_PRI}, stop:0.55 #4F46E5, stop:1 {ORANGE_PRI});
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 11px 24px;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.4px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {GREEN_DARK}, stop:0.55 #4338CA, stop:1 {ORANGE_DARK});
}}
QPushButton:pressed {{ background: #4338CA; }}
QPushButton:disabled {{
    background: #E2E8F0;
    color: #94A3B8;
}}
"""

GREEN_BTN = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GREEN_PRI}, stop:1 #38BDF8);
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 11px 22px;
    font-weight: 800;
    font-size: 14px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GREEN_DARK}, stop:1 #0284C7);
}}
QPushButton:pressed {{ background: {GREEN_DARK}; }}
QPushButton:disabled {{
    background: #E2E8F0;
    color: #94A3B8;
}}
"""

SECONDARY_BTN = f"""
QPushButton {{
    background: rgba(255, 255, 255, 0.92);
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 10px 20px;
    font-weight: 700;
    font-size: 14px;
}}
QPushButton:hover {{
    border-color: rgba(37, 99, 235, 0.45);
    color: {GREEN_DARK};
    background: {BG_HOVER};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    border-color: {BORDER};
    background: #F8FAFC;
}}
"""

GHOST_BTN = f"""
QPushButton {{
    background: rgba(241, 245, 249, 0.92);
    color: {TEXT_SEC};
    border: 1px solid rgba(226, 232, 240, 0.70);
    border-radius: {RADIUS_SM}px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    color: {GREEN_DARK};
    border-color: rgba(37, 99, 235, 0.26);
}}
"""

DANGER_BTN = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {DANGER}, stop:1 #FB7185);
    color: white;
    border: none;
    border-radius: {RADIUS}px;
    padding: 11px 22px;
    font-weight: 800;
    font-size: 14px;
}}
QPushButton:hover {{ background: #DC2626; }}
"""

# ── 输入控件 ───────────────────────────────────────────────────────────────────
INPUT_STYLE = f"""
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: rgba(255, 255, 255, 0.96);
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 160%;
    selection-background-color: {GREEN_LIGHT};
    selection-color: {GREEN_DARK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {GREEN_PRI};
    background: #FFFFFF;
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border: 1px solid #CBD5E1;
}}
QComboBox {{
    background: rgba(255, 255, 255, 0.96);
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 400;
    min-height: 36px;
}}
QComboBox:focus {{ border: 1.5px solid {GREEN_PRI}; }}
QComboBox:hover {{ border: 1px solid #CBD5E1; }}
QComboBox::drop-down {{ border: none; width: 42px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
    width: 0;
    height: 0;
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    color: {TEXT_PRI};
    selection-background-color: #EAF1FF;
    selection-color: {GREEN_DARK};
    outline: none;
    border-radius: 16px;
    padding: 10px;
    margin-top: 8px;
    font-size: 15px;
    font-weight: 400;
}}
QComboBox QAbstractItemView::item {{
    min-height: 40px;
    padding: 8px 14px;
    border-radius: 10px;
}}
QSpinBox {{
    background: rgba(255, 255, 255, 0.96);
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 10px 16px;
    font-size: 14px;
}}
QSpinBox:focus {{ border: 1.5px solid {GREEN_PRI}; }}
QCheckBox {{
    color: {TEXT_SEC};
    spacing: 10px;
    background: transparent;
    font-size: 14px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    background: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background: {GREEN_PRI};
    border-color: {GREEN_PRI};
}}
QCheckBox::indicator:hover {{ border-color: {GREEN_MUTED}; }}
"""

# ── 表格样式 ───────────────────────────────────────────────────────────────────
TABLE_STYLE = f"""
QTableWidget {{
    background: {BG_CARD};
    border: none;
    border-radius: {RADIUS_LG}px;
    gridline-color: transparent;
    color: {TEXT_PRI};
    font-size: 13px;
    outline: none;
    alternate-background-color: #F8FAFC;
}}
QTableWidget::item {{
    padding: 12px 16px;
    border: none;
    border-bottom: 1px solid {BORDER_LIGHT};
}}
QTableWidget::item:selected {{
    background: {GREEN_LIGHT};
    color: {GREEN_DARK};
}}
QTableWidget::item:hover {{ background: {BG_HOVER}; }}
QHeaderView::section {{
    background: #F8FAFC;
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 13px 16px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.5px;
}}
QHeaderView::section:hover {{ background: {BG_HOVER}; }}
"""

# ── 列表样式 ───────────────────────────────────────────────────────────────────
LIST_STYLE = f"""
QListWidget {{
    background: {BG_CARD};
    border: 1px solid rgba(226, 232, 240, 0.85);
    border-radius: {RADIUS_LG}px;
    outline: none;
    padding: 6px;
}}
QListWidget::item {{
    border-radius: {RADIUS_SM}px;
    padding: 11px 14px;
    margin: 3px 4px;
    color: {TEXT_PRI};
}}
QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(37, 99, 235, 0.14), stop:1 rgba(124, 58, 237, 0.10));
    color: {GREEN_DARK};
    font-weight: 800;
}}
QListWidget::item:hover {{ background: {BG_HOVER}; }}
"""

# ── Tab 样式 ───────────────────────────────────────────────────────────────────
TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    border-radius: {RADIUS_LG}px;
    background: {BG_CARD};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SEC};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 13px 22px;
    font-weight: 800;
    font-size: 14px;
}}
QTabBar::tab:hover {{ color: {TEXT_H1}; }}
QTabBar::tab:selected {{
    color: {GREEN_PRI};
    border-bottom: 3px solid {GREEN_PRI};
    background: transparent;
}}
"""

CARD_STYLE = f"""
    background: {BG_CARD};
    border: 1px solid rgba(226, 232, 240, 0.62);
    border-radius: {RADIUS_LG}px;
"""

CARD_ELEVATED = f"""
    background: {BG_CARD};
    border: 1px solid rgba(226, 232, 240, 0.48);
    border-radius: {RADIUS_LG}px;
"""

# ── 进度条 ─────────────────────────────────────────────────────────────────────
PROGRESS_STYLE = f"""
QProgressBar {{
    background: #E2E8F0;
    border-radius: 5px;
    border: none;
    color: transparent;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GREEN_PRI}, stop:0.55 #38BDF8, stop:1 {ORANGE_PRI});
    border-radius: 5px;
}}
"""

# ── 菜单样式 ───────────────────────────────────────────────────────────────────
MENU_STYLE = f"""
QMenu {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 8px;
}}
QMenu::item {{
    padding: 9px 22px;
    border-radius: {RADIUS_SM - 2}px;
    color: {TEXT_PRI};
}}
QMenu::item:selected {{
    background: {BG_HOVER};
    color: {GREEN_DARK};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER_LIGHT};
    margin: 7px 12px;
}}
"""
