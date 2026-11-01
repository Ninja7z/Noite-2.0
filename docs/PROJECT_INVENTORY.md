# Inventário do projeto — 2026-11-01

## Checkout e Git

- Checkout: `<checkout-root>`.
- Branch: `codex/stabilize-core`, HEAD local `ac204fafac8868687b8241978a385f1e37d1eb23`; mudanças posteriores estão locais e sem commit.
- `origin`: `https://github.com/Ninja7z/Noite-2.0.git`.
- PR #1 está aberto como draft e sem merge; último head remoto confirmado `ac204fa`. Mudanças seguintes ainda não foram publicadas.
- As alterações do trabalho atual são locais e não commitadas. Nenhuma operação remota foi feita.

## Arquitetura atual

- Python 3.11+, UI PySide6, `AssistantService` assíncrono, gateway LiteLLM/Ollama.
- Ollama local configurado em `http://127.0.0.1:11435`, modelo `qwen2.5:3b` (ver configuração efetiva no registro de engenharia).
- Conversas persistentes em SQLite com IDs e FTS5; dados em `%USERPROFILE%\.noite`.
- MCP stdio manual com confirmação humana por descoberta/chamada; o modelo não chama ferramentas automaticamente.
- IDE em início: `ProjectDock` abre workspace, navega a árvore e edita arquivos UTF-8 pequenos em abas PySide6. Salvamento explícito, busca/substituição no buffer, criação confirmada, AST Python, proteção de hash, bloqueio de arquivos sensíveis e caminhos externos, limite 1 MB e preservação de BOM/EOL.
- Busca global inicial opera em background, filtra segredos/dependências e navega para arquivo/linha.
- Contexto seletivo lê buffer e trechos relevantes no modo off-grid; limita tamanho e mascara segredos comuns.
- Ainda sem terminal, rename/delete, diagnósticos Ruff/pytest, painel de testes, diff/Git UI ou indexação simbólica.
- Não há execução arbitrária de comando pelo modelo.

## Dados do usuário

- DB existente migrado aditivamente; 22 mensagens preservadas.
- Backup pré-migração guardado em `%USERPROFILE%\.noite\noite.sqlite3.pre-conversations-20261101-010721.bak`.
- Workspace recente salvo localmente via `QSettings`; não armazena conteúdo do projeto.
- `.env` não está presente nem rastreado no checkout; houve um `.env` histórico em `9af7993` com chave Anthropic vazia e configurações locais, sem segredo detectado. Nunca copiar segredos de projeto para contexto/LLM.

## Validação registrada

- Baseline antes da implementação: 35 testes e Ruff passaram.
- Após a Fase 1: 42 testes, Ruff, diff check e CLI `/sair` passaram.
- Fase 2 inicial: `pytest -q` — 55 passaram; Ruff, formatação dos arquivos tocados, `git diff --check` e smoke do CLI passaram. Busca validada visualmente no Windows; veja `ENGINEERING_LOG.md`.
- Continuação atual: `pytest -q` — 99 passaram; Ruff, `git diff --check`, `uv lock --check` e CLI passaram. CI remota não executada.

## Referências

- Plano vivo: `MASTER_PLAN.md`.
- Auditoria original e evidências: `ENGINEERING_AUDIT.md`.
- Matriz: `TEST_MATRIX.md`.
- Build/launcher: `BUILD_WINDOWS.md`.
- PDFs de referência em `docs/reference/` descrevem material histórico, não funcionalidades implementadas.
