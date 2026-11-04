# Arquitetura de sistema — Noite 2.0

**Status:** normativo. Descreve o **estado real** do código no HEAD e o alvo
decidido. Onde os dois divergem, está marcado como dívida.

## Camadas

A separação inegociável é entre **inteligência**, **autorização** e **execução**:

```
Interface (mascote; legado isolado)
        │  sinais Qt / chamada assíncrona
        ▼
Núcleo conversacional  ── AssistantService (assistant.py)
        │                 ├── histórico + conversas (store.py → SQLite/FTS5)
        │                 ├── contexto de projeto (workspace.py)
        │                 └── identidade, personalidade, orçamento de contexto
        ▼
Model Gateway (model_gateway.py)  ── Ollama local │ GLM opcional (opt-in)
        │
        │  o modelo pode PROPOR uma ação (nunca autorizá-la)
        ▼
Autorização (security/)  ── ToolGuard → PolicyEngine → ApprovalManager → AuditLogger
        ▼
Execução  ── workspace (arquivos) │ terminal (PowerShell) │ MCP │ integrações
```

Regra: **o modelo propõe, o código autoriza, o executor executa.** Um componente
de inteligência nunca importa um executor diretamente.

## Mapa de módulos (estado real)

| Módulo | Responsabilidade | Observação de estado |
|---|---|---|
| `contracts.py` | `Intent`, `IntentKind` (chat, open_app, search_file, show/hide mascot) | estável |
| `normalization.py` | normalização de transcrição | estável |
| `router.py` | intenção determinística por regex → `Intent` | estável; **não** usa LLM |
| `assistant.py` | `AssistantService`: `respond`, histórico, CRUD de conversas, identidade, contexto | **sem import de Qt** (invariante válida) |
| `task_router.py` | categoria de tarefa, decisão local/GLM, filtros de dado sensível, estimativa de hardware | determinístico; sem segundo LLM |
| `model_gateway.py` | único ponto que importa `litellm`; Ollama e GLM | adaptador de provedor de fato |
| `store.py` | SQLite: `messages`, `messages_fts` (FTS5 + triggers), `conversations`, `noite_metadata` | sem vetores |
| `workspace.py` | abrir/salvar/criar/buscar arquivos, contexto de projeto, redação de segredos | salvar é atômico (`mkstemp`+`fsync`+`os.replace`) |
| `terminal.py` | PowerShell com Job Object, timeout, limite de saída, modo seguro | **Windows-only** |
| `mcp_client.py` / `mcp_server.py` | cliente/servidor MCP stdio | chamada passa por `ToolGuard` na UI |
| `security/*` | perfis, política, aprovação, auditoria, path guard, painel | ver `SECURITY_ARCHITECTURE.md` |
| `mascot.py` | **interface principal** (flutuante, compacta) | fala com `AssistantService`; não importa gateway |
| `ui.py` + `ui/client.py` + `ide.py` | interface completa anterior (**legado isolado**) | `ide.ProjectDock` só existe aqui |
| `orchestrator.py` | `Agent`, `ChatAgent`, `Orchestrator`, `PermissionLevel` | usado **apenas** por `integrations/openwebui/noite_api.py` |
| `activity.py` / `activity_panel.py` | modelo e painel de atividades | estável |
| `attachments.py` | extração de TXT/MD/JSON/CSV/PDF/DOCX/XLSX/PPTX sem execução | estável |
| `hf_catalog.py` | busca explícita no catálogo Hugging Face | só após ação do usuário |
| `config.py` / `logging_setup.py` / `cli.py` | settings (Pydantic), logs, CLI | estável |
| `integrations/openwebui/noite_api.py` | ponte HTTP local (FastAPI, bearer) | transporte externo, não é a UI |

## Invariantes (o que não pode ser violado)

| # | Invariante | Verificação |
|---|---|---|
| I1 | Núcleo (`assistant`, `store`, `workspace`, `security`) não importa Qt | `grep -rn PySide6` nesses módulos deve retornar vazio |
| I2 | UI não importa `model_gateway`; conversa via `AssistantService` | `grep -rn model_gateway src/noite/mascot.py` vazio |
| I3 | Chamada de rede/modelo fora da thread visual; UI atualiza por sinal Qt | `QThread` em `mascot.py`/`ui.py`; testes de ciclo de vida |
| I4 | Nenhuma ferramenta executa sem `ToolGuard` | parcial: terminal + MCP (PR 002); arquivos do editor pendentes (D1) |
| I5 | Permissão padrão é Sem acesso; política só muda pela interface de configurações | `tests/test_security_core.py` |
| I6 | Conteúdo externo é dado, não instrução; contexto entra rotulado como não confiável | `assistant.respond` (JSON rotulado) + `_redact_secret_values` no limite do modelo |
| I7 | Identidade não depende do provedor ativo | teste de identidade em `tests/test_assistant.py` |

## Fluxos principais

**1. Conversa local:** UI → `AssistantService.respond` → `route` → `route_model`
→ `model_gateway.ask_local_model` (Ollama) → chunks por `on_chunk` → UI insere
texto (em lote) → resposta gravada em `store.add_message`.

**2. Tarefa auxiliar com nuvem (opt-in):** `route_model` exige categoria autorizada
+ chave + `off_grid=false`; conteúdo sensível força local; `ask_glm_model`
**revalida** a autorização antes de enviar. Só a mensagem atual é enviada.

**3. Busca de arquivos:** intenção `SEARCH_FILE` → `tools.search_workspace`
(nomes, sem seguir link) → resposta determinística; não vai ao modelo.

**4. Chamada MCP:** diálogo (UI) → `PolicyEngine` → aprovação do usuário →
`ToolGuard.execute` → `MCPClient.call_tool` → auditoria. Único fluxo já guardado.

**5. Contexto de projeto:** `workspace.retrieve_workspace_context` (lexical,
≤5.000 chars, somente leitura, segredos mascarados) → anexado como **dado não
confiável** na mensagem.

## Dívidas estruturais declaradas (trabalho pendente, não bug oculto)

| # | Dívida | Evidência |
|---|---|---|
| D1 | Terminal e MCP já passam pelo `GuardedTools`; **arquivos do editor** ainda são chamados direto | `tests/test_execution_boundary.py` (allowlist com exceção em `ide.py`) |
| D2 | ~~Dois validadores de caminho divergentes~~ **fechada (PR 003)**: ambos rejeitam symlink/junction por componente | `workspace.resolve_workspace_path`, `security/path_guard.py` |
| D3 | ~~Permissão paralela no orquestrador~~ **fechada (PR 003)**: ordem de perfis vive só em `noite.security` (`PROFILE_ORDER`/`profile_allows`) | `security/permission_manager.py` |
| D4 | IDE completa existe apenas no legado; o mascote não hospeda projeto/editor | `ide.py` importado só por `ui.py` |
| D5 | ~~Auditoria por subquery~~ **fechada (PR 003)**: `record()` devolve o id e o resultado é gravado por `id` | `security/audit_logger.py`, `security/tool_guard.py` |
| D6 | Terminal é Windows-only, mas o CI roda Ubuntu | `terminal.py:1`; 4 testes skipados |
| D7 | `_redact_secret_values` é privado, mas importado por 3 módulos | `assistant.py:33`, `model_gateway.py:15`, `task_router.py:8` |

Essas dívidas estão mapeadas na Fase 1 do `DEVELOPMENT_ROADMAP.md`. D2, D3 e D5
já foram fechadas (PR 003); nenhuma ferramenta nova deve entrar antes de a parte
restante de D1 (arquivos do editor, D7) ser resolvida.
