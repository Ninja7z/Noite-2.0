"""Small, UI-agnostic activity events shared by the assistant and desktop UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import uuid4

ActivityState = Literal["started", "completed", "failed", "cancelled"]


@dataclass(frozen=True)
class ActivityEvent:
    event_id: str
    operation: str
    state: ActivityState
    summary: str
    occurred_at: datetime
    duration_ms: int | None = None
    details: str = ""


def make_activity_event(
    operation: str,
    state: ActivityState,
    summary: str,
    *,
    duration_ms: int | None = None,
    details: str = "",
) -> ActivityEvent:
    """Create an event without capturing prompts, file contents, or credentials."""
    return ActivityEvent(
        event_id=uuid4().hex,
        operation=operation,
        state=state,
        summary=summary,
        occurred_at=datetime.now().astimezone(),
        duration_ms=duration_ms,
        details=details,
    )
