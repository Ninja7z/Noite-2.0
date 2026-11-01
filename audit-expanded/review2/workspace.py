from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_TEXT_FILE_BYTES = 1_000_000
MAX_SEARCH_FILES = 5_000
MAX_SEARCH_BYTES = 100_000_000
MAX_SEARCH_RESULTS = 1_000
MAX_CONTEXT_FILES = 3
MAX_PROJECT_CONTEXT_CHARS = 5_000
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
_SECRET_VALUE = re.compile(
    r"(?im)(\b[A-Z0-9_]*(?:API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|CREDENTIALS?)[A-Z0-9_]*"
    r"\s*[:=]\s*)([\"']?)([^\s\"'`;,]+)([\"']?)"
)
_BEARER_VALUE = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
_BASIC_VALUE = re.compile(r"(?i)(\bBasic\s+)[A-Za-z0-9+/=_-]+")
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----.*?-----END \1-----",
    re.DOTALL | re.IGNORECASE,
)
_URL = re.compile(r"[a-z][a-z0-9+.-]*://[^\s\"'<>]+", re.IGNORECASE)
_SENSITIVE_NAME = re.compile(
    r"(?i)(?:^|[_-])(?:secret|token|password|passwd|credential|api[_-]?key|private[_-]?key|client[_-]?secret)(?:$|[_-])"
)
_ASSIGNMENT = re.compile(r"(?im)^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*[:=]\s*(.*)$")
_KNOWN_TOKEN = re.compile(
    r"(?:sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|AKIA[A-Z0-9]{16})"
)
_QUOTED_SECRET = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|"
    r"CREDENTIALS?)[A-Z0-9_]*)\b\s*[:=]\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
)


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
        if not _is_within_workspace(current_path, root):
            directories.clear()
            continue
        directories[:] = [
            name
            for name in directories
            if name.casefold() not in ignored
            and not _is_sensitive(current_path / name)
            and not (current_path / name).is_symlink()
            and _is_within_workspace(current_path / name, root)
        ]
        for filename in filenames:
            if cancelled():
                return matches
            path = current_path / filename
            if _is_sensitive(path) or path.is_symlink() or not _is_within_workspace(path, root):
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


def retrieve_workspace_context(
    workspace: Path,
    query: str,
    *,
    active_file: str | None = None,
    active_text: str | None = None,
    max_chars: int = MAX_PROJECT_CONTEXT_CHARS,
) -> str:
    """Select small, relevant text excerpts without following links or reading secrets."""
    root = Path(workspace).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("O workspace não é uma pasta.")
    budget = max(0, min(max_chars, MAX_PROJECT_CONTEXT_CHARS))
    if not budget:
        return ""
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
    terms = {
        term.casefold()
        for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", query)
        if term.casefold() not in {"this", "that", "with", "from", "para", "como", "qual"}
    }
    selected: list[tuple[str, str]] = []
    seen: set[Path] = set()
    if active_file is not None and active_text is not None:
        candidate = Path(active_file)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            path = candidate.resolve(strict=True)
            if path.is_relative_to(root) and not _is_sensitive(path) and path.is_file():
                text = _redact_secret_values(active_text)[: min(MAX_TEXT_FILE_BYTES, budget)]
                selected.append((path.relative_to(root).as_posix(), text))
                seen.add(path)
        except (OSError, ValueError):
            pass
    if terms and len(selected) < MAX_CONTEXT_FILES:
        ranked: list[tuple[int, Path, str]] = []
        scanned_bytes = 0
        scanned_files = 0
        for current, directories, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            if not _is_within_workspace(current_path, root):
                directories.clear()
                continue
            directories[:] = [
                name
                for name in directories
                if name.casefold() not in ignored
                and not _is_sensitive(current_path / name)
                and not (current_path / name).is_symlink()
                and _is_within_workspace(current_path / name, root)
                and not (
                    hasattr(current_path / name, "is_junction")
                    and (current_path / name).is_junction()
                )
            ]
            for filename in filenames:
                path = current_path / filename
                if (
                    path in seen
                    or _is_sensitive(path)
                    or path.is_symlink()
                    or not _is_within_workspace(path, root)
                ):
                    continue
                if hasattr(path, "is_junction") and path.is_junction():
                    continue
                try:
                    size = path.stat().st_size
                    if size > MAX_TEXT_FILE_BYTES or scanned_bytes + size > 20_000_000:
                        continue
                    raw = path.read_bytes()
                except OSError:
                    continue
                scanned_files += 1
                scanned_bytes += len(raw)
                if scanned_files > 500:
                    return _format_project_context(selected, budget)
                if b"\0" in raw:
                    continue
                try:
                    content = _redact_secret_values(raw.decode("utf-8-sig"))
                except UnicodeDecodeError:
                    continue
                folded = content.casefold()
                score = sum(folded.count(term) for term in terms)
                if not score:
                    continue
                excerpts = []
                for line_number, line in enumerate(content.splitlines(), start=1):
                    if any(term in line.casefold() for term in terms):
                        excerpts.append(f"{line_number}: {line[:300]}")
                    if len(excerpts) >= 8:
                        break
                ranked.append((score, path, "\n".join(excerpts)))
        ranked.sort(key=lambda item: (-item[0], item[1].as_posix().casefold()))
        for _score, path, excerpt in ranked:
            selected.append((path.relative_to(root).as_posix(), excerpt))
            if len(selected) >= MAX_CONTEXT_FILES:
                break
    return _format_project_context(selected, budget)


