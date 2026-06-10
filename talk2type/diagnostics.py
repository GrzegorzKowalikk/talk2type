import logging
import sys
import threading

from PySide6.QtCore import qInstallMessageHandler

log = logging.getLogger(__name__)


def install_crash_hooks() -> None:
    """Log every unhandled exception instead of dying silently."""

    def _hook(exc_type, exc, tb):
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    def _thread_hook(args):
        name = args.thread.name if args.thread else "?"
        log.critical(
            "Unhandled exception in thread %s", name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    def _qt_handler(_mode, _ctx, msg):
        log.warning("Qt: %s", msg)

    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    qInstallMessageHandler(_qt_handler)
