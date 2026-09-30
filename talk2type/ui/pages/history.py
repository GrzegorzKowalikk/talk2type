from datetime import datetime, timedelta

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from talk2type.db.engine import get_session
from talk2type.db.model import Transcription
from talk2type.db.repository import TranscriptionRepository
from talk2type.ui.detail_dialog import TranscriptionDetailDialog

_HEADER_ROLE = Qt.ItemDataRole.UserRole + 1
_ID_ROLE = Qt.ItemDataRole.UserRole + 2



class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("history_page")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Search bar row
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText("Search...")
        self._search.textEdited.connect(self._filter)
        search_row.addWidget(self._search)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("clear_btn")
        self._clear_btn.clicked.connect(self._clear_search)
        search_row.addWidget(self._clear_btn)
        layout.addLayout(search_row)

        # Transcription list
        self._list = QListWidget()
        self._list.setObjectName("transcription_list")
        self._list.setWordWrap(True)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self._load_more_btn = QPushButton("Load more")
        self._load_more_btn.setObjectName("load_more_btn")
        self._load_more_btn.clicked.connect(self._load_more)
        layout.addWidget(self._load_more_btn)
        self._cursor = None
        self._current_header = None

    # --- Public API ---

    def refresh_data(self):
        """Reload the first page, preserving the current search."""
        self._list.clear()
        self._cursor = None
        self._current_header = None
        self._load_more()

    def _load_more(self):
        with get_session() as session:
            records = TranscriptionRepository(session).history(
                limit=51, query=self._search.text(), before=self._cursor,
            )
        self._load_more_btn.setVisible(len(records) > 50)
        records = records[:50]
        if records:
            self._cursor = (records[-1].ts, records[-1].id)

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        for row_id, ts, cleaned in records:
            row_date = ts.date()
            if row_date == today:
                header = "TODAY"
            elif row_date == yesterday:
                header = "YESTERDAY"
            else:
                header = ts.strftime("%B %d, %Y")

            if header != self._current_header:
                self._current_header = header
                h_item = QListWidgetItem(header)
                h_item.setData(_HEADER_ROLE, True)
                h_item.setFlags(h_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                font = h_item.font()
                font.setBold(True)
                font.setPointSize(10)
                h_item.setFont(font)
                self._list.addItem(h_item)

            time_str = ts.strftime("%I:%M %p")
            display = f'{time_str}  "{cleaned}"'
            item = QListWidgetItem(display)
            item.setData(_ID_ROLE, row_id)
            item.setData(_HEADER_ROLE, False)
            self._list.addItem(item)

    # --- Private ---

    def _filter(self, text: str):
        self._search.setText(text)
        self.refresh_data()

    def _clear_search(self):
        self._search.setText("")
        self._filter("")

    def _show_context_menu(self, pos: QPoint):
        item = self._list.itemAt(pos)
        if item is None or item.data(_HEADER_ROLE) is True:
            return
        menu = self._build_context_menu(item)
        menu.exec(self._list.viewport().mapToGlobal(pos))

    def _build_context_menu(self, item: QListWidgetItem) -> QMenu:
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self._copy_text(item))
        menu.addAction(copy_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        menu.addAction(delete_action)
        return menu

    def _copy_text(self, item: QListWidgetItem):
        text = item.text()
        # Extract content between quotes
        start = text.find('"')
        end = text.rfind('"')
        if start != -1 and end != -1 and end > start:
            text = text[start + 1 : end]
        QApplication.clipboard().setText(text)

    def _delete_item(self, item: QListWidgetItem):
        row_id = item.data(_ID_ROLE)
        if row_id is None:
            return
        with get_session() as session:
            obj = session.get(Transcription, row_id)
            if obj:
                session.delete(obj)
        self.refresh_data()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row_id = item.data(_ID_ROLE)
        if row_id is None:
            return
        dlg = TranscriptionDetailDialog(row_id, parent=self)
        dlg.exec()