def _redact_secret_values(text: str) -> str:
    text = _PRIVATE_KEY_BLOCK.sub("[REDACTED PRIVATE KEY]", text)
    text = _URL.sub(_redact_url, text)
    text = _QUOTED_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = _SECRET_VALUE.sub(r"\1\2[REDACTED]\4", text)
    text = _BEARER_VALUE.sub(r"\1[REDACTED]", text)
    text = _BASIC_VALUE.sub(r"\1[REDACTED]", text)
    text = _redact_sensitive_assignments(text)
    return _KNOWN_TOKEN.sub("[REDACTED]", text)


def _redact_url(match: re.Match[str]) -> str:
    raw = match.group(0)
    try:
        parts = urlsplit(raw)
        netloc = parts.netloc
        userinfo, separator, _host = parts.netloc.rpartition("@")
        has_password_delimiter = separator and ":" in userinfo
        known_secret_user = bool(_KNOWN_TOKEN.search(parts.username or ""))
        if has_password_delimiter or known_secret_user:
            host = parts.hostname or ""
            if parts.port:
                host += f":{parts.port}"
            netloc = f"[REDACTED]@{host}"
        query = urlencode(
            [
                (key, "[REDACTED]" if _is_sensitive_query_key(key) else value)
                for key, value in parse_qsl(parts.query, keep_blank_values=True)
            ]
        )
        return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))
    except ValueError:
        return raw


def _is_sensitive_query_key(key: str) -> bool:
    return bool(_SENSITIVE_NAME.search(key)) or key.casefold() in {"password", "passwd", "token"}


def _redact_sensitive_assignments(text: str) -> str:
    lines = []
    for line in text.splitlines(keepends=True):
        match = _ASSIGNMENT.match(line)
        explicit_client_id = bool(
            match
            and re.search(r"(?i)\bCLIENT[_-]?ID\b", match.group(1))
            and re.search(r"(?i)\bcredential\b", line)
        )
        if match and (_SENSITIVE_NAME.search(match.group(1)) or explicit_client_id):
            value_start, value_end = match.span(2)
            value = line[value_start:value_end]
            quote = value[:1] if value[:1] in {"'", '"'} else ""
            closing = quote if quote and value.endswith(quote) else ""
            line = line[:value_start] + quote + "[REDACTED]" + closing + line[value_end:]
        lines.append(line)
    return "".join(lines)


def _is_within_workspace(path: Path, root: Path) -> bool:
    try:
        return path.resolve(strict=False).is_relative_to(root)
    except (OSError, ValueError):
        return False


def _format_project_context(files: list[tuple[str, str]], budget: int) -> str:
    parts: list[str] = []
    remaining = budget
    for name, excerpt in files:
        section = f"--- {name} ---\n{excerpt.strip()}\n"
        if len(section) > remaining:
            section = section[:remaining]
        if section:
            parts.append(section)
            remaining -= len(section)
        if remaining <= 0:
            break
    return "\n".join(parts)
