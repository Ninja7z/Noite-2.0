# Estado de continuação

## Objetivo

Construir uma assistente desktop local-first funcional sem executar ações arbitrárias nem publicar sem autorização.

## Concluído nesta etapa

- Interface desktop PySide6 com chat, Enter/Shift+Enter, seleção de modelo por sessão, estado Ollama, histórico e worker em thread.
- Interface atualizada para o layout escuro de três áreas das referências, mantendo chat, modelo, status, composer, streaming, cancelamento e painel MCP.
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
- Lançador `Noite.exe` construído para a Área de Trabalho; abre o checkout local usando o Python do `.venv` e mantém dados do usuário em `%USERPROFILE%\.noite`.
- Registro do erro `QtWidgets` e dos limites do empacotamento em `docs/BUILD_WINDOWS.md`.

## Validação executada

- pytest -q: 35 testes passaram, incluindo ciclo de vida/cancelamento, streaming do gateway, persistência de resposta parcial e aprovação MCP.
- ruff check .: passou.
- GUI: janela real inspecionada no Windows após a reformulação; status exibiu Ollama conectado e resposta `UI_OK` apareceu no chat. Streaming do Ollama foi observado e cancelado na interface; encerramento ocorreu e resposta parcial foi confirmada no SQLite temporário. Testes offscreen cobrem conexão de sinais, fechamento e cancelamento.
- Lançador desktop: build PyInstaller concluído; o `Noite.exe` em `C:\Users\crist\OneDrive\Desktop` abriu o app. O teste usou dados temporários e preservou `%USERPROFILE%\.noite`.
- CLI: `python -m noite --cli` iniciou, saiu por `/sair` e fez chamada real ao modelo local, retornando `TESTE_OK`.
- CI: a validação previamente registrada para o commit `dc5e2b9`, Ruff, os 35 testes e o smoke test do CLI passaram em Ubuntu e Windows pelo GitHub Actions.
- Congelamento standalone de Qt: não validado; cx_Freeze e PyInstaller reproduziram erro ao importar QtWidgets no teste local, e Nuitka parou ao compilar LiteLLM. O lançador desktop não inclui runtime/dependências.

## Pendências

- MCP está disponível no painel da UI com confirmação por chamada; não é invocado automaticamente pelo modelo. Revisão de permissões e resultados de servidores de terceiros permanece uma decisão consciente do usuário.
- Abertura de aplicativo continua indisponível; pesquisa lista nomes somente no workspace configurado.
- Concluir e validar um empacotamento standalone do app Qt para distribuição a outros PCs.
- Revisar teste de carregamento `.env`: verifica URL configurada; override de modelo por dotenv não está coberto.
- Integração Roblox ainda não implementada; proposta de arquitetura deve priorizar Studio MCP em modo de leitura e aprovação por operação de escrita.
- O cancelamento interrompe o fluxo assíncrono da chamada LiteLLM/Ollama; testes reais cobriram a UI e persistência parcial neste equipamento. Outros provedores/modelos devem ser conferidos ao serem adicionados.

## Execução

- Instalar: python -m pip install -e ".[desktop,dev,mcp]".
- GUI: python -m noite.
- CLI: python -m noite --cli.
- Testes: python -m pytest -q.
- Lint: ruff check .

## Git

- Branch atual: `codex/stabilize-core`.
- Repositório oficial confirmado pelo usuário: `Ninja7z/Noite-2.0`.
- PR #1 (`codex/stabilize-core` → `main`) segue aberto como draft, sem merge; head publicado `dc5e2b9`.
- O `origin` local ainda aponta para `cristnzx/Noite-2.0`; antes de sincronizar, apontá-lo para `https://github.com/Ninja7z/Noite-2.0.git` e conferir novamente o head remoto.

## Próxima ação

A branch local contém mudanças de UI e empacotamento ainda não commitadas. Publicar somente na branch `codex/stabilize-core` do repositório oficial e atualizar o PR #1; manter draft e não fazer merge.
