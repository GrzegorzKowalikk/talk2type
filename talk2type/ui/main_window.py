from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from talk2type.ui.pages.dictionary import DictionaryPage
from talk2type.ui.pages.history import HistoryPage
from talk2type.ui.pages.home import HomePage
from talk2type.ui.pages.notes import NotesPage
from talk2type.ui.pages.settings import SettingsPage
from talk2type.ui.pages.snippets import SnippetsPage

DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
ACCENT = "#89b4fa"

_PAGES = ["Home", "History", "Dictionary", "Snippets", "Notes", "Settings"]

_QSS = f"""
QMainWindow {{
    background-color: {DARK_BG};
}}
#sidebar {{
    background-color: {DARKER_BG};
    border-right: 1px solid #313244;
}}
#brand {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 15px;
    font-weight: bold;
    padding: 0px;
}}
#brand_accent {{
    color: {ACCENT};
}}
QPushButton {{
    color: {SUBTEXT};
    background-color: transparent;
    border: none;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
    font-family: "Segoe UI", sans-serif;
    border-radius: 8px;
    margin: 1px 8px;
}}
QPushButton:hover {{
    background-color: rgba(205, 214, 244, 0.06);
    color: {TEXT};
}}
QPushButton[active="true"] {{
    color: {ACCENT};
    background-color: rgba(137, 180, 250, 0.15);
    font-weight: bold;
}}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Talk2Type")
        self.setStyleSheet(_QSS)

        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Brand header
        brand_wrap = QWidget()
        brand_wrap.setFixedHeight(56)
        brand_inner = QHBoxLayout(brand_wrap)
        brand_inner.setContentsMargins(20, 0, 16, 0)
        brand_inner.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        brand = QLabel('<span style="color:#89b4fa">T2</span>T')
        brand.setObjectName("brand")
        brand_inner.addWidget(brand)
        sb_layout.addWidget(brand_wrap)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #313244; max-height: 1px; border: none;")
        sep.setFixedHeight(1)
        sb_layout.addWidget(sep)
        sb_layout.addSpacing(8)

        self._nav_buttons: list[QPushButton] = []
        for name in _PAGES:
            btn = QPushButton(name)
            btn.setObjectName(f"nav_{name.lower()}")
            btn.clicked.connect(lambda checked, n=name: self._switch(n))
            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sb_layout.addStretch()
        h.addWidget(sidebar)

        # Pages
        self._stack = QStackedWidget()
        self._stack.setObjectName("pages")

        self.home_page = HomePage()
        self.history_page = HistoryPage()
        self.dictionary_page = DictionaryPage()
        self.snippets_page = SnippetsPage()
        self.notes_page = NotesPage()
        self.settings_page = SettingsPage()

        for page in (self.home_page, self.history_page, self.dictionary_page,
                     self.snippets_page, self.notes_page, self.settings_page):
            self._stack.addWidget(page)
        h.addWidget(self._stack)

        self._set_active(0)

    def _switch(self, name: str):
        idx = _PAGES.index(name)
        self._stack.setCurrentIndex(idx)
        self._set_active(idx)
        self.refresh_current_page()

    def _set_active(self, idx: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", i == idx)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def bring_to_front(self):
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def refresh_current_page(self):
        page = self._stack.currentWidget()
        if hasattr(page, "refresh_data"):
            page.refresh_data()
