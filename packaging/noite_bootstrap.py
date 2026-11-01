"""Desktop launcher; the build script replaces PROJECT_ROOT for this machine."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from noite_path_placeholder import PROJECT_ROOT


def main() -> int:
    root = Path(PROJECT_ROOT)
    pythonw = root / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.is_file():
        pythonw = root / ".venv" / "Scripts" / "python.exe"
    if not pythonw.is_file() or not (root / "src" / "noite").is_dir():
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            "Ambiente do Noite não encontrado. Reconstrua o app com "
            "scripts/build_windows.ps1.",
            "Noite 2.0",
            0x10,
        )
        return 1

    env = os.environ.copy()
    source = str(root / "src")
    prior_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = source if not prior_path else source + os.pathsep + prior_path
    subprocess.Popen(
        [str(pythonw), "-m", "noite"],
        cwd=root,
        env=env,
        close_fds=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
