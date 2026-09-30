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



class TranscriptionDetailDialog(QDialog):
    def __init__(self, transcription_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcription")
        self.setMinimumWidth(580)
        self.setMinimumHeight(300)
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
