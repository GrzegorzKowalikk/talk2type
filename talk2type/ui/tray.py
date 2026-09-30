from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from talk2type.config import ICON_ICO


class Tray:
    def __init__(self, on_quit, *, on_open):
        self._menu = QMenu()
        self._menu.addAction("Open", on_open)
        self._menu.addAction("Quit", on_quit)
        self._icon = QSystemTrayIcon(QIcon(str(ICON_ICO)))
        self._icon.setToolTip("Talk2Type")
        self._icon.setContextMenu(self._menu)
        self._icon.activated.connect(
            lambda reason: reason == QSystemTrayIcon.ActivationReason.Trigger and on_open()
        )
        self._icon.show()
