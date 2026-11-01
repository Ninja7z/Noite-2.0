import asyncio
import sys

from .config import get_settings


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
    print(f"Noite 2.0 | modelo local: {settings.local_model} | digite /sair para encerrar")
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
            reply = asyncio.run(_handle(text))
            print(f"Noite: {reply}")
        except Exception as exc:
            print(f"Noite: não consegui concluir a solicitação ({type(exc).__name__}).")
