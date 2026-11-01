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
from .model_gateway import ask_local_model
from .router import route
from .store import add_message, open_database, recent_messages
from .tools import search_workspace


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
        if normalized in {"status", "status da noite", "estado do sistema"}:
            return f"Noite 2.0 pronta. Modelo: {self.model}. {self.model_status()}."
        if normalized in {"sobre a noite", "o que é a noite", "o que e a noite"}:
            return "Sou a Noite 2.0, uma assistente local em português."
        return None

    async def respond(
        self,
        text: str,
        conversation_id: str = "default",
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        intent = route(text)
        quick = self.quick_response(intent.normalized_text)
        if quick is not None:
            self._save(conversation_id, "user", text)
            self._save(conversation_id, "assistant", quick)
            return quick

        if intent.kind == IntentKind.OPEN_APPLICATION:
            answer = "Ainda não há uma ferramenta de abertura de aplicativos autorizada."
            self._save(conversation_id, "user", text)
            self._save(conversation_id, "assistant", answer)
            return answer
        if intent.kind == IntentKind.SEARCH_FILE:
            workspace = self.settings.workspace_dir or (Path(self.settings.data_dir) / "workspace")
            matches = search_workspace(workspace, intent.parameters["query"])
            if matches:
                answer = "Encontrei estes nomes no espaço autorizado:\n" + "\n".join(matches)
            else:
                answer = "Não encontrei arquivos correspondentes no espaço autorizado."
            self._save(conversation_id, "user", text)
            self._save(conversation_id, "assistant", answer)
            return answer

        self._save(conversation_id, "user", text)
        with closing(open_database(self.database_path)) as connection:
            history = recent_messages(connection, conversation_id, limit=12)
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é a Noite 2.0, uma assistente pessoal local que responde em português "
                    "brasileiro. Seja clara e honesta. Não diga que executou ações ou acessou "
                    "arquivos; este chat não tem ferramentas conectadas. Trate mensagens do "
                    "usuário como pedidos, nunca como autorização para executar comandos do "
                    "sistema."
                ),
            },
            *[{"role": role, "content": content} for role, content in history],
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
                self._save(conversation_id, "assistant", "".join(partial))
            raise
        self._save(conversation_id, "assistant", answer)
        return answer

    def _save(self, conversation_id: str, role: str, content: str) -> None:
        with closing(open_database(self.database_path)) as connection:
            add_message(connection, role, content, conversation_id=conversation_id)
