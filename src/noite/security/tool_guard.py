from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from .approval_manager import ApprovalManager
from .audit_logger import AuditLogger
from .models import ActionRequest, DecisionKind, PolicyDecision
from .policy_engine import PolicyEngine


class ToolDenied(PermissionError):
    pass


class ToolGuard:
    """The only supported path from an agent tool request to a tool executor."""

    def __init__(
        self,
        policy: PolicyEngine,
        approvals: ApprovalManager,
        audit: AuditLogger,
    ) -> None:
        self.policy = policy
        self.approvals = approvals
        self.audit = audit

    def execute(
        self,
        request: ActionRequest,
        executor: Callable[..., Any],
        *,
        approval_token: str | None = None,
    ) -> Any:
        decision = self.policy.authorize(request, approval_token, self.approvals)
        audit_id = self.audit.record(request, decision)
        if decision.decision != DecisionKind.ALLOW:
            raise ToolDenied(decision.reason)

        # Re-check immediately before dispatch so revocation beats an old approval.
        if not self.policy.permissions.is_enabled(request.capability):
            revoked = PolicyDecision(
                decision=DecisionKind.DENY,
                reason="A permissão foi revogada antes da execução.",
                request_id=request.request_id,
                fingerprint=request.fingerprint(),
            )
            self.audit.record(request, revoked)
            raise ToolDenied(revoked.reason)

        try:
            result = executor(**request.arguments)
        except Exception as exc:
            self.audit.record_execution_result(
                request, succeeded=False, error_type=type(exc).__name__, audit_id=audit_id
            )
            raise

        if inspect.isawaitable(result):
            return self._await_and_record(result, request, audit_id)
        self.audit.record_execution_result(request, succeeded=True, audit_id=audit_id)
        return result

    async def _await_and_record(
        self, result: Any, request: ActionRequest, audit_id: int | None = None
    ) -> Any:
        try:
            value = await result
        except Exception as exc:
            self.audit.record_execution_result(
                request, succeeded=False, error_type=type(exc).__name__, audit_id=audit_id
            )
            raise
        self.audit.record_execution_result(request, succeeded=True, audit_id=audit_id)
        return value
