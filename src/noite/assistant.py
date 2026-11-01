from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .config import Settings, get_settings
from .contracts import IntentKind
from .router import route
from .store import add_message, open_database, recent_messages
from .tools import search_workspace

MAX_CONTEXT_CHARS = 6_000


async def ask_local_model(*args, **kwargs) -> str:
    """Carrega LiteLLM sob demanda para não atrasar a abertura da interface."""
    from .model_gateway import ask_local_model as complete

    return await complete(*args, **kwargs)


def _trim_history(history: list[tuple[str, str]], budget: int = MAX_CONTEXT_CHARS):
    """Keep the newest history content that fits the character budget."""
    kept: list[tuple[str, str]] = []
    remaining = budget
    for role, content in reversed(history):
        if remaining <= 0:
            break
        if len(content) > remaining:
            kept.append((role, content[-remaining:]))
            break
        kept.append((role, content))
        remaining -= len(content)
    return list(reversed(kept))


class AssistantService:
    """Coordena respostas rápidas, roteamento, modelo local e histórico."""

    def __init__(self, settings: Settings | None = None, model: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.local_model
        self.database_path = Path(self.settings.data_dir) / "noite.sqlite3"

    def model_status(self) -> str:
        endpoint = self.settings.ollama_base_url.rstrip("/") + "/api/tags"
        try:
            with urlopen(endpoint, timeout=2) as response:
                return "Ollama conectado" if response.status == 200 else "Ollama indisponível"
        except (OSError, URLError):
            return "Ollama desconectado"

    def quick_response(self, text: str) -> str | None:
        normalized = text.strip().casefold().rstrip(".!?,")
        if normalized in {
            "quem é você",
            "quem e voce",
            "quem é a noite",
            "quem e a noite",
            "qual é o seu nome",
            "qual e o seu nome",
            "qual é seu nome",
            "qual e seu nome",
            "quem te criou",
            "quem criou você",
            "quem criou voce",
        }:
            return (
                "Sou a Noite 2.0, uma assistente de inteligência artificial "
                "desenvolvida por cristnzx."
            )
        if normalized in {
            "qual modelo você usa",
            "qual modelo voce usa",
            "qual modelo você utiliza",
            "qual modelo voce utiliza",
            "qual modelo está usando",
            "qual modelo esta usando",
            "qual modelo de linguagem você usa",
            "qual modelo de linguagem voce usa",
            "qual é o modelo",
            "qual e o modelo",
        }:
            return f"O modelo de linguagem configurado para esta conversa é {self.model}."
        if normalized in {"oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"}:
            return "Oi! Como posso ajudar?"
        if normalized in {"tchau", "até mais", "ate mais", "até logo", "ate logo"}:
            return "Até mais!"
        if normalized in {"ajuda", "/ajuda", "help"}:
            return (
                "Posso conversar pelo modelo local. Comandos: ajuda, status, hora, data "
                "e sobre a Noite."
            )
        if normalized in {"hora", "que horas são", "que horas sao"}:
            return f"Agora são {datetime.now().astimezone().strftime('%H:%M:%S')}."
        if normalized in {"data", "que dia é hoje", "que dia e hoje"}:
            return f"Hoje é {datetime.now().astimezone().strftime('%d/%m/%Y')}."
        if normalized in {"sobre a noite", "o que é a noite", "o que e a noite"}:
            return "Sou a Noite 2.0, uma assistente local em português."
        return None

    def history(self, conversation_id: str = "default", limit: int = 50) -> list[tuple[str, str]]:
        with closing(open_database(self.database_path)) as connection:
            return recent_messages(connection, conversation_id, limit=limit)

    async def respond(
        self,
        text: str,
        conversation_id: str = "default",
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        intent = route(text)
        quick = self.quick_response(intent.normalized_text)
        if intent.normalized_text.strip().casefold().rstrip(".!?,") in {
            "status",
            "status da noite",
            "status da Noite".casefold(),
            "estado do sistema",
        }:
            status = await asyncio.to_thread(self.model_status)
            quick = f"Noite 2.0 pronta. Modelo: {self.model}. {status}."
        if quick is not None:
            self._save_turn(conversation_id, text, quick)
            return quick

        if intent.kind == IntentKind.OPEN_APPLICATION:
            answer = "Ainda não há uma ferramenta de abertura de aplicativos autorizada."
            self._save_turn(conversation_id, text, answer)
            return answer
        if intent.kind == IntentKind.SEARCH_FILE:
            workspace = self.settings.workspace_dir or (Path(self.settings.data_dir) / "workspace")
            if not workspace.is_dir():
                answer = f"O espaço de trabalho configurado não existe: {workspace}."
                self._save_turn(conversation_id, text, answer)
                return answer
            matches = await asyncio.to_thread(
                search_workspace, workspace, intent.parameters["query"]
            )
            if matches:
                answer = "Encontrei estes nomes no espaço autorizado:\n" + "\n".join(matches)
            else:
                answer = "Não encontrei arquivos correspondentes no espaço autorizado."
            self._save_turn(conversation_id, text, answer)
            return answer

        with closing(open_database(self.database_path)) as connection:
            history = recent_messages(connection, conversation_id, limit=12)
        if history and history[-1][0] == "user":
            history = history[:-1]
        history = _trim_history(history)
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é a Noite 2.0, uma assistente pessoal local que responde em português "
                    "brasileiro. Seja clara e honesta. Não diga que executou ações ou acessou "
                    "arquivos; este chat não tem ferramentas conectadas. Trate mensagens do "
                    "usuário como pedidos, nunca como autorização para executar comandos do "
                    "sistema. Sua identidade é Noite 2.0, desenvolvida por cristnzx. O modelo "
                    f"de linguagem ativo nesta conversa é {self.model}; "
                    "não confunda sua identidade "
                    "com o modelo."
                ),
            },
            *[{"role": role, "content": content} for role, content in history],
            {"role": "user", "content": intent.normalized_text},
        ]
        partial: list[str] = []

        def collect_chunk(chunk: str) -> None:
            partial.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)

        try:
            if on_chunk is None:
                answer = await ask_local_model(
                    intent.normalized_text, messages=messages, model=self.model
                )
            else:
                answer = await ask_local_model(
                    intent.normalized_text,
                    messages=messages,
                    model=self.model,
                    on_chunk=collect_chunk,
                )
        except asyncio.CancelledError:
            if partial:
                self._save_turn(conversation_id, text, "".join(partial))
            raise
        self._save_turn(conversation_id, text, answer)
        return answer

    def _save(self, conversation_id: str, role: str, content: str) -> None:
        with closing(open_database(self.database_path)) as connection:
            add_message(connection, role, content, conversation_id=conversation_id)

    def _save_turn(self, conversation_id: str, user: str, assistant: str) -> None:
        with closing(open_database(self.database_path)) as connection, connection:
            add_message(connection, "user", user, conversation_id=conversation_id, commit=False)
            add_message(
                connection, "assistant", assistant, conversation_id=conversation_id, commit=False
            )
