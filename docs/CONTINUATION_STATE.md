## Aviso de estado — 2026-11-03

O conteúdo abaixo é histórico e não descreve o checkout ativo. Checkout atual:
worktree stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001, HEAD 76d7c91.
Não reutilize hashes, branch, estado remoto, testes ou próximo passo sem nova
verificação. Preserve alterações locais preexistentes.

# Estado de continuidade — evolução Noite 2.0

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


## Atualização de segurança e integração - 2026-11-04

### Linha Git confirmada

- Checkout de trabalho: `baseline/noite-2.0-core-2026-11-03`, HEAD inicial `76d7c91`.
- Branch remota de integração revisada: `origin/integration/audit-2026-11-04`, ponta `ee99075`, oito commits à frente do HEAD inicial.
- Essa branch contém a integração dos PRs #1 a #6. As melhorias úteis foram revisadas e incorporadas seletivamente ao checkout local.
- `origin/audit/local-snapshot-2026-11-01` é um snapshot de auditoria, não uma branch de integração segura: seu diff remove partes substanciais da aplicação atual, interface, assets e documentação. Não fazer merge dessa snapshot.
- Não executar push, commit ou merge até a revisão final de staging. Preservar arquivos locais modificados, scripts auxiliares e backups.

### Segurança e arquitetura

- Terminal: parser AST do PowerShell; caminho restrito com allowlist de comandos somente leitura; modo avançado exige confirmação explícita, capability TERMINAL e aprovação R2 de uso único. O modo avançado não é sandbox e executa com as permissões da conta Windows.
- Execução de ferramentas: importado `GuardedTools` como caminho autorizado para terminal e chamadas MCP na UI. O estado de permissões é recarregado antes da decisão e da execução.
- Auditoria: execução agora atualiza o registro exato da tentativa via ID da linha, evitando que retries com o mesmo request ID sobrescrevam o status errado.
- MCP HTTP: binding fixo em `127.0.0.1`, bearer token obrigatório e validação do resource; o servidor falha fechado se `NOITE_MCP_AUTH_TOKEN` estiver vazio.
- MCP client: referências de ambiente limitadas a prefixos aprovados, com bloqueio adicional de nomes de variáveis sensíveis; argumentos e schemas têm limites e rejeitam referências/padrões não confiáveis.
- Anexos Office: parser `defusedxml`, com DTD/entities/external entities proibidos.
- Workspace: validação de cada componente, rejeição de symlinks/junctions e verificação do caminho final do handle aberto antes de ler.
- FTS5: operadores são tratados como texto literal com parâmetros SQL; limite de resultados validado entre 1 e 100.
- Aprovação: tokens aleatórios, vinculados ao fingerprint exato e consumidos uma única vez; grants expirados são removidos quando novas aprovações são emitidas.
- Redação de contexto: mantidas melhorias para atribuições, JSON, YAML multilinha, PEM, JWT e credenciais em URLs. Detecção genérica de base64/hex não foi adotada por risco de falsos positivos.

### Integração útil do GitHub

- Importados: `GuardedTools`, `PermissionManager.reload()`, definições centralizadas de perfis, `path_guard`, auditoria por tentativa, testes de fronteira de execução e ADR/documentação de arquitetura.
- Task router: consolidada a estimativa de memória/VRAM e corrigida a leitura de tags quantizadas do Ollama; removidas duplicações.
- Orchestrator: removidos stubs antigos de permissões e operações de arquivo sem chamadores no runtime; o pacote `noite.security` permanece como fonte de verdade.
- Empacotamento: `ui/client.py` agora entra no wheel; o teste runner inclui a raiz do projeto no `pythonpath`.
- Dependência runtime adicionada: `defusedxml`.

### Validação final

- Suíte completa: **337 passed, 3 skipped**, exit code 0.
- UI lifecycle: **27 passed**.
- Mascot lifecycle: **8 passed**; testes usam serviço fake para não instanciar múltiplos serviços reais no mesmo processo Qt e evitar crash nativo do teardown no Windows.
- Ruff em `src integrations tests`: aprovado.
- `git diff --check`: aprovado.
- `uv lock --check`: aprovado.
- Wheel: build aprovado; inspeção confirmou `ui/client.py` e o pacote `noite.security` incluídos.

### Próxima ação Git

Fazer revisão final dos arquivos modificados e novos. Não incluir backups `.pre-hardening-*`, scripts temporários `_patch_*`/`_verify_*`, `test_classify.py`, `test_miniastral.py` nem `security-findings.local.md` nos commits. Em seguida, criar commits temáticos, mesclar `origin/integration/audit-2026-11-04` no branch baseline e publicar no upstream do branch baseline. Não mesclar a snapshot `audit/local-snapshot` nem alterar `main` sem nova decisão explícita.

## Continuação Open WebUI - 2026-11-04

- Integração de serviços preservada: API OpenAI-compatible `8765`, Noite Web `8766`, MCP Noite `8767`, MCP Roblox `8768`, Open WebUI `8080`, Ollama `11434`.
- O endpoint `/v1/chat/completions` agora suporta o ciclo nativo de ferramentas: recebe schemas do Open WebUI, encaminha ao Ollama local em `/api/chat`, converte `tool_calls` para OpenAI, recebe mensagens assistant/tool de retorno e reconstrói o formato nativo do Ollama.
- Execução MCP continua no Open WebUI. A API da Noite não executa tools; valida schemas, limita payloads, valida argumentos JSON e rejeita nomes de ferramenta que não foram anunciados.
- Tool calling usa somente o modelo local configurado, atualmente `qwen2.5:3b`; não encaminha schemas nem resultados para Gemini/GLM.
- Smoke test real do modelo gerou `noite_status`; smoke test de round-trip recebeu resultado da ferramenta e respondeu em português. Endpoint completo também foi chamado diretamente em memória e retornou `finish_reason=tool_calls`.
- Testes: suíte completa `365 passed, 3 skipped`; 55 testes direcionados da ponte/MCP passaram. Ruff passou nos arquivos alterados; `compileall` passou. O Ruff global em `.` encontra erros em backups temporários e scripts auxiliares antigos no root, fora dos arquivos alterados. `git diff --check` ainda acusa duas linhas com trailing whitespace em `src/noite/terminal.py`, alteração preexistente e não relacionada à ponte.
- `run_noite.ps1 -Status` confirmou portas 8765, 8766, 8767, 8768 e 8080 indisponíveis; somente Ollama 11434 estava ativo. Nenhum servidor Open WebUI, MCP, Noite Web ou mascote foi iniciado.
- Imagens inline OpenAI `image_url`/`input_image` em data URL PNG/JPEG/WebP agora são convertidas para `images` no Ollama e analisadas pelo modelo local `qwen2.5vl:3b` (configurável por `NOITE_VISION_MODEL`), com limites de tamanho e rejeição de URLs externas. Imagem + tool calling no mesmo turno ainda é bloqueado explicitamente.
- Limites restantes: validação ponta a ponta do RAG/anexos documentais do Open WebUI, áudio bruto/TTS e tool calling Cloud. A validação visual numa conversa salva do Open WebUI ainda não foi feita.
- Próxima ação: fechar o suporte multimodal/RAG de forma segura; depois validar a cadeia visual em Open WebUI quando houver autorização para iniciar os serviços. Não fazer commit, merge ou push sem revisão e decisão explícita.