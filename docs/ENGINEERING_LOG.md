# Registro de engenharia

## 2026-11-01 — Auditoria e início da Fase 1

- **Objetivo:** confirmar o estado atual da branch oficial e iniciar gerenciamento persistente de conversas/identidade.
- **Estado inicial:** `codex/stabilize-core` em `fc62d00`; árvore limpa; `origin` é `Ninja7z/Noite-2.0`; PR #1 aberto draft e sem merge.
- **Decisões:** preservar `messages` e seus IDs; migração aditiva para metadados de conversa; usar a conversa legada `default` sem regravar mensagens; garantir identidade/modelo por respostas determinísticas; não ligar modelo a ferramentas ou comandos.
- **Baseline:** Python `.venv` 3.13.16; PySide6 6.12.0; LiteLLM 1.106.6; Ollama HTTP 200 com `qwen2.5:3b`; banco do usuário contém 22 mensagens, todas em `default`; `pytest -q` 35 passed; `ruff check .` passed.
- **Arquivos criados/alterados:** `ENGINEERING_AUDIT.md`, `MASTER_PLAN.md`, `ENGINEERING_LOG.md`, `TEST_MATRIX.md`, `PROJECT_INVENTORY.md`, `CONTINUATION_STATE.md`, além de código/testes da Fase 1 após a implementação.
- **Resultado:** auditoria confirma ausência de conversas CRUD, identidade natural determinística, IDE, terminal integrado, diagnósticos e Git UI. Limites detalhados em `ENGINEERING_AUDIT.md`.
- **Resultado da Fase 1:** migração da base do usuário testada em cópia e aplicada após backup íntegro; conteúdo/contagem das 22 mensagens mantidos. UI verificada e conversas CRUD testadas após reinício.
- **Operações remotas:** nenhuma. Não fazer commit/push/merge sem autorização específica.

## 2026-11-01 — Primeira fatia da Fase 2: workspace e editor

- **Objetivo:** abrir um projeto real, navegar por arquivos e editar com salvamento explícito sem expor arquivos sensíveis.
- **Decisão técnica:** `QPlainTextEdit` + `QSyntaxHighlighter` do Qt, sem nova dependência. A documentação oficial do Qt confirma edição de texto otimizada e suporte ao highlighter; QScintilla requer binding PyQt e tem licença GPLv3/comercial, incompatível com a arquitetura PySide6 atual sem decisão de licença.
- **Arquivos:** `src/noite/ide.py`, `src/noite/workspace.py`, integração `src/noite/ui.py`, `tests/test_workspace.py`, `tests/test_ui_lifecycle.py`, plano e matriz.
- **Implementação:** dock do projeto com caminho visível e persistência local; árvore do sistema de arquivos; abas; numeração de linhas; destaque Python básico; marcador de edição; salvamento acionado pelo usuário; rejeição de segredos comuns, arquivo binário, UTF-8 inválido, >1 MB, caminhos fora do workspace e alteração externa desde a abertura. UTF-8 BOM e CRLF/CR preservados.
- **Segurança:** caminho é resolvido contra o workspace antes de leitura/escrita. Salvamento compara SHA-256 do arquivo antes de substituí-lo e escreve temporário no mesmo diretório com troca atômica.
- **Estado após a rodada final:** suíte integral — 55 passaram; `ruff check .` passou; 9 arquivos tocados passam `ruff format --check`; `git diff --check` passou; CLI iniciou e encerrou com `/sair`.
- **Inspeção visual:** UI abriu o workspace oficial, exibiu a árvore filtrada e permitiu pesquisar `MAX_SEARCH_RESULTS` em 2 ocorrências; duplo clique abriu `workspace.py` no editor. A busca foi concluída sem travar a janela.
- **Pendências:** busca dentro do arquivo, criação/renomeação/exclusão de arquivos, terminal, painel inferior, contexto de projeto da IA e linguagens adicionais permanecem pendentes.
- **Operações remotas:** nenhuma.

## 2026-11-01 — Busca global inicial

- **Objetivo:** localizar texto em arquivos legíveis do workspace sem bloquear a UI e abrir o resultado na linha correspondente.
- **Implementação:** busca case-insensitive limitada a arquivos UTF-8 de até 1 MB, 5.000 arquivos, 100 MB e 1.000 resultados; ignora dependências, caches, segredos, links simbólicos, binários e arquivos ilegíveis. Executa em `QThread`, tem cancelamento e mostra caminho, linha e trecho.
- **Arquivos:** `src/noite/workspace.py`, `src/noite/ide.py`, `tests/test_workspace.py`, `tests/test_ui_lifecycle.py`, documentação de fases/matriz.
- **Validação focal:** 20 testes passaram após retirar o bombeamento de eventos Qt do teste de worker, que causava abortos instáveis. A busca é coberta diretamente e o redirecionamento resultado→linha é coberto no teste do dock. Suíte integral final: 55 passaram; Ruff, `git diff --check` e CLI também passaram. O fluxo interativo foi validado no Windows: 2 resultados para `MAX_SEARCH_RESULTS`; abrir por duplo clique carregou `workspace.py`.
- **Pendências:** busca dentro do arquivo, operações de criação/renomeação/exclusão e terminal ainda pendentes.
- **Operações remotas:** nenhuma.

