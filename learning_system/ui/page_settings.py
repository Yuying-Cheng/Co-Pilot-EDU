"""
Settings page — Swiss minimalist
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import SectionHeader, HDivider
import llm_client

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
        root.setSpacing(0)
        root.setAlignment(Qt.AlignTop)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 32)
        title = QLabel("系统设置")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;")
        hdr.addWidget(title)
        root.addLayout(hdr)

        # ── API Key card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        card.setMaximumWidth(560)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 24, 28, 24)
        cl.setSpacing(16)

        cl.addWidget(SectionHeader("DeepSeek API Key"))

        desc = QLabel("前往 platform.deepseek.com 注册并获取 API Key。\nKey 仅保存在本机 config.json，不会上传至任何服务器。")
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 160%;")
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
        self._toggle_btn.setFixedWidth(52)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_visibility)

        input_row.addWidget(self._key_input, 1)
        input_row.addWidget(self._toggle_btn)
        cl.addLayout(input_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        cl.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.setStyleSheet(SECONDARY_BTN)
        self._test_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._test_btn.setIcon(qta.icon("ri.wifi-line", color=TEXT_PRI))
            except: pass
        self._test_btn.clicked.connect(self._test_connection)

        self._save_btn = QPushButton("保存")
        self._save_btn.setStyleSheet(PRIMARY_BTN)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._save_btn.setIcon(qta.icon("ri.save-line", color="white"))
            except: pass
        self._save_btn.clicked.connect(self._save)

        btn_row.addWidget(self._test_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        cl.addLayout(btn_row)

        root.addWidget(card)
        root.addSpacing(20)

        # ── Info card ─────────────────────────────────────────────────────────
        info = QFrame()
        info.setStyleSheet(f"background: {BG_DARK}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;")
        info.setMaximumWidth(560)
        il = QVBoxLayout(info)
        il.setContentsMargins(24, 18, 24, 18)
        il.setSpacing(10)

        for line in [
            "本系统调用 DeepSeek API，费用由您的账户承担。",
            "deepseek-chat 模型价格极低，正常使用每次评阅约 ¥0.01。",
            "API Key 保存在项目目录的 config.json 中，请勿分享他人。",
        ]:
            lbl = QLabel(f"·  {line}")
            lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
            il.addWidget(lbl)

        root.addWidget(info)

    def _load_current(self):
        key = llm_client.get_api_key()
        if key:
            self._key_input.setText(key)
            self._status_lbl.setText("已配置")
            self._status_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        else:
            self._status_lbl.setText("尚未配置，AI 功能不可用")
            self._status_lbl.setStyleSheet(f"color: {ACCENT3}; font-size: 11px;")

    def _toggle_visibility(self):
        if self._key_input.echoMode() == QLineEdit.Password:
            self._key_input.setEchoMode(QLineEdit.Normal)
            self._toggle_btn.setText("隐藏")
        else:
            self._key_input.setEchoMode(QLineEdit.Password)
            self._toggle_btn.setText("显示")

    def _save(self):
        key = self._key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入 API Key。")
            return
        llm_client.save_config({"api_key": key})
        self._status_lbl.setText("已保存")
        self._status_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        QMessageBox.information(self, "已保存", "API Key 已保存，现在可以使用 AI 功能了。")

    def _test_connection(self):
        key = self._key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请先输入 API Key。")
            return
        llm_client.save_config({"api_key": key})
        self._test_btn.setEnabled(False)
        self._test_btn.setText("连接中…")
        from ui.widgets import Worker
        self._worker = Worker(llm_client.call_llm, "你是助手。", "回复：OK", 20)
        self._worker.finished.connect(self._on_test_ok)
        self._worker.error.connect(self._on_test_fail)
        self._worker.start()

    def _on_test_ok(self, _):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("测试连接")
        self._status_lbl.setText("连接成功")
        self._status_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        QMessageBox.information(self, "成功", "DeepSeek API 连接正常！")

    def _on_test_fail(self, err: str):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("测试连接")
        self._status_lbl.setText("连接失败，请检查 Key")
        self._status_lbl.setStyleSheet(f"color: {ACCENT4}; font-size: 11px;")
        QMessageBox.critical(self, "连接失败", err)
