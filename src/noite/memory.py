"""Sistema de memória da Noite 2.0.

Arquitetura:
- Memória de curto prazo: fatos dentro de uma sessão/conversa, descartados ao fim dela.
- Memória de longo prazo: fatos persistentes no SQLite, com origem, confiança e validade.
- Deduplicação por hash normalizado do conteúdo.
- Atualização controlada: fatos com mesma chave (slot) são substituídos, não duplicados.
- Esquecimento: fatos marcados como expirados ou removidos explicitamente.
- Classificação de fonte: 'user' (alta confiança), 'assistant' (inferência), 'external' (dado
  não confiável), 'system' (inicialização).

IMPORTANTE: Conteúdo externo, de ferramentas, web ou arquivos é classificado como 'external'
e tem confiança mínima. Apenas o usuário pode promover um fato para alta confiança.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Literal

MemorySource = Literal["user", "assistant", "external", "system"]
_SCHEMA_LOCK = threading.RLock()

# Confiança por fonte: 0.0 (não confiável) a 1.0 (certo)
_SOURCE_CONFIDENCE: dict[MemorySource, float] = {
    "user": 1.0,
    "system": 0.9,
    "assistant": 0.6,
    "external": 0.2,
}

MAX_FACT_CONTENT = 2_000
MAX_SLOT_LEN = 200
MAX_FACTS_PER_QUERY = 50


def open_memory_db(path: Path) -> sqlite3.Connection:
    """Abre (ou cria) o banco de memória, separado do banco de mensagens.

    journal_mode=WAL é definido apenas durante a criação do schema (sob _SCHEMA_LOCK),
    pois é uma opção persistente. Definir em cada abertura de conexão causa
    "database is locked" sob concorrência, pois PRAGMA journal_mode requer lock
    de escrita exclusivo.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    with _SCHEMA_LOCK:
        conn.execute("PRAGMA journal_mode = WAL")
        _ensure_memory_schema(conn)
        conn.commit()
    return conn


