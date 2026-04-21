import threading

from PIL import Image
from pystray import Icon, Menu, MenuItem


def _img(color: str) -> Image.Image:
    return Image.new("RGB", (64, 64), color)


class Tray:
    COLORS = {"idle": "gray", "recording": "red", "processing": "orange"}

    def __init__(self, on_quit):
        self._icons = {state: _img(color) for state, color in self.COLORS.items()}
        self._icon = Icon(
            "Talk2Type",
            self._icons["idle"],
            "Talk2Type",
            Menu(MenuItem("Quit", lambda i, _: (on_quit(), i.stop()))),
        )

    def set_state(self, state: str):
        self._icon.icon = self._icons.get(state, self._icons["idle"])

    def run(self):
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self):
        self._icon.stop()
