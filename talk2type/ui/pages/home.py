from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from talk2type.db.engine import get_session
from talk2type.db.repository import TranscriptionRepository
from talk2type.ui.detail_dialog import TranscriptionDetailDialog

_ID_ROLE = Qt.ItemDataRole.UserRole

DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
CARD_BG = "#181825"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
ACCENT = "#89b4fa"

_QSS = f"""
QLabel {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
}}
QListWidget {{
    background-color: {DARKER_BG};
    color: {TEXT};
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 8px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 4px;
    border-bottom: 1px solid #313244;
}}
QListWidget::item:last-child {{
    border-bottom: none;
}}
QScrollBar:vertical {{
    background: {DARKER_BG};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #585b70;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
QFrame#stat_card {{
    background-color: {CARD_BG};
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 16px;
}}
"""


def _stat_card(value: str, label: str) -> QFrame:
    card = QFrame()
    card.setObjectName("stat_card")
    card.setStyleSheet(
        f"""
        QFrame#stat_card {{
            background-color: {CARD_BG};
            border: 1px solid #313244;
            border-radius: 12px;
        }}
        """
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    val = QLabel(value)
    val.setStyleSheet(
        f"color: {ACCENT}; font-size: 32px; font-weight: bold; border: none;"
    )
    val.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(val)

    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        f"color: {SUBTEXT}; font-size: 11px; border: none;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)

    card._value_label = val  # type: ignore[attr-defined]
    return card


class HomePage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        # Welcome
        welcome = QLabel("Welcome back!")
        welcome.setStyleSheet(
            f"color: {TEXT}; font-size: 22px; font-weight: bold; font-family: 'Segoe UI', sans-serif;"
        )
        root.addWidget(welcome)
        root.addSpacing(4)

        # Stat cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self._total_card = _stat_card("0", "total words")
        self.total_words_label = self._total_card._value_label  # type: ignore[attr-defined]
        cards_row.addWidget(self._total_card, stretch=1)

        self._days_card = _stat_card("0", "days")
        self.days_label = self._days_card._value_label  # type: ignore[attr-defined]
        cards_row.addWidget(self._days_card, stretch=1)

        self._wpm_card = _stat_card("0", "avg WPM")
        self.wpm_label = self._wpm_card._value_label  # type: ignore[attr-defined]
        cards_row.addWidget(self._wpm_card, stretch=1)

        root.addLayout(cards_row)

        # Recent activity header
        header_row = QHBoxLayout()
        header_row.setSpacing(0)
        recent_label = QLabel("Recent activity")
        recent_label.setStyleSheet(
            f"color: {TEXT}; font-size: 16px; font-weight: bold;"
        )
        header_row.addWidget(recent_label)
        header_row.addStretch()

        today_badge = QLabel("TODAY")
        today_badge.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: bold; "
            f"background-color: rgba(137, 180, 250, 0.15); "
            f"border-radius: 4px; padding: 2px 8px;"
        )
        header_row.addWidget(today_badge)
        root.addLayout(header_row)

        # Recent list
        self.recent_list = QListWidget()
        self.recent_list.setWordWrap(True)
        self.recent_list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self.recent_list)

        root.addStretch()

    def refresh_data(self) -> None:
        with get_session() as session:
            self._load_stats(session)
            self._load_recent(session)

    def _load_stats(self, session) -> None:  # type: ignore[type-arg]
        total_words, distinct_days, avg_wpm = TranscriptionRepository(session).statistics()
        self.total_words_label.setText(str(total_words))
        self.days_label.setText(str(distinct_days))
        self.wpm_label.setText(str(avg_wpm))

    def _load_recent(self, session) -> None:  # type: ignore[type-arg]
        self.recent_list.clear()
        rows = TranscriptionRepository(session).history(limit=20)

        for r in rows:
            time_str = r.ts.strftime("%I:%M %p")
            item = QListWidgetItem(f'{time_str}  "{r.cleaned}"')
            item.setData(_ID_ROLE, r.id)
            self.recent_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row_id = item.data(_ID_ROLE)
        if row_id is None:
            return
        dlg = TranscriptionDetailDialog(row_id, parent=self)
        dlg.exec()
