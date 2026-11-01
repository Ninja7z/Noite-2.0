import sqlite3

from noite.store import open_database


def test_database_creation_persistence_and_fts_triggers(tmp_path) -> None:
    path = tmp_path / "data" / "noite.sqlite3"
    connection = open_database(path)
    assert path.exists()

    connection.execute(
        "INSERT INTO messages(trace_id, role, content) VALUES (?, ?, ?)",
        ("trace-1", "user", "alpha texto pesquisável"),
    )
    connection.commit()
    message_id = connection.execute(
        "SELECT id FROM messages WHERE trace_id = ?", ("trace-1",)
    ).fetchone()[0]
    assert connection.execute(
        "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'alpha'"
    ).fetchone() == (message_id,)

    connection.execute(
        "UPDATE messages SET content = ? WHERE id = ?", ("beta texto atualizado", message_id)
    )
    connection.commit()
    assert connection.execute(
        "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'beta'"
    ).fetchone() == (message_id,)
    assert connection.execute(
        "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'alpha'"
    ).fetchone() is None

    connection.close()
    connection = open_database(path)
    assert connection.execute(
        "SELECT content FROM messages WHERE id = ?", (message_id,)
    ).fetchone() == ("beta texto atualizado",)
    connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    connection.commit()
    assert connection.execute(
        "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'beta'"
    ).fetchone() is None
    connection.close()


def test_open_database_rebuilds_fts_for_legacy_rows(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY, trace_id TEXT NOT NULL, role TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE VIRTUAL TABLE messages_fts
        USING fts5(content, content='messages', content_rowid='id');
        INSERT INTO messages(trace_id, role, content) VALUES ('old', 'user', 'legado pesquisável');
        """
    )
    connection.commit()
    connection.close()

    connection = open_database(path)
    assert connection.execute(
        "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'legado'"
    ).fetchone() == (1,)
    connection.close()
