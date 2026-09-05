from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class KeyCaptureButton(QPushButton):
    key_captured = Signal(str)

    def __init__(self, current_key: str):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._current_key = current_key
        self._listening = False
        self._update_text()
        self.clicked.connect(self._start_listening)

    def _update_text(self):
        if self._listening:
            self.setText("Listening... Press a key")
            self.setStyleSheet("color: #89b4fa; background-color: rgba(137, 180, 250, 0.15);")
        else:
            self.setText(f"Current: {self._current_key.upper()}")
            self.setStyleSheet("")

    def _start_listening(self):
        self._listening = True
        self._update_text()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._listening:
            super().keyPressEvent(event)
            return

        key_str = QKeySequence(event.key()).toString().lower()
        if not key_str:
            return

        # Handle some PyQt to pynput naming differences if necessary, but
        # QKeySequence handles F1-F12 and letters well.
        self._current_key = key_str
        self._listening = False
        self._update_text()
        self.key_captured.emit(self._current_key)


class SettingsPage(QWidget):
    settings_changed = Signal(str, str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title)

        # We will set these from app.py initially
        self._pl_key = "f9"
        self._en_key = "f10"

        # PL Hotkey Row
        pl_row = QHBoxLayout()
        pl_label = QLabel("Polish Dictation Hotkey:")
        pl_label.setStyleSheet("color: #a6adc8; font-size: 14px;")
        self.pl_btn = KeyCaptureButton(self._pl_key)
        self.pl_btn.key_captured.connect(self._on_pl_changed)
        pl_row.addWidget(pl_label)
        pl_row.addStretch()
        pl_row.addWidget(self.pl_btn)
        layout.addLayout(pl_row)

        # EN Hotkey Row
        en_row = QHBoxLayout()
        en_label = QLabel("English Dictation Hotkey:")
        en_label.setStyleSheet("color: #a6adc8; font-size: 14px;")
        self.en_btn = KeyCaptureButton(self._en_key)
        self.en_btn.key_captured.connect(self._on_en_changed)
        en_row.addWidget(en_label)
        en_row.addStretch()
        en_row.addWidget(self.en_btn)
        layout.addLayout(en_row)

        layout.addStretch()

    def set_initial_keys(self, pl_key: str, en_key: str):
        self._pl_key = pl_key
        self._en_key = en_key
        self.pl_btn._current_key = pl_key
        self.pl_btn._update_text()
        self.en_btn._current_key = en_key
        self.en_btn._update_text()

    def _on_pl_changed(self, key_str: str):
        self._pl_key = key_str
        self.settings_changed.emit(self._pl_key, self._en_key)

    def _on_en_changed(self, key_str: str):
        self._en_key = key_str
        self.settings_changed.emit(self._pl_key, self._en_key)