def _ensure_memory_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_facts (
            id          INTEGER PRIMARY KEY,
            slot        TEXT NOT NULL,
            content     TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            source      TEXT NOT NULL DEFAULT 'assistant',
            confidence  REAL NOT NULL DEFAULT 0.6
                        CHECK (confidence >= 0.0 AND confidence <= 1.0),
            scope       TEXT NOT NULL DEFAULT 'long',
            conversation_id TEXT,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at  TEXT,
            active      INTEGER NOT NULL DEFAULT 1
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
            memory_facts_slot_scope_conversation
            ON memory_facts(slot, scope, COALESCE(conversation_id, ''));

        CREATE INDEX IF NOT EXISTS memory_facts_conversation_id
            ON memory_facts(conversation_id);

        CREATE INDEX IF NOT EXISTS memory_facts_active_scope
            ON memory_facts(active, scope);

        CREATE VIRTUAL TABLE IF NOT EXISTS memory_facts_fts
            USING fts5(
                content,
                slot,
                content='memory_facts',
                content_rowid='id'
            );

        CREATE TRIGGER IF NOT EXISTS mf_ai AFTER INSERT ON memory_facts BEGIN
            INSERT INTO memory_facts_fts(rowid, content, slot)
                VALUES (new.id, new.content, new.slot);
        END;

        CREATE TRIGGER IF NOT EXISTS mf_ad AFTER DELETE ON memory_facts BEGIN
            INSERT INTO memory_facts_fts(memory_facts_fts, rowid, content, slot)
                VALUES ('delete', old.id, old.content, old.slot);
        END;

        CREATE TRIGGER IF NOT EXISTS mf_au AFTER UPDATE ON memory_facts BEGIN
            INSERT INTO memory_facts_fts(memory_facts_fts, rowid, content, slot)
                VALUES ('delete', old.id, old.content, old.slot);
            INSERT INTO memory_facts_fts(rowid, content, slot)
                VALUES (new.id, new.content, new.slot);
        END;
        """
    )


def _content_hash(content: str) -> str:
    normalized = " ".join(content.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def _validated_content(content: str) -> str:
    content = content.strip()
    if not content:
        raise ValueError("O conteúdo do fato não pode ser vazio.")
    if len(content) > MAX_FACT_CONTENT:
        raise ValueError(f"O conteúdo excede {MAX_FACT_CONTENT} caracteres.")
    return content


def _validated_slot(slot: str) -> str:
    slot = slot.strip().casefold()
    if not slot:
        raise ValueError("O slot de memória não pode ser vazio.")
    if len(slot) > MAX_SLOT_LEN:
        raise ValueError(f"O slot excede {MAX_SLOT_LEN} caracteres.")
    return slot


def remember(
    conn: sqlite3.Connection,
    slot: str,
    content: str,
    *,
    source: MemorySource = "assistant",
    scope: Literal["short", "long"] = "long",
    conversation_id: str | None = None,
    confidence: float | None = None,
    expires_at: str | None = None,
) -> int:
    """Armazena ou atualiza um fato.

    Se já existir um fato com o mesmo slot+scope+conversation_id, ele é atualizado
    (nunca duplicado). Fatos com source='external' têm confiança máxima de 0.2 — isso
    não pode ser elevado por conteúdo, apenas pelo usuário via source='user'.

    Retorna o id do fato criado/atualizado.
    """
    slot = _validated_slot(slot)
    content = _validated_content(content)
    if source not in ("user", "assistant", "external", "system"):
        raise ValueError(f"Fonte inválida: {source!r}")
    base_confidence = _SOURCE_CONFIDENCE[source]
    if confidence is None:
        effective_confidence = base_confidence
    else:
        # Nunca elevar confiança acima da máxima permitida pela fonte
        effective_confidence = min(float(confidence), base_confidence)
        if not 0.0 <= effective_confidence <= 1.0:
            raise ValueError("Confiança deve estar entre 0.0 e 1.0.")
    h = _content_hash(content)
    scope_val = scope
    conv_id = conversation_id if conversation_id else None

    # UPSERT: mesma chave lógica (slot + scope + conversation_id), atualiza conteúdo
    row = conn.execute(
        """
        SELECT id, content_hash FROM memory_facts
        WHERE slot = ? AND scope = ? AND COALESCE(conversation_id, '') = COALESCE(?, '')
        """,
        (slot, scope_val, conv_id),
    ).fetchone()

    if row is not None:
        existing_id, existing_hash = row
        if existing_hash == h:
            # Conteúdo idêntico — só atualiza metadados se necessário
            conn.execute(
                """
                UPDATE memory_facts
                SET active = 1, confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP,
                    expires_at = ?
                WHERE id = ?
                """,
                (effective_confidence, source, expires_at, existing_id),
            )
        else:
            conn.execute(
                """
                UPDATE memory_facts
                SET content = ?, content_hash = ?, source = ?, confidence = ?,
                    updated_at = CURRENT_TIMESTAMP, expires_at = ?, active = 1
                WHERE id = ?
                """,
                (content, h, source, effective_confidence, expires_at, existing_id),
            )
        conn.commit()
        return int(existing_id)
    else:
        cursor = conn.execute(
            """
            INSERT INTO memory_facts
                (slot, content, content_hash, source, confidence, scope,
                 conversation_id, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (slot, content, h, source, effective_confidence, scope_val, conv_id, expires_at),
        )
        conn.commit()
        return int(cursor.lastrowid)


def forget(
    conn: sqlite3.Connection,
    slot: str,
    *,
    scope: Literal["short", "long"] | None = None,
    conversation_id: str | None = None,
) -> int:
    """Desativa (soft-delete) fatos com o slot indicado.

    Retorna a quantidade de fatos desativados.
    """
    slot = _validated_slot(slot)
    params: list = [slot]
    clauses = ["slot = ?"]
    if scope is not None:
        clauses.append("scope = ?")
        params.append(scope)
    if conversation_id is not None:
        clauses.append("conversation_id = ?")
        params.append(conversation_id)
    where = " AND ".join(clauses)
    cursor = conn.execute(
        f"UPDATE memory_facts SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE {where}",
        params,
    )
    conn.commit()
    return cursor.rowcount


def recall(
    conn: sqlite3.Connection,
    slot: str,
    *,
    scope: Literal["short", "long"] | None = None,
    conversation_id: str | None = None,
    min_confidence: float = 0.0,
) -> dict | None:
    """Recupera o fato mais recente e ativo para o slot dado.

    Retorna None se não existir. Fatos expirados são ignorados.
    """
    slot = _validated_slot(slot)
    params: list = [slot, min_confidence]
    clauses = [
        "slot = ?",
        "active = 1",
        "confidence >= ?",
        "(expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
    ]
    if scope is not None:
        clauses.append("scope = ?")
        params.append(scope)
    if conversation_id is not None:
        clauses.append("COALESCE(conversation_id, '') = ?")
        params.append(conversation_id)
    where = " AND ".join(clauses)
    row = conn.execute(
        f"""
        SELECT id, slot, content, source, confidence, scope, conversation_id,
               created_at, updated_at, expires_at
        FROM memory_facts WHERE {where}
        ORDER BY updated_at DESC, id DESC LIMIT 1
        """,
        params,
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def search_memory(
    conn: sqlite3.Connection,
    query: str,
    *,
    scope: Literal["short", "long"] | None = None,
    conversation_id: str | None = None,
    min_confidence: float = 0.0,
    limit: int = 10,
) -> list[dict]:
    """Busca fatos por conteúdo via FTS5.

    A query é sanitizada — cada termo é tratado como literal (não operador FTS5).
    """
    if not isinstance(limit, int) or not 1 <= limit <= MAX_FACTS_PER_QUERY:
        raise ValueError(f"limit deve estar entre 1 e {MAX_FACTS_PER_QUERY}.")
    query = query.strip()
    if not query:
        return []
    if len(query) > 512:
        raise ValueError("A query de busca excede 512 caracteres.")

    terms = query.split()[:20]
    safe_query = " AND ".join(f'"{t.replace(chr(34), chr(34) * 2)}"' for t in terms)

    # FTS busca rowids, depois filtra por metadados
    fts_rows = conn.execute(
        "SELECT rowid FROM memory_facts_fts WHERE memory_facts_fts MATCH ? LIMIT ?",
        (safe_query, limit * 3),
    ).fetchall()
    if not fts_rows:
        return []

    rowids = [r[0] for r in fts_rows]
    placeholders = ",".join("?" * len(rowids))
    extra_clauses = [
        "active = 1",
        "confidence >= ?",
        "(expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
    ]
    params: list = [min_confidence]
    if scope is not None:
        extra_clauses.append("scope = ?")
        params.append(scope)
    if conversation_id is not None:
        extra_clauses.append("COALESCE(conversation_id, '') = ?")
        params.append(conversation_id)

    where = " AND ".join(extra_clauses)
    rows = conn.execute(
        f"""
        SELECT id, slot, content, source, confidence, scope, conversation_id,
               created_at, updated_at, expires_at
        FROM memory_facts
        WHERE id IN ({placeholders}) AND {where}
        ORDER BY confidence DESC, updated_at DESC
        LIMIT ?
        """,
        rowids + params + [limit],
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_facts(
    conn: sqlite3.Connection,
    *,
    scope: Literal["short", "long"] | None = None,
    conversation_id: str | None = None,
    min_confidence: float = 0.0,
    limit: int = 50,
    include_expired: bool = False,
) -> list[dict]:
    """Lista fatos ativos, ordenados por atualização mais recente."""
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit deve estar entre 1 e 200.")
    clauses = ["active = 1", "confidence >= ?"]
    params: list = [min_confidence]
    if not include_expired:
        clauses.append("(expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)")
    if scope is not None:
        clauses.append("scope = ?")
        params.append(scope)
    if conversation_id is not None:
        clauses.append("COALESCE(conversation_id, '') = ?")
        params.append(conversation_id)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT id, slot, content, source, confidence, scope, conversation_id,
               created_at, updated_at, expires_at
        FROM memory_facts WHERE {where}
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def purge_short_term(conn: sqlite3.Connection, conversation_id: str) -> int:
    """Remove permanentemente fatos de curto prazo de uma conversa encerrada.

    Use após deletar uma conversa ou ao encerrar uma sessão.
    """
    cursor = conn.execute(
        "DELETE FROM memory_facts WHERE scope = 'short' AND conversation_id = ?",
        (conversation_id,),
    )
    conn.commit()
    return cursor.rowcount


def purge_expired(conn: sqlite3.Connection) -> int:
    """Remove fatos expirados permanentemente (manutenção periódica)."""
    cursor = conn.execute(
        "DELETE FROM memory_facts WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP"
    )
    conn.commit()
    return cursor.rowcount


def _row_to_dict(row: tuple) -> dict:
    return {
        "id": int(row[0]),
        "slot": str(row[1]),
        "content": str(row[2]),
        "source": str(row[3]),
        "confidence": float(row[4]),
        "scope": str(row[5]),
        "conversation_id": row[6],
        "created_at": str(row[7]),
        "updated_at": str(row[8]),
        "expires_at": row[9],
    }