## 2026-11-01 — Busca local e criação segura no workspace

- **Implementação:** atalho Ctrl+F e busca com retorno ao início no arquivo atual; criação de arquivo/pasta na raiz após confirmação, sem sobrescrever itens existentes. Nomes inválidos, traversal, nomes reservados do Windows e padrões de segredo são rejeitados.
- **Testes:** busca no editor e confirmação/cancelamento da criação exercitados em testes Qt; criação também coberta no nível workspace.
- **Validação atual:** `pytest -q` — 61 passaram; `ruff check .` passou; `git diff --check` passou. CLI pendente de execução nesta rodada.
- **Correção durante validação:** `QShortcut` estava importado de QtWidgets e impedia a coleta dos testes; movido para QtGui, módulo onde existe na versão instalada do PySide6.
- **Pendências:** renomear/excluir, busca/substituição avançadas, terminal, diagnósticos e contexto do projeto da IA.
- **Operações remotas:** nenhuma.


## 2026-11-01 — Correções prioritárias da revisão de segurança

- **Escopo:** comparar o relatório anexado, baseado no head remoto `fc62d00`, com o checkout que também contém alterações locais não publicadas. Mantida a identidade da branch e sem alterar o remoto.
- **Corrigido:** endpoint Ollama limitado a HTTP(S), credenciais URL proibidas e `off_grid` exige host local; status HTTP e busca de workspace executados com `asyncio.to_thread`; workspace inexistente reportado; gravação de turno usuário+assistente em uma transação, sem mensagem órfã em erro; histórico antigo limitado a 6.000 caracteres; roteador entende imperativos e exige referência explícita a arquivos na busca local; UI usa `AssistantService.history`; LiteLLM carregado sob demanda; CLI reaproveita `asyncio.Runner` e trata Ctrl+C na geração; launcher registra stdout/stderr; logs rotativos locais registram tipo da exceção sem conteúdo de conversa/credenciais.
- **MCP corrigido:** confirmação mostra executável no formato Windows; fingerprint de command/args conferido contra configuração em memória e persistida antes de chamar; arquivo inválido preservado como `mcp_servers.json.corrupt`; resultado identificado como não confiável e limitado a 20 mil caracteres; schema transmitido pela UI é validado antes da inicialização do processo.
- **Validação:** `pytest -q` — 85 passaram; `ruff check .` passou; `git diff --check` passou; import da UI não carrega LiteLLM; CLI encerrou com código 0.
- **Limitações conhecidas:** referências de variáveis secretas/keyring para ambientes MCP ainda não implementadas; processo MCP ainda reinicia a cada chamada; áreas da UI ainda acessam SQLite para CRUD local de conversas; o log registra classe da falha sem traceback deliberadamente, para manter a sanitização.
- **Operações remotas:** nenhuma.


## 2026-11-01 — Parcial em falhas, SQLite e revisão de operações

- **Persistência:** WAL e busy_timeout de 5 s; schema inicializado uma vez por caminho de banco/processo; API `AssistantService` agora concentra histórico e CRUD de conversas e a UI deixou de abrir SQLite diretamente.
- **Resiliência:** resposta parcial agora é persistida com marcador também em falha/timeout do provedor, além de cancelamento.
- **Privacidade:** removi dos documentos versionados os caminhos absolutos da máquina e substituí por `<checkout-root>` ou `%USERPROFILE%`.
- **Segurança IDE:** desenho de limites e ameaças registrado em `WORKSPACE_OPERATIONS_SECURITY.md` e enviado ao Slack para revisão. Conforme a revisão da equipe, rename/delete e terminal não serão implementados até receber comentários sobre o desenho.
- **Validação focal:** 32 testes de store/assistant/UI passaram; `ruff check .` passou. Regressão completa após estas alterações ainda pendente.
- **Operações remotas:** nenhuma desde o push `ac204fa`.


## 2026-11-01 — Busca/substituição, sintaxe e contexto de projeto

- **IDE:** busca/substituição no buffer ativo; substituição global é uma ação única de undo e não salva automaticamente.
- **Diagnóstico:** checagem Python via AST no conteúdo atual do editor, com navegação para linha/coluna; não executa o projeto.
- **Contexto:** seleção lexical de trechos do buffer ativo e até três arquivos, limitada a 5.000 caracteres. Habilitada apenas com `off_grid=true`; caminhos sensíveis são ignorados, segredos comuns mascarados e conteúdo declarado como dado não confiável.
- **CI:** lockfile `uv.lock`; matriz Python 3.11/3.13 em Windows/Ubuntu com `uv sync --locked`.
- **Arquivos:** `.github/workflows/ci.yml`, `uv.lock`, docs de engenharia, `src/noite/{assistant,ide,mcp_client,store,ui,workspace}.py` e testes correspondentes.
- **Validação local:** `ruff check .` passou; `pytest -q` — 99 passaram; CLI iniciou/encerrou com `/sair`; `git diff --check` e `uv lock --check` passaram. CI remota ainda não executada.
- **Bloqueios:** rename/delete e terminal seguem aguardando revisão do desenho de segurança no Slack; execução de Roblox e distribuição standalone não foram validadas.
- **Git:** alterações locais ainda não commitadas nesta etapa; sem merge.
