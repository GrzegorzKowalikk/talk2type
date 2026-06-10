import subprocess
import sys
from pathlib import Path

TASK_NAME = "talk2type"
DELAY = "PT30S"

# Register-ScheduledTask instead of `schtasks /Create /XML`: the latter
# requires elevation, the CIM API can register a current-user logon task
# without admin rights.
_INSTALL_PS = """
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = '{delay}'
$action = New-ScheduledTaskAction -Execute '{pythonw}' -Argument '"{main_py}"' -WorkingDirectory '{project_root}'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName '{task_name}' -Trigger $trigger -Action $action -Settings $settings -Force | Out-Null
"""


def _run_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )


def install():
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise RuntimeError(f"pythonw.exe not found next to {sys.executable}")

    result = _run_ps(
        _INSTALL_PS.format(
            delay=DELAY,
            pythonw=pythonw,
            main_py=main_py,
            project_root=project_root,
            task_name=TASK_NAME,
        )
    )
    if result.returncode != 0:
        raise RuntimeError(f"Register-ScheduledTask failed:\n{result.stderr}")
    print(f"Installed: Task Scheduler task '{TASK_NAME}' (30s delay after logon)")


def uninstall():
    result = _run_ps(
        f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"
    )
    if result.returncode == 0:
        print(f"Removed: Task Scheduler task '{TASK_NAME}'")
    else:
        print("Not installed.")


if __name__ == "__main__":
    (uninstall if "--uninstall" in sys.argv else install)()
