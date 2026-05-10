from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from talk2type.config import WHISPER_HOTWORDS
from talk2type.db.engine import get_session
from talk2type.db.model import Hotword

DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
ACCENT = "#89b4fa"
INPUT_BG = "#313244"
HOVER = "#45475a"
SELECTED = "#585b70"

_WORD_DATA = 256  # Qt.ItemDataRole.UserRole
_ID_DATA = 257

_QSS = f"""
QLabel {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
}}
QLineEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QListWidget {{
    background-color: {DARKER_BG};
    color: {TEXT};
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 4px;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid #313244;
}}
QListWidget::item:last-child {{
    border-bottom: none;
}}
QPushButton {{
    background-color: transparent;
    color: {SUBTEXT};
    border: none;
    font-size: 16px;
    padding: 4px 8px;
    border-radius: 4px;
}}
QPushButton:hover {{
    background-color: #45475a;
    color: #f38ba8;
}}
"""


class DictionaryPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        title = QLabel("Dictionary")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 24px; font-weight: bold;"
        )
        root.addWidget(title)

        subtitle = QLabel("Words Whisper often mishears.")
        subtitle.setStyleSheet(
            f"color: {SUBTEXT}; font-size: 13px;"
        )
        root.addWidget(subtitle)

        self.input = QLineEdit()
        self.input.setPlaceholderText("+ Add word...")
        self.input.returnPressed.connect(self.add_word)
        root.addWidget(self.input)

        self.word_list = QListWidget()
        self.word_list.setObjectName("word_list")
        root.addWidget(self.word_list)

        root.addStretch()

        self.seed_from_config()
        self.refresh_data()

    def seed_from_config(self) -> None:
        with get_session() as s:
            existing = s.exec(select(Hotword)).first()
            if existing is not None:
                return
            for w in WHISPER_HOTWORDS:
                s.add(Hotword(word=w))
            s.commit()

    def refresh_data(self) -> None:
        self.word_list.clear()
        with get_session() as s:
            rows = s.exec(select(Hotword).order_by(Hotword.word)).all()
            records = [(r.id, r.word) for r in rows]
        for row_id, word in records:
            item = QListWidgetItem(word)
            item.setData(_WORD_DATA, word)
            item.setData(_ID_DATA, row_id)

            btn = QPushButton("✕")
            btn.setFixedSize(28, 28)
            btn.clicked.connect(lambda checked, wid=row_id: self.remove_word(wid))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addStretch()
            row_layout.addWidget(btn)

            item.setSizeHint(row_widget.sizeHint())
            self.word_list.addItem(item)
            self.word_list.setItemWidget(item, row_widget)

    def add_word(self) -> None:
        word = self.input.text().strip()
        if not word:
            return
        with get_session() as s:
            existing = s.exec(
                select(Hotword).where(Hotword.word == word)
            ).first()
            if existing is not None:
                return
            s.add(Hotword(word=word))
            s.commit()
        self.input.clear()
        self.refresh_data()

    def remove_word(self, word_id: int) -> None:
        with get_session() as s:
            row = s.get(Hotword, word_id)
            if row is not None:
                s.delete(row)
                s.commit()
        self.refresh_data()
