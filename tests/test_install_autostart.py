import json
from unittest.mock import MagicMock, patch

import pytest


def test_install_upserts_profile_and_registers_task(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"profiles": {"list": []}}), encoding="utf-8")
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("scripts.install_autostart.PYTHON") as PY, \
         patch("scripts.install_autostart._wt_exe", return_value=tmp_path / "wt.exe"), \
         patch("scripts.install_autostart._wt_settings_path", return_value=settings), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        PY.exists.return_value = True
        PY.__str__.return_value = "C:\\python.exe"

        from scripts.install_autostart import install
        install()

    data = json.loads(settings.read_text(encoding="utf-8"))
    profile = next(p for p in data["profiles"]["list"] if p["name"] == "talk2type")
    assert profile["tabColor"] == "#0078D4"
    assert profile["suppressApplicationTitle"] is True
    assert profile["commandline"].endswith('"')

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "powershell" in cmd
    ps = cmd[-1]
    assert "Register-ScheduledTask" in ps
    assert '-p "talk2type"' in ps


def test_install_raises_if_python_missing():
    with patch("scripts.install_autostart.PYTHON") as PY:
        PY.exists.return_value = False
        from scripts.install_autostart import install
        with pytest.raises(RuntimeError):
            install()


def test_uninstall_removes_profile_and_task(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"profiles": {"list": [
            {"name": "talk2type", "guid": "{x}"},
            {"name": "keep", "guid": "{y}"},
        ]}}),
        encoding="utf-8",
    )
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("scripts.install_autostart._wt_settings_path", return_value=settings), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        from scripts.install_autostart import uninstall
        uninstall()

    data = json.loads(settings.read_text(encoding="utf-8"))
    names = [p["name"] for p in data["profiles"]["list"]]
    assert "talk2type" not in names
    assert "keep" in names

    ps = mock_run.call_args[0][0][-1]
    assert "Unregister-ScheduledTask" in ps
    assert "talk2type" in ps
