from unittest.mock import MagicMock, patch


def test_install_creates_task():
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run, \
         patch("scripts.install_autostart.Path") as MockPath:

        pythonw = MagicMock()
        pythonw.exists.return_value = True
        pythonw.__str__ = lambda s: "C:\\pythonw.exe"

        xml_file = MagicMock()
        xml_file.__str__ = lambda s: "C:\\project\\scripts\\_autostart_task.xml"

        root = MagicMock()
        scripts_dir = MagicMock()
        scripts_dir.__truediv__ = lambda s, o: xml_file
        root.__truediv__ = lambda s, o: scripts_dir

        instance = MockPath.return_value
        instance.resolve.return_value.parent.parent = root
        instance.with_name.return_value = pythonw

        from scripts.install_autostart import install
        install()

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "schtasks" in args
    assert "/Create" in args


def test_install_raises_if_pythonw_missing():
    with patch("scripts.install_autostart.Path") as MockPath:
        pythonw = MagicMock()
        pythonw.exists.return_value = False

        root = MagicMock()
        root.__truediv__ = lambda s, o: MagicMock()

        instance = MockPath.return_value
        instance.resolve.return_value.parent.parent = root
        instance.with_name.return_value = pythonw

        from scripts.install_autostart import install
        try:
            install()
            assert False, "should have raised"
        except RuntimeError:
            pass


def test_uninstall_calls_schtasks_delete():
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        from scripts.install_autostart import uninstall
        uninstall()

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "schtasks" in args
    assert "/Delete" in args
    assert "talk2type" in args
