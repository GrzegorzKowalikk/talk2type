import os
import sys
from pathlib import Path

import pythoncom
from win32com.shell import shell, shellcon


def install():
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise RuntimeError(f"pythonw.exe not found next to {sys.executable}")

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    link.SetPath(str(pythonw))
    link.SetArguments(f'"{main_py}"')
    link.SetWorkingDirectory(str(project_root))
    link.SetDescription("talk2type autostart")

    startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    target = os.path.join(startup, "talk2type.lnk")
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(target, 0)
    print(f"Installed: {target}")


def uninstall():
    startup = shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)
    target = os.path.join(startup, "talk2type.lnk")
    if os.path.exists(target):
        os.remove(target)
        print(f"Removed: {target}")
    else:
        print("Not installed.")


if __name__ == "__main__":
    (uninstall if "--uninstall" in sys.argv else install)()
