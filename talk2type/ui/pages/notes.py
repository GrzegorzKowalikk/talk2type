from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from talk2type.db.engine import get_session
from talk2type.db.model import Note

DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
TEXT = "#cdd6f4"
ACCENT = "#89b4fa"
INPUT_BG = "#313244"
HOVER = "#45475a"
SELECTED = "#585b70"

_QSS = f"""
QLabel {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
}}
QPushButton {{
    color: {TEXT};
    background-color: {INPUT_BG};
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {HOVER};
}}
QLineEdit {{
    color: {TEXT};
    background-color: {INPUT_BG};
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
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
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 6px;
    border-bottom: 1px solid #313244;
    border-radius: 4px;
}}
QListWidget::item:last-child {{
    border-bottom: none;
}}
QListWidget::item:selected {{
    background-color: {SELECTED};
}}
QListWidget::item:hover {{
    background-color: {HOVER};
}}
QPlainTextEdit {{
    color: {TEXT};
    background-color: {DARKER_BG};
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
    outline: none;
}}
"""

_DEBOUNCE_MS = 500


class NotesPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(_QSS)
        self._current_id: int | None = None
        self._all_notes: list[Note] = []
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Left panel ---
        left = QWidget()
        left.setFixedWidth(250)
        left.setStyleSheet(f"background-color: {DARK_BG};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 16, 12, 12)
        left_layout.setSpacing(8)

        title = QLabel("Notes")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: bold; border: none;")
        left_layout.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.new_btn = QPushButton("+ New Note")
        self.new_btn.clicked.connect(self.create_note)
        btn_row.addWidget(self.new_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_note)
        btn_row.addWidget(self.delete_btn)
        left_layout.addLayout(btn_row)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search notes...")
        self.search_edit.textChanged.connect(self._filter)
        left_layout.addWidget(self.search_edit)

        self.note_list = QListWidget()
        self.note_list.currentRowChanged.connect(self._on_note_selected)
        left_layout.addWidget(self.note_list)

        layout.addWidget(left)

        # --- Right panel ---
        right = QWidget()
        right.setStyleSheet(f"background-color: {DARK_BG};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 16, 20, 16)
        right_layout.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Note title")
        self.title_edit.setStyleSheet(
            "font-size: 18px; font-weight: bold; border: none; "
            "background-color: transparent; padding: 4px 0;"
        )
        self.title_edit.textChanged.connect(self._schedule_save)
        right_layout.addWidget(self.title_edit)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Start writing...")
        self.editor.textChanged.connect(self._schedule_save)
        right_layout.addWidget(self.editor)

        layout.addWidget(right)

        self.refresh_data()

    # --- Public API ---

    def refresh_data(self) -> None:
        with get_session() as session:
            notes = session.exec(select(Note)).all()
            self._all_notes = [Note(id=n.id, title=n.title, body=n.body) for n in notes]
        self._rebuild_list()

    def create_note(self) -> None:
        note = Note(title="New Note", body="")
        with get_session() as session:
            session.add(note)
            session.flush()
            note_id = note.id
        self.refresh_data()
        self._select_by_id(note_id)

    def delete_note(self) -> None:
        if self._current_id is None:
            return
        with get_session() as session:
            note = session.get(Note, self._current_id)
            if note:
                session.delete(note)
        self._current_id = None
        self.refresh_data()
        self._clear_editor()

    # --- Internal ---

    def _rebuild_list(self) -> None:
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in self._all_notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)
        if self._all_notes:
            self.note_list.setCurrentRow(0)

    def _select_by_id(self, note_id: int | None) -> None:
        if note_id is None:
            return
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentRow(i)
                return

    def _on_note_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self.note_list.item(row)
        if item is None:
            return
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_id = note_id

        # Load note from DB
        with get_session() as session:
            note = session.get(Note, note_id)
            if note is None:
                return
            title = note.title
            body = note.body

        self.title_edit.blockSignals(True)
        self.title_edit.setText(title)
        self.title_edit.blockSignals(False)

        self.editor.blockSignals(True)
        self.editor.setPlainText(body)
        self.editor.blockSignals(False)

    def _schedule_save(self) -> None:
        if self._current_id is None:
            return
        self._save_timer.start(_DEBOUNCE_MS)

    def _save_current(self) -> None:
        if self._current_id is None:
            return
        title = self.title_edit.text()
        body = self.editor.toPlainText()
        with get_session() as session:
            note = session.get(Note, self._current_id)
            if note is None:
                return
            note.title = title
            note.body = body
        # Update list item title without full refresh
        row = self.note_list.currentRow()
        if row >= 0:
            item = self.note_list.item(row)
            if item:
                item.setText(title)
        self._update_internal_title(self._current_id, title)

    def _update_internal_title(self, note_id: int, new_title: str) -> None:
        for n in self._all_notes:
            if n.id == note_id:
                n.title = new_title
                break

    def _filter(self, text: str) -> None:
        lower = text.lower()
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            item.setHidden(lower not in item.text().lower())

    def _clear_editor(self) -> None:
        self.title_edit.blockSignals(True)
        self.title_edit.clear()
        self.title_edit.blockSignals(False)
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
