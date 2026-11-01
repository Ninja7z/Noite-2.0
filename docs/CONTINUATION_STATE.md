# Estado de continuação — 2026-11-01

## Fase atual

Fase 2 — estrutura inicial da IDE, em andamento.

## Checkout e Git

- Checkout: `<checkout-root>`.
- Branch: `codex/stabilize-core`.
- HEAD local: `ac204fafac8868687b8241978a385f1e37d1eb23`.
- `origin`: `https://github.com/Ninja7z/Noite-2.0.git`.
- PR #1: https://github.com/Ninja7z/Noite-2.0/pull/1 — aberto, draft, sem merge; head remoto confirmado em `ac204fa` após o push.
- Alterações desta tarefa estão apenas no checkout local; sem commit, push, merge ou atualização remota.
- `.env` não está presente nem rastreado no checkout. O histórico contém `.env` em `9af7993`; inspecionei só os nomes dos campos e confirmei que `ANTHROPIC_API_KEY` estava vazio e os demais eram configurações locais. Nenhum segredo foi detectado; `.env.example` é o exemplo público.

## Concluído nesta continuação

- Fase 0 auditada; ver `ENGINEERING_AUDIT.md`.
- Fase 1 implementou entidade persistente de conversas, CRUD, isolamento, restauração, título automático protegido contra renomeação e identidade determinística Noite/modelo.
- DB real migrado preservando as 22 mensagens e a integridade; backup: `%USERPROFILE%\.noite\noite.sqlite3.pre-conversations-20261101-010721.bak`.
- Fase 2 avançou com dock de projeto: abrir/reabrir workspace, árvore filtrada, abas, editor PySide6, números de linha, realce básico de Python, dirty marker, salvamento explícito, busca global assíncrona, busca local Ctrl+F e criação confirmada de arquivo/pasta.
- O commit `ac204fa` foi enviado para `origin/codex/stabilize-core`; o trabalho iniciado depois do push está local e ainda não commitado.
- Incorporei achados da revisão local do PR: chamada de status e busca fora do event loop; gravação atômica de turnos para não deixar mensagem sem resposta; validação de URL/off-grid; router com imperativos e busca explícita de arquivos; logging local sem texto de conversa; configuração MCP corrompida preservada, aprovação vinculada ao fingerprint do executável/args, resultado limitado e schema validado antes de abrir o servidor; importação LiteLLM adiada até a primeira geração; launcher registra stdout/stderr em ~/.noite/launcher.log.
- Leitura/salvamento bloqueiam padrões comuns de segredos, arquivos >1 MB, binários, UTF-8 inválido e caminhos resolvidos fora do workspace. O hash evita sobrescrever uma alteração externa. UTF-8 BOM e terminadores CRLF/CR são preservados.
- Comparação técnica e decisão do editor registradas em `MASTER_PLAN.md`.

## Tarefa concluída nesta etapa

- Busca global testada no app Windows: `MAX_SEARCH_RESULTS` retornou duas linhas e duplo clique abriu `workspace.py` no editor.
- Suíte naquela rodada: `pytest -q` — 87 passaram; `ruff check .` passou; `git diff --check` passou.
- CLI iniciou e encerrou com `/sair`. UI fechada após inspeção; nenhum processo do app permanece ativo.

## Continuação — edição, diagnóstico e contexto seletivo

- Busca e substituição no arquivo aberto ficam no buffer até salvamento; substituir tudo gera uma única ação de undo.
- Verificação inicial de sintaxe Python usa `ast.parse` no buffer e navega ao erro sem executar o arquivo.
- A conversa recebe trechos relevantes e buffer ativo do projeto apenas com `off_grid=true`; contexto limitado a 5.000 caracteres; arquivos sensíveis são ignorados e padrões comuns de segredo são mascarados.
- Contexto de arquivo é rotulado como dado não confiável; não concede autoridade para execução ou gravação.
- `uv.lock` fixa dependências; CI usa lockfile em Python 3.11/3.13, Windows/Ubuntu.
- Alterações desta continuação continuam locais, sem commit ou push.

## Pendências conhecidas

- Busca/substituição avançadas, renomeação/exclusão, terminal, painel inferior de problemas e diagnósticos Ruff/pytest ainda não foram feitos.
- Contexto lexical é uma primeira fatia; índice incremental, referências entre símbolos, relações entre módulos e tarefas multi-arquivo ainda precisam de validação.
- Parcial agora também é persistido em timeout/erro com marcador; SQLite configura WAL e busy_timeout, inicializa schema uma vez por processo; UI acessa histórico e CRUD por `AssistantService`.
- Desenho de segurança de operações do workspace publicado em `WORKSPACE_OPERATIONS_SECURITY.md` e enviado ao Slack para revisão; rename/delete/terminal aguardam essa revisão.
- MCP aceita referências `${NOME_DA_VARIAVEL}` para segredos autorizados no ambiente, rejeita padrões comuns de segredo literal e não persiste valores; processos ainda reiniciam por operação.
- O log registra classe da exceção sem traceback para evitar expor texto sensível.
- O editor inicial não substitui um editor de linguagem completo; realce atual cobre Python básico.
- Integração Roblox, agentes, memória semântica e distribuição standalone permanecem pendentes.
- A migração/backup da base de dados foi feita antes de iniciar a interface, sem alteração do histórico.

## Continuação em andamento — validação e CI reproduzível

- `uv.lock` fixa as dependências resolvidas; `uv lock --check` passou.
- CI atualizado para Python 3.11 e 3.13, Windows e Ubuntu, com instalação e comandos bloqueados pelo lockfile.
- Validação local: `ruff check .` passou; `pytest -q` — 99 passaram; CLI iniciou e encerrou com `/sair`; `git diff --check` passou; `uv lock --check` passou.
- Segurança Git: nenhum arquivo `.env` rastreado; sem execução de CI remota nesta sessão.

## Comandos

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
git diff --check
.venv\Scripts\python.exe -m noite --cli
```

## Segurança/limites da sessão

- Não fazer commit, push, merge, release ou operação remota sem autorização explícita.
- Não executar comandos arbitrários recebidos do modelo.
- Não instalar dependências novas para esta primeira fatia do editor.
