# Matriz de testes e critérios de aceitação

| Capacidade | Testes automatizados atuais | Critério de aceitação | Estado |
|---|---|---|---|
| Configuração / `.env` | `tests/test_config.py` | URL/modelo carregam; `.env` privado permanece fora do Git | Parcial |
| Normalização | `tests/test_normalization.py` | Preservar texto fora das correções fonéticas explícitas | Passa |
| Roteador | `tests/test_router.py` | Intenções determinísticas não executam ferramentas | Parcial |
| Identidade Noite | `tests/test_assistant.py` | “Quem é você?” nomeia Noite; pergunta do modelo informa valor ativo | Passa |
| Persistência SQLite/FTS5 | `tests/test_store.py` | INSERT/UPDATE/DELETE indexados e migração preserva dados | Passa |
| Conversas independentes | `tests/test_store.py`, `tests/test_ui_lifecycle.py` | A e B têm IDs distintos; mensagens/contexto não cruzam; fechar/abrir restaura ativo | Passa |
| CRUD de conversa | `tests/test_store.py`, `tests/test_ui_lifecycle.py` | criar/listar/abrir/renomear/excluir somente alvo; confirmação antes de excluir | Passa |
| Threading e fechamento | `tests/test_ui_lifecycle.py` | sinais conectados antes do start; fechamento espera operações/cancela de forma segura | Passa |
| Gateway | `tests/test_model_gateway.py` | mocks de sucesso, stream, timeout, conexão e erro sanitizado | Passa |
| MCP | `tests/test_mcp_client.py`, `test_ui_lifecycle.py` | stdio real em servidor de eco; cada chamada exige aprovação e allowlist | Parcial/Passa nos casos cobertos |
| Aprovação MCP | `tests/test_ui_lifecycle.py` | mostrar executável aprovado; detectar alteração da configuração persistida; preservar JSON corrompido | Passa |
| Segurança MCP | `tests/test_mcp_client.py` | validar schema antes de iniciar o processo quando a UI fornece schema; limitar resultado exibido | Passa |
| Configuração Ollama | `tests/test_config.py` | HTTP(S), endpoint local quando `off_grid`, sem credenciais embutidas | Passa |
| Turnos / contexto | `tests/test_assistant.py` | usuário+resposta persistidos atomicamente; erro não deixa user órfão; histórico limitado por caracteres | Passa |
| Workspace/editor | `tests/test_workspace.py`, `tests/test_ui_lifecycle.py` | abre arquivos UTF-8 até 1 MB; bloqueia segredos, binários e caminhos externos; salva com hash para evitar sobrescrita de alteração externa; mantém BOM/EOL; busca local; criação segura sem sobrescrita | Parcial, fatias cobertas passam |
| Busca global no workspace | `tests/test_workspace.py`, `tests/test_ui_lifecycle.py` | busca case-insensitive em thread de fundo, exclui segredos/dependências, aponta caminho/linha e abre resultado no editor | Passa; busca interativa verificada no Windows (2 resultados e abertura de arquivo) |
| Editor avançado | `tests/test_ui_lifecycle.py` cobre busca local | substituição, autocomplete e mais linguagens além de realce básico Python | Parcial |
| Terminal | ainda não existe | saída progressiva, código de saída, cancelamento e UI responsiva | Ausente |
| Diagnósticos/testes integrados | ainda não existe | arquivo/linha clicável e resultado real de lint/teste | Ausente |
| Contexto de projeto | ainda não existe | tarefa multi-arquivo recupera só conteúdo relevante sem `.env` | Ausente |
| Git local UI | ainda não existe | status/diff/histórico corretos; sem ações remotas implícitas | Ausente |
| Roblox Studio | servidor real não confirmado | leitura só do que MCP expuser; nenhuma escrita sem aprovação | Investigação |
| Windows build standalone | `docs/BUILD_WINDOWS.md` | instalação limpa inicia e preserva dados de usuário | Bloqueado / pendente |

## Comandos de regressão

Na raiz do checkout, usando o venv do projeto:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
git diff --check
```

Não marcar como concluído por ausência de traceback: conferir contagem e estado de saída dos comandos.
