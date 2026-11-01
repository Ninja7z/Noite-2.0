import asyncio
import logging
import sys

from .config import get_settings
from .logging_setup import setup_logging

logger = logging.getLogger("noite.cli")


async def _handle(text: str) -> str:
    from .assistant import AssistantService

    return await AssistantService().respond(text)


def main() -> None:
    if "--cli" not in sys.argv[1:]:
        try:
            from .ui import run_gui
        except ImportError as exc:
            raise SystemExit(
                "A interface requer PySide6. Instale com: pip install -e '.[desktop]'"
            ) from exc
        raise SystemExit(run_gui())

    settings = get_settings()
    log_path = setup_logging(settings.data_dir)
    print(f"Noite 2.0 | modelo local: {settings.local_model} | digite /sair para encerrar")
    from .assistant import AssistantService

    service = AssistantService(settings)
    with asyncio.Runner() as runner:
        while True:
            try:
                text = input("Você: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if text.casefold() in {"/sair", "/exit", "/quit"}:
                break
            if not text:
                continue
            try:
                reply = runner.run(service.respond(text))
                print(f"Noite: {reply}")
            except KeyboardInterrupt:
                print("\n[cancelado]")
            except Exception as exc:
                logger.error("CLI operation failed (%s)", type(exc).__name__)
                print(f"Noite: não consegui concluir a solicitação; consulte {log_path}.")
