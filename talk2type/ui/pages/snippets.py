from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from talk2type.db.engine import get_session
from talk2type.db.model import Snippet

# --- Dark theme palette ---
DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
TEXT = "#cdd6f4"
ACCENT = "#89b4fa"
INPUT_BG = "#313244"
HOVER = "#45475a"
SELECTED = "#585b70"


@dataclass
class SnippetData:
    id: int
    name: str
    body: str


_QSS = f"""
QWidget {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
}}
QLineEdit, QTextEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {HOVER};
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QPushButton {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {HOVER};
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {HOVER};
}}
QPushButton#new_btn {{
    background-color: {ACCENT};
    color: {DARKER_BG};
    border: none;
    font-weight: bold;
}}
QPushButton#new_btn:hover {{
    background-color: #b4d0fb;
}}
QPushButton#delete_btn {{
    background-color: transparent;
    color: #f38ba8;
    border: none;
    padding: 2px 6px;
    font-size: 12px;
}}
QPushButton#delete_btn:hover {{
    background-color: #45475a;
}}
QListWidget {{
    background-color: {DARK_BG};
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {HOVER};
}}
QListWidget::item:hover {{
    background-color: {HOVER};
}}
QLabel {{
    background: transparent;
    border: none;
}}
"""


class SnippetCard(QWidget):
    """Single row in the list: name + body preview + delete button."""

    def __init__(self, data: SnippetData, parent: SnippetsPage | None = None):
        super().__init__(parent)
        self.data = data
        self._page = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name = QLabel(data.name)
        name.setObjectName("snippet_name")
        name.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {TEXT};")

        preview_text = data.body.split("\n")[0][:120]
        preview = QLabel(preview_text)
        preview.setObjectName("snippet_preview")
        preview.setStyleSheet(f"font-size: 12px; color: {HOVER};")

        text_col.addWidget(name)
        text_col.addWidget(preview)
        layout.addLayout(text_col, stretch=1)

        del_btn = QPushButton("x")
        del_btn.setObjectName("delete_btn")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)

    def _on_delete(self):
        if self._page:
            self._page.delete_snippet(self.data.id)

    def mouseReleaseEvent(self, event):
        QApplication.clipboard().setText(self.data.body)
        if self._page:
            self._page._flash_copied(self)


class SnippetsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_QSS)
        self._snippets: list[SnippetData] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # --- Header row ---
        header = QHBoxLayout()

        title = QLabel("Snippets")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {TEXT};")
        header.addWidget(title)
        header.addStretch()

        self.new_btn = QPushButton("+ New Snippet")
        self.new_btn.setObjectName("new_btn")
        self.new_btn.clicked.connect(self._show_form)
        header.addWidget(self.new_btn)
        root.addLayout(header)

        # --- Search ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snippets...")
        self.search_input.textChanged.connect(self._filter)
        root.addWidget(self.search_input)

        # --- List ---
        self.list_widget = QListWidget()
        self.list_widget.clicked.connect(self._on_item_clicked)
        root.addWidget(self.list_widget)

        # --- Inline form (hidden) ---
        self.form_container = QWidget()
        self.form_container.setVisible(False)
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(0, 8, 0, 0)
        form_layout.setSpacing(8)

        self.form_name = QLineEdit()
        self.form_name.setPlaceholderText("Snippet name")
        form_layout.addWidget(self.form_name)

        self.form_body = QTextEdit()
        self.form_body.setPlaceholderText("Snippet body")
        self.form_body.setMaximumHeight(100)
        form_layout.addWidget(self.form_body)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.add_snippet)
        form_layout.addWidget(self.save_btn)

        root.addWidget(self.form_container)

        self.refresh_data()

    # --- Data ---

    def refresh_data(self):
        self.list_widget.clear()
        self._snippets.clear()
        with get_session() as s:
            for sn in s.exec(select(Snippet)).all():
                d = SnippetData(id=sn.id, name=sn.name, body=sn.body)
                self._snippets.append(d)
                self._add_row(d)
        self._filter(self.search_input.text())

    def add_snippet(self):
        name = self.form_name.text().strip()
        body = self.form_body.toPlainText().strip()
        if not name or not body:
            return
        with get_session() as s:
            sn = Snippet(name=name, body=body)
            s.add(sn)
            s.commit()
            s.refresh(sn)
            d = SnippetData(id=sn.id, name=sn.name, body=sn.body)
            self._snippets.append(d)
            self._add_row(d)
        self.form_container.setVisible(False)
        self.form_name.clear()
        self.form_body.clear()
        self._filter(self.search_input.text())

    def delete_snippet(self, snippet_id: int):
        with get_session() as s:
            sn = s.get(Snippet, snippet_id)
            if sn:
                s.delete(sn)
                s.commit()
        self._snippets = [s for s in self._snippets if s.id != snippet_id]
        self.refresh_data()

    # --- Private ---

    def _add_row(self, data: SnippetData):
        item = QListWidgetItem(self.list_widget)
        item.setData(Qt.ItemDataRole.UserRole, data.id)
        card = SnippetCard(data, parent=self)
        item.setSizeHint(card.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)

    def _show_form(self):
        self.form_container.setVisible(True)
        self.form_name.setFocus()

    def _filter(self, text: str):
        query = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            sid = item.data(Qt.ItemDataRole.UserRole)
            sn = next((s for s in self._snippets if s.id == sid), None)
            hide = bool(query and sn and query not in sn.name.lower())
            item.setHidden(hide)

    def _on_item_clicked(self, index):
        item = self.list_widget.item(index.row())
        card = self.list_widget.itemWidget(item)
        if card:
            QApplication.clipboard().setText(card.data.body)
            self._flash_copied(card)

    def _flash_copied(self, card: SnippetCard):
        original = card.styleSheet()
        card.setStyleSheet(f"background-color: {SELECTED};")
        from PySide6.QtCore import QTimer

        QTimer.singleShot(300, lambda: card.setStyleSheet(original))
