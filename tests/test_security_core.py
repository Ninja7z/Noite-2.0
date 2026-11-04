from __future__ import annotations

import pytest

from noite.security import (
    ActionRequest,
    ApprovalManager,
    AuditLogger,
    Capability,
    DecisionKind,
    PermissionManager,
    PermissionProfile,
    PolicyEngine,
    RiskLevel,
    ToolDenied,
    ToolGuard,
    resolve_allowed_path,
)


def _request(risk=RiskLevel.R0):
    return ActionRequest(
        actor="test-agent",
        tool="workspace.read",
        capability=Capability.FILE_READ,
        operation="read",
        resource="notes.txt",
        arguments={"value": "safe"},
        risk=risk,
    )


def test_permissions_default_to_no_access(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    assert manager.profile == PermissionProfile.NONE
    assert not manager.is_enabled(Capability.FILE_READ)


def test_none_profile_clears_all_capabilities(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    manager.save_from_user(PermissionProfile.NONE, {Capability.FILE_READ})
    reloaded = PermissionManager(manager.config_path)
    assert reloaded.profile == PermissionProfile.NONE
    assert not reloaded.enabled


def test_restricted_permissions_are_explicit_and_persisted(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.RESTRICTED, {Capability.FILE_READ})
    reloaded = PermissionManager(manager.config_path)
    assert reloaded.is_enabled(Capability.FILE_READ)
    assert not reloaded.is_enabled(Capability.TERMINAL)


def test_restricted_profile_cannot_enable_terminal_even_if_config_is_tampered(tmp_path):
    path = tmp_path / "permissions.json"
    path.write_text(
        '{"schema_version":1,"profile":"restricted","enabled":["terminal.execute"]}',
        encoding="utf-8",
    )
    manager = PermissionManager(path)
    assert not manager.is_enabled(Capability.TERMINAL)


def test_policy_denies_ungranted_capability(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    decision = PolicyEngine(manager).evaluate(_request())
    assert decision.decision == DecisionKind.DENY


def test_low_risk_action_is_allowed_when_capability_is_enabled(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.RESTRICTED, {Capability.FILE_READ})
    decision = PolicyEngine(manager).evaluate(_request())
    assert decision.decision == DecisionKind.ALLOW


def test_high_risk_action_requires_approval(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    decision = PolicyEngine(manager).evaluate(_request(RiskLevel.R2))
    assert decision.decision == DecisionKind.REQUIRE_APPROVAL


def test_approval_is_bound_to_exact_arguments_and_single_use():
    approvals = ApprovalManager()
    request = _request(RiskLevel.R2)
    session_id = "test-session"
    token = approvals.approve_from_ui(request, session_id)
    changed = request.model_copy(update={"arguments": {"value": "different"}})
    assert not approvals.consume(changed, token, session_id)
    assert not approvals.consume(request, token, session_id)


def test_approval_token_is_single_use():
    approvals = ApprovalManager()
    request = _request(RiskLevel.R2)
    session_id = "test-session"
    token = approvals.approve_from_ui(request, session_id)
    assert approvals.consume(request, token, session_id)
    assert not approvals.consume(request, token, session_id)


def test_tool_guard_blocks_before_executor_when_not_authorized(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    approvals = ApprovalManager()
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    guard = ToolGuard(PolicyEngine(manager), approvals, audit)
    called = []
    with pytest.raises(ToolDenied):
        guard.execute(_request(), lambda **kwargs: called.append(kwargs))
    assert called == []
    assert audit.recent()[0]["decision"] == "deny"


def test_tool_guard_executes_authorized_low_risk_action(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.RESTRICTED, {Capability.FILE_READ})
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    guard = ToolGuard(PolicyEngine(manager), ApprovalManager(), audit)
    assert guard.execute(_request(), lambda **kwargs: kwargs["value"]) == "safe"
    assert audit.recent()[0]["execution_status"] == "succeeded"


def test_tool_guard_records_async_executor_result(tmp_path):
    import asyncio

    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.RESTRICTED, {Capability.FILE_READ})
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    guard = ToolGuard(PolicyEngine(manager), ApprovalManager(), audit)

    async def executor(**kwargs):
        await asyncio.sleep(0)
        return kwargs["value"]

    result = asyncio.run(guard.execute(_request(), executor))
    assert result == "safe"
    assert audit.recent()[0]["execution_status"] == "succeeded"


def test_tool_guard_requires_exact_human_approval_for_high_risk(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    approvals = ApprovalManager()
    guard = ToolGuard(
        PolicyEngine(manager), approvals, AuditLogger(tmp_path / "audit.sqlite3")
    )
    request = _request(RiskLevel.R2)
    session_id = "test-session"
    with pytest.raises(ToolDenied):
        guard.execute(request, lambda **kwargs: "should not run", session_id=session_id)
    token = approvals.approve_from_ui(request, session_id)
    assert (
        guard.execute(
            request, lambda **kwargs: "approved", approval_token=token, session_id=session_id
        )
        == "approved"
    )


def test_revoked_permission_blocks_even_after_approval(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    approvals = ApprovalManager()
    guard = ToolGuard(
        PolicyEngine(manager), approvals, AuditLogger(tmp_path / "audit.sqlite3")
    )
    request = _request(RiskLevel.R2)
    session_id = "test-session"
    token = approvals.approve_from_ui(request, session_id)
    manager.save_from_user(PermissionProfile.NONE, set())
    with pytest.raises(ToolDenied):
        guard.execute(
            request,
            lambda **kwargs: "should not run",
            approval_token=token,
            session_id=session_id,
        )


def test_audit_does_not_store_raw_arguments(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    request = _request()
    decision = PolicyEngine(manager).evaluate(request)
    audit.record(request, decision)
    row = audit.recent()[0]
    assert "safe" not in str(row)
    assert row["fingerprint"] == request.fingerprint()


def test_path_guard_rejects_traversal_and_accepts_workspace_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("hello", encoding="utf-8")
    assert resolve_allowed_path(workspace, "notes.txt").name == "notes.txt"
    with pytest.raises(ValueError):
        resolve_allowed_path(workspace, "../outside.txt", must_exist=False)


def test_path_guard_rejects_symlink_when_supported(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("private", encoding="utf-8")
    link = workspace / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(ValueError, match="Links simbólicos"):
        resolve_allowed_path(workspace, "linked/secret.txt")


def test_expired_approvals_are_pruned(monkeypatch):
    import time

    from noite.security import approval_manager as approval_module

    approvals = ApprovalManager(ttl_seconds=10)
    request = _request(RiskLevel.R2)
    session_id = "test-session"
    stale = approvals.approve_from_ui(request, session_id)
    future = time.monotonic() + 3600
    monkeypatch.setattr(approval_module.time, "monotonic", lambda: future)

    fresh = approvals.approve_from_ui(request, session_id)

    assert len(approvals._grants) == 1
    assert not approvals.consume(request, stale, session_id)
    assert approvals.consume(request, fresh, session_id)


def test_profile_allows_uses_the_single_documented_order():
    from noite.security import PROFILE_ORDER, profile_allows

    assert PROFILE_ORDER == (
        PermissionProfile.NONE,
        PermissionProfile.RESTRICTED,
        PermissionProfile.FULL,
    )
    assert profile_allows(PermissionProfile.RESTRICTED, PermissionProfile.RESTRICTED)
    assert profile_allows(PermissionProfile.RESTRICTED, PermissionProfile.FULL)
    assert not profile_allows(PermissionProfile.FULL, PermissionProfile.RESTRICTED)
    assert not profile_allows(PermissionProfile.RESTRICTED, PermissionProfile.NONE)


def test_execution_status_is_recorded_per_attempt(tmp_path):
    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    guard = ToolGuard(PolicyEngine(manager), ApprovalManager(), audit)
    request = _request()

    def boom(**kwargs):
        raise RuntimeError("falha simulada")

    with pytest.raises(RuntimeError):
        guard.execute(request, boom)
    assert guard.execute(request, lambda **kwargs: "ok") == "ok"

    assert [row["execution_status"] for row in audit.recent()] == ["succeeded", "failed"]


def test_tool_guard_audits_async_cancellation(tmp_path):
    import asyncio

    manager = PermissionManager(tmp_path / "permissions.json")
    manager.save_from_user(PermissionProfile.FULL, {Capability.FILE_READ})
    audit = AuditLogger(tmp_path / "audit.sqlite3")
    guard = ToolGuard(PolicyEngine(manager), ApprovalManager(), audit)

    async def long_executor(**kwargs):
        await asyncio.sleep(30)

    async def run_and_cancel():
        task = asyncio.create_task(guard.execute(_request(), long_executor))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_and_cancel())
    assert audit.recent()[0]["execution_status"] == "cancelled"
