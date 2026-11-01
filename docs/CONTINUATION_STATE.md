# Estado de continuação

## Objetivo

Construir uma assistente desktop local-first funcional sem executar ações arbitrárias nem publicar sem autorização.

## Concluído nesta etapa

- Interface desktop PySide6 com chat, Enter/Shift+Enter, seleção de modelo por sessão, estado Ollama, histórico e worker em thread.
- Respostas do Ollama aparecem em streaming por chunks; o botão Cancelar cancela a tarefa assíncrona em execução e o texto parcial permanece no histórico SQLite.
- Handlers dos sinais são conectados antes de iniciar QThread; teste de regressão simula uma tarefa que completa imediatamente.
- Serviço de conversa com respostas determinísticas de saudação, despedida, ajuda, hora, data, status e identidade.
- Conversa livre conectada ao gateway Ollama e contexto limitado às 12 mensagens recentes.
- Geração real pelo gateway e pelo serviço de conversa confirmada com qwen2.5:3b; a geração fria inicial levou cerca de 131 s.
- Persistência SQLite de mensagens com identificador de conversa e migração compatível.
- Pesquisa apenas de nomes no workspace configurado, sem abrir ou ler arquivos.
- Cliente MCP stdio experimental: descoberta, validação JSON Schema, allowlist, timeout e teste com servidor local.
- Painel MCP na UI para configuração local de servidores, descoberta após confirmação e aprovação explícita de cada chamada com visualização dos argumentos.
- Encerramento coordenado da janela: fechamento é adiado até as threads ativas concluírem, sem destruir QThread em execução.
- Workflow GitHub Actions para Ruff, pytest e smoke test do CLI em Ubuntu e Windows.
- Documentação de inventário e limites MCP.

## Validação executada

- pytest -q: 35 testes passaram, incluindo ciclo de vida/cancelamento, streaming do gateway, persistência de resposta parcial e aprovação MCP.
- ruff check .: passou.
- GUI: janela real inspecionada no Windows; status exibiu Ollama conectado. Streaming do Ollama foi observado e cancelado na interface; encerramento ocorreu e resposta parcial foi confirmada no SQLite temporário. Testes offscreen cobrem conexão de sinais, fechamento e cancelamento.
- CI: no commit `2739d3a`, Ruff, os 35 testes e o smoke test do CLI passaram em Ubuntu e Windows pelo GitHub Actions.
- CLI: validado em etapa anterior, permanece acessível com `python -m noite --cli`.
- Chamada Ollama real: gateway respondeu OK após elevar o timeout configurável para 180 s.

## Pendências

- MCP está disponível no painel da UI com confirmação por chamada; não é invocado automaticamente pelo modelo. Revisão de permissões e resultados de servidores de terceiros permanece uma decisão consciente do usuário.
- Abertura de aplicativo continua indisponível; pesquisa lista nomes somente no workspace configurado.
- Revisar teste de carregamento .env: verifica URL configurada; override de modelo por dotenv não está coberto.
- O cancelamento interrompe o fluxo assíncrono da chamada LiteLLM/Ollama; testes reais cobriram a UI e persistência parcial neste equipamento. Outros provedores/modelos devem ser conferidos ao serem adicionados.

## Execução

- Instalar: python -m pip install -e ".[desktop,dev,mcp]".
- GUI: python -m noite.
- CLI: python -m noite --cli.
- Testes: python -m pytest -q.
- Lint: ruff check .

## Git

- Branch atual: codex/stabilize-core.
- Base remota correta: Ninja7z/Noite-2.0, main 9af7993.
- PR #1: https://github.com/Ninja7z/Noite-2.0/pull/1 (draft, sem merge).
- Atualizações desta continuação devem entrar na mesma branch do PR; não fazer merge.

## Próxima ação

Streaming e cancelamento estão publicados no PR draft e passaram no CI em Ubuntu e Windows. Manter o PR aberto para revisão; nenhum merge está autorizado.
