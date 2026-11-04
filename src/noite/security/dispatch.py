"""Single authorized path from an intent to any tool executor.

Nothing in the UI or the agent layer may call an executor directly: they build an
`ActionRequest`, ask this facade for a decision, obtain an approval when the policy
requires one, and only then let the guard dispatch the call.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .approval_manager import ApprovalManager
from .audit_logger import AuditLogger
from .models import ActionRequest, Capability, PolicyDecision, RiskLevel
from .permission_manager import PermissionManager
from .policy_engine import PolicyEngine
from .tool_guard import ToolGuard

DEFAULT_TERMINAL_TIMEOUT = 120


class GuardedTools:
    """Owns the only ToolGuard instance used by the application."""

    def __init__(self, data_dir: Path, *, actor: str = "user") -> None:
        security_dir = Path(data_dir) / "security"
        self.permissions = PermissionManager(security_dir / "permissions.json")
        self.approvals = ApprovalManager()
        self.audit = AuditLogger(security_dir / "audit.sqlite3")
        self.guard = ToolGuard(PolicyEngine(self.permissions), self.approvals, self.audit)
        self.actor = actor
        # Session ID for approval binding - generated once per application session
        self._session_id = secrets.token_urlsafe(16)

    @property
    def session_id(self) -> str:
        return self._session_id

    # --- policy plumbing -------------------------------------------------
    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        self.permissions.reload()
        return self.guard.policy.evaluate(request)

    def record(self, request: ActionRequest, decision: PolicyDecision) -> None:
        """Persist a decision that will not be dispatched (denial, cancellation)."""
        self.audit.record(request, decision)

    def approve_from_ui(self, request: ActionRequest) -> str:
        """Only a trusted UI flow may call this, after explicit user confirmation."""
        return self.approvals.approve_from_ui(request, self._session_id)

    def execute(
        self,
        request: ActionRequest,
        executor: Callable[..., Any],
        *,
        approval_token: str | None = None,
    ) -> Any:
        # Refresh before dispatch so a permission revoked while the approval dialog
        # was open is honoured (the guard also re-checks right before the call).
        self.permissions.reload()
        return self.guard.execute(
            request,
            executor,
            approval_token=approval_token,
            session_id=self._session_id,
        )

    # --- typed operations ------------------------------------------------
    def terminal_request(self, command: str, cwd: Path, *, advanced: bool) -> ActionRequest:
        return ActionRequest(
            actor=self.actor,
            tool="terminal",
            capability=Capability.TERMINAL,
            operation="run_advanced" if advanced else "run_safe",
            resource=str(Path(cwd)),
            arguments={"command": command, "cwd": str(cwd), "advanced": advanced},
            # Advanced mode can run anything the user typed; safe mode is read-only.
            risk=RiskLevel.R2 if advanced else RiskLevel.R1,
        )

    def run_terminal(
        self,
        command: str,
        cwd: Path,
        *,
        advanced: bool = False,
        approval_token: str | None = None,
        timeout_seconds: int = DEFAULT_TERMINAL_TIMEOUT,
        cancel_event: Any = None,
        on_output: Callable[[str], None] | None = None,
    ) -> Any:
        from ..terminal import run_terminal_command

        request = self.terminal_request(command, cwd, advanced=advanced)
        return self.execute(
            request,
            lambda **arguments: run_terminal_command(
                arguments["command"],
                Path(arguments["cwd"]),
                advanced=arguments["advanced"],
                timeout_seconds=timeout_seconds,
                cancel_event=cancel_event,
                on_output=on_output,
            ),
            approval_token=approval_token,
        )

    def mcp_request(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> ActionRequest:
        return ActionRequest(
            actor=self.actor,
            tool="mcp",
            capability=Capability.MCP,
            operation="call_tool",
            resource=f"{server_name}/{tool_name}",
            arguments=arguments,
            risk=RiskLevel.R2,
        )
