from __future__ import annotations

import threading

import pytest

from noite.terminal import (
    TerminalCommandError,
    _safe_environment,
    run_terminal_command,
    validate_terminal_command,
)


def test_safe_terminal_rejects_shell_chaining_and_unknown_commands():
    assert validate_terminal_command("Get-ChildItem") == "Get-ChildItem"
    with pytest.raises(TerminalCommandError, match="encadeamento"):
        validate_terminal_command("Get-ChildItem; Remove-Item file.txt")
    with pytest.raises(TerminalCommandError, match="lista segura"):
        validate_terminal_command("Remove-Item file.txt")
    with pytest.raises(TerminalCommandError, match="lista segura"):
        validate_terminal_command("python -c 'print(1)'")


def test_safe_terminal_rejects_powershell_subexpressions_and_escape_paths(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("outside workspace", encoding="utf-8")
    with pytest.raises(TerminalCommandError):
        validate_terminal_command("Get-Content $(Get-Location)", cwd=tmp_path)
    with pytest.raises(TerminalCommandError, match="workspace"):
        validate_terminal_command(f"Get-Content ..\\{outside.name}", cwd=tmp_path)


@pytest.mark.parametrize(
    "command",
    [
        "Get-Content $(Get-Location)",
        "Get-Content ${env:PATH}",
        "Get-Content file.txt; Remove-Item file.txt",
        "{ Remove-Item file.txt }",
        "powershell.exe -EncodedCommand SQBFAFgA",
        "iex 'Remove-Item file.txt'",
        "Invoke-Expression 'Remove-Item file.txt'",
        "Start-Process powershell -ArgumentList '-EncodedCommand SQBFAFgA'",
        "ri file.txt",
        "Get-Content file.txt > output.txt",
        "Get-Content \"$(Get-Location)\"",
    ],
)
def test_powershell_ast_rejects_compound_and_obfuscated_commands(command):
    with pytest.raises(TerminalCommandError):
        validate_terminal_command(command, advanced=True)


def test_safe_terminal_allowlist_rejects_destructive_aliases():
    for command in ("ri file.txt", "del file.txt", "erase file.txt"):
        with pytest.raises(TerminalCommandError):
            validate_terminal_command(command)


def test_advanced_terminal_requires_explicit_mode():
    with pytest.raises(TerminalCommandError):
        validate_terminal_command("Write-Output ready")
    assert validate_terminal_command("Write-Output ready", advanced=True)


def test_advanced_terminal_allows_literal_pipelines_but_not_script_blocks():
    assert validate_terminal_command(
        "Get-ChildItem | Select-Object Name", advanced=True
    ) == "Get-ChildItem | Select-Object Name"
    with pytest.raises(TerminalCommandError):
        validate_terminal_command("Get-ChildItem | ForEach-Object { $_.Name }", advanced=True)


def test_terminal_environment_omits_api_and_database_secrets(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "private-key")
    monkeypatch.setenv("DB_PASSWORD", "private-password")

    environment = _safe_environment()

    assert "ZAI_API_KEY" not in environment
    assert "DB_PASSWORD" not in environment


def test_terminal_runs_in_workspace_and_returns_real_exit_code(tmp_path):
    result = run_terminal_command("Get-Location", tmp_path)
    assert result.exit_code == 0
    assert str(tmp_path).casefold() in result.output.casefold()
    assert result.cwd == tmp_path.resolve()
    assert result.duration_ms >= 0


def test_terminal_can_cancel_an_active_process(tmp_path):
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    result = run_terminal_command(
        "Start-Sleep -Seconds 5", tmp_path, advanced=True, cancel_event=cancel
    )
    timer.join(timeout=1)
    assert result.cancelled


def test_terminal_timeout_kills_job_tree(tmp_path):
    result = run_terminal_command(
        "Start-Sleep -Seconds 5", tmp_path, advanced=True, timeout_seconds=1
    )
    assert result.timed_out
    assert result.duration_ms < 4000


def test_terminal_output_is_capped_and_nonzero_exit_is_returned(tmp_path):
    large_file = tmp_path / "large.txt"
    large_file.write_text("x" * 205_000, encoding="utf-8")
    result = run_terminal_command(
        "Get-Content large.txt | Out-String", tmp_path, advanced=True
    )
    assert result.truncated
    assert len(result.output.encode("utf-8")) <= 205_000

    nonzero = run_terminal_command(
        "Get-Content missing.txt -ErrorAction Stop", tmp_path, advanced=True
    )
    assert nonzero.exit_code != 0
