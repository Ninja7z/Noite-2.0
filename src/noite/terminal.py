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

from .workspace import _is_sensitive

MAX_OUTPUT_BYTES = 200_000
DEFAULT_TIMEOUT_SECONDS = 120
_SAFE_COMMANDS = {
    "dir",
    "get-childitem",
    "get-content",
    "get-location",
    "select-string",
}
_DESTRUCTIVE = re.compile(
    r"(?i)(?:\bremove-item\b|\bdel(?:ete)?\b|\berase\b|\brmdir\b|\bformat\b|"
    r"\bclear-content\b|\bset-content\b|\badd-content\b|\bnew-item\b|\bcopy-item\b|"
    r"\bout-file\b|\bexport-\w+\b|\bmove-item\b|\brename-item\b|\bstart-process\b|"
    r"\bstop-process\b|\binvoke-expression\b|\binvoke-command\b|"
    r"\bgit\s+(?:reset|clean|checkout|restore|rebase|merge|push|pull)\b|--fix\b)"
)
_SHELL_OPERATORS = re.compile(r"[;&|<>`$(){}'\"\r\n]")
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.\\/-]{1,260}$")


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


def is_destructive_command(command: str) -> bool:
    return bool(_DESTRUCTIVE.search(command))


def _workspace_path(token: str, cwd: Path) -> Path:
    if not _SAFE_TOKEN.fullmatch(token) or token.startswith(("/", "\\", "-")):
        raise TerminalCommandError("Use um caminho relativo simples dentro do workspace.")
    try:
        candidate = (cwd / token).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise TerminalCommandError("O caminho precisa existir dentro do workspace.") from exc
    try:
        candidate.relative_to(cwd)
    except ValueError as exc:
        raise TerminalCommandError("O caminho precisa permanecer dentro do workspace.") from exc
    if _is_sensitive(candidate):
        raise TerminalCommandError("O modo seguro não lê arquivos de credenciais ou chaves.")
    return candidate


def validate_terminal_command(
    command: str, *, advanced: bool = False, cwd: Path | None = None
) -> str:
    normalized = command.strip()
    if not normalized:
        raise TerminalCommandError("Digite um comando antes de executar.")
    if "\x00" in normalized:
        raise TerminalCommandError("O comando contém um caractere inválido.")
    if not advanced:
        first = re.match(r"[A-Za-z][A-Za-z0-9_-]*", normalized)
        if first is None or first.group(0).casefold() not in _SAFE_COMMANDS:
            raise TerminalCommandError(
                "Comando fora da lista segura. Habilite o modo avançado nas configurações "
                "para executar um comando arbitrário com confirmação."
            )
        if _SHELL_OPERATORS.search(normalized):
            raise TerminalCommandError("O modo seguro não aceita encadeamento ou redirecionamento.")
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
        if cwd is not None:
            path_tokens = arguments[-1:] if verb == "select-string" else arguments
            for token in path_tokens:
                _workspace_path(token, cwd)
    return normalized


def _safe_environment() -> dict[str, str]:
    permitted = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE"}
    return {key: value for key, value in os.environ.items() if key.upper() in permitted}


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
