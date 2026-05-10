import subprocess
import sys
from pathlib import Path

TASK_NAME = "talk2type"
DELAY = "PT30S"


def install():
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise RuntimeError(f"pythonw.exe not found next to {sys.executable}")

    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>{DELAY}</Delay>
    </LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{pythonw}</Command>
      <Arguments>"{main_py}"</Arguments>
      <WorkingDirectory>{project_root}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_file = project_root / "scripts" / "_autostart_task.xml"
    xml_file.write_text(xml, encoding="utf-16")
    try:
        subprocess.run(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_file), "/F"],
            check=True,
            capture_output=True,
        )
        print(f"Installed: Task Scheduler task '{TASK_NAME}' (30s delay after logon)")
    finally:
        xml_file.unlink(missing_ok=True)


def uninstall():
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )
    if result.returncode == 0:
        print(f"Removed: Task Scheduler task '{TASK_NAME}'")
    else:
        print("Not installed.")


if __name__ == "__main__":
    (uninstall if "--uninstall" in sys.argv else install)()
