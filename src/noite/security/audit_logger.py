from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import ActionRequest, PolicyDecision


class AuditLogger:
    """Structured security audit; raw tool arguments and secrets are never stored."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS security_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    execution_status TEXT NOT NULL DEFAULT 'not_started',
                    error_type TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(security_audit)")
            }
            if "execution_status" not in columns:
                connection.execute(
                    "ALTER TABLE security_audit ADD COLUMN execution_status "
                    "TEXT NOT NULL DEFAULT 'not_started'"
                )
            if "error_type" not in columns:
                connection.execute(
                    "ALTER TABLE security_audit ADD COLUMN error_type TEXT NOT NULL DEFAULT ''"
                )

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def record(self, request: ActionRequest, decision: PolicyDecision) -> int:
        """Persist one decision and return the audit row id for status updates."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO security_audit (
                    request_id, created_at, actor, tool, capability, operation,
                    resource, risk, decision, reason, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id,
                    request.created_at.isoformat(),
                    request.actor[:80],
                    request.tool[:100],
                    request.capability.value,
                    request.operation[:100],
                    request.resource[:500],
                    request.risk.value,
                    decision.decision.value,
                    decision.reason[:300],
                    decision.fingerprint,
                ),
            )
            return int(cursor.lastrowid or 0)

    def record_execution_result(
        self,
        request: ActionRequest,
        *,
        succeeded: bool | None = None,
        status: str | None = None,
        error_type: str = "",
        audit_id: int | None = None,
    ) -> None:
        """Update the execution status of one attempt.

        `audit_id` comes from `record()`. Without it we fall back to the newest
        allowed row for the request, which is ambiguous when the same request is
        retried; callers in the guard always pass the id.
        """
        if status is None:
            status = "succeeded" if succeeded else "failed"
        if status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("Invalid audit execution status.")
        with self._connect() as connection:
            if audit_id is not None:
                connection.execute(
                    "UPDATE security_audit SET execution_status = ?, error_type = ? WHERE id = ?",
                    (status, error_type[:100], audit_id),
                )
                return
            connection.execute(
                """
                UPDATE security_audit
                SET execution_status = ?, error_type = ?
                WHERE id = (
                    SELECT id FROM security_audit
                    WHERE request_id = ? AND decision = 'allow'
                    ORDER BY id DESC LIMIT 1
                )
                """,
                (status, error_type[:100], request.request_id),
            )

    def recent(self, limit: int = 100) -> list[dict[str, str]]:
        bounded = max(1, min(int(limit), 500))
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM security_audit ORDER BY id DESC LIMIT ?", (bounded,)
            ).fetchall()
        return [dict(row) for row in rows]
