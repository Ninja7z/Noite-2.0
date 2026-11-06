"""Bounded, cancellable Windows terminal runner for explicit user commands."""

from __future__ import annotations

import ctypes
import os
import queue
import re
import subprocess
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT_BYTES = 200_000
DEFAULT_TIMEOUT_SECONDS = 120

# Strict allowlist of safe commands for non-advanced mode
_SAFE_COMMANDS = frozenset({
    "dir",
    "get-childitem",
    "get-content",
    "get-location",
    "select-string",
})

# Commands that are never allowed (even in advanced mode)
_BLOCKED_COMMANDS = frozenset({
    "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "cmd", "cmd.exe", "wscript", "wscript.exe",
    "cscript", "cscript.exe",
    "invoke-expression", "iex",
    "invoke-command", "icm",
    "start-process", "start", "saps",
    "remove-item", "ri", "rm", "del", "delete", "erase", "rmdir",
    "kill", "stop-process",
    "clear-content", "set-content", "add-content",
    "new-item", "copy-item", "move-item", "rename-item",
    "out-file", "export-*",
    "format",
})

# Parameters that are never allowed
_BLOCKED_PARAMETERS = frozenset({
    "encodedcommand", "encodedarguments", "command", "file", "executionpolicy",
})

# Safe token pattern for arguments (alphanumeric, underscore, dot, hyphen, slash)
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.\\/-]{1,260}$")

# PowerShell AST validator - uses stdin for source to avoid env var injection
_POWERSHELL_AST_VALIDATOR = r'''
$ErrorActionPreference = 'Stop'
$source = [Console]::In.ReadToEnd()
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput(
    $source,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -gt 0 -or $ast.EndBlock.Statements.Count -ne 1) { exit 2 }
$statement = $ast.EndBlock.Statements[0]
if ($statement -isnot [System.Management.Automation.Language.PipelineAst]) { exit 3 }
if ($statement.PipelineElements.Count -lt 1) { exit 4 }
$forbidden = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.ScriptBlockExpressionAst] -or
    $node -is [System.Management.Automation.Language.SubExpressionAst] -or
    $node -is [System.Management.Automation.Language.ExpandableStringExpressionAst] -or
    $node -is [System.Management.Automation.Language.VariableExpressionAst] -or
    $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -or
    $node -is [System.Management.Automation.Language.ArrayExpressionAst] -or
    $node -is [System.Management.Automation.Language.HashtableAst] -or
    $node -is [System.Management.Automation.Language.BinaryExpressionAst] -or
    $node -is [System.Management.Automation.Language.UnaryExpressionAst] -or
    $node -is [System.Management.Automation.Language.TypeExpressionAst] -or
    $node -is [System.Management.Automation.Language.IndexExpressionAst] -or
    $node -is [System.Management.Automation.Language.MemberExpressionAst] -or
    $node -is [System.Management.Automation.Language.ConvertExpressionAst] -or
    $node -is [System.Management.Automation.Language.AttributeAst]
}, $true)
if ($forbidden) { exit 7 }
$blockedCommands = @'
^(?i)(powershell(?:\.exe)?|pwsh(?:\.exe)?|cmd(?:\.exe)?|wscript(?:\.exe)?|
cscript(?:\.exe)?|invoke-expression|iex|invoke-command|icm|start-process|start|saps|ri|rm|kill)$
'@ -replace '\s', ''
$blockedParameters = '^(?i)(encodedcommand|encodedarguments|command|file|executionpolicy)$'
$names = [System.Collections.Generic.List[string]]::new()
foreach ($commandAst in $statement.PipelineElements) {
    if ($commandAst -isnot [System.Management.Automation.Language.CommandAst]) { exit 5 }
    if ($commandAst.Redirections.Count -gt 0) { exit 6 }
    foreach ($element in $commandAst.CommandElements) {
        $isLiteral = (
            $element -is [System.Management.Automation.Language.StringConstantExpressionAst] -or
            $element -is [System.Management.Automation.Language.ConstantExpressionAst] -or
            $element -is [System.Management.Automation.Language.CommandParameterAst]
        )
        if (-not $isLiteral) { exit 8 }
    }
    $name = $commandAst.GetCommandName()
    if ([string]::IsNullOrWhiteSpace($name)) { exit 9 }
    if ($name -match $blockedCommands) { exit 10 }
    $resolvedCommand = Get-Command -Name $name -ErrorAction SilentlyContinue
    if (
        $resolvedCommand -and $resolvedCommand.CommandType -eq 'Alias' -and $name -ne 'dir'
    ) { exit 12 }
    if ($commandAst.CommandElements | Where-Object {
        $_ -is [System.Management.Automation.Language.CommandParameterAst] -and
        $_.ParameterName -match $blockedParameters
    }) { exit 11 }
    $names.Add($name)
}
[Console]::Out.Write([string]::Join('|', $names))
'''


