"""
Settings page.
"""

import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles import *
from ui.widgets import HDivider, SectionHeader

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_current()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(20)
        root.setAlignment(Qt.AlignTop)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 12)
        title = QLabel("系统设置")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: 0;")
        hdr.addWidget(title)
        root.addLayout(hdr)

        card = QFrame()
        card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        card.setMaximumWidth(640)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 24, 28, 24)
        cl.setSpacing(16)

        cl.addWidget(SectionHeader("DeepSeek API Key"))

        desc = QLabel("用于知识点抽取、任务生成和语义评阅。Key 仅保存在本机 config.local.json，也可以用环境变量 DEEPSEEK_API_KEY 覆盖。")
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%;")
        desc.setWordWrap(True)
        cl.addWidget(desc)
        cl.addWidget(HDivider())

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-...")
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setStyleSheet(INPUT_STYLE)

        self._toggle_btn = QPushButton("显示")
        self._toggle_btn.setStyleSheet(GHOST_BTN)
        self._toggle_btn.setFixedWidth(56)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_visibility)

        input_row.addWidget(self._key_input, 1)
        input_row.addWidget(self._toggle_btn)
        cl.addLayout(input_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        cl.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("保存配置")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try:
                self._save_btn.setIcon(qta.icon("ri.save-line", color="white"))
            except Exception:
                pass
        self._save_btn.clicked.connect(self._save)

        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        cl.addLayout(btn_row)

        root.addWidget(card)

        info = QFrame()
        info.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        info.setMaximumWidth(640)
        il = QVBoxLayout(info)
        il.setContentsMargins(24, 18, 24, 18)
        il.setSpacing(10)

        for line in [
            "不配置 API Key 时，桌面程序仍可打开，统计和本地数据管理功能可用。",
            "需要调用大模型的知识点抽取、任务生成、语义评阅会在运行时提示配置 Key。",
            "config.local.json 是本机私有配置文件，不建议提交或分享给他人。",
        ]:
            lbl = QLabel(f"- {line}")
            lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
            lbl.setWordWrap(True)
            il.addWidget(lbl)

        root.addWidget(info)
        root.addStretch()

    @property
    def _config_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.local.json")

    def _load_current(self):
        try:
            from config import DEEPSEEK_API_KEY
            if DEEPSEEK_API_KEY:
                self._key_input.setText(DEEPSEEK_API_KEY)
                self._status_lbl.setText("已配置")
                self._status_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
                return
        except ImportError:
            pass
        self._status_lbl.setText("尚未配置，调用大模型的功能会提示输入 Key")
        self._status_lbl.setStyleSheet(f"color: {ACCENT3}; font-size: 11px;")

    def _save(self):
        key = self._key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入 API Key。")
            return

        payload = {
            "DEEPSEEK_API_KEY": key,
            "BASE_URL": "https://api.deepseek.com",
        }
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._status_lbl.setText("已保存，重启软件后生效")
            self._status_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
            QMessageBox.information(self, "已保存", "API Key 已保存到 config.local.json，重启软件后生效。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{e}")

    def _toggle_visibility(self):
        if self._key_input.echoMode() == QLineEdit.Password:
            self._key_input.setEchoMode(QLineEdit.Normal)
            self._toggle_btn.setText("隐藏")
        else:
            self._key_input.setEchoMode(QLineEdit.Password)
            self._toggle_btn.setText("显示")
