from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from .models import ActionRequest


@dataclass(frozen=True)
class ApprovalGrant:
    token: str
    fingerprint: str
    expires_at: float
    session_id: str  # Bind approval to originating session


class ApprovalManager:
    """Single-use, short-lived approval bound to one exact action fingerprint and session."""

    def __init__(self, ttl_seconds: int = 90) -> None:
        self.ttl_seconds = max(10, min(ttl_seconds, 300))
        self._grants: dict[str, ApprovalGrant] = {}

    def approve_from_ui(self, request: ActionRequest, session_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        self._prune(now)
        self._grants[token] = ApprovalGrant(
            token=token,
            fingerprint=request.fingerprint(),
            expires_at=now + self.ttl_seconds,
            session_id=session_id,
        )
        return token

    def _prune(self, now: float) -> None:
        """Drop expired grants so unused approvals cannot accumulate."""
        expired = [token for token, grant in self._grants.items() if grant.expires_at < now]
        for token in expired:
            self._grants.pop(token, None)

    def consume(self, request: ActionRequest, token: str | None, session_id: str) -> bool:
        if not token:
            return False
        grant = self._grants.pop(token, None)
        return bool(
            grant
            and grant.expires_at >= time.monotonic()
            and secrets.compare_digest(grant.fingerprint, request.fingerprint())
            and grant.session_id == session_id
        )

    def revoke_all(self) -> None:
        self._grants.clear()
