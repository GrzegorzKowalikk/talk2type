import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

TASK_NAME = "talk2type"
PROFILE_NAME = "talk2type"
DELAY = "PT30S"
TAB_COLOR = "#0078D4"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = PROJECT_ROOT / "main.py"
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
ICON = PROJECT_ROOT / "images" / "icon.png"

# Register-ScheduledTask instead of `schtasks /Create /XML`: the latter
# requires elevation, the CIM API can register a current-user logon task
# without admin rights. The task opens the branded Windows Terminal profile;
# the app's own single-instance guard prevents duplicate launches.
_INSTALL_PS = """
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = '{delay}'
$action = New-ScheduledTaskAction -Execute '{wt}' -Argument '-p "{profile}"'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName '{task_name}' -Trigger $trigger -Action $action -Settings $settings -Force | Out-Null
"""


def _run_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )


def _wt_settings_path() -> Path:
    local = Path(os.environ["LOCALAPPDATA"])
    for pkg in (local / "Packages").glob("Microsoft.WindowsTerminal*"):
        sp = pkg / "LocalState" / "settings.json"
        if sp.exists():
            return sp
    unpackaged = local / "Microsoft" / "Windows Terminal" / "settings.json"
    if unpackaged.exists():
        return unpackaged
    raise RuntimeError("Windows Terminal settings.json not found -- is Windows Terminal installed?")


def _wt_exe() -> Path:
    wt = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps" / "wt.exe"
    if not wt.exists():
        raise RuntimeError(f"wt.exe not found at {wt} -- is Windows Terminal installed?")
    return wt


def _upsert_profile() -> Path:
    settings_path = _wt_settings_path()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    profiles = settings.setdefault("profiles", {}).setdefault("list", [])
    profile = next((p for p in profiles if p.get("name") == PROFILE_NAME), None)
    if profile is None:
        profile = {"guid": "{" + str(uuid.uuid4()) + "}", "name": PROFILE_NAME}
        profiles.append(profile)
    profile.update({
        "commandline": f'"{PYTHON}" "{MAIN_PY}"',
        "startingDirectory": str(PROJECT_ROOT),
        "icon": str(ICON),
        "tabColor": TAB_COLOR,
        "suppressApplicationTitle": True,
        "hidden": False,
    })
    backup = settings_path.with_name(settings_path.name + ".talk2type.bak")
    if not backup.exists():
        backup.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")
    settings_path.write_text(
        json.dumps(settings, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    return settings_path


def _remove_profile():
    settings_path = _wt_settings_path()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    profiles = settings.get("profiles", {}).get("list", [])
    kept = [p for p in profiles if p.get("name") != PROFILE_NAME]
    if len(kept) != len(profiles):
        settings["profiles"]["list"] = kept
        settings_path.write_text(
            json.dumps(settings, indent=4, ensure_ascii=False), encoding="utf-8"
        )


def install():
    if not PYTHON.exists():
        raise RuntimeError(f"venv python not found at {PYTHON} -- run `uv sync` first")
    wt = _wt_exe()
    settings_path = _upsert_profile()
    print(f"Installed: Windows Terminal profile '{PROFILE_NAME}' in {settings_path}")

    result = _run_ps(
        _INSTALL_PS.format(
            delay=DELAY,
            wt=wt,
            profile=PROFILE_NAME,
            task_name=TASK_NAME,
        )
    )
    if result.returncode != 0:
        raise RuntimeError(f"Register-ScheduledTask failed:\n{result.stderr}")
    print(f"Installed: Task Scheduler task '{TASK_NAME}' (30s delay after logon)")


def uninstall():
    _remove_profile()
    print(f"Removed: Windows Terminal profile '{PROFILE_NAME}'")
    result = _run_ps(
        f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"
    )
    if result.returncode == 0:
        print(f"Removed: Task Scheduler task '{TASK_NAME}'")
    else:
        print("Task not installed.")


if __name__ == "__main__":
    (uninstall if "--uninstall" in sys.argv else install)()
