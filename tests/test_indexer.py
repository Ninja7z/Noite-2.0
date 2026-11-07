"""Testes independentes do módulo indexador (noite.indexer).

Usa diretorios e bancos temporarios. Nunca toca nos dados reais do usuario.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from noite.indexer import (
    MAX_CHUNKS_PER_FILE,
    index_file,
    index_workspace,
    open_index_db,
    search_documents,
    stats_index,
)


@pytest.fixture
def idx_conn(tmp_path: Path):
    db_path = tmp_path / "idx_test.sqlite3"
    conn = open_index_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def workspace(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    yield ws


def test_index_plain_text_file(idx_conn, workspace):
    (workspace / "ola.txt").write_text("Ola mundo, este é um teste de indexacao.", encoding="utf-8")
    result = index_file(idx_conn, workspace, "ola.txt")
    assert result["status"] == "indexed"
    assert result["chunks"] >= 1


def test_search_documents_fts(idx_conn, workspace):
    (workspace / "doc.txt").write_text(
        "A raposa marrom salta sobre o cachorro preguiçoso.", encoding="utf-8"
    )
    index_file(idx_conn, workspace, "doc.txt")

    results = search_documents(idx_conn, "raposa", workspace=workspace)
    assert len(results) >= 1
    assert any("raposa" in r["content"].lower() for r in results)


def test_search_documents_empty_query(idx_conn, workspace):
    assert search_documents(idx_conn, "", workspace=workspace) == []


def test_chunking_splits_long_document(idx_conn, workspace):
    long_text = "Paragrafo um. " * 200
    (workspace / "longo.txt").write_text(long_text, encoding="utf-8")
    result = index_file(idx_conn, workspace, "longo.txt")
    assert result["status"] == "indexed"
    assert result["chunks"] >= 2


def test_respect_max_chunks_per_file(idx_conn, workspace):
    long_text = "Linha de teste. " * 5000
    (workspace / "muito_longo.txt").write_text(long_text, encoding="utf-8")
    result = index_file(idx_conn, workspace, "muito_longo.txt")
    assert result["chunks"] <= MAX_CHUNKS_PER_FILE


def test_update_modified_file(idx_conn, workspace):
    (workspace / "v1.txt").write_text("versao um", encoding="utf-8")
    r1 = index_file(idx_conn, workspace, "v1.txt")
    assert r1["status"] == "indexed"

    (workspace / "v1.txt").write_text("versao dois alterada", encoding="utf-8")
    r2 = index_file(idx_conn, workspace, "v1.txt")
    assert r2["status"] == "indexed"

    results = search_documents(idx_conn, "versao dois", workspace=workspace)
    assert len(results) >= 1
    assert any("versao dois" in r["content"] for r in results)

    results_old = search_documents(idx_conn, "versao um", workspace=workspace)
    assert len(results_old) == 0


def test_unchanged_file_not_reindexed(idx_conn, workspace):
    (workspace / "estatico.txt").write_text("conteudo estatico", encoding="utf-8")
    r1 = index_file(idx_conn, workspace, "estatico.txt")
    assert r1["status"] == "indexed"

    r2 = index_file(idx_conn, workspace, "estatico.txt")
    assert r2["status"] == "unchanged"


def test_remove_deleted_file(idx_conn, workspace):
    (workspace / "temp.txt").write_text("temporario", encoding="utf-8")
    index_file(idx_conn, workspace, "temp.txt")

    (workspace / "temp.txt").unlink()

    stats = index_workspace(idx_conn, workspace)
    assert stats["removed"] >= 1

    results = search_documents(idx_conn, "temporario", workspace=workspace)
    assert len(results) == 0


def test_no_duplicate_indexing(idx_conn, workspace):
    (workspace / "unico.txt").write_text("conteudo unico", encoding="utf-8")
    index_file(idx_conn, workspace, "unico.txt")
    index_file(idx_conn, workspace, "unico.txt")

    results = search_documents(idx_conn, "unico", workspace=workspace)
    assert len(results) <= 2


def test_ignore_binary_file(idx_conn, workspace):
    (workspace / "dados.dat").write_bytes(b"\x00\x01\x02\x03\x04binary")
    result = index_file(idx_conn, workspace, "dados.dat")
    assert result["status"] == "skipped_binary"


def test_ignore_too_large_file(idx_conn, workspace, monkeypatch):
    import noite.indexer as idx_mod

    original = idx_mod.MAX_FILE_BYTES
    idx_mod.MAX_FILE_BYTES = 100
    try:
        (workspace / "grande.txt").write_text("x" * 200, encoding="utf-8")
        result = index_file(idx_conn, workspace, "grande.txt")
        assert result["status"] == "skipped_too_large"
    finally:
        idx_mod.MAX_FILE_BYTES = original


def test_reject_path_outside_workspace(idx_conn, workspace, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("fora do workspace", encoding="utf-8")

    result = index_file(idx_conn, workspace, "../outside.txt")
    assert result["status"] == "rejected"


def test_ignore_secret_files(idx_conn, workspace):
    secret_files = [".env", "id_rsa", "credentials.json", "secrets.json"]
    for name in secret_files:
        (workspace / name).write_text("conteudo secreto", encoding="utf-8")
        result = index_file(idx_conn, workspace, name)
        assert result["status"] == "skipped_sensitive", f"{name} deveria ser sensível"


def test_ignore_dotenv_variants(idx_conn, workspace):
    for name in [".env.local", ".env.production"]:
        (workspace / name).write_text("SECRET=abc", encoding="utf-8")
        result = index_file(idx_conn, workspace, name)
        assert result["status"] == "skipped_sensitive"


def test_index_workspace_stats(idx_conn, workspace):
    (workspace / "a.txt").write_text("arquivo a", encoding="utf-8")
    (workspace / "b.txt").write_text("arquivo b", encoding="utf-8")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "c.txt").write_text("arquivo c", encoding="utf-8")

    stats = index_workspace(idx_conn, workspace)
    assert stats["indexed"] >= 3
    assert stats["errors"] == 0


def test_index_workspace_ignored_dirs(idx_conn, workspace):
    git_dir = workspace / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]", encoding="utf-8")

    node_modules = workspace / "node_modules"
    node_modules.mkdir()
    (node_modules / "pkg.js").write_text("console.log(1);", encoding="utf-8")

    index_workspace(idx_conn, workspace)
    results = search_documents(idx_conn, "console.log", workspace=workspace)
    assert len(results) == 0


def test_stats_index(idx_conn, workspace):
    (workspace / "s1.txt").write_text("estatistica um", encoding="utf-8")
    index_file(idx_conn, workspace, "s1.txt")

    stats = stats_index(idx_conn, workspace=workspace)
    assert stats["files"] >= 1
    assert stats["chunks"] >= 1
    assert stats["total_bytes"] >= 0
