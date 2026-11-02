from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from noite.assistant import AssistantService, ollama_binary, start_ollama_server
from noite.config import Settings


class NoiteClient(Protocol):
    async def enviar(
        self,
        texto: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
        **contexto: object,
    ) -> str: ...

    def parar(self) -> None: ...

    def sessoes(self) -> list[tuple[str, str, str]]: ...

    def contexto(self) -> dict[str, object]: ...

    def ferramentas(self) -> list[str]: ...


class ServiceClient:
    """Thin UI adapter around AssistantService; calls remain in the worker thread."""

    def __init__(self, settings: Settings, model: str | None = None) -> None:
        self.settings = settings
        self._service = AssistantService(settings, model=model)
        self._stop_callback: Callable[[], None] | None = None

    def __getattr__(self, name: str):
        return getattr(self._service, name)

    def set_model(self, model: str) -> None:
        self._service = AssistantService(self.settings, model=model)

    async def enviar(
        self,
        texto: str,
        *,
        conversation_id: str,
        on_chunk: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
        on_activity: Callable[[object], None] | None = None,
        project_root: Path | None = None,
        active_file: str | None = None,
        active_text: str | None = None,
    ) -> str:
        return await self._service.respond(
            texto,
            conversation_id=conversation_id,
            on_chunk=on_chunk,
            on_thinking=on_thinking,
            on_activity=on_activity,
            project_root=project_root,
            active_file=active_file,
            active_text=active_text,
        )

    def parar(self) -> None:
        if self._stop_callback is not None:
            self._stop_callback()

    def bind_stop(self, callback: Callable[[], None] | None) -> None:
        self._stop_callback = callback

    def sessoes(self) -> list[tuple[str, str, str]]:
        return self._service.conversations()

    def contexto(self) -> dict[str, object]:
        return {"workspace": self.settings.workspace_dir, "off_grid": self.settings.off_grid}

    def ferramentas(self) -> list[str]:
        return ["Calculadora", "Pesquisa na Web", "Executar Comando", "Abrir Arquivo"]

    def model_diagnostics(self) -> dict[str, object]:
        return self._service.model_diagnostics()

    def ollama_available(self) -> bool:
        return ollama_binary() is not None

    def iniciar_ollama(self, log_dir: Path | None = None) -> bool:
        return start_ollama_server(log_dir)


class MockClient:
    """Fixed reference data for screenshots and UI tests only."""

    def __init__(self) -> None:
        self._conversations = [
            ("mock-python", "Análise de código Python", ""),
            ("mock-plan", "Planejamento do projeto", ""),
            ("mock-local", "Dúvidas sobre IA local", ""),
        ]

    def active_conversation_id(self) -> str:
        return "mock-home"

    def conversations(self) -> list[tuple[str, str, str]]:
        return list(self._conversations)

    def sessoes(self) -> list[tuple[str, str, str]]:
        return self.conversations()

    def history(self, _conversation_id: str, limit: int = 50) -> list[tuple[str, str]]:
        return [] if limit > 0 else []

    def set_active_conversation(self, _conversation_id: str) -> None:
        return None

    def create_conversation(self) -> str:
        conversation_id = f"mock-{len(self._conversations) + 1}"
        self._conversations.insert(0, (conversation_id, "Nova conversa", ""))
        return conversation_id

    def rename_conversation(self, conversation_id: str, title: str) -> bool:
        self._conversations = [
            (item_id, title if item_id == conversation_id else name, stamp)
            for item_id, name, stamp in self._conversations
        ]
        return any(item_id == conversation_id for item_id, _, _ in self._conversations)

    def delete_conversation(self, conversation_id: str) -> str | None:
        self._conversations = [item for item in self._conversations if item[0] != conversation_id]
        return self._conversations[0][0] if self._conversations else None

    async def enviar(self, texto: str, **_contexto: object) -> str:
        response = f"Resposta de demonstração para: {texto}"
        for start in range(0, len(response), 12):
            await asyncio.sleep(0.02)
            callback = _contexto.get("on_chunk")
            if callable(callback):
                callback(response[start : start + 12])
        return response

    def parar(self) -> None:
        return None

    def contexto(self) -> dict[str, object]:
        return {
            "project": "Noite-2.0",
            "directory": r"C:\Users\example\Noite-2.0",
            "indexed_documents": 18,
        }

    def ferramentas(self) -> list[str]:
        return ["Calculadora", "Pesquisa na Web", "Executar Comando", "Abrir Arquivo"]

    def model_diagnostics(self) -> dict[str, object]:
        return {
            "server": "up",
            "endpoint": "http://127.0.0.1:11434",
            "model": "qwen2.5:3b",
            "model_installed": True,
            "installed_models": ["qwen2.5:3b"],
            "message": (
                "Ollama conectado em http://127.0.0.1:11434. "
                "Modelo qwen2.5:3b pronto para uso."
            ),
        }

    def ollama_available(self) -> bool:
        return False

    def iniciar_ollama(self) -> None:
        raise RuntimeError("O MockClient não inicia o Ollama.")
