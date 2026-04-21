import collections
import ctypes

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget

_BARS = 44
_BAR_W = 4
_BAR_GAP = 3
_BAR_MAX_H = 36
_W = 420        # pill width
_H = 76         # pill height
_RADIUS = 38    # = H/2 → perfect pill
_LABEL_END = 88
_M = 12         # transparent margin on each side — absorbs DWM shadow

_WIN_W = _W + 2 * _M
_WIN_H = _H + 2 * _M


def _setup_dwm(hwnd: int) -> None:
    """Remove Windows DWM border/shadow for this window."""
    try:
        dwm = ctypes.windll.dwmapi
        # Disable non-client rendering (border glow)
        dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(ctypes.c_int(1)), 4)
        # Windows 11: don't auto-round corners
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(1)), 4)
        # Windows 11: remove 1px accent border (dark mode adds gray outline)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_uint32(0xFFFFFFFE)), 4)
    except Exception:
        pass


class _Signals(QObject):
    start_recording = Signal(str)
    start_processing = Signal()
    do_hide = Signal()


class OverlayWindow(QWidget):
    def __init__(self):
        flags = (
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAutoFillBackground(False)
        self.setFixedSize(_WIN_W, _WIN_H)

        self._state = "hidden"
        self._lang = ""
        self._rms: collections.deque[float] = collections.deque([0.0] * _BARS, maxlen=_BARS)
        self._alpha = 255
        self._dot_on = True

        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(50)
        self._wave_timer.timeout.connect(self.update)

        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(600)
        self._dot_timer.timeout.connect(self._toggle_dot)

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_step)

        self._sig = _Signals()
        self._sig.start_recording.connect(self._on_recording, Qt.ConnectionType.QueuedConnection)
        self._sig.start_processing.connect(self._on_processing, Qt.ConnectionType.QueuedConnection)
        self._sig.do_hide.connect(self._on_hide, Qt.ConnectionType.QueuedConnection)

        self._reposition()

    def showEvent(self, event):
        super().showEvent(event)
        _setup_dwm(int(self.winId()))

    # --- public API (thread-safe) ---

    def request_recording(self, lang: str):
        self._sig.start_recording.emit(lang)

    def request_processing(self):
        self._sig.start_processing.emit()

    def request_hide(self):
        self._sig.do_hide.emit()

    def push_rms(self, rms: float):
        self._rms.append(min(rms * 10.0, 1.0))

    # --- slots (main thread only) ---

    @Slot(str)
    def _on_recording(self, lang: str):
        self._fade_timer.stop()
        self._state = "recording"
        self._lang = lang.upper()
        self._alpha = 255
        self._dot_on = True
        self._dot_timer.start()
        self._wave_timer.start()
        self.show()
        self.update()

    @Slot()
    def _on_processing(self):
        self._state = "processing"
        self._wave_timer.stop()
        self._dot_timer.stop()
        self.update()

    @Slot()
    def _on_hide(self):
        self._dot_timer.stop()
        self._wave_timer.stop()
        self._fade_timer.start()

    def _toggle_dot(self):
        self._dot_on = not self._dot_on
        self.update()

    def _fade_step(self):
        self._alpha = max(0, self._alpha - 20)
        self.update()
        if self._alpha == 0:
            self._fade_timer.stop()
            self.hide()

    def _reposition(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center().x() - _WIN_W // 2, screen.bottom() - 120 - _WIN_H)

    # --- painting ---

    def paintEvent(self, _):
        if self._alpha == 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear entire window to transparent — hides DWM shadow within the margin
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(0, 0, _WIN_W, _WIN_H, QColor(0, 0, 0, 0))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        p.setOpacity(self._alpha / 255.0)
        path = QPainterPath()
        path.addRoundedRect(_M, _M, _W, _H, _RADIUS, _RADIUS)
        p.fillPath(path, QColor(20, 20, 25, 242))

        if self._state == "recording":
            self._paint_recording(p)
        elif self._state == "processing":
            self._paint_processing(p)

        p.end()

    def _paint_recording(self, p: QPainter):
        if self._dot_on:
            p.setBrush(QColor(255, 60, 60))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(_M + 18, _M + _H // 2 - 6, 12, 12)

        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        p.setPen(QColor(255, 255, 255, 180))
        p.drawText(
            _M + 38, _M, 44, _H,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._lang,
        )

        bars = list(self._rms)
        p.setPen(Qt.PenStyle.NoPen)
        for i, v in enumerate(bars):
            h = max(4, int(v * _BAR_MAX_H))
            x = _M + _LABEL_END + i * (_BAR_W + _BAR_GAP)
            y = _M + (_H - h) // 2
            p.setBrush(QColor(100, 180, 255, int(120 + 135 * v)))
            p.drawRoundedRect(x, y, _BAR_W, h, 2, 2)

    def _paint_processing(self, p: QPainter):
        p.setFont(QFont("Segoe UI", 12))
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(_M, _M, _W, _H, Qt.AlignmentFlag.AlignCenter, "Processing...")
