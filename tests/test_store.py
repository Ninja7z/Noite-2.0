import sqlite3

from noite.store import (
    add_message,
    create_conversation,
    delete_conversation,
    get_active_conversation_id,
    list_conversations,
    open_database,
    recent_messages,
    rename_conversation,
    set_active_conversation_id,
)


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
    assert (
        connection.execute(
            "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'alpha'"
        ).fetchone()
        is None
    )

    connection.close()
    connection = open_database(path)
    assert connection.execute(
        "SELECT content FROM messages WHERE id = ?", (message_id,)
    ).fetchone() == ("beta texto atualizado",)
    connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    connection.commit()
    assert (
        connection.execute(
            "SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'beta'"
        ).fetchone()
        is None
    )
    connection.close()


def test_database_uses_wal_and_busy_timeout(tmp_path):
    connection = open_database(tmp_path / "noite.sqlite3")

    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
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
    assert connection.execute(
        "SELECT title FROM conversations WHERE id = 'default'"
    ).fetchone() == ("Conversa local",)
    assert get_active_conversation_id(connection) == "default"
    connection.close()


def test_conversations_are_isolated_and_active_selection_persists(tmp_path) -> None:
    path = tmp_path / "noite.sqlite3"
    with open_database(path) as connection:
        first_id = get_active_conversation_id(connection)
        add_message(connection, "user", "mensagem da primeira", first_id)
        second_id = create_conversation(connection)
        add_message(connection, "user", "mensagem da segunda", second_id)
        set_active_conversation_id(connection, second_id)

    with open_database(path) as connection:
        assert get_active_conversation_id(connection) == second_id
        assert recent_messages(connection, first_id) == [("user", "mensagem da primeira")]
        assert recent_messages(connection, second_id) == [("user", "mensagem da segunda")]
        assert {item[0] for item in list_conversations(connection)} == {first_id, second_id}


def test_conversation_rename_is_validated_and_prevents_auto_title(tmp_path) -> None:
    with open_database(tmp_path / "noite.sqlite3") as connection:
        conversation_id = create_conversation(connection)
        assert rename_conversation(connection, conversation_id, "  Nome   escolhido  ")
        add_message(
            connection,
            "user",
            "a primeira mensagem não sobrescreve o título",
            conversation_id,
        )
        assert connection.execute(
            "SELECT title, title_locked FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone() == ("Nome escolhido", 1)


def test_deleting_conversation_removes_only_its_messages_and_fts_rows(tmp_path) -> None:
    with open_database(tmp_path / "noite.sqlite3") as connection:
        first_id = get_active_conversation_id(connection)
        second_id = create_conversation(connection)
        add_message(connection, "user", "elefanteazul", first_id)
        add_message(connection, "user", "girassolroxo", second_id)
        set_active_conversation_id(connection, first_id)

        next_active = delete_conversation(connection, first_id)

        assert next_active == second_id
        assert get_active_conversation_id(connection) == second_id
        assert recent_messages(connection, first_id) == []
        assert recent_messages(connection, second_id) == [("user", "girassolroxo")]
        assert (
            connection.execute(
                "SELECT content FROM messages_fts WHERE messages_fts MATCH 'elefanteazul'"
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT content FROM messages_fts WHERE messages_fts MATCH 'girassolroxo'"
            ).fetchone()
            is not None
        )


def test_deleting_last_conversation_creates_a_blank_replacement(tmp_path) -> None:
    with open_database(tmp_path / "noite.sqlite3") as connection:
        only_id = get_active_conversation_id(connection)
        replacement = delete_conversation(connection, only_id)
        assert replacement is not None and replacement != only_id
        assert get_active_conversation_id(connection) == replacement
        assert recent_messages(connection, replacement) == []
