"""Indexador de documentos do workspace da Noite 2.0.

Responsabilidades:
- Indexar arquivos de texto do workspace no SQLite com FTS5.
- Chunking por tamanho + fronteiras de parágrafo.
- Deduplicação por hash SHA-256 do conteúdo bruto.
- Atualização incremental: reindexar apenas arquivos modificados.
- Detecção de arquivos removidos.
- Nunca expor segredos: redireciona via _redact_secret_values do workspace.
- Nunca indexar arquivos que o workspace considera sensíveis.

Arquitetura do schema:
  indexed_files  - metadados por arquivo (path, mtime, size, content_hash)
  document_chunks - fatias do texto indexável
  document_chunks_fts - FTS5 sobre document_chunks

LIMITES:
  - Arquivos maiores que MAX_FILE_BYTES são ignorados.
  - Chunks de no máximo CHUNK_MAX_CHARS caracteres.
  - Máximo de MAX_CHUNKS_PER_FILE chunks por arquivo.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
import threading
from pathlib import Path

MAX_FILE_BYTES = 500_000  # 500 KB por arquivo
CHUNK_MAX_CHARS = 1_000  # chars por chunk
CHUNK_OVERLAP_CHARS = 100  # overlap entre chunks
MAX_CHUNKS_PER_FILE = 200
MAX_INDEX_FILES = 10_000
MAX_INDEX_BYTES = 200_000_000  # 200 MB total varrido
MAX_SEARCH_RESULTS = 100

_SCHEMA_LOCK = threading.RLock()

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        ".ssh",
        ".aws",
        ".azure",
        ".gnupg",
    }
)
IGNORED_SUFFIXES = frozenset(
    {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
        ".sqlite3",
        ".db",
        ".pyc",
        ".pyo",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".lock",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".ico",
        ".mp3",
        ".mp4",
        ".wav",
        ".avi",
        ".mkv",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
    }
)
SENSITIVE_NAMES = frozenset(
    {
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
    }
)


def open_index_db(path: Path) -> sqlite3.Connection:
    """Abre (ou cria) o banco do indexador."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    with _SCHEMA_LOCK:
        _ensure_index_schema(conn)
        conn.commit()
    return conn


