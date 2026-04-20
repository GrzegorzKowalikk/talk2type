import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def tmp_startup(tmp_path):
    """Provide a temp directory as the Startup folder."""
    return tmp_path


def test_install_creates_lnk(tmp_startup):
    with (
        patch("scripts.install_autostart.pythoncom") as mock_com,
        patch("scripts.install_autostart.shell") as mock_shell,
        patch("scripts.install_autostart.shellcon") as mock_shellcon,
        patch(
            "scripts.install_autostart.os.path.join",
            return_value=str(tmp_startup / "own_wisprflow.lnk"),
        ),
        patch("scripts.install_autostart.Path") as MockPath,
        patch("scripts.install_autostart.sys") as mock_sys,
    ):
        from scripts.install_autostart import install

        mock_shellcon.CSIDL_STARTUP = 7
        mock_shell.SHGetFolderPath.return_value = str(tmp_startup)

        link = MagicMock()
        mock_com.CoCreateInstance.return_value = link
        persist = MagicMock()
        link.QueryInterface.return_value = persist

        pythonw = MagicMock()
        pythonw.exists.return_value = True
        pythonw.__str__ = lambda s: "C:\\pythonw.exe"
        mock_sys.executable = "C:\\Python312\\python.exe"

        # Patch Path to resolve to project root
        root = MagicMock()
        root.__truediv__ = lambda s, o: MagicMock()
        MockPath.return_value.resolve.return_value.parent.parent = root

        install()

        # Verify COM was used to create the link
        mock_com.CoCreateInstance.assert_called_once()
        persist.Save.assert_called_once()


def test_uninstall_removes_lnk(tmp_startup):
    from scripts.install_autostart import uninstall

    # Create a fake .lnk file
    lnk_path = tmp_startup / "own_wisprflow.lnk"
    lnk_path.write_text("fake shortcut")

    with (
        patch("scripts.install_autostart.shell") as mock_shell,
        patch("scripts.install_autostart.shellcon") as mock_shellcon,
    ):
        mock_shellcon.CSIDL_STARTUP = 7
        mock_shell.SHGetFolderPath.return_value = str(tmp_startup)
        uninstall()

    assert not lnk_path.exists()