class TerminalCommandError(ValueError):
    pass


@dataclass(frozen=True)
class TerminalResult:
    command: str
    cwd: Path
    output: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False
    cancelled: bool = False
    truncated: bool = False


class _WindowsJob:
    """Own the PowerShell process tree and terminate descendants on close/cancel."""

    def __init__(self) -> None:
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        self._kernel.SetInformationJobObject.restype = wintypes.BOOL
        self._kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.INT,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        self._kernel.CloseHandle.restype = wintypes.BOOL
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.TerminateJobObject.restype = wintypes.BOOL
        self._kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self._kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel.OpenProcess.restype = wintypes.HANDLE
        self._kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.handle = self._kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        configured = self._kernel.SetInformationJobObject(
            self.handle,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )
        if not configured:
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "SetInformationJobObject failed")

    def assign(self, process_id: int) -> None:
        process = self._kernel.OpenProcess(0x0100 | 0x0001, False, process_id)
        if not process:
            raise OSError(ctypes.get_last_error(), "OpenProcess failed")
        try:
            if not self._kernel.AssignProcessToJobObject(self.handle, process):
                raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
        finally:
            self._kernel.CloseHandle(process)

    def terminate(self) -> None:
        if self.handle:
            self._kernel.TerminateJobObject(self.handle, 1)

    def close(self) -> None:
        if self.handle:
            self._kernel.CloseHandle(self.handle)
            self.handle = None


def _workspace_path(token: str, cwd: Path) -> Path:
    if not _SAFE_TOKEN.fullmatch(token) or token.startswith(("/", "\\", "-")):
        raise TerminalCommandError("Use um caminho relativo simples dentro do workspace.")
    candidate = (cwd / token).resolve(strict=True)
    try:
        candidate.relative_to(cwd)
    except ValueError as exc:
        raise TerminalCommandError("O caminho precisa permanecer dentro do workspace.") from exc
    return candidate


