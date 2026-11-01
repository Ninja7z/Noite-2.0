import sqlite3
from pathlib import Path


def open_database(path: Path) -> sqlite3.Connection:
    """Abre o banco local e prepara histórico pesquisável com FTS5."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
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
    fts_version = connection.execute(
        "SELECT value FROM noite_metadata WHERE key = 'fts_sync_version'"
    ).fetchone()
    if fts_version is None:
        connection.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
        connection.execute(
            "INSERT INTO noite_metadata(key, value) VALUES ('fts_sync_version', '1')"
        )
    connection.commit()
    return connection


def add_message(
    connection: sqlite3.Connection,
    role: str,
    content: str,
    conversation_id: str = "default",
    trace_id: str = "local",
) -> int:
    cursor = connection.execute(
        "INSERT INTO messages(trace_id, role, content, conversation_id) VALUES (?, ?, ?, ?)",
        (trace_id, role, content, conversation_id),
    )
    connection.commit()
    return int(cursor.lastrowid)


def recent_messages(
    connection: sqlite3.Connection, conversation_id: str = "default", limit: int = 50
) -> list[tuple[str, str]]:
    rows = connection.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? "
        "ORDER BY id DESC LIMIT ?",
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
