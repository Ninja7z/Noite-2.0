# Noite 2.0 - checkpoint de emergência
**Data:** 2026-11-06, aproximadamente 14h (horário de Brasília)
**Motivo:** pausa preventiva por tempestade/risco de queda de energia.

## Estado do repositório
- Repositório: https://github.com/Ninja7z/Noite-2.0
- Branch de trabalho/publicação: `baseline/noite-2.0-core-2026-11-03`
- Branch `main`: não foi alterada.
- Último commit remoto verificado antes desta publicação: `61c71eea0904f2f83188ac3073a49af10726090d`.
- Commit local já existente e ainda não publicado ao iniciar esta sessão: `4fe98631df207b85cc88191f33fe4c22979d757b` (`fix: harden symlink checks and terminal validation`).
- O histórico local e remoto estava em fast-forward, sem divergência.
- Esta nota registra o ponto de retomada. Consulte o commit mais recente desta branch para o snapshot de código.

## O que foi alterado nesta sessão
### Backend e Ollama
- `integrations/openwebui/noite_api.py`: verificação leve de prontidão do Ollama antes de iniciar geração em modo local; respostas 503 com mensagens específicas quando Ollama está offline ou sem modelos; tratamento de timeout, falha de conexão e erros de geração.
- `src/noite/config.py`: caminho do `.env` resolvido a partir da raiz do projeto; novo `orchestration_timeout_seconds` com validação.
- `src/noite/assistant.py`: persistência do pedido e de um marcador de cancelamento mesmo quando a geração é cancelada antes do primeiro token.
- Teste de regressão adicionado para cancelamento antes do primeiro token.
- `tests/test_noite_web.py`: health check do Ollama simulado nos testes e cenário de Ollama offline.

### Interface Web
- `landing/assets/app.js`: AbortController para cancelar geração pelo botão Enviar/Cancelar; campo de texto permanece habilitado; permite trocar de conversa e criar nova conversa durante geração; feedback visual de "pensando", erro e cancelamento; botão de tentar novamente quando a geração falha sem produzir texto; recarrega histórico da conversa correta.
- `landing/assets/ux-state.css`: estilos para cancelamento, status e retry.
- `landing/index.html`: cache-busting atualizado para os novos arquivos CSS/JS.
- A restauração UTF-8 do JS e os headers charset/cache-control feitos anteriormente também estão presentes no estado local.

### Inicialização e caminhos
- `run_noite.ps1` e `integrations/openwebui/Start-Noite-OpenWebUI.ps1`: caminhos agora derivados da localização do projeto/diretórios permanentes, logs em Temporarios e host da Noite Web em 0.0.0.0 para permitir acesso LAN (a validação por celular ainda não foi feita).
- `scripts/start_mcp_servers.ps1`: inicializador MCP separado que evita processo duplicado e informa que Roblox MCP ainda não foi restaurado.

## Verificações feitas
- Backend `/health` respondeu HTTP 200.
- Ollama respondeu em `127.0.0.1:11434` e tinha modelos instalados no momento da verificação.
- Smoke test real da API de chat concluiu: HTTP 200, resposta exata `BACKEND_OK_123`, UTF-8 válido e conversa temporária removida.
- Headers verificados:
  - `/` -> `text/html; charset=utf-8`
  - `/assets/app.js` -> `text/javascript; charset=utf-8`
  - `/assets/app.css` -> `text/css; charset=utf-8`
  - `/health` -> JSON, sem cache.
- Ruff e `py_compile` passaram para backend antes das últimas alterações de cancelamento.
- **Pendente:** concluir novamente Ruff, `py_compile`, `node --check` e testes direcionados `test_noite_web.py`, `test_orchestrator.py`, `test_assistant.py`. A suíte completa foi iniciada, mas interrompida por não apresentar progresso no PC lento. Não declarar suíte completa aprovada.
- **Pendente:** validação visual no navegador, testar botão cancelar/retry, navegação entre conversas durante geração e acesso pelo celular na rede local.
- **Pendente:** testar restart pelo `run_noite.ps1` e conferir estado PID/launcher para evitar duplicação.

## Arquivos locais deliberadamente fora do Git
Backups `.bak*`, logs em `Temporarios/Logs`, dumps e artefatos temporários. Não publicar segredos, `.env`, chaves, bancos locais ou dados pessoais.

## Próxima sequência ao retomar
1. Verificar se a energia/PC estabilizou e confirmar que existe apenas um listener na porta 8766.
2. Conferir `git status`, branch e commit remoto antes de qualquer nova publicação.
3. Rodar validações rápidas e direcionadas (Ruff, py_compile, node --check e testes de backend/assistant).
4. Corrigir qualquer regressão encontrada no cancelamento, persistência de histórico, timeout ou health check.
5. Abrir `http://127.0.0.1:8766/` no navegador e validar visualmente a interface; testar pelo celular via IP LAN quando possível.
6. Revisar caminhos e inicializadores MCP/Open WebUI; manter Open WebUI fora do caminho crítico até validação explícita.
7. Só então continuar os ajustes de UX e parâmetros de inferência. Não reduzir `num_ctx` ou aumentar timeouts indiscriminadamente sem medir o modelo e a memória.

## Regras de preservação
- Não alterar `main` nem forçar push.
- Não apagar backups/logs para "limpar" o projeto.
- Não iniciar segunda instância se a porta já estiver ocupada por Noite Web.
- Não publicar arquivos temporários, credenciais ou dados locais.
- Preservar arquitetura e fallback legado definidos em `AGENTS.md`.