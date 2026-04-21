import time
from unittest.mock import MagicMock, patch


@patch("talk2type.resource_mgr.win32gui")
@patch("talk2type.resource_mgr.win32api")
@patch("talk2type.resource_mgr.win32con")
def test_fullscreen_detection_normal_window(mock_con, mock_api, mock_gui):
    from talk2type.resource_mgr import is_fullscreen

    mock_gui.GetForegroundWindow.return_value = 123
    mock_gui.GetClassName.return_value = "Chrome_WidgetWin_1"
    mock_gui.GetWindowText.return_value = "Google Chrome"
    mock_gui.GetWindowRect.return_value = (100, 100, 900, 700)
    mock_api.GetSystemMetrics.side_effect = [1920, 1080]

    assert is_fullscreen() is False


@patch("talk2type.resource_mgr.win32gui")
@patch("talk2type.resource_mgr.win32api")
@patch("talk2type.resource_mgr.win32con")
def test_fullscreen_detection_true_fullscreen(mock_con, mock_api, mock_gui):
    from talk2type.resource_mgr import is_fullscreen

    mock_gui.GetForegroundWindow.return_value = 456
    mock_gui.GetClassName.return_value = "ApplicationFrameWindow"
    mock_gui.GetWindowText.return_value = "Counter-Strike"
    mock_gui.GetWindowRect.return_value = (0, 0, 1920, 1080)
    mock_api.GetSystemMetrics.side_effect = [1920, 1080]

    assert is_fullscreen() is True


@patch("talk2type.resource_mgr.win32gui")
@patch("talk2type.resource_mgr.win32api")
@patch("talk2type.resource_mgr.win32con")
def test_fullscreen_skips_shell_classes(mock_con, mock_api, mock_gui):
    from talk2type.resource_mgr import is_fullscreen

    mock_gui.GetForegroundWindow.return_value = 789
    mock_gui.GetClassName.return_value = "Progman"
    # Even if rect is fullscreen
    mock_gui.GetWindowRect.return_value = (0, 0, 1920, 1080)
    mock_api.GetSystemMetrics.side_effect = [1920, 1080]

    assert is_fullscreen() is False


def test_idle_triggers_unload():
    from talk2type.resource_mgr import ResourceManager

    on_unload = MagicMock()
    mgr = ResourceManager(on_unload=on_unload, idle_timeout_sec=0.2, poll_sec=0.05)
    with patch("talk2type.resource_mgr.is_fullscreen", return_value=False):
        mgr.start()
        mgr.mark_activity()
        time.sleep(0.35)
        mgr.stop()

    assert on_unload.call_count == 1

    # Should NOT fire again — guard _unloaded
    time.sleep(0.3)
    assert on_unload.call_count == 1


@patch("talk2type.resource_mgr.is_fullscreen", return_value=True)
def test_fullscreen_triggers_unload(mock_fs):
    from talk2type.resource_mgr import ResourceManager

    on_unload = MagicMock()
    mgr = ResourceManager(on_unload=on_unload, idle_timeout_sec=10, poll_sec=0.05)
    mgr.start()
    mgr.mark_activity()
    time.sleep(0.15)
    mgr.stop()

    on_unload.assert_called_once()
