from __future__ import annotations

from .approval_manager import ApprovalManager
from .models import (
    ActionRequest,
    DecisionKind,
    PolicyDecision,
    RiskLevel,
)
from .permission_manager import PermissionManager

_APPROVAL_RISK = {RiskLevel.R2, RiskLevel.R3}


class PolicyEngine:
    """Deterministic policy decision point. Errors and unknown capabilities fail closed."""

    def __init__(self, permissions: PermissionManager) -> None:
        self.permissions = permissions

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        fingerprint = request.fingerprint()
        if not self.permissions.is_enabled(request.capability):
            return PolicyDecision(
                decision=DecisionKind.DENY,
                reason=f"Permissão não concedida: {request.capability.value}",
                request_id=request.request_id,
                fingerprint=fingerprint,
            )
        if request.risk in _APPROVAL_RISK:
            return PolicyDecision(
                decision=DecisionKind.REQUIRE_APPROVAL,
                reason=f"A operação exige confirmação humana ({request.risk.value}).",
                request_id=request.request_id,
                fingerprint=fingerprint,
            )
        return PolicyDecision(
            decision=DecisionKind.ALLOW,
            reason="Permissão concedida pela política local.",
            request_id=request.request_id,
            fingerprint=fingerprint,
        )

    def authorize(
        self,
        request: ActionRequest,
        approval_token: str | None = None,
        approvals: ApprovalManager | None = None,
        session_id: str | None = None,
    ) -> PolicyDecision:
        decision = self.evaluate(request)
        if decision.decision != DecisionKind.REQUIRE_APPROVAL:
            return decision
        if approvals is not None and approvals.consume(request, approval_token, session_id or ""):
            return PolicyDecision(
                decision=DecisionKind.ALLOW,
                reason="Ação aprovada pelo usuário para esta solicitação exata.",
                request_id=request.request_id,
                fingerprint=request.fingerprint(),
            )
        return decision
