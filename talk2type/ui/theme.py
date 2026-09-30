DARK_BG = "#1e1e2e"
DARKER_BG = "#11111b"
CARD_BG = "#181825"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
ACCENT = "#89b4fa"
INPUT_BG = "#313244"
HOVER = "#45475a"
SELECTED = "#585b70"

QSS = f"""
QMainWindow, QDialog {{
    background-color: {DARK_BG};
}}
QLabel {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    background: transparent;
    border: none;
}}
QDialog QLabel {{
    color: {SUBTEXT};
    font-size: 12px;
}}
QLineEdit, QTextEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {HOVER};
    border-radius: 6px;
    padding: 8px 12px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QPlainTextEdit, QDialog QTextEdit {{
    background-color: {DARKER_BG};
    color: {TEXT};
    border: 1px solid {INPUT_BG};
    border-radius: 8px;
    padding: 12px;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
    outline: none;
}}
QPushButton {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {HOVER};
    border-radius: 6px;
    padding: 6px 14px;
    font-family: "Segoe UI", sans-serif;
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
    background-color: {HOVER};
}}
#word_list QPushButton {{
    background-color: transparent;
    color: {SUBTEXT};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 16px;
}}
#word_list QPushButton:hover {{
    background-color: {HOVER};
    color: #f38ba8;
}}
QListWidget {{
    background-color: {DARKER_BG};
    color: {TEXT};
    border: 1px solid {INPUT_BG};
    border-radius: 8px;
    padding: 4px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {INPUT_BG};
}}
QListWidget::item:last-child {{
    border-bottom: none;
}}
QListWidget::item:hover {{
    background-color: {HOVER};
}}
QListWidget::item:selected {{
    background-color: {SELECTED};
}}
QScrollBar:vertical {{
    background: {DARKER_BG};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar:horizontal {{
    background: {DARKER_BG};
    height: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {SELECTED};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:horizontal {{
    background: {SELECTED};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}
QFrame#stat_card {{
    background-color: {CARD_BG};
    border: 1px solid {INPUT_BG};
    border-radius: 12px;
}}
#sidebar {{
    background-color: {DARKER_BG};
    border-right: 1px solid {INPUT_BG};
}}
#brand {{
    font-size: 15px;
    font-weight: bold;
    padding: 0px;
}}
#sidebar QPushButton {{
    color: {SUBTEXT};
    background-color: transparent;
    border: none;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
    border-radius: 8px;
    margin: 1px 8px;
}}
#sidebar QPushButton:hover {{
    background-color: rgba(205, 214, 244, 0.06);
    color: {TEXT};
}}
#sidebar QPushButton[active="true"] {{
    color: {ACCENT};
    background-color: rgba(137, 180, 250, 0.15);
    font-weight: bold;
}}
"""
