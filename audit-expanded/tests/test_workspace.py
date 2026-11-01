from __future__ import annotations

import pytest

from noite.workspace import (
    create_workspace_directory,
    create_workspace_file,
    read_workspace_text,
    retrieve_workspace_context,
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


def test_project_context_selects_relevant_files_and_excludes_secrets(tmp_path):
    source = tmp_path / "src" / "router.py"
    source.parent.mkdir()
    source.write_text(
        "def classify_intent(text):\n    return route(text)\npassword = 'sensitive-value-123456'\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.txt").write_text("unrelated notes", encoding="utf-8")
    (tmp_path / ".env").write_text("router_intent=private-token", encoding="utf-8")

    context = retrieve_workspace_context(
        tmp_path,
        "explain router intent classification password",
        active_file=".env",
        active_text="private-token",
    )

    assert "src/router.py" in context
    assert "classify_intent" in context
    assert "private-token" not in context
    assert "sensitive-value-123456" not in context
    assert "[REDACTED]" in context
    assert "unrelated notes" not in context
    assert len(context) <= 5_000


def test_project_context_redacts_provider_secrets_and_bearer_tokens(tmp_path):
    source = tmp_path / "settings.py"
    secret = "synthetic-review-secret-value-123"
    source.write_text(
        f'AWS_SECRET_ACCESS_KEY = "{secret}"\n'
        'GITLAB_TOKEN=abc1234\n'
        'Authorization: Bearer synthetic-bearer-value-123\n',
        encoding="utf-8",
    )

    context = retrieve_workspace_context(tmp_path, "AWS_SECRET_ACCESS_KEY GITLAB_TOKEN")

    assert secret not in context
    assert "abc1234" not in context
    assert "synthetic-bearer-value-123" not in context
    bearer_context = retrieve_workspace_context(tmp_path, "Authorization Bearer")
    assert "synthetic-bearer-value-123" not in bearer_context
    assert "[REDACTED]" in bearer_context
    assert context.count("[REDACTED]") >= 2


@pytest.mark.parametrize(
    ("filename", "content", "query", "secret"),
    [
        (
            "database_url.txt",
            "DATABASE_URL=postgres://user:synthetic-db-pass@db/one",
            "database url",
            "synthetic-db-pass",
        ),
        (
            "private_key.txt",
            "PRIVATE_KEY=synthetic-private-key-material",
            "private key",
            "synthetic-private-key-material",
        ),
        (
            "client_secret.txt",
            "CLIENT_SECRET='synthetic-client-secret-value'",
            "client secret",
            "synthetic-client-secret-value",
        ),
        (
            "aws_secret.txt",
            "AWS_SECRET_ACCESS_KEY=synthetic-aws-access-key",
            "aws secret access",
            "synthetic-aws-access-key",
        ),
        (
            "gitlab_token.txt",
            "GITLAB_TOKEN=synthetic-gitlab-token",
            "gitlab token",
            "synthetic-gitlab-token",
        ),
        (
            "api_key.txt",
            'API_KEY="synthetic-api-key-value"',
            "api key",
            "synthetic-api-key-value",
        ),
        (
            "authorization.txt",
            "Authorization: Bearer synthetic-bearer-token",
            "authorization bearer",
            "synthetic-bearer-token",
        ),
        (
            "pem_key.txt",
            "-----BEGIN PRIVATE KEY-----\nsynthetic-pem-material\n-----END PRIVATE KEY-----",
            "private key",
            "synthetic-pem-material",
        ),
        (
            "encrypted_key.txt",
            "-----BEGIN ENCRYPTED PRIVATE KEY-----\n"
            "synthetic-encrypted-key\n"
            "-----END ENCRYPTED PRIVATE KEY-----",
            "encrypted private key",
            "synthetic-encrypted-key",
        ),
        (
            "rsa_key.txt",
            "-----BEGIN RSA PRIVATE KEY-----\nsynthetic-rsa-key\n-----END RSA PRIVATE KEY-----",
            "rsa private key",
            "synthetic-rsa-key",
        ),
        (
            "basic_auth.txt",
            "Authorization: Basic c3ludGhldGljLWJhc2ljLWNyZWRlbnRpYWw=",
            "authorization basic",
            "c3ludGhldGljLWJhc2ljLWNyZWRlbnRpYWw=",
        ),
        (
            "query_password.txt",
            "DATABASE_URL=postgres://db/app?password=synthetic-query-password&sslmode=require",
            "database url",
            "synthetic-query-password",
        ),
        (
            "query_token.txt",
            "DATABASE_URL=postgres://db/app?token=synthetic-query-token&application_name=noite",
            "database url",
            "synthetic-query-token",
        ),
        (
            "client_id.txt",
            "CLIENT_ID=synthetic-client-id-secret # credential",
            "client id credential",
            "synthetic-client-id-secret",
        ),
    ],
)
def test_context_redacts_common_credential_formats(tmp_path, filename, content, query, secret):
    (tmp_path / filename).write_text(content, encoding="utf-8")
    context = retrieve_workspace_context(tmp_path, query)
    assert secret not in context


def test_redaction_preserves_public_config_urls_and_non_sensitive_suffixes(tmp_path):
    source = tmp_path / "public_config.txt"
    source.write_text(
        "PUBLIC_URL=https://example.test/path?theme=dark&lang=pt\n"
        "CLIENT_ID=public-application-id\n"
        "PORT=8080 # keep this comment\n"
        "FEATURE_FLAG=true\n",
        encoding="utf-8",
    )
    context = retrieve_workspace_context(
        tmp_path, "public config url client id port feature flag"
    )
    assert "https://example.test/path?theme=dark&lang=pt" in context
    assert "public-application-id" in context
    assert "# keep this comment" in context
    assert "FEATURE_FLAG=true" in context


def test_redaction_preserves_non_sensitive_url_userinfo(tmp_path):
    source = tmp_path / "url_notes.txt"
    source.write_text(
        "https://label@example.test/path?theme=dark&lang=pt\n",
        encoding="utf-8",
    )
    context = retrieve_workspace_context(tmp_path, "url notes theme")
    assert "https://label@example.test/path?theme=dark&lang=pt" in context


def test_workspace_search_and_context_do_not_follow_external_directory_symlink(tmp_path):
    external = tmp_path.parent / f"{tmp_path.name}-external"
    external.mkdir()
    (external / "outside.py").write_text("needle external_secret_123456", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        link.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks unavailable")

    assert search_workspace_text(tmp_path, "needle") == []
    assert "external_secret_123456" not in retrieve_workspace_context(tmp_path, "needle")


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
