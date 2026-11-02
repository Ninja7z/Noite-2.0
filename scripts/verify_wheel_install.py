from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica imports de um wheel fora do checkout.")
    parser.add_argument("wheel_dir", type=Path)
    args = parser.parse_args()
    wheels = list(args.wheel_dir.glob("noite_assistant-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Esperado um wheel em {args.wheel_dir}; encontrados: {len(wheels)}")

    with tempfile.TemporaryDirectory(prefix="noite-wheel-smoke-") as temporary:
        root = Path(temporary)
        target = root / "site-packages"
        installer = shutil.which("uv")
        command = (
            [installer, "pip", "install", "--no-deps", "--target", str(target), str(wheels[0])]
            if installer
            else [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                str(target),
                str(wheels[0]),
            ]
        )
        subprocess.run(command, check=True)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(target)
        probe = """
from importlib.metadata import distribution
from pathlib import Path
import noite
import ui.client
from noite.ui import run_gui

package = Path(noite.__file__).resolve().parent
assert Path(ui.client.__file__).resolve().is_relative_to(Path(package.parent / 'ui'))
for resource in ('theme.json', 'assets/noite.ico', 'assets/icons/moon.svg'):
    assert (package / resource).is_file(), resource
assert any(
    entry.group == 'console_scripts' and entry.name == 'noite'
    for entry in distribution('noite-assistant').entry_points
)
print('Wheel import smoke test passed.')
"""
        subprocess.run(
            [sys.executable, "-c", probe],
            cwd=root,
            env=environment,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
