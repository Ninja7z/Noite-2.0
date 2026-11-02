# Estado de continuidade — evolução Noite 2.0

Atualizado em 2026-11-01 após testes completos, build e smoke test visual do EXE final.

## Ambiente preservado

- Worktree: `C:\Users\crist\Noite-2.0-worktrees\stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001`.
- Branch: `codex/noite-ui-build`.
- Commit-base: `b1f2e87fb60c9cd1ae8fa7d2c32c5b66d2fb8efa`.
- Ambiente virtual existente `.venv` reutilizado; nenhuma dependência foi instalada ou atualizada.
- Ollama local previamente verificado em `http://127.0.0.1:11434`, modelo `qwen2.5:3b`.
- Hardware de referência: i7-3770 sem AVX2, GTX 1660 Super 6 GB, 16 GB DDR3, Windows 11 x64.
- Nenhum commit, push, merge, reset ou operação remota foi executado.

## Implementação integrada

- Tema escuro, claro e sistema; sidebar esquerda/direita/superior; preferências salvas em `QSettings`.
- Command Palette `Ctrl+K`; painel de contexto/atividade com estados emitidos pelo sistema, duração em tempo real e preferência de exibição.
- Streaming incremental como texto plano; Markdown final é renderizado ao concluir; cancelamento assíncrono e encerramento aguardando workers.
- Terminal PowerShell com workspace obrigatório, allowlist de leitura e caminhos resolvidos dentro do workspace, modo avançado separado, confirmação de comandos destrutivos, ambiente reduzido, timeout, saída limitada e Job Object para a árvore do processo.
- Anexos por botão/drag and drop: TXT, MD, PY, JSON, CSV, XML, LOG, YAML/YML, PDF, DOCX, XLSX e PPTX; extração em background; até quatro arquivos e trechos relevantes limitados por mensagem.
- PDF extraído pelo módulo QtPdf já disponível no PySide6. PDF digitalizado sem texto não tem OCR.
- Gerenciador do Ollama consulta modelos locais e metadados; seleção persistente. Busca Hugging Face é explícita, limitada a metadados e não baixa pesos.
- Ícone `.ico` da lua roxa recortado da marca nas imagens de referência, ligado à janela e ao processo PyInstaller.
- Referências Open WebUI consultadas para padrões de navegação/chat; identidade visual preservada.

## Limites conhecidos

- O catálogo Hugging Face oferece parecer preliminar por tags/tamanho publicado; não afirma benchmark, RAM de execução ou compatibilidade garantida com CPU sem AVX2.
- PDFs sem camada textual não passam por OCR.
- O EXE produzido pelo script é um lançador do checkout e do `.venv`; não é standalone nem inclui Ollama/pesos.
- A conversa real e o início do EXE foram verificados; ainda falta uma matriz visual completa em diferentes larguras e instalação em Windows limpo.
- O status do workspace tinha referência a um atributo removido (`project_label`); foi removida e um teste de regressão foi incluído.
- O plano mestre continua parcialmente incompleto: fases 4–8 têm itens pendentes listados em `EVOLUTION_PROGRESS.md`.

## Validação desta retomada

- `pytest -q`: 209 passaram, 1 ignorado.
- `ruff check .`, `python -m compileall -q src tests` e `git diff --check`: passaram.
- Consulta de metadados Hugging Face manual e explícita retornou cinco opções GGUF quantizadas; nenhum modelo foi baixado.
- EXE testado: `dist\Noite-2.0-Evolution-20261101-final.exe` (8.681.583 bytes, SHA-256 `B9040F23CBF80779B13EF4DC2C690DE722B31D9CABAD31DB8478DDA481A7EC1B`). O launcher exige que este checkout e `.venv` permaneçam disponíveis.
- Dois EXEs anteriores preservados. Nenhum commit, push, merge ou operação remota executada.

## Próxima ação exata

Retomar a Fase 4 de `docs\MASTER_PLAN.md` nos itens de indexação incremental e fluxo de proposta/aprovação/undo para escrita; depois implementar e validar as fases 5–8. Ver `docs\EVOLUTION_PROGRESS.md` para limitações e estado detalhado.
