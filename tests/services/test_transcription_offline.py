from unittest.mock import MagicMock, patch


def test_load_prefers_cache_then_falls_back_to_download():
    from talk2type.services.transcription import TranscriptionService

    with patch("talk2type.services.transcription.WhisperModel") as WM, patch.object(
        TranscriptionService, "refresh_hotwords"
    ):
        WM.side_effect = [OSError("not cached"), MagicMock()]
        TranscriptionService().preload()
        assert [c.kwargs.get("local_files_only", False) for c in WM.call_args_list] == [True, False]