def _ensure_index_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS indexed_files (
            id           INTEGER PRIMARY KEY,
            workspace    TEXT NOT NULL,
            rel_path     TEXT NOT NULL,
            abs_path     TEXT NOT NULL,
            mtime_ns     INTEGER NOT NULL,
            size_bytes   INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            indexed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(workspace, rel_path)
        );

        CREATE INDEX IF NOT EXISTS idx_files_workspace
            ON indexed_files(workspace);

        CREATE TABLE IF NOT EXISTS document_chunks (
            id          INTEGER PRIMARY KEY,
            file_id     INTEGER NOT NULL
                        REFERENCES indexed_files(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            char_start  INTEGER NOT NULL,
            char_end    INTEGER NOT NULL,
            UNIQUE(file_id, chunk_index)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_file_id
            ON document_chunks(file_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
            USING fts5(
                content,
                content='document_chunks',
                content_rowid='id'
            );

        CREATE TRIGGER IF NOT EXISTS dc_ai AFTER INSERT ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(rowid, content)
                VALUES (new.id, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS dc_ad AFTER DELETE ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
        END;

        CREATE TRIGGER IF NOT EXISTS dc_au AFTER UPDATE ON document_chunks BEGIN
            INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
            INSERT INTO document_chunks_fts(rowid, content)
                VALUES (new.id, new.content);
        END;
        """
    )


def _file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sensitive(path: Path) -> bool:
    name = path.name.casefold()
    if name in SENSITIVE_NAMES:
        return True
    suffix = path.suffix.casefold()
    if suffix in IGNORED_SUFFIXES:
        return True
    return False


def _is_text(raw: bytes) -> bool:
    """Heurística rápida: arquivo sem bytes nulos é provavelmente texto."""
    return b"\x00" not in raw


def _chunk_text(text: str) -> list[tuple[int, int, str]]:
    """Divide o texto em chunks com overlap, respeitando fronteiras de parágrafo.

    Retorna lista de (char_start, char_end, chunk_content).
    """
    if not text:
        return []
    chunks: list[tuple[int, int, str]] = []
    pos = 0
    total = len(text)
    while pos < total and len(chunks) < MAX_CHUNKS_PER_FILE:
        end = min(pos + CHUNK_MAX_CHARS, total)
        # Tenta terminar no último parágrafo dentro do chunk
        if end < total:
            # procura "\n\n" para fronteira de parágrafo
            break_pos = text.rfind("\n\n", pos, end)
            if break_pos > pos + CHUNK_OVERLAP_CHARS:
                end = break_pos + 2
            else:
                # fallback: quebra de linha simples
                break_pos = text.rfind("\n", pos, end)
                if break_pos > pos + CHUNK_OVERLAP_CHARS:
                    end = break_pos + 1
        chunk = text[pos:end].strip()
        if chunk:
            chunks.append((pos, end, chunk))
        # Avança com overlap
        next_pos = end - CHUNK_OVERLAP_CHARS
        pos = next_pos if next_pos > pos else end
    return chunks


def index_file(
    conn: sqlite3.Connection,
    workspace: Path,
    rel_path: str,
    *,
    redact_fn=None,
) -> dict:
    """Indexa (ou atualiza) um único arquivo.

    - Se o arquivo não mudou (mtime + hash), não faz nada (retorna status='unchanged').
    - Se mudou, remove os chunks antigos e reindexar.
    - Se for binário/sensível/grande, remove do índice e retorna status='skipped'.

    Retorna dict com 'status', 'rel_path', 'chunks'.
    """
    workspace = Path(workspace).resolve()
    abs_path = (workspace / rel_path).resolve()

    # Verificação de segurança: dentro do workspace
    try:
        abs_path.relative_to(workspace)
    except ValueError:
        return {"status": "rejected", "rel_path": rel_path, "chunks": 0}

    if _is_sensitive(abs_path):
        _remove_file_from_index(conn, str(workspace), rel_path)
        return {"status": "skipped_sensitive", "rel_path": rel_path, "chunks": 0}

    if not abs_path.is_file() or abs_path.is_symlink():
        _remove_file_from_index(conn, str(workspace), rel_path)
        return {"status": "not_found", "rel_path": rel_path, "chunks": 0}

    try:
        st = abs_path.stat()
    except OSError:
        return {"status": "error", "rel_path": rel_path, "chunks": 0}

    if st.st_size > MAX_FILE_BYTES:
        _remove_file_from_index(conn, str(workspace), rel_path)
        return {"status": "skipped_too_large", "rel_path": rel_path, "chunks": 0}

    # Verificar se já indexado e inalterado
    existing = conn.execute(
        "SELECT id, mtime_ns, content_hash FROM indexed_files WHERE workspace = ? AND rel_path = ?",
        (str(workspace), rel_path),
    ).fetchone()

    if existing is not None:
        file_id, old_mtime, old_hash = existing
        if old_mtime == st.st_mtime_ns:
            return {"status": "unchanged", "rel_path": rel_path, "chunks": 0}

    # Leitura do conteúdo
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(str(abs_path), flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return {"status": "skipped_not_regular", "rel_path": rel_path, "chunks": 0}
            raw = os.read(fd, MAX_FILE_BYTES + 1)
        finally:
            os.close(fd)
    except OSError:
        return {"status": "error", "rel_path": rel_path, "chunks": 0}

    if len(raw) > MAX_FILE_BYTES:
        _remove_file_from_index(conn, str(workspace), rel_path)
        return {"status": "skipped_too_large", "rel_path": rel_path, "chunks": 0}

    if not _is_text(raw):
        _remove_file_from_index(conn, str(workspace), rel_path)
        return {"status": "skipped_binary", "rel_path": rel_path, "chunks": 0}

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            _remove_file_from_index(conn, str(workspace), rel_path)
            return {"status": "skipped_encoding", "rel_path": rel_path, "chunks": 0}

    content_hash = _file_hash(raw)

    # Se hash idêntico mas mtime diferente (cópia), atualiza só o mtime
    if existing is not None and old_hash == content_hash:
        conn.execute(
            "UPDATE indexed_files SET mtime_ns = ?, indexed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (st.st_mtime_ns, file_id),
        )
        conn.commit()
        return {"status": "unchanged_content", "rel_path": rel_path, "chunks": 0}

    # Redação de segredos se fornecida
    if redact_fn is not None:
        try:
            text = redact_fn(text)
        except Exception:
            pass  # redação não deve bloquear indexação

    chunks = _chunk_text(text)

    with conn:
        if existing is not None:
            # Remover chunks antigos (cascade pelo FK cuida do FTS via trigger)
            conn.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))
            conn.execute(
                """
                UPDATE indexed_files SET mtime_ns=?, size_bytes=?, content_hash=?,
                    abs_path=?, indexed_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (st.st_mtime_ns, st.st_size, content_hash, str(abs_path), file_id),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO indexed_files(
                    workspace, rel_path, abs_path, mtime_ns, size_bytes, content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(workspace), rel_path, str(abs_path), st.st_mtime_ns, st.st_size, content_hash),
            )
            file_id = cur.lastrowid

        for idx, (start, end, chunk_text) in enumerate(chunks):
            conn.execute(
                """
                INSERT INTO document_chunks(
                    file_id, chunk_index, content, char_start, char_end
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_id, idx, chunk_text, start, end),
            )

    return {"status": "indexed", "rel_path": rel_path, "chunks": len(chunks)}


def _remove_file_from_index(conn: sqlite3.Connection, workspace: str, rel_path: str) -> None:
    """Remove arquivo e seus chunks do índice (delete cascade cuida dos chunks)."""
    conn.execute(
        "DELETE FROM indexed_files WHERE workspace = ? AND rel_path = ?",
        (workspace, rel_path),
    )
    conn.commit()


def index_workspace(
    conn: sqlite3.Connection,
    workspace: Path,
    *,
    redact_fn=None,
    on_progress=None,
) -> dict:
    """Indexa ou atualiza incrementalmente todos os arquivos do workspace.

    - Detecta e remove arquivos que sumiram do disco.
    - Reindexar apenas arquivos modificados.
    - Respeita limites MAX_INDEX_FILES e MAX_INDEX_BYTES.

    Retorna dict com estatísticas.
    """
    workspace = Path(workspace).resolve()
    ws_str = str(workspace)

    stats = {"indexed": 0, "unchanged": 0, "skipped": 0, "removed": 0, "errors": 0}
    files_seen: set[str] = set()
    files_scanned = 0
    bytes_scanned = 0

    for dirpath, dirnames, filenames in os.walk(str(workspace), followlinks=False):
        dirpath_obj = Path(dirpath)
        # Filtrar diretórios ignorados
        dirnames[:] = [
            d
            for d in dirnames
            if d.casefold() not in IGNORED_DIRS and not (dirpath_obj / d).is_symlink()
        ]
        for filename in filenames:
            abs_path = dirpath_obj / filename
            if abs_path.is_symlink():
                continue
            try:
                rel = abs_path.relative_to(workspace).as_posix()
            except ValueError:
                continue

            if files_scanned >= MAX_INDEX_FILES:
                if on_progress:
                    on_progress("limit", f"Limite de {MAX_INDEX_FILES} arquivos atingido.")
                break

            try:
                sz = abs_path.stat().st_size
            except OSError:
                continue
            if bytes_scanned + sz > MAX_INDEX_BYTES:
                if on_progress:
                    on_progress("limit", "Limite de bytes atingido.")
                break

            files_scanned += 1
            bytes_scanned += sz
            files_seen.add(rel)

            result = index_file(conn, workspace, rel, redact_fn=redact_fn)
            status = result["status"]
            if status == "indexed":
                stats["indexed"] += 1
                if on_progress:
                    on_progress("indexed", rel)
            elif status in ("unchanged", "unchanged_content"):
                stats["unchanged"] += 1
            elif status.startswith("skipped") or status == "not_found":
                stats["skipped"] += 1
            else:
                stats["errors"] += 1

    # Remover entradas de arquivos que sumiram do disco
    existing_in_db = conn.execute(
        "SELECT rel_path FROM indexed_files WHERE workspace = ?", (ws_str,)
    ).fetchall()
    for (rel_path,) in existing_in_db:
        if rel_path not in files_seen:
            _remove_file_from_index(conn, ws_str, rel_path)
            stats["removed"] += 1

    return stats


def search_documents(
    conn: sqlite3.Connection,
    query: str,
    *,
    workspace: Path | None = None,
    limit: int = 10,
) -> list[dict]:
    """Busca chunks de documentos indexados por FTS5.

    Retorna lista de dicts com 'rel_path', 'chunk_index', 'content', 'char_start', 'char_end'.
    """
    if not isinstance(limit, int) or not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValueError(f"limit deve estar entre 1 e {MAX_SEARCH_RESULTS}.")
    query = query.strip()
    if not query:
        return []
    if len(query) > 512:
        raise ValueError("A query excede 512 caracteres.")

    terms = query.split()[:20]
    safe_query = " AND ".join(f'"{t.replace(chr(34), chr(34) * 2)}"' for t in terms)

    fts_rows = conn.execute(
        "SELECT rowid FROM document_chunks_fts WHERE document_chunks_fts MATCH ? LIMIT ?",
        (safe_query, limit * 3),
    ).fetchall()
    if not fts_rows:
        return []

    rowids = [r[0] for r in fts_rows]
    placeholders = ",".join("?" * len(rowids))

    extra_where = ""
    extra_params: list = []
    if workspace is not None:
        extra_where = " AND f.workspace = ?"
        extra_params.append(str(Path(workspace).resolve()))

    rows = conn.execute(
        f"""
        SELECT f.rel_path, dc.chunk_index, dc.content, dc.char_start, dc.char_end
        FROM document_chunks dc
        JOIN indexed_files f ON f.id = dc.file_id
        WHERE dc.id IN ({placeholders}){extra_where}
        ORDER BY f.rel_path, dc.chunk_index
        LIMIT ?
        """,
        rowids + extra_params + [limit],
    ).fetchall()

    return [
        {
            "rel_path": str(r[0]),
            "chunk_index": int(r[1]),
            "content": str(r[2]),
            "char_start": int(r[3]),
            "char_end": int(r[4]),
        }
        for r in rows
    ]


def stats_index(conn: sqlite3.Connection, workspace: Path | None = None) -> dict:
    """Retorna estatísticas do índice."""
    ws_filter = ""
    params: list = []
    if workspace is not None:
        ws_filter = "WHERE workspace = ?"
        params.append(str(Path(workspace).resolve()))
    files = conn.execute(
        f"SELECT COUNT(*), SUM(size_bytes) FROM indexed_files {ws_filter}", params
    ).fetchone()
    chunks = conn.execute(
        f"""
        SELECT COUNT(*) FROM document_chunks dc
        JOIN indexed_files f ON f.id = dc.file_id
        {ws_filter.replace("WHERE", "WHERE f.")}
        """,
        params,
    ).fetchone()
    return {
        "files": int(files[0]) if files[0] else 0,
        "total_bytes": int(files[1]) if files[1] else 0,
        "chunks": int(chunks[0]) if chunks[0] else 0,
    }
