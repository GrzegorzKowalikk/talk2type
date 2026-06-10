from unittest.mock import MagicMock

from talk2type.app import App
from talk2type.config import IDLE_TIMEOUT_SEC


def test_idle_timeout_is_15_minutes():
    assert IDLE_TIMEOUT_SEC == 900


def test_unload_models_unloads_both_services():
    app = App.__new__(App)
    app._transcription = MagicMock()
    app._cleanup = MagicMock()
    app._unload_models()
    app._transcription.unload.assert_called_once()
    app._cleanup.unload.assert_called_once()
