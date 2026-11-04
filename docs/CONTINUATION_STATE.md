# Estado de continuidade — evolução Noite 2.0

> **Histórico (não normativo).** Este documento registra o estado de uma data
> específica; hashes, branch e contagens de teste podem não corresponder ao HEAD.
> Para arquitetura e ordem de trabalho, use [README.md](README.md),
> [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) e [ADR/](ADR/).

Atualizado em 2026-11-02 antes da publicação da branch.

## Ambiente preservado

- Worktree: worktree local da branch `ui-correcao` (caminho de máquina omitido).
- Branch: `ui-correcao`.
- Snapshot-base: `2176ec54b4598a303d4fb53f9756bd393aa80ce8`, filho de `b1f2e87`.
- Ambiente virtual existente `.venv` reutilizado; nenhuma dependência foi instalada ou atualizada.
- Ollama local previamente verificado em `http://127.0.0.1:11434`, modelo `qwen2.5:3b`.
- Hardware de referência: i7-3770 sem AVX2, GTX 1660 Super 6 GB, 16 GB DDR3, Windows 11 x64.
- O remoto foi consultado; a branch `origin/ui-correcao` ainda não existia. `origin/main` tem 3 commits que não estão nesta linha de desenvolvimento; nenhum foi integrado.

## Implementação integrada

- Tema escuro, claro e sistema; a sidebar inicia à esquerda e pode ser reposicionada na sessão.
- Command Palette `Ctrl+K`; painel lateral apenas com Destaques, Contexto Atual e Ferramentas. Progresso da geração aparece no chat; pensamento só aparece se enviado pelo modelo.
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
- Mensagem real enviada pelo `ServiceClient` ao Ollama (`qwen2.5:3b`); a resposta `integração real confirmada.` apareceu na UI.
- O status do workspace tinha referência a um atributo removido (`project_label`); foi removida e um teste de regressão foi incluído.
- O plano mestre continua parcialmente incompleto: fases 4–8 têm itens pendentes listados em `EVOLUTION_PROGRESS.md`.

## Validação desta retomada

- `pytest -q`: 222 passaram, 1 ignorado (teste de symlink externo não aplicável no Windows).
- `ruff check .`, `python -m compileall -q src ui run_ui.py tests` e `git diff --check`: passaram.
- Consulta de metadados Hugging Face manual e explícita retornou cinco opções GGUF quantizadas; nenhum modelo foi baixado.
- EXE atual: `dist\Noite.exe` (8.679.768 bytes, SHA-256 `0FCCE2695CCB10B540FA24BA6E67CD8AC70E6905D725E507CF8049EBC221CCD8`). É launcher dependente deste checkout, `.venv`, Python/dependências e Ollama; não é standalone. Atalho de desktop aponta para este build e para `assets\noite.ico`.
- Quatro builds antigos preservados em `dist/` e ignorados pelo Git. Nenhum EXE ou ambiente virtual será publicado.

## Próxima ação exata

Retomar a Fase 4 de `docs\MASTER_PLAN.md` nos itens de indexação incremental e fluxo de proposta/aprovação/undo para escrita; depois implementar e validar as fases 5–8. Ver `docs\EVOLUTION_PROGRESS.md` para limitações e estado detalhado.
