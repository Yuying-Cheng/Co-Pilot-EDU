"""
Settings Page — Warm Academic Style
"""

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from ui.styles import *
from ui.widgets import SectionHeader, SubHeader, HDivider, add_shadow, make_svg_widget, ILLUSTRATION_CAMPUS
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
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignTop)

        # 页头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 28)
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        t = QLabel("系统设置")
        t.setStyleSheet(f"color: {TEXT_H1}; font-size: 20px; font-weight: 800; background: transparent;")
        s = QLabel("配置大模型 API Key，所有数据本地存储")
        s.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; background: transparent;")
        title_col.addWidget(t)
        title_col.addWidget(s)
        hdr.addLayout(title_col)
        hdr.addStretch()
        root.addLayout(hdr)

        # API Key 卡片
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: none;
                border-radius: {RADIUS_LG}px;
            }}
        """)
        card.setMaximumWidth(600)
        add_shadow(card)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 24, 28, 24)
        cl.setSpacing(16)

        cl.addWidget(SectionHeader("DeepSeek API Key"))

        desc = QLabel(
            "前往 platform.deepseek.com 注册并获取 API Key。\n"
            "Key 仅保存在本机 config.json，不会上传至任何服务器。"
        )
        desc.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px; line-height: 170%; background: transparent;")
        desc.setWordWrap(True)
        cl.addWidget(desc)
        cl.addWidget(HDivider())

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-...")
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setStyleSheet(INPUT_STYLE)

        self._toggle_btn = QPushButton("显示")
        self._toggle_btn.setStyleSheet(GHOST_BTN)
        self._toggle_btn.setFixedWidth(56)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)

        input_row.addWidget(self._key_input, 1)
        input_row.addWidget(self._toggle_btn)
        cl.addLayout(input_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        cl.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.setStyleSheet(SECONDARY_BTN)
        self._test_btn.setCursor(Qt.PointingHandCursor)
        if HAS_QTA:
            try: self._test_btn.setIcon(qta.icon("ri.wifi-line", color=TEXT_SEC))
            except: pass
        self._test_btn.clicked.connect(self._test_connection)

        self._save_btn = QPushButton("保存配置")
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

        # 说明卡片
        info = QFrame()
        info.setStyleSheet(f"""
            QFrame {{
                background: {GREEN_LIGHT};
                border: none;
                border-radius: {RADIUS}px;
            }}
        """)
        info.setMaximumWidth(600)
        il = QVBoxLayout(info)
        il.setContentsMargins(20, 16, 20, 16)
        il.setSpacing(8)
        for line in [
            "🔒  API Key 仅保存在本机 config.json，不会上传至任何服务器。",
            "💰  DeepSeek 定价极低，正常使用每次评阅约 ¥0.01。",
            "📁  除大模型 API 调用外，系统完全离线运行，数据本地存储。",
            "✅  保存后可点击「测试连接」验证 Key 是否有效。",
        ]:
            lbl = QLabel(line)
            lbl.setStyleSheet(f"color: {GREEN_DARK}; font-size: 14px; line-height: 160%; background: transparent;")
            lbl.setWordWrap(True)
            il.addWidget(lbl)
        root.addWidget(info)

        # 底部插画
        try:
            campus = make_svg_widget(ILLUSTRATION_CAMPUS, 300, 110)
            root.addSpacing(20)
            root.addWidget(campus, alignment=Qt.AlignLeft)
        except Exception: pass

        root.addStretch()

    def _load_current(self):
        key = llm_client.get_api_key()
        if key:
            self._key_input.setText(key)
            self._status_lbl.setText("✅ 已配置 API Key")
            self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; background: transparent;")
        else:
            self._status_lbl.setText("⚠️ 尚未配置，AI 功能不可用")
            self._status_lbl.setStyleSheet(f"color: {WARNING}; font-size: 11px; background: transparent;")

    def _toggle(self):
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
        self._status_lbl.setText("✅ 已保存")
        self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; background: transparent;")
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
        self._status_lbl.setText("✅ 连接成功")
        self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; background: transparent;")
        QMessageBox.information(self, "成功", "✅ DeepSeek API 连接正常！")

    def _on_test_fail(self, err: str):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("测试连接")
        self._status_lbl.setText("❌ 连接失败，请检查 Key")
        self._status_lbl.setStyleSheet(f"color: {DANGER}; font-size: 11px; background: transparent;")
        QMessageBox.critical(self, "连接失败", err)
