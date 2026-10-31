import asyncio

from .config import get_settings
from .contracts import IntentKind
from .model_gateway import ask_local_model
from .router import route


async def _handle(text: str) -> str:
    intent = route(text)
    if intent.kind == IntentKind.CHAT:
        return await ask_local_model(intent.normalized_text)
    if intent.kind == IntentKind.OPEN_APPLICATION:
        return (
            f"Ação identificada: abrir {intent.parameters['app']}. "
            "Execução ficará na camada segura de ferramentas."
        )
    return (
        f"Busca identificada: {intent.parameters['query']}. "
        "Execução ficará na camada segura de ferramentas."
    )


def main() -> None:
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
