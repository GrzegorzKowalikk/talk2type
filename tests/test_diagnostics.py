import sys
import threading

from talk2type.diagnostics import install_crash_hooks


def test_hooks_installed(monkeypatch):
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)
    install_crash_hooks()
    assert sys.excepthook is not sys.__excepthook__
    assert threading.excepthook is not threading.__excepthook__


def test_hook_logs_critical(caplog):
    install_crash_hooks()
    try:
        raise ValueError("boom")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert "Unhandled exception" in caplog.text
