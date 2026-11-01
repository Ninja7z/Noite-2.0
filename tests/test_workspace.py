from __future__ import annotations

import pytest

from noite.workspace import (
    create_workspace_directory,
    create_workspace_file,
    read_workspace_text,
    save_workspace_text,
    search_workspace_text,
)


def test_read_and_save_text_file_inside_workspace(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("print('before')\n", encoding="utf-8")

    opened = read_workspace_text(tmp_path, source)
    digest = save_workspace_text(tmp_path, source, "print('after')\n", opened.sha256)

    assert source.read_text(encoding="utf-8") == "print('after')\n"
    assert read_workspace_text(tmp_path, source).sha256 == digest


def test_reject_path_outside_workspace(tmp_path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("private", encoding="utf-8")

    with pytest.raises(ValueError, match="fora do projeto"):
        read_workspace_text(tmp_path, outside)


@pytest.mark.parametrize("name", [".env", ".env.local", "api_secret.txt", "id_rsa.key"])
def test_reject_secret_files(tmp_path, name):
    secret = tmp_path / name
    secret.write_text("must not be read", encoding="utf-8")

    with pytest.raises(ValueError, match="segredos"):
        read_workspace_text(tmp_path, secret)


def test_allow_env_example_template(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text("NOITE_MODEL=qwen2.5:3b\n", encoding="utf-8")

    assert read_workspace_text(tmp_path, example).text == "NOITE_MODEL=qwen2.5:3b\r\n"


def test_reject_save_after_external_change(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("original", encoding="utf-8")
    opened = read_workspace_text(tmp_path, source)
    source.write_text("changed externally", encoding="utf-8")

    with pytest.raises(ValueError, match="mudou fora"):
        save_workspace_text(tmp_path, source, "editor change", opened.sha256)


def test_reject_binary_files(tmp_path):
    source = tmp_path / "image.bin"
    source.write_bytes(b"\x00\x01")

    with pytest.raises(ValueError, match="binários"):
        read_workspace_text(tmp_path, source)


def test_preserve_windows_line_endings_and_utf8_bom(tmp_path):
    source = tmp_path / "sample.py"
    source.write_bytes(b"\xef\xbb\xbfprint('one')\r\nprint('two')\r\n")
    opened = read_workspace_text(tmp_path, source)

    save_workspace_text(
        tmp_path,
        source,
        opened.text + "print('three')\n",
        opened.sha256,
        line_ending=opened.line_ending,
        has_utf8_bom=opened.has_utf8_bom,
    )

    assert source.read_bytes() == (
        b"\xef\xbb\xbfprint('one')\r\nprint('two')\r\nprint('three')\r\n"
    )


def test_search_workspace_is_case_insensitive_and_skips_secrets_and_dependencies(tmp_path):
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir()
    source.write_text("first\nNeedle value\n", encoding="utf-8")
    (tmp_path / ".env").write_text("needle private\n", encoding="utf-8")
    dependency = tmp_path / ".venv" / "lib.py"
    dependency.parent.mkdir()
    dependency.write_text("needle dependency\n", encoding="utf-8")

    matches = search_workspace_text(tmp_path, "NEEDLE")

    assert [(match.path, match.line, match.excerpt) for match in matches] == [
        (source.resolve(), 2, "Needle value")
    ]


def test_search_workspace_validates_query(tmp_path):
    with pytest.raises(ValueError, match="1 a 200"):
        search_workspace_text(tmp_path, " ")


def test_create_file_and_directory_without_overwriting(tmp_path):
    created_file = create_workspace_file(tmp_path, "notes.txt")
    created_directory = create_workspace_directory(tmp_path, "notes")
    created_file.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        create_workspace_file(tmp_path, "notes.txt")
    with pytest.raises(FileExistsError):
        create_workspace_directory(tmp_path, "notes")

    assert created_file.read_text(encoding="utf-8") == "keep"
    assert created_directory.is_dir()


@pytest.mark.parametrize("name", ["../escape.txt", ".env", "CON", "folder/file.py"])
def test_reject_invalid_or_sensitive_new_item_names(tmp_path, name):
    with pytest.raises(ValueError):
        create_workspace_file(tmp_path, name)
