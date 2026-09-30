from __future__ import annotations

from PySide6.QtCore import QTimer
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
from talk2type.ui.theme import HOVER, SELECTED, TEXT


class SnippetCard(QWidget):
    """Single row in the list: name + body preview + delete button."""

    def __init__(self, id: int, name: str, body: str, parent: SnippetsPage | None = None):
        super().__init__(parent)
        self.id = id
        self.name = name
        self.body = body
        self._page = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name_lbl = QLabel(name)
        name_lbl.setObjectName("snippet_name")
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {TEXT};")

        preview = QLabel(body.split("\n")[0][:120])
        preview.setObjectName("snippet_preview")
        preview.setStyleSheet(f"font-size: 12px; color: {HOVER};")

        text_col.addWidget(name_lbl)
        text_col.addWidget(preview)
        layout.addLayout(text_col, stretch=1)

        del_btn = QPushButton("x")
        del_btn.setObjectName("delete_btn")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)

    def _on_delete(self):
        if self._page:
            self._page.delete_snippet(self.id)

    def mouseReleaseEvent(self, event):
        QApplication.clipboard().setText(self.body)
        if self._page:
            self._page._flash_copied(self)


class SnippetsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        with get_session() as s:
            for sn in s.exec(select(Snippet)).all():
                self._add_row(sn)
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
            self._add_row(sn)
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
        self.refresh_data()

    # --- Private ---

    def _add_row(self, sn: Snippet):
        item = QListWidgetItem(self.list_widget)
        card = SnippetCard(sn.id, sn.name, sn.body, parent=self)
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
            name = self.list_widget.itemWidget(item).name.lower()
            item.setHidden(bool(query and query not in name))

    def _on_item_clicked(self, index):
        card = self.list_widget.itemWidget(self.list_widget.item(index.row()))
        if card:
            QApplication.clipboard().setText(card.body)
            self._flash_copied(card)

    def _flash_copied(self, card: SnippetCard):
        original = card.styleSheet()
        card.setStyleSheet(f"background-color: {SELECTED};")
        QTimer.singleShot(300, lambda: card.setStyleSheet(original))
