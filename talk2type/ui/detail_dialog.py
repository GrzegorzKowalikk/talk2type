from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from talk2type.db.engine import get_session
from talk2type.db.model import Transcription

_DARK_BG = "#1e1e2e"
_DARKER_BG = "#11111b"
_TEXT = "#cdd6f4"
_SUBTEXT = "#a6adc8"
_ACCENT = "#89b4fa"
_INPUT_BG = "#313244"
_HOVER = "#45475a"

_QSS = f"""
QDialog {{
    background-color: {_DARK_BG};
}}
QLabel {{
    color: {_SUBTEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
    background: transparent;
}}
QTextEdit {{
    background-color: {_DARKER_BG};
    color: {_TEXT};
    border: 1px solid {_HOVER};
    border-radius: 6px;
    padding: 10px;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.5;
}}
QPushButton {{
    background-color: {_INPUT_BG};
    color: {_TEXT};
    border: 1px solid {_HOVER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {_HOVER};
}}
"""


class TranscriptionDetailDialog(QDialog):
    def __init__(self, transcription_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcription")
        self.setMinimumWidth(580)
        self.setMinimumHeight(300)
        self.setStyleSheet(_QSS)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        with get_session() as session:
            record = session.get(Transcription, transcription_id)
            ts = record.ts if record else None
            text = record.cleaned if record else ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        if ts:
            ts_label = QLabel(ts.strftime("%B %d, %Y  %I:%M %p"))
            layout.addWidget(ts_label)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(text))
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)
