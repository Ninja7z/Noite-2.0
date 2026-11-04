from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Capability, PermissionProfile

# Single source of truth for the read/write-only profile used by the core and the UI.
RESTRICTED_CAPABILITIES = frozenset({Capability.FILE_READ, Capability.FILE_WRITE})


class PermissionManager:
    """User-owned permission state. LLM-facing code must never receive this object."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)
        self.profile = PermissionProfile.NONE
        self.enabled: set[Capability] = set()
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.profile = PermissionProfile(payload.get("profile", "none"))
            raw = payload.get("enabled", [])
            self.enabled = {
                Capability(item)
                for item in raw
                if item in Capability._value2member_map_
            }
            if self.profile == PermissionProfile.NONE:
                self.enabled.clear()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.profile = PermissionProfile.NONE
            self.enabled = set()

    def is_enabled(self, capability: Capability) -> bool:
        if self.profile == PermissionProfile.NONE:
            return False
        if self.profile == PermissionProfile.RESTRICTED:
            return capability in self.enabled and capability in RESTRICTED_CAPABILITIES
        return capability in self.enabled

    def save_from_user(
        self, profile: PermissionProfile, enabled: set[Capability]
    ) -> None:
        """Persist settings only when called by a trusted UI/controller boundary."""
        normalized = set(enabled)
        if profile == PermissionProfile.NONE:
            normalized.clear()
        elif profile == PermissionProfile.RESTRICTED:
            normalized.intersection_update(RESTRICTED_CAPABILITIES)
        payload = {
            "schema_version": 1,
            "profile": profile.value,
            "enabled": sorted(item.value for item in normalized),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".permissions-", suffix=".tmp", dir=self.config_path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.config_path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        self.profile = profile
        self.enabled = normalized
