"""Orquestrador de bastidores da Noite 2.0."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from .activity import ActivityEvent, ActivityState, make_activity_event
from .assistant import AssistantService
from .config import Settings
from .router import Intent, IntentKind, route
from .task_router import (
    classify_task,
    get_hardware_profile,
    is_model_compatible,
    route_model,
)

logger = logging.getLogger("noite.orchestrator")

AgentStatus = Literal["idle", "working", "completed", "error"]


@dataclass
class OrchestrationPlan:
    operation: str
    agents: list[str] = field(default_factory=list)
    parallel: bool = False
    summary: str = ""


class Agent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.status: AgentStatus = "idle"

    @abstractmethod
    async def can_handle(self, text: str, intent: Intent) -> bool: ...

    @abstractmethod
    async def execute(self, text: str, intent: Intent, context: dict) -> str: ...


class ChatAgent(Agent):
    def __init__(self, service: AssistantService) -> None:
        super().__init__("chat")
        self.service = service

    async def can_handle(self, text: str, intent: Intent) -> bool:
        return intent.kind == IntentKind.CHAT

    async def execute(self, text: str, intent: Intent, context: dict) -> str:
        conversation_id = context.get("conversation_id", "default")
        history = context.get("history", [])
        return await self.service.respond(
            text,
            conversation_id=conversation_id,
            history_override=history,
            on_chunk=context.get("on_chunk"),
        )


class Orchestrator:
    def __init__(self, service: AssistantService, settings: Settings | None = None) -> None:
        self.service = service
        self.settings = settings or service.settings
        self.agents: dict[str, Agent] = {}
        self._activity_callback: Callable[[ActivityEvent], None] | None = None
        self._request_activity_callback: ContextVar[Callable[[ActivityEvent], None] | None] = (
            ContextVar("noite_orchestrator_activity_callback", default=None)
        )
        self._action_handlers: dict[IntentKind, Callable[[Intent], Awaitable[str]]] = {}
        self.register_agent(ChatAgent(self.service))
        self._max_iterations = getattr(self.settings, "max_orchestration_iterations", 5)
        self._timeout_seconds = getattr(self.settings, "orchestration_timeout_seconds", 60)

    def set_max_iterations(self, n: int) -> None:
        """Define o número máximo de iterações para o orchestration."""
        if n < 1:
            raise ValueError("O limite de iterações deve ser pelo menos 1.")
        self._max_iterations = n

    def set_timeout(self, seconds: int) -> None:
        """Define o timeout máximo em segundos para o orchestration."""
        if seconds <= 0:
            raise ValueError("O timeout deve ser maior que zero.")
        self._timeout_seconds = seconds

    def register_action_handler(
        self, kind: IntentKind, handler: Callable[[Intent], Awaitable[str]]
    ) -> None:
        """Registra uma ação determinística executada antes de qualquer modelo."""
        self._action_handlers[kind] = handler

    def register_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent
        logger.info("Agente registrado: %s", agent.name)

    def set_activity_callback(self, callback: Callable[[ActivityEvent], None]) -> None:
        self._activity_callback = callback

    def _emit_activity(
        self,
        operation: str,
        state: ActivityState,
        summary: str,
        *,
        duration_ms: int | None = None,
        details: str = "",
    ) -> None:
        callback = self._request_activity_callback.get() or self._activity_callback
        if callback is None:
            return
        try:
            callback(
                make_activity_event(
                    operation,
                    state,
                    summary,
                    duration_ms=duration_ms,
                    details=details,
                )
            )
        except Exception:
            return

    def _plan(self, text: str, intent: Intent) -> OrchestrationPlan:
        category = classify_task(text)
        model_route = route_model(text, self.settings)
        # Usa o perfil configurado, evitando o antigo limite fixo de 8 GB de RAM.
        hardware = get_hardware_profile()
        model_compatible = is_model_compatible(
            self.settings.local_model,
            hardware["vram_gb"],
            hardware["system_ram_gb"],
        )
        if model_compatible is False:
            summary = f"Modelo {self.settings.local_model} acima do limite do hardware"
            self._emit_activity(
                "modelo",
                "warning",
                summary,
            )
        if model_route.provider == "glm":
            self._emit_activity(
                "roteamento",
                "info",
                "Tarefa auxiliar autorizada para o provedor GLM",
                details=model_route.reason,
            )
        agents = ["chat"]
        parallel = False
        summary = "Processando sua solicitação"
        if intent.kind == IntentKind.OPEN_APPLICATION:
            summary = "Abrindo o aplicativo solicitado"
        elif intent.kind == IntentKind.SEARCH_FILE:
            summary = "Pesquisando arquivos no workspace"
        return OrchestrationPlan(
            operation=category.value,
            agents=agents,
            parallel=parallel,
            summary=summary,
        )

    async def process_request(
        self,
        text: str,
        conversation_id: str = "default",
        history: list[tuple[str, str]] | None = None,
        on_activity: Callable[[ActivityEvent], None] | None = None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        token = self._request_activity_callback.set(on_activity)
        try:
            return await self._process_request_impl(text, conversation_id, history, on_chunk)
        finally:
            self._request_activity_callback.reset(token)

    async def _process_request_impl(
        self,
        text: str,
        conversation_id: str,
        history: list[tuple[str, str]] | None,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        started_at = datetime.now().astimezone()
        self._emit_activity(
            "orquestrador",
            "started",
            "Recebendo solicitação",
            details=text[:80],
        )

        try:
            intent = route(text)
        except ValueError as exc:
            self._emit_activity(
                "orquestrador",
                "failed",
                "Solicitação inválida",
                details=str(exc),
            )
            raise

        # Hide and close share one intent kind; the registered handler
        # distinguishes the requested action using intent.parameters.
        action_handler = self._action_handlers.get(intent.kind)
        if action_handler is not None:
            self._emit_activity(
                "acao_deterministica",
                "started",
                "Executando ação direta",
                details=intent.kind.value,
            )
            try:
                async with asyncio.timeout(self._timeout_seconds):
                    answer = await action_handler(intent)
            except TimeoutError:
                self._emit_activity(
                    "acao_deterministica",
                    "failed",
                    "Ação excedeu o tempo limite",
                    details=f"Timeout de {self._timeout_seconds}s",
                )
                raise
            except Exception as exc:
                self._emit_activity(
                    "acao_deterministica",
                    "failed",
                    "Ação direta falhou",
                    details=type(exc).__name__,
                )
                raise
            self._emit_activity(
                "acao_deterministica",
                "completed",
                "Ação direta concluída",
                details=intent.kind.value,
            )
            return answer

        plan = self._plan(text, intent)
        self._emit_activity(
            "orquestrador",
            "started",
            plan.summary,
            details=f"Agentes: {', '.join(plan.agents)}",
        )

        agent = self.agents.get(plan.agents[0])
        if agent is None:
            agent = self.agents.get("chat")

        if len(plan.agents) > self._max_iterations:
            raise RuntimeError(f"O plano excede o limite de {self._max_iterations} etapas/agentes.")
        context = {
            "conversation_id": conversation_id,
            "history": history or [],
            "intent": intent,
            "plan": plan,
            "max_iterations": self._max_iterations,
            "on_chunk": on_chunk,
        }

        try:
            async with asyncio.timeout(self._timeout_seconds):
                if plan.parallel and len(plan.agents) > 1:
                    answer = await self._run_parallel(text, intent, context, plan)
                else:
                    self._emit_activity(
                        "agente",
                        "started",
                        f"Agente {agent.name} executando",
                    )
                    answer = await agent.execute(text, intent, context)
                    self._emit_activity(
                        "agente",
                        "completed",
                        f"Agente {agent.name} concluiu",
                    )
        except TimeoutError:
            self._emit_activity(
                "orquestrador",
                "failed",
                "Tempo limite da orquestração excedido",
                details=f"Timeout de {self._timeout_seconds}s",
            )
            raise
        except asyncio.CancelledError:
            self._emit_activity(
                "orquestrador",
                "cancelled",
                "Orquestração cancelada",
            )
            raise
        except Exception as exc:
            logger.error("Orchestrator failed (%s)", type(exc).__name__)
            self._emit_activity(
                "orquestrador",
                "failed",
                "Falha na orquestração",
                details=f"{type(exc).__name__}",
            )
            raise

        elapsed = int((datetime.now().astimezone() - started_at).total_seconds() * 1000)
        self._emit_activity(
            "orquestrador",
            "completed",
            "Tarefa concluída",
            duration_ms=elapsed,
        )
        return answer

    async def _run_parallel(
        self,
        text: str,
        intent: Intent,
        context: dict,
        plan: OrchestrationPlan,
    ) -> str:
        self._emit_activity(
            "subagentes",
            "started",
            f"Iniciando {len(plan.agents)} subagentes em paralelo",
        )

        async def _run_one(agent_name: str) -> str:
            agent = self.agents.get(agent_name)
            if agent is None:
                return f"[{agent_name}: não disponível]"
            self._emit_activity(
                "subagente",
                "started",
                f"Subagente {agent.name} trabalhando",
            )
            try:
                result = await agent.execute(text, intent, context)
                self._emit_activity(
                    "subagente",
                    "completed",
                    f"Subagente {agent.name} finalizado",
                )
                return result
            except Exception as exc:
                self._emit_activity(
                    "subagente",
                    "error",
                    f"Subagente {agent.name} falhou",
                    details=str(exc)[:80],
                )
                return f"[{agent_name}: erro - {type(exc).__name__}]"

        results = await asyncio.gather(
            *(_run_one(name) for name in plan.agents),
            return_exceptions=False,
        )

        consolidated = "\n".join(
            f"• {name}: {result}" for name, result in zip(plan.agents, results)
        )
        self._emit_activity(
            "subagentes",
            "completed",
            f"{len(plan.agents)} subagentes concluídos",
        )
        return consolidated
