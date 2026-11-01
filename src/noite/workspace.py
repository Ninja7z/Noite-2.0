from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MAX_TEXT_FILE_BYTES = 1_000_000
MAX_SEARCH_FILES = 5_000
MAX_SEARCH_BYTES = 100_000_000
MAX_SEARCH_RESULTS = 1_000
BLOCKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
BLOCKED_DIRECTORIES = {".ssh", ".aws", ".azure", ".gnupg"}


@dataclass(frozen=True)
class OpenedTextFile:
    path: Path
    text: str
    sha256: str
    line_ending: str
    has_utf8_bom: bool


@dataclass(frozen=True)
class SearchMatch:
    path: Path
    line: int
    excerpt: str


def resolve_workspace_path(workspace: Path, candidate: Path) -> Path:
    root = Path(workspace).resolve(strict=True)
    path = Path(candidate)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("O caminho está fora do projeto aberto.")
    return resolved


def _is_sensitive(path: Path) -> bool:
    lowered = path.name.casefold()
    return (
        any(part.casefold() in BLOCKED_DIRECTORIES for part in path.parts)
        or lowered in BLOCKED_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or lowered.endswith(tuple(BLOCKED_SUFFIXES))
        or "credential" in lowered
        or "secret" in lowered
    )


def read_workspace_text(workspace: Path, candidate: Path) -> OpenedTextFile:
    path = resolve_workspace_path(workspace, candidate)
    if _is_sensitive(path):
        raise ValueError("Arquivos de credenciais e segredos não podem ser abertos.")
    if not path.is_file():
        raise ValueError("Selecione um arquivo regular do projeto.")
    if path.stat().st_size > MAX_TEXT_FILE_BYTES:
        raise ValueError("O arquivo excede o limite de 1 MB nesta versão.")
    raw = path.read_bytes()
    if b"\0" in raw:
        raise ValueError("Arquivos binários não podem ser abertos no editor de texto.")
    has_utf8_bom = raw.startswith(b"\xef\xbb\xbf")
    line_ending = "\r\n" if b"\r\n" in raw else "\r" if b"\r" in raw else "\n"
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("O arquivo não está codificado em UTF-8.") from exc
    return OpenedTextFile(path, text, hashlib.sha256(raw).hexdigest(), line_ending, has_utf8_bom)


def save_workspace_text(
    workspace: Path,
    candidate: Path,
    text: str,
    expected_sha256: str,
    *,
    line_ending: str = "\n",
    has_utf8_bom: bool = False,
) -> str:
    path = resolve_workspace_path(workspace, candidate)
    if _is_sensitive(path):
        raise ValueError("Arquivos de credenciais e segredos não podem ser salvos.")
    if not path.is_file():
        raise ValueError("O arquivo original não existe mais.")
    current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if current_hash != expected_sha256:
        raise ValueError("O arquivo mudou fora do editor. Reabra-o antes de salvar.")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    encoded = normalized.replace("\n", line_ending).encode("utf-8")
    if has_utf8_bom:
        encoded = b"\xef\xbb\xbf" + encoded
    if len(encoded) > MAX_TEXT_FILE_BYTES:
        raise ValueError("O arquivo excede o limite de 1 MB nesta versão.")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return hashlib.sha256(encoded).hexdigest()


def _new_workspace_item_path(workspace: Path, name: str) -> Path:
    root = Path(workspace).resolve(strict=True)
    normalized = name.strip()
    windows_reserved = {"con", "prn", "aux", "nul"} | {
        f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
    }
    if (
        not normalized
        or normalized in {".", ".."}
        or Path(normalized).name != normalized
        or any(character in normalized for character in '<>:"/\\|?*')
        or normalized.endswith((" ", "."))
        or normalized.split(".", maxsplit=1)[0].casefold() in windows_reserved
    ):
        raise ValueError("Informe um nome simples e válido para o novo item.")
    path = (root / normalized).resolve(strict=False)
    if not path.is_relative_to(root):
        raise ValueError("O caminho está fora do projeto aberto.")
    if _is_sensitive(path):
        raise ValueError("Não crie arquivos com nomes reservados para segredos.")
    return path


def create_workspace_file(workspace: Path, name: str) -> Path:
    path = _new_workspace_item_path(workspace, name)
    with path.open("x", encoding="utf-8", newline=""):
        pass
    return path


def create_workspace_directory(workspace: Path, name: str) -> Path:
    path = _new_workspace_item_path(workspace, name)
    path.mkdir(exist_ok=False)
    return path


def search_workspace_text(
    workspace: Path,
    query: str,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    progress: Callable[[str], None] = lambda _message: None,
) -> list[SearchMatch]:
    root = Path(workspace).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("O workspace não é uma pasta.")
    needle = query.strip()
    if not needle or len(needle) > 200:
        raise ValueError("Digite um termo de pesquisa de 1 a 200 caracteres.")
    ignored = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    matches: list[SearchMatch] = []
    files_scanned = 0
    bytes_scanned = 0
    folded_needle = needle.casefold()
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name.casefold() not in ignored
            and not _is_sensitive(current_path / name)
            and not (current_path / name).is_symlink()
        ]
        for filename in filenames:
            if cancelled():
                return matches
            path = current_path / filename
            if _is_sensitive(path) or path.is_symlink():
                continue
            try:
                size = path.stat().st_size
                if size > MAX_TEXT_FILE_BYTES:
                    continue
                if files_scanned >= MAX_SEARCH_FILES or bytes_scanned + size > MAX_SEARCH_BYTES:
                    progress("Limite de varredura atingido; resultados parciais exibidos.")
                    return matches
                raw = path.read_bytes()
            except OSError:
                continue
            files_scanned += 1
            bytes_scanned += len(raw)
            if b"\0" in raw:
                continue
            try:
                content = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                if folded_needle in line.casefold():
                    excerpt = line.strip()
                    if len(excerpt) > 400:
                        excerpt = excerpt[:397] + "..."
                    matches.append(SearchMatch(path, line_number, excerpt))
                    if len(matches) >= MAX_SEARCH_RESULTS:
                        progress("Limite de resultados atingido.")
                        return matches
            if files_scanned % 100 == 0:
                progress(f"Arquivos examinados: {files_scanned}")
    return matches
