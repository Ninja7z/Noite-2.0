from __future__ import annotations

import argparse

from noite.mascot import run_mascot


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia a interface da Noite 2.0.")
    parser.add_argument(
        "--legacy", action="store_true", help="Abre a interface completa anterior (legado)."
    )
    parser.add_argument(
        "--mock", action="store_true", help="Usa dados fixos na interface legada para testes."
    )
    arguments = parser.parse_args()
    if arguments.legacy:
        from noite.ui import run_gui
        from ui.client import MockClient

        return run_gui(client=MockClient() if arguments.mock else None)
    if arguments.mock:
        parser.error("--mock só pode ser usado com --legacy.")
    return run_mascot()


if __name__ == "__main__":
    raise SystemExit(main())