def _validate_powershell_ast(command: str) -> str:
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
        r"System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    if not executable.is_file():
        raise TerminalCommandError("Windows PowerShell não está disponível para validar o comando.")
    environment = _safe_environment()
    try:
        parsed = subprocess.run(
            [
                str(executable),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                _POWERSHELL_AST_VALIDATOR,
            ],
            input=command,
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = "Não foi possível analisar o comando PowerShell com segurança."
        raise TerminalCommandError(message) from exc
    if parsed.returncode != 0:
        raise TerminalCommandError(
            "O comando precisa conter uma única chamada PowerShell literal, sem encadeamento, "
            "scripts, variáveis, subexpressões, pipelines, redirecionamentos ou shells aninhados."
        )
    return parsed.stdout.strip().casefold()


def validate_terminal_command(
    command: str, *, advanced: bool = False, cwd: Path | None = None
) -> str:
    normalized = command.strip()
    if not normalized:
        raise TerminalCommandError("Digite um comando antes de executar.")
    if "\x00" in normalized:
        raise TerminalCommandError("O comando contém um caractere inválido.")
    
    # Validate via PowerShell AST parser (blocks subexpressions, variables, script blocks, etc.)
    verb = _validate_powershell_ast(normalized)
    
    if not advanced:
        if verb not in _SAFE_COMMANDS:
            raise TerminalCommandError(
                "Comando fora da lista segura. Habilite o modo avançado nas configurações "
                "para executar um comando arbitrário com confirmação."
            )
        tokens = normalized.split()
        verb = tokens[0].casefold()
        arguments = tokens[1:]
        if not all(_SAFE_TOKEN.fullmatch(token) for token in arguments):
            raise TerminalCommandError("O modo seguro aceita apenas argumentos simples.")
        if verb == "get-location" and arguments:
            raise TerminalCommandError("Get-Location não aceita argumentos no modo seguro.")
        if verb in {"dir", "get-childitem", "get-content"} and len(arguments) > 1:
            raise TerminalCommandError("Informe no máximo um caminho relativo.")
        if verb == "select-string" and len(arguments) != 2:
            raise TerminalCommandError("Use Select-String com um padrão simples e um arquivo.")
        if verb == "select-string" and len(arguments[0]) > 256:
            raise TerminalCommandError("O padrão de busca excede 256 caracteres.")
        if verb == "select-string" and arguments[0].startswith("-"):
            raise TerminalCommandError("O padrão precisa ser texto simples, não um parâmetro.")
        path_tokens = (
            arguments if verb == "select-string" else arguments
        )
        if cwd is not None:
            for token in path_tokens[-1:] if verb == "select-string" else path_tokens:
                _workspace_path(token, cwd)
    return normalized


def _safe_environment() -> dict[str, str]:
    permitted = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE"}
    return {key: value for key, value in os.environ.items() if key.upper() in permitted}


def is_destructive_command(command: str) -> bool:
    """Check if a command would be rejected in safe mode (requires advanced mode)."""
    try:
        validate_terminal_command(command, advanced=False, cwd=Path.cwd())
        return False
    except TerminalCommandError:
        return True


def run_terminal_command(
    command: str,
    cwd: Path,
    *,
    advanced: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    cancel_event: threading.Event | None = None,
    on_output: Callable[[str], None] | None = None,
) -> TerminalResult:
    root = Path(cwd).resolve(strict=True)
    if not root.is_dir():
        raise TerminalCommandError("O diretório de trabalho precisa ser uma pasta existente.")
    command = validate_terminal_command(command, advanced=advanced, cwd=root)
    powershell = (
        os.environ.get("SystemRoot", r"C:\Windows")
        + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    if not Path(powershell).is_file():
        raise TerminalCommandError("Windows PowerShell não está disponível neste computador.")

    started = time.monotonic()
    job = _WindowsJob()
    try:
        process = subprocess.Popen(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=root,
            env=_safe_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        job.assign(process.pid)
    except OSError as exc:
        if "process" in locals():
            process.kill()
            process.wait()
        job.close()
        raise TerminalCommandError(
            "Não foi possível supervisionar a árvore do processo no Job Object do Windows."
        ) from exc
    chunks: queue.Queue[bytes | None] = queue.Queue(maxsize=32)

    def read_output() -> None:
        assert process.stdout is not None
        try:
            while chunk := process.stdout.read(4096):
                chunks.put(chunk)
        finally:
            chunks.put(None)

    reader = threading.Thread(target=read_output, name="noite-terminal-output", daemon=True)
    reader.start()
    output = bytearray()
    truncated = False
    timed_out = False
    cancelled = False
    reader_done = False
    deadline = started + max(1, timeout_seconds)
    while not reader_done:
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            job.terminate()
            job.close()
        elif time.monotonic() >= deadline:
            timed_out = True
            job.terminate()
            job.close()
        elif process.poll() is not None and job.handle:
            # The shell is done; close the job now so detached children cannot hold its pipe open.
            job.close()
        try:
            chunk = chunks.get(timeout=0.05)
        except queue.Empty:
            continue
        if chunk is None:
            reader_done = True
            continue
        remaining = MAX_OUTPUT_BYTES - len(output)
        if remaining > 0:
            output.extend(chunk[:remaining])
            if on_output is not None:
                on_output(chunk[:remaining].decode("utf-8", errors="replace"))
        if len(chunk) > remaining:
            truncated = True
            job.terminate()
            job.close()
    process.wait(timeout=5)
    job.close()
    duration_ms = max(0, round((time.monotonic() - started) * 1000))
    text = output.decode("utf-8", errors="replace")
    if truncated:
        text += "\n[Saída limitada a 200 KB.]"
    return TerminalResult(
        command=command,
        cwd=root,
        output=text,
        exit_code=process.returncode,
        duration_ms=duration_ms,
        timed_out=timed_out,
        cancelled=cancelled,
        truncated=truncated,
    )
