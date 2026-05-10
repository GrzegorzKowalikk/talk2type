import threading
from pathlib import Path

from PIL import Image
from pystray import Icon, Menu, MenuItem

_IMAGES_DIR = Path(__file__).parent.parent / "images"


class Tray:
    def __init__(self, on_quit, *, on_open=None):
        menu_items = []
        if on_open is not None:
            menu_items.append(MenuItem("Open", lambda i, _: on_open()))
        menu_items.append(MenuItem("Quit", lambda i, _: (on_quit(), i.stop())))
        self._icon = Icon(
            "Talk2Type",
            Image.open(_IMAGES_DIR / "icon.png"),
            "Talk2Type",
            Menu(*menu_items),
        )

    def set_state(self, state: str):
        pass

    def run(self):
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self):
        self._icon.stop()
