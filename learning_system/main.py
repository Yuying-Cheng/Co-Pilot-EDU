#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow
import llm_client

def main():
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setApplicationName("探究式学习系统")

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
        window._switch_page(4)  # 自动跳到设置页

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
