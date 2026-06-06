#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 必须在 QApplication 创建前设置 DPI 属性
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QColor, QPalette

# 禁用 Windows 11 深色模式对 Qt 窗口的影响
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "windows:darkmode=0")

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

from ui.main_window import MainWindow
from ui.styles import MAIN_STYLE
import llm_client


def _win_force_light(hwnd: int) -> None:
    """调用 DWM API 禁用单个窗口的深色模式。"""
    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(0)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass


class _DialogLightFix(QObject):
    """事件过滤器：让所有 QDialog（包括 QMessageBox）使用浅色调色板。"""
    def __init__(self, app: QApplication):
        super().__init__(app)
        self._app = app

    def eventFilter(self, obj, event):
        if isinstance(obj, QDialog) and event.type() == QEvent.Show:
            obj.setPalette(self._app.palette())
            wid = obj.winId()
            if sys.platform == "win32" and wid:
                _win_force_light(int(wid))
        return False


def main():
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("探究式学习系统")

    # Fusion 风格：避免 Windows 11 深色模式渗透
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor("#F5F7FA"))
    pal.setColor(QPalette.WindowText,      QColor("#26364D"))
    pal.setColor(QPalette.Base,            QColor("#FFFFFF"))
    pal.setColor(QPalette.AlternateBase,   QColor("#F8FAFC"))
    pal.setColor(QPalette.Text,            QColor("#26364D"))
    pal.setColor(QPalette.Button,          QColor("#F8FAFC"))
    pal.setColor(QPalette.ButtonText,      QColor("#26364D"))
    pal.setColor(QPalette.BrightText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.Highlight,       QColor("#2F80ED"))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase,     QColor("#18233A"))
    pal.setColor(QPalette.ToolTipText,     QColor("#FFFFFF"))
    pal.setColor(QPalette.Mid,             QColor("#DDE5EE"))
    pal.setColor(QPalette.Dark,            QColor("#BCC8D6"))
    pal.setColor(QPalette.Shadow,          QColor("#94A3B8"))
    app.setPalette(pal)

    # 全局样式表：覆盖所有顶层窗口
    app.setStyleSheet(MAIN_STYLE)

    # 事件过滤器：对话框出现时强制应用浅色
    _fix = _DialogLightFix(app)
    app.installEventFilter(_fix)

    window = MainWindow()
    window.show()

    # 首次启动提示
    if not llm_client.is_configured():
        QMessageBox.information(
            window, "欢迎使用",
            "检测到尚未配置 API Key。\n\n"
            "请前往【⚙️ 系统设置】填写您的 DeepSeek API Key，\n"
            "否则 AI 功能将无法使用。"
        )
        window._switch_page(4)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
