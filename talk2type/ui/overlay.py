import collections
import ctypes

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget

_BARS = 28
_BAR_W = 3
_BAR_GAP = 2
_BAR_MAX_H = 22
_W = 260        # pill width
_H = 44         # pill height
_RADIUS = 22    # = H/2 -> perfect pill
_LABEL_END = 52
_M = 12         # transparent margin -- absorbs DWM shadow

_WIN_W = _W + 2 * _M
_WIN_H = _H + 2 * _M

_BG = QColor(8, 8, 8, 247)
_FG = QColor(255, 255, 255)
_FG_DIM = QColor(255, 255, 255, 130)


def _setup_dwm(hwnd: int) -> None:
    """Remove Windows DWM border/shadow for this window."""
    try:
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(ctypes.c_int(1)), 4)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(1)), 4)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_uint32(0xFFFFFFFE)), 4)
    except Exception:
        pass


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
        self._tick = 0
        self._progress_label = ""
        self._progress_detail = ""

        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(50)
        self._wave_timer.timeout.connect(self.update)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(300)
        self._pulse_timer.timeout.connect(self._pulse)

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_step)

        self._reposition()

    def showEvent(self, event):
        super().showEvent(event)
        _setup_dwm(int(self.winId()))

    # --- public slots (connected to DictationStateMachine signals) ---

    @Slot(str)
    def on_recording(self, lang: str):
        self._fade_timer.stop()
        self._state = "recording"
        self._lang = lang.upper()
        self._alpha = 255
        self._tick = 0
        self._progress_label = ""
        self._progress_detail = ""
        self._pulse_timer.start()
        self._wave_timer.start()
        self._reposition()
        self.show()
        self.update()

    @Slot()
    def on_processing(self):
        self._state = "processing"
        self._wave_timer.stop()
        self.update()

    @Slot(str, str)
    def on_progress(self, label: str, detail: str):
        self._progress_label = label
        self._progress_detail = detail
        self.update()

    @Slot(str)
    def on_idle(self, _reason: str):
        self._pulse_timer.stop()
        self._wave_timer.stop()
        self._fade_timer.start()

    def push_rms(self, rms: float):
        self._rms.append(min(rms * 10.0, 1.0))

    # --- internals (main thread only) ---

    def _pulse(self):
        self._tick += 1
        self.update()

    def _fade_step(self):
        self._alpha = max(0, self._alpha - 20)
        self.update()
        if self._alpha == 0:
            self._fade_timer.stop()
            self.hide()

    def _reposition(self):
        screen_obj = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        screen = screen_obj.geometry()
        self.move(screen.center().x() - _WIN_W // 2, screen.bottom() - 120 - _WIN_H)

    # --- painting ---

    def paintEvent(self, _):
        if self._alpha == 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(0, 0, _WIN_W, _WIN_H, QColor(0, 0, 0, 0))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        p.setOpacity(self._alpha / 255.0)
        path = QPainterPath()
        path.addRoundedRect(_M, _M, _W, _H, _RADIUS, _RADIUS)
        p.fillPath(path, _BG)

        if self._state == "recording":
            self._paint_recording(p)
        elif self._state == "processing":
            self._paint_processing(p)

        p.end()

    def _paint_recording(self, p: QPainter):
        dot_alpha = 255 if self._tick % 2 == 0 else 90
        p.setBrush(QColor(255, 255, 255, dot_alpha))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(_M + 14, _M + _H // 2 - 3, 6, 6)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(_FG_DIM)
        p.drawText(
            _M + 26, _M, 26, _H,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._lang,
        )

        p.setPen(Qt.PenStyle.NoPen)
        # copy: audio thread appends to the deque while we iterate
        for i, v in enumerate(list(self._rms)):
            h = max(3, int(v * _BAR_MAX_H))
            x = _M + _LABEL_END + i * (_BAR_W + _BAR_GAP)
            y = _M + (_H - h) // 2
            p.setBrush(QColor(255, 255, 255, int(90 + 165 * v)))
            p.drawRoundedRect(x, y, _BAR_W, h, 1, 1)

    def _paint_processing(self, p: QPainter):
        detail_text = f"({self._progress_detail})" if self._progress_detail else ""

        if self._progress_label.startswith("Przetwarzam") or not self._progress_label:
            # 3 animated dots + detail text
            dots_w = 34
            font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
            p.setFont(font)
            fm = QFontMetrics(font)
            text_w = fm.horizontalAdvance(detail_text) if detail_text else 0
            
            total_w = dots_w + (6 + text_w if text_w else 0)
            start_x = _M + (_W - total_w) // 2
            
            # Draw dots
            p.setPen(Qt.PenStyle.NoPen)
            cy = _M + _H // 2 - 3
            cx = start_x
            for i in range(3):
                alpha = 255 if self._tick % 3 == i else 80
                p.setBrush(QColor(255, 255, 255, alpha))
                p.drawEllipse(cx + i * 12, cy, 6, 6)
                
            # Draw detail
            if detail_text:
                p.setPen(_FG_DIM)
                p.drawText(
                    cx + dots_w + 6, _M, text_w, _H,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    detail_text,
                )
        else:
            # Draw label + detail (e.g. Pobieram... (1.2/3.1 GB))
            font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
            p.setFont(font)
            fm = QFontMetrics(font)

            full_text = f"{self._progress_label} {detail_text}".rstrip()
            text_w = fm.horizontalAdvance(full_text)
            text_x = _M + (_W - text_w) // 2

            # Main label in white
            p.setPen(_FG)
            p.drawText(
                text_x, _M, text_w, _H,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._progress_label,
            )
            # Detail in dim
            if detail_text:
                label_w = fm.horizontalAdvance(self._progress_label + " ")
                p.setPen(_FG_DIM)
                p.drawText(
                    text_x + label_w, _M, fm.horizontalAdvance(detail_text), _H,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    detail_text,
                )
