from __future__ import annotations

import argparse

from noite.ui import run_gui
from ui.client import MockClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia a interface desktop da Noite.")
    parser.add_argument(
        "--mock", action="store_true", help="Usa dados fixos para screenshots/testes."
    )
    arguments = parser.parse_args()
    return run_gui(client=MockClient() if arguments.mock else None)


if __name__ == "__main__":
    raise SystemExit(main())
