"""Testes independentes do módulo de memória (noite.memory).

Usa diretórios e bancos temporários. Nunca toca nos dados reais do usuário.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from noite.memory import (
    MAX_FACT_CONTENT,
    MAX_FACTS_PER_QUERY,
    MAX_SLOT_LEN,
    forget,
    list_facts,
    open_memory_db,
    purge_expired,
    purge_short_term,
    recall,
    remember,
    search_memory,
)


@pytest.fixture
def mem_conn(tmp_path: Path):
    db_path = tmp_path / "mem_test.sqlite3"
    conn = open_memory_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def conv_id() -> str:
    return "conv-teste-1"


def test_save_and_retrieve_fact(mem_conn, conv_id):
    fact_id = remember(
        mem_conn,
        slot="nome_usuario",
        content="O usuário se chama João.",
        source="user",
        conversation_id=conv_id,
    )
    assert fact_id > 0
    fact = recall(mem_conn, "nome_usuario", conversation_id=conv_id)
    assert fact is not None
    assert fact["content"] == "O usuário se chama João."
    assert fact["source"] == "user"
    assert fact["confidence"] == 1.0


def test_save_and_retrieve_long_content(mem_conn, conv_id):
    content = "A" * MAX_FACT_CONTENT
    fact_id = remember(
        mem_conn, slot="grande", content=content, source="user", conversation_id=conv_id
    )
    assert fact_id > 0
    fact = recall(mem_conn, "grande", conversation_id=conv_id)
    assert fact is not None
    assert len(fact["content"]) == MAX_FACT_CONTENT


def test_content_exceeds_limit_raises(mem_conn, conv_id):
    with pytest.raises(ValueError):
        remember(
            mem_conn,
            slot="grande",
            content="A" * (MAX_FACT_CONTENT + 1),
            source="user",
            conversation_id=conv_id,
        )


def test_update_existing_fact(mem_conn, conv_id):
    remember(
        mem_conn,
        slot="cidade",
        content="São Paulo",
        source="user",
        conversation_id=conv_id,
    )
    remember(
        mem_conn,
        slot="cidade",
        content="Rio de Janeiro",
        source="user",
        conversation_id=conv_id,
    )
    facts = recall(mem_conn, "cidade", conversation_id=conv_id)
    assert facts is not None
    assert facts["content"] == "Rio de Janeiro"
    all_facts = list_facts(mem_conn, conversation_id=conv_id)
    cidades = [f for f in all_facts if f["slot"] == "cidade"]
    assert len(cidades) == 1


def test_deduplicate_identical_content(mem_conn, conv_id):
    id1 = remember(
        mem_conn, slot="dedup", content="mesmo texto", source="user", conversation_id=conv_id
    )
    id2 = remember(
        mem_conn, slot="dedup", content="mesmo texto", source="user", conversation_id=conv_id
    )
    assert id1 == id2


def test_source_confidence_levels(mem_conn, conv_id):
    remember(mem_conn, slot="s_user", content="u", source="user", conversation_id=conv_id)
    remember(mem_conn, slot="s_sys", content="s", source="system", conversation_id=conv_id)
    remember(mem_conn, slot="s_ass", content="a", source="assistant", conversation_id=conv_id)
    remember(mem_conn, slot="s_ext", content="e", source="external", conversation_id=conv_id)

    assert recall(mem_conn, "s_user", conversation_id=conv_id)["confidence"] == 1.0
    assert recall(mem_conn, "s_sys", conversation_id=conv_id)["confidence"] == 0.9
    assert recall(mem_conn, "s_ass", conversation_id=conv_id)["confidence"] == 0.6
    assert recall(mem_conn, "s_ext", conversation_id=conv_id)["confidence"] == 0.2


def test_external_source_cannot_be_promoted(mem_conn, conv_id):
    remember(
        mem_conn,
        slot="ext",
        content="dado externo",
        source="external",
        confidence=0.9,
        conversation_id=conv_id,
    )
    fact = recall(mem_conn, "ext", conversation_id=conv_id)
    assert fact is not None
    assert fact["confidence"] == 0.2


def test_invalid_source_raises(mem_conn, conv_id):
    with pytest.raises(ValueError):
        remember(
            mem_conn,
            slot="bad",
            content="x",
            source="invalido",
            conversation_id=conv_id,
        )


def test_expire_fact(mem_conn, conv_id):
    remember(
        mem_conn,
        slot="temp",
        content="temporario",
        source="user",
        expires_at="2000-01-01 00:00:00",
        conversation_id=conv_id,
    )
    fact = recall(mem_conn, "temp", conversation_id=conv_id)
    assert fact is None
    all_facts = list_facts(mem_conn, conversation_id=conv_id, include_expired=True)
    assert any(f["slot"] == "temp" for f in all_facts)


def test_forget_fact(mem_conn, conv_id):
    remember(mem_conn, slot="esqueca", content="apague-me", source="user", conversation_id=conv_id)
    removed = forget(mem_conn, "esqueca", conversation_id=conv_id)
    assert removed == 1
    fact = recall(mem_conn, "esqueca", conversation_id=conv_id)
    assert fact is None


def test_forget_nonexistent_slot(mem_conn, conv_id):
    removed = forget(mem_conn, "nao_existe", conversation_id=conv_id)
    assert removed == 0


def test_memory_isolated_by_conversation(mem_conn):
    remember(mem_conn, slot="chave", content="conv-a", source="user", conversation_id="conv-a")
    remember(mem_conn, slot="chave", content="conv-b", source="user", conversation_id="conv-b")

    a = recall(mem_conn, "chave", conversation_id="conv-a")
    b = recall(mem_conn, "chave", conversation_id="conv-b")
    assert a is not None and a["content"] == "conv-a"
    assert b is not None and b["content"] == "conv-b"
    all_facts = list_facts(mem_conn)
    assert len(all_facts) == 2


def test_search_memory_fts(mem_conn, conv_id):
    remember(
        mem_conn,
        slot="gato",
        content="O gato está no telhado.",
        source="user",
        conversation_id=conv_id,
    )
    remember(
        mem_conn,
        slot="cachorro",
        content="O cachorro late muito.",
        source="user",
        conversation_id=conv_id,
    )

    results = search_memory(mem_conn, "telhado", conversation_id=conv_id)
    assert len(results) >= 1
    assert any("telhado" in r["content"] for r in results)


def test_search_memory_empty_query(mem_conn, conv_id):
    assert search_memory(mem_conn, "", conversation_id=conv_id) == []


def test_empty_slot_raises(mem_conn, conv_id):
    with pytest.raises(ValueError):
        remember(mem_conn, slot="   ", content="x", source="user", conversation_id=conv_id)


def test_slot_too_long_raises(mem_conn, conv_id):
    with pytest.raises(ValueError):
        remember(
            mem_conn,
            slot="x" * (MAX_SLOT_LEN + 1),
            content="y",
            source="user",
            conversation_id=conv_id,
        )


def test_search_limit_validation(mem_conn, conv_id):
    with pytest.raises(ValueError):
        search_memory(mem_conn, "x", conversation_id=conv_id, limit=0)
    with pytest.raises(ValueError):
        search_memory(mem_conn, "x", conversation_id=conv_id, limit=MAX_FACTS_PER_QUERY + 1)


def test_concurrent_writes(tmp_path: Path):
    """Várias threads gravando com conexoes separadas nao devem corromper o banco."""
    db_path = tmp_path / "mem_conc.sqlite3"
    errors: list[str] = []

    def write_fact(i: int):
        try:
            conn = open_memory_db(db_path)
            try:
                remember(
                    conn,
                    slot=f"conc-{i}",
                    content=f"conteudo {i}",
                    source="user",
                    conversation_id="conv-conc",
                )
            finally:
                conn.close()
        except Exception as exc:
            errors.append(str(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write_fact, i) for i in range(50)]
        for fut in as_completed(futures):
            fut.result()

    assert not errors, f"Erros na concorrencia: {errors}"
    conn = open_memory_db(db_path)
    try:
        facts = list_facts(conn, conversation_id="conv-conc")
    finally:
        conn.close()
    assert len(facts) == 50


def test_concurrent_reads_and_writes(tmp_path: Path):
    """Leituras concorrentes com escritas usando conexoes separadas nao devem falhar."""
    db_path = tmp_path / "mem_rw.sqlite3"
    conn = open_memory_db(db_path)
    remember(conn, slot="base", content="valor", source="user", conversation_id="conv-rw")
    conn.close()

    def reader():
        for _ in range(20):
            c = open_memory_db(db_path)
            try:
                recall(c, "base", conversation_id="conv-rw")
                list_facts(c, conversation_id="conv-rw")
            finally:
                c.close()

    def writer():
        for i in range(20):
            c = open_memory_db(db_path)
            try:
                remember(
                    c,
                    slot=f"rw-{i}",
                    content=f"valor {i}",
                    source="user",
                    conversation_id="conv-rw",
                )
            finally:
                c.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(reader) for _ in range(2)] + [pool.submit(writer)]
        for fut in as_completed(futures):
            fut.result()


def test_purge_expired(mem_conn, conv_id):
    remember(
        mem_conn,
        slot="e1",
        content="expirado 1",
        source="user",
        expires_at="2000-01-01 00:00:00",
        conversation_id=conv_id,
    )
    remember(
        mem_conn,
        slot="e2",
        content="expirado 2",
        source="user",
        expires_at="2000-01-01 00:00:00",
        conversation_id=conv_id,
    )
    remember(
        mem_conn,
        slot="vivo",
        content="ainda vivo",
        source="user",
        conversation_id=conv_id,
    )

    removed = purge_expired(mem_conn)
    assert removed == 2
    assert recall(mem_conn, "vivo", conversation_id=conv_id) is not None


def test_purge_short_term(mem_conn):
    remember(
        mem_conn,
        slot="s1",
        content="curto 1",
        source="user",
        scope="short",
        conversation_id="conv-x",
    )
    remember(
        mem_conn,
        slot="s2",
        content="curto 2",
        source="user",
        scope="short",
        conversation_id="conv-x",
    )
    remember(
        mem_conn, slot="l1", content="longo", source="user", scope="long", conversation_id="conv-x"
    )

    removed = purge_short_term(mem_conn, "conv-x")
    assert removed == 2
    assert recall(mem_conn, "l1", conversation_id="conv-x") is not None
    assert recall(mem_conn, "s1", conversation_id="conv-x") is None


def test_list_facts_filters(mem_conn, conv_id):
    remember(mem_conn, slot="a", content="a", source="user", scope="long", conversation_id=conv_id)
    remember(
        mem_conn, slot="b", content="b", source="external", scope="short", conversation_id=conv_id
    )

    long_only = list_facts(mem_conn, scope="long", conversation_id=conv_id)
    assert len(long_only) == 1
    assert long_only[0]["slot"] == "a"

    high_conf = list_facts(mem_conn, min_confidence=0.5, conversation_id=conv_id)
    assert len(high_conf) == 1
    assert high_conf[0]["slot"] == "a"


def test_list_facts_limit_validation(mem_conn, conv_id):
    with pytest.raises(ValueError):
        list_facts(mem_conn, limit=0)
    with pytest.raises(ValueError):
        list_facts(mem_conn, limit=201)
