# Inventário do projeto — 2026-11-01

## Checkout e Git

- Checkout: `C:\Users\crist\Noite-2.0\Noite-2.0-canonical`.
- Branch: `codex/stabilize-core`, HEAD local `fc62d00e95699bfc85b3a10872b107f65a04199a`.
- `origin`: `https://github.com/Ninja7z/Noite-2.0.git`.
- PR #1 está aberto como draft e sem merge; GitHub confirmou head remoto `fc62d00` na consulta de 2026-11-01.
- As alterações do trabalho atual são locais e não commitadas. Nenhuma operação remota foi feita.

## Arquitetura atual

- Python 3.11+, UI PySide6, `AssistantService` assíncrono, gateway LiteLLM/Ollama.
- Ollama local configurado em `http://127.0.0.1:11435`, modelo `qwen2.5:3b` (ver configuração efetiva no registro de engenharia).
- Conversas persistentes em SQLite com IDs e FTS5; dados em `%USERPROFILE%\.noite`.
- MCP stdio manual com confirmação humana por descoberta/chamada; o modelo não chama ferramentas automaticamente.
- IDE em início: `ProjectDock` abre workspace, navega a árvore e edita arquivos UTF-8 pequenos em abas PySide6. Salvamento explícito, proteção de hash contra mudanças externas, bloqueio de segredos/binaries/caminhos externos, limite 1 MB e preservação de BOM/EOL.
- Busca global inicial opera em background, filtra segredos/dependências e navega para arquivo/linha.
- Ainda sem terminal, busca dentro do arquivo, diagnósticos, painel de testes, diff/Git UI ou contexto seletivo do workspace conectado ao modelo.
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

## Referências

- Plano vivo: `MASTER_PLAN.md`.
- Auditoria original e evidências: `ENGINEERING_AUDIT.md`.
- Matriz: `TEST_MATRIX.md`.
- Build/launcher: `BUILD_WINDOWS.md`.
- PDFs de referência em `docs/reference/` descrevem material histórico, não funcionalidades implementadas.
