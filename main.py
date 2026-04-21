import logging
import signal
import sys
import time

from talk2type.audio import Recorder
from talk2type.config import setup_logging
from talk2type.hotkey import HotkeyListener
from talk2type.llm import cleanup_text, unload as unload_llm
from talk2type.paste import paste_text
from talk2type.resource_mgr import ResourceManager
from talk2type.stt import WhisperSTT
from talk2type.tray import Tray

log = logging.getLogger(__name__)


class App:
    def __init__(self):
        setup_logging()
        self.recorder = Recorder()
        self.stt = WhisperSTT()
        self.tray = Tray(on_quit=self.shutdown)
        self.resmgr = ResourceManager(on_unload=self.unload_all)
        self.hotkey = HotkeyListener(
            on_pl_start=lambda: self._start("pl"),
            on_pl_stop=lambda: self._stop("pl"),
            on_en_start=lambda: self._start("en"),
            on_en_stop=lambda: self._stop("en"),
        )
        self._busy = False
        log.info("App initialized — F9=PL, F10=EN")

    def unload_all(self):
        self.stt.unload()
        unload_llm()

    def _start(self, lang):
        if self._busy:
            return
        self.tray.set_state("recording")
        self.recorder.start()
        self._lang = lang
        log.info("Recording started [%s]", lang)

    def _stop(self, lang):
        if self._busy:
            return
        self._busy = True
        audio = self.recorder.stop()
        t0 = time.monotonic()
        self.tray.set_state("processing")
        try:
            if audio.size < 1600:
                log.info("Short audio (%d samples) — skipping", audio.size)
                return
            raw = self.stt.transcribe(audio, language=lang)
            self.resmgr.mark_activity()
            log.info("STT [%s]: %s", lang, raw)
            cleaned = cleanup_text(raw, language=lang)
            log.info("LLM: %s", cleaned)
            paste_text(cleaned)
            log.info("Pipeline: %.2fs", time.monotonic() - t0)
        finally:
            self.tray.set_state("idle")
            self._busy = False

    def run(self):
        self.tray.run()
        self.resmgr.start()
        self.hotkey.start()
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())
        if hasattr(signal, "pause"):
            signal.pause()
        else:
            time.sleep(1e9)

    def shutdown(self):
        log.info("Shutting down")
        self.hotkey.stop()
        self.resmgr.stop()
        self.unload_all()
        sys.exit(0)


if __name__ == "__main__":
    App().run()
