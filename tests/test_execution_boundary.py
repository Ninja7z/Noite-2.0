"""Impõe a fronteira de execução declarada em `docs/ADR/003-tool-authorization.md`.

Regra: fora do `noite.security`, nenhum módulo chama executor de ferramenta nem
constrói as peças de autorização. As exceções abaixo são dívida declarada e
devem encolher; este teste falha se uma nova aparecer.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from noite.security import (
    ActionRequest,
    Capability,
    DecisionKind,
    GuardedTools,
    PermissionProfile,
    RiskLevel,
    ToolDenied,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "src" / "noite", ROOT / "integrations")

EXECUTOR_CALLS = {
    "run_terminal_command",
    "save_workspace_text",
    "create_workspace_file",
    "create_workspace_directory",
}
EXECUTOR_ALLOWED = {
    "security/dispatch.py": "caminho único autorizado (PR 002)",
    "terminal.py": "definição do executor",
    "workspace.py": "definição do executor",
    "ide.py": "legado: migra com ADR-006 fatia 1/2 (PR 006)",
}

GUARD_COMPONENTS = {
    "ToolGuard",
    "PolicyEngine",
    "ApprovalManager",
    "AuditLogger",
    "PermissionManager",
}
GUARD_ALLOWED_PREFIX = "security/"

SUBPROCESS_ALLOWED = {
    "terminal.py": "executor do guard (Windows Job Object)",
    "assistant.py": "ollama serve pedido explicitamente pelo usuário",
    "ui.py": "subprocess.list2cmdline: formatação de texto, não execução",
    "integrations/openwebui/noite_api.py": "abre o processo do mascote",
}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def _relative(path: Path) -> str:
    for base in (ROOT / "src" / "noite", ROOT):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _scan(names: set[str]) -> set[str]:
    hits: set[str] = set()
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if names & _called_names(tree):
            hits.add(_relative(path))
    return hits


def test_only_the_authorized_path_calls_tool_executors():
    offenders = _scan(EXECUTOR_CALLS) - set(EXECUTOR_ALLOWED)
    assert not offenders, (
        "Executores chamados fora do caminho autorizado: "
        + ", ".join(sorted(offenders))
        + ". Use noite.security.GuardedTools."
    )


def test_executor_exceptions_are_the_documented_ones():
    found = _scan(EXECUTOR_CALLS) - {"security/dispatch.py", "terminal.py", "workspace.py"}
    expected = set(EXECUTOR_ALLOWED) - {"security/dispatch.py", "terminal.py", "workspace.py"}
    assert found == expected, f"Exceções de executor mudaram: {sorted(found)} != {sorted(expected)}"


def test_only_the_security_package_constructs_guard_components():
    offenders = sorted(
        file for file in _scan(GUARD_COMPONENTS) if not file.startswith(GUARD_ALLOWED_PREFIX)
    )
    assert not offenders, (
        "Peças de autorização construídas fora de noite.security: " + ", ".join(offenders)
    )


def test_subprocess_usage_is_inventoried():
    unexpected = _scan({"Popen", "system", "startfile"}) - set(SUBPROCESS_ALLOWED)
    assert not unexpected, (
        "Novo ponto de execução de processo sem decisão de arquitetura: "
        + ", ".join(sorted(unexpected))
        + ". Atualize docs/SECURITY_ARCHITECTURE.md e este allowlist."
    )


# --- comportamento do caminho único -------------------------------------


def _grant(tools: GuardedTools, *capabilities: Capability) -> None:
    tools.permissions.save_from_user(PermissionProfile.FULL, set(capabilities))


def test_guarded_tools_denies_by_default(tmp_path):
    tools = GuardedTools(tmp_path)
    request = ActionRequest(
        actor="test",
        tool="test-tool",
        capability=Capability.TERMINAL,
        operation="run",
        resource="workspace",
        arguments={"value": "ok"},
        risk=RiskLevel.R1,
    )
    assert tools.evaluate(request).decision == DecisionKind.DENY
    with pytest.raises(ToolDenied):
        tools.execute(request, lambda **kwargs: "should not run")


def test_granted_safe_command_runs_without_approval(tmp_path):
    tools = GuardedTools(tmp_path)
    _grant(tools, Capability.TERMINAL)
    request = tools.terminal_request("Get-Location", tmp_path, advanced=False)
    assert tools.evaluate(request).decision == DecisionKind.ALLOW
    assert tools.execute(request, lambda **kwargs: kwargs["command"]) == "Get-Location"


def test_advanced_terminal_requires_single_use_approval(tmp_path):
    tools = GuardedTools(tmp_path)
    _grant(tools, Capability.TERMINAL)
    request = tools.terminal_request("Write-Output oi", tmp_path, advanced=True)
    assert tools.evaluate(request).decision == DecisionKind.REQUIRE_APPROVAL
    with pytest.raises(ToolDenied):
        tools.execute(request, lambda **kwargs: "should not run")
    token = tools.approve_from_ui(request)
    assert tools.execute(request, lambda **kwargs: "ran", approval_token=token) == "ran"
    with pytest.raises(ToolDenied):
        tools.execute(request, lambda **kwargs: "again", approval_token=token)


def test_approval_is_bound_to_the_exact_command(tmp_path):
    tools = GuardedTools(tmp_path)
    _grant(tools, Capability.TERMINAL)
    approved = tools.terminal_request("Write-Output permitido", tmp_path, advanced=True)
    token = tools.approve_from_ui(approved)
    other = tools.terminal_request("Remove-Item dados.txt", tmp_path, advanced=True)
    with pytest.raises(ToolDenied):
        tools.execute(other, lambda **kwargs: "should not run", approval_token=token)


def test_revoked_capability_beats_a_previous_approval(tmp_path):
    tools = GuardedTools(tmp_path)
    _grant(tools, Capability.TERMINAL)
    request = tools.terminal_request("Write-Output oi", tmp_path, advanced=True)
    token = tools.approve_from_ui(request)
    tools.permissions.save_from_user(PermissionProfile.NONE, set())
    with pytest.raises(ToolDenied):
        tools.execute(request, lambda **kwargs: "should not run", approval_token=token)
