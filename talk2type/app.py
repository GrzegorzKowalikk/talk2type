import logging
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from talk2type.config import setup_logging
from talk2type.core.pipeline import DictationPipeline
from talk2type.core.states import DictationStateMachine
from talk2type.diagnostics import install_crash_hooks
from talk2type.hotkey import HotkeyListener
from talk2type.resource_mgr import ResourceManager
from talk2type.services.audio import AudioRecorder
from talk2type.services.cleanup import CleanupService
from talk2type.services.paste import PasteService
from talk2type.services.transcription import TranscriptionService
from talk2type.ui.main_window import MainWindow
from talk2type.ui.overlay import OverlayWindow
from talk2type.ui.tray import Tray

log = logging.getLogger(__name__)


class App:
    def __init__(self):
        setup_logging()
        install_crash_hooks()
        self._qt = QApplication(sys.argv)

        self._machine = DictationStateMachine()
        self._overlay = OverlayWindow()
        self._window = MainWindow()
        self._transcription = TranscriptionService()
        self._cleanup = CleanupService()
        self._resmgr = ResourceManager(on_unload=self._unload_models)
        self._pipeline = DictationPipeline(
            machine=self._machine,
            recorder=AudioRecorder(),
            transcription=self._transcription,
            cleanup=self._cleanup,
            paste=PasteService(),
            level_callback=self._overlay.push_rms,
            on_activity=self._resmgr.mark_activity,
        )
        self._hotkey = HotkeyListener(
            on_start=self._pipeline.on_press,
            on_stop=self._pipeline.on_release,
            on_cancel=self._pipeline.on_cancel,
        )
        self._tray = Tray(
            on_quit=lambda: QTimer.singleShot(0, self._qt, self.shutdown),
            on_open=lambda: QTimer.singleShot(0, self._qt, self._window.bring_to_front),
        )
        self._connect_signals()
        log.info("App initialized -- F9=PL, F10=EN, Esc=cancel")

    def _connect_signals(self):
        self._machine.recording_started.connect(self._overlay.on_recording)
        self._machine.processing_started.connect(self._overlay.on_processing)
        self._machine.returned_to_idle.connect(self._overlay.on_idle)
        self._window.dictionary_page.hotwords_changed.connect(
            self._transcription.refresh_hotwords
        )

    def _unload_models(self):
        self._transcription.unload()
        self._cleanup.unload()

    def run(self):
        self._tray.run()
        self._resmgr.start()
        self._hotkey.start()
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        sigint_timer = QTimer()
        sigint_timer.start(200)
        sigint_timer.timeout.connect(lambda: None)
        self._qt.exec()
        sys.exit(0)

    def shutdown(self):
        log.info("Shutting down")
        self._hotkey.stop()
        self._resmgr.stop()
        self._unload_models()
        self._qt.quit()
