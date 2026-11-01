import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

NEW_CONVERSATION_TITLE = "Nova conversa"
MAX_CONVERSATION_TITLE = 120
_SCHEMA_LOCK = threading.RLock()


def open_database(path: Path) -> sqlite3.Connection:
    """Abre o banco local e prepara histórico pesquisável com FTS5."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA foreign_keys = ON")
    with _SCHEMA_LOCK:
        _ensure_schema(connection)
        connection.commit()
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            trace_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(messages)")}
    if "conversation_id" not in columns:
        connection.execute(
            "ALTER TABLE messages ADD COLUMN conversation_id TEXT NOT NULL DEFAULT 'default'"
        )
    connection.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
        USING fts5(content, content='messages', content_rowid='id')
        """
    )
    connection.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, content)
            VALUES ('delete', old.id, old.content);
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END;
        """
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS noite_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            title_locked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conversation_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(conversations)")
    }
    if "title_locked" not in conversation_columns:
        connection.execute(
            "ALTER TABLE conversations ADD COLUMN title_locked INTEGER NOT NULL DEFAULT 0"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS messages_conversation_id_id ON messages(conversation_id, id)"
    )
    connection.execute(
        "INSERT OR IGNORE INTO conversations(id, title) VALUES ('default', 'Conversa local')"
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO conversations(id, title)
        SELECT DISTINCT conversation_id,
            CASE WHEN conversation_id = 'default' THEN 'Conversa local'
                 ELSE 'Conversa importada' END
        FROM messages
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO noite_metadata(key, value)
        VALUES ('active_conversation_id', 'default')
        """
    )
    fts_version = connection.execute(
        "SELECT value FROM noite_metadata WHERE key = 'fts_sync_version'"
    ).fetchone()
    if fts_version is None:
        connection.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
        connection.execute(
            "INSERT INTO noite_metadata(key, value) VALUES ('fts_sync_version', '1')"
        )
    active = connection.execute(
        "SELECT value FROM noite_metadata WHERE key = 'active_conversation_id'"
    ).fetchone()
    if (
        active is None
        or connection.execute("SELECT 1 FROM conversations WHERE id = ?", (active[0],)).fetchone()
        is None
    ):
        latest = connection.execute(
            "SELECT id FROM conversations ORDER BY updated_at DESC, created_at DESC LIMIT 1"
        ).fetchone()
        active_id = str(latest[0]) if latest else create_conversation(connection)
        connection.execute(
            "INSERT INTO noite_metadata(key, value) VALUES ('active_conversation_id', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (active_id,),
        )


def create_conversation(
    connection: sqlite3.Connection,
    title: str | None = None,
    conversation_id: str | None = None,
) -> str:
    """Cria uma conversa; título informado pelo usuário fica protegido da auto nomeação."""
    conversation_id = conversation_id or str(uuid4())
    normalized_title = _validated_title(title) if title is not None else NEW_CONVERSATION_TITLE
    connection.execute(
        "INSERT INTO conversations(id, title, title_locked) VALUES (?, ?, ?)",
        (conversation_id, normalized_title, int(title is not None)),
    )
    connection.commit()
    return conversation_id


def list_conversations(connection: sqlite3.Connection) -> list[tuple[str, str, str]]:
    rows = connection.execute(
        "SELECT id, title, updated_at FROM conversations "
        "ORDER BY updated_at DESC, created_at DESC, id"
    ).fetchall()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


def get_active_conversation_id(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT value FROM noite_metadata WHERE key = 'active_conversation_id'"
    ).fetchone()
    if row and connection.execute("SELECT 1 FROM conversations WHERE id = ?", (row[0],)).fetchone():
        return str(row[0])
    conversations = list_conversations(connection)
    conversation_id = conversations[0][0] if conversations else create_conversation(connection)
    set_active_conversation_id(connection, conversation_id)
    return conversation_id


def set_active_conversation_id(connection: sqlite3.Connection, conversation_id: str) -> None:
    if (
        connection.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        is None
    ):
        raise ValueError("A conversa solicitada não existe.")
    connection.execute(
        "INSERT INTO noite_metadata(key, value) VALUES ('active_conversation_id', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (conversation_id,),
    )
    connection.commit()


def rename_conversation(connection: sqlite3.Connection, conversation_id: str, title: str) -> bool:
    normalized_title = _validated_title(title)
    cursor = connection.execute(
        "UPDATE conversations SET title = ?, title_locked = 1, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (normalized_title, conversation_id),
    )
    connection.commit()
    return cursor.rowcount == 1


def delete_conversation(connection: sqlite3.Connection, conversation_id: str) -> str | None:
    """Exclui só a conversa indicada e suas mensagens; retorna a conversa ativa resultante."""
    exists = connection.execute(
        "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if exists is None:
        return get_active_conversation_id(connection)

    active_id = get_active_conversation_id(connection)
    connection.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    remaining = connection.execute(
        "SELECT id FROM conversations ORDER BY updated_at DESC, created_at DESC LIMIT 1"
    ).fetchone()
    if remaining is None:
        replacement_id = create_conversation(connection)
    else:
        replacement_id = str(remaining[0])
    if active_id == conversation_id:
        set_active_conversation_id(connection, replacement_id)
    else:
        connection.commit()
    return replacement_id if active_id == conversation_id else active_id


def _validated_title(title: str) -> str:
    normalized = " ".join(title.split())
    if not normalized:
        raise ValueError("O título da conversa não pode ficar vazio.")
    if len(normalized) > MAX_CONVERSATION_TITLE:
        raise ValueError(f"O título deve ter até {MAX_CONVERSATION_TITLE} caracteres.")
    return normalized


def add_message(
    connection: sqlite3.Connection,
    role: str,
    content: str,
    conversation_id: str = "default",
    trace_id: str = "local",
    commit: bool = True,
) -> int:
    conversation = connection.execute(
        "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if conversation is None:
        connection.execute(
            "INSERT INTO conversations(id, title) VALUES (?, ?)",
            (conversation_id, NEW_CONVERSATION_TITLE),
        )
    cursor = connection.execute(
        "INSERT INTO messages(trace_id, role, content, conversation_id) VALUES (?, ?, ?, ?)",
        (trace_id, role, content, conversation_id),
    )
    if role == "user":
        title = " ".join(content.split())[:MAX_CONVERSATION_TITLE]
        if title:
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND title_locked = 0 AND title = ? "
                "AND (SELECT COUNT(*) FROM messages WHERE conversation_id = ? "
                "AND role = 'user') = 1",
                (title, conversation_id, NEW_CONVERSATION_TITLE, conversation_id),
            )
    connection.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,),
    )
    if commit:
        connection.commit()
    return int(cursor.lastrowid)


def recent_messages(
    connection: sqlite3.Connection, conversation_id: str = "default", limit: int = 50
) -> list[tuple[str, str]]:
    rows = connection.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    ).fetchall()
    return [(str(role), str(content)) for role, content in reversed(rows)]


def search_messages(connection: sqlite3.Connection, query: str, limit: int = 10) -> list[str]:
    terms = [term for term in query.split() if term]
    if not terms:
        return []
    match_query = " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)
    rows = connection.execute(
        "SELECT messages.content FROM messages_fts "
        "JOIN messages ON messages.id = messages_fts.rowid "
        "WHERE messages_fts MATCH ? ORDER BY messages.id DESC LIMIT ?",
        (match_query, limit),
    ).fetchall()
    return [str(row[0]) for row in rows]
