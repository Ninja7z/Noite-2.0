# Estado de continuação — 2026-11-01

## Fase atual

Fase 2 — estrutura inicial da IDE, em andamento.

## Checkout e Git

- Checkout: `C:\Users\crist\Noite-2.0\Noite-2.0-canonical`.
- Branch: `codex/stabilize-core`.
- HEAD local: `fc62d00e95699bfc85b3a10872b107f65a04199a`.
- `origin`: `https://github.com/Ninja7z/Noite-2.0.git`.
- PR #1: https://github.com/Ninja7z/Noite-2.0/pull/1 — aberto, draft, sem merge; head remoto ainda `fc62d00` na última consulta somente leitura.
- Alterações desta tarefa estão apenas no checkout local; sem commit, push, merge ou atualização remota.
- `.env` não está presente nem rastreado no checkout. O histórico contém `.env` em `9af7993`; inspecionei só os nomes dos campos e confirmei que `ANTHROPIC_API_KEY` estava vazio e os demais eram configurações locais. Nenhum segredo foi detectado; `.env.example` é o exemplo público.

## Concluído nesta continuação

- Fase 0 auditada; ver `ENGINEERING_AUDIT.md`.
- Fase 1 implementou entidade persistente de conversas, CRUD, isolamento, restauração, título automático protegido contra renomeação e identidade determinística Noite/modelo.
- DB real migrado preservando as 22 mensagens e a integridade; backup: `C:\Users\crist\.noite\noite.sqlite3.pre-conversations-20261101-010721.bak`.
- Fase 2 avançou com dock de projeto: abrir/reabrir workspace, árvore filtrada, abas, editor PySide6, números de linha, realce básico de Python, dirty marker, salvamento explícito, busca global assíncrona, busca local Ctrl+F e criação confirmada de arquivo/pasta.
- Incorporei achados da revisão local do PR: chamada de status e busca fora do event loop; gravação atômica de turnos para não deixar mensagem sem resposta; validação de URL/off-grid; router com imperativos e busca explícita de arquivos; logging local sem texto de conversa; configuração MCP corrompida preservada, aprovação vinculada ao fingerprint do executável/args, resultado limitado e schema validado antes de abrir o servidor; importação LiteLLM adiada até a primeira geração; launcher registra stdout/stderr em ~/.noite/launcher.log.
- Leitura/salvamento bloqueiam padrões comuns de segredos, arquivos >1 MB, binários, UTF-8 inválido e caminhos resolvidos fora do workspace. O hash evita sobrescrever uma alteração externa. UTF-8 BOM e terminadores CRLF/CR são preservados.
- Comparação técnica e decisão do editor registradas em `MASTER_PLAN.md`.

## Tarefa concluída nesta etapa

- Busca global testada no app Windows: `MAX_SEARCH_RESULTS` retornou duas linhas e duplo clique abriu `workspace.py` no editor.
- Suíte: `pytest -q` — 85 passaram; `ruff check .` passou; `git diff --check` passou.
- CLI iniciou e encerrou com `/sair`. UI fechada após inspeção; nenhum processo do app permanece ativo.

## Pendências conhecidas

- Substituição dentro do arquivo, renomeação/exclusão de arquivos, terminal, painel inferior, diagnósticos e integração de contexto do projeto com a IA ainda não foram feitos.
- Pendências da revisão: credenciais MCP ainda podem estar em argumentos de processo/configuração; o cliente reabre processo MCP por chamada quando não recebe schema; UI ainda mantém operações locais de conversas no SQLite; o log registra classe da exceção sem traceback para evitar expor texto sensível.
- O editor inicial não substitui um editor de linguagem completo; realce atual cobre Python básico.
- Integração Roblox, agentes, memória semântica e distribuição standalone permanecem pendentes.
- A migração/backup da base de dados foi feita antes de iniciar a interface, sem alteração do histórico.

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
