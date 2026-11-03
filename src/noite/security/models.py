from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PermissionProfile(StrEnum):
    NONE = "none"
    RESTRICTED = "restricted"
    FULL = "full"


class Capability(StrEnum):
    FILE_READ = "files.read"
    FILE_WRITE = "files.write"
    FILE_DELETE = "files.delete"
    TERMINAL = "terminal.execute"
    APPLICATIONS = "applications.control"
    NETWORK = "network.access"
    MCP = "mcp.call"


class RiskLevel(StrEnum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class DecisionKind(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    actor: str = "assistant"
    tool: str = Field(min_length=1, max_length=100)
    capability: Capability
    operation: str = Field(min_length=1, max_length=100)
    resource: str = Field(default="", max_length=2048)
    arguments: dict = Field(default_factory=dict)
    risk: RiskLevel = RiskLevel.R0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def fingerprint(self) -> str:
        payload = {
            "actor": self.actor,
            "tool": self.tool,
            "capability": self.capability.value,
            "operation": self.operation,
            "resource": self.resource,
            "arguments": self.arguments,
            "risk": self.risk.value,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: DecisionKind
    reason: str
    request_id: str
    fingerprint: str
