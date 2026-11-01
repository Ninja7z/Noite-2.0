# Estado de continuação

## Objetivo

Construir uma assistente desktop local-first funcional sem executar ações arbitrárias nem publicar sem autorização.

## Concluído nesta etapa

- Interface desktop PySide6 com chat, Enter/Shift+Enter, seleção de modelo por sessão, estado Ollama, histórico e worker em thread.
- Serviço de conversa com respostas determinísticas de saudação, despedida, ajuda, hora, data, status e identidade.
- Conversa livre conectada ao gateway Ollama e contexto limitado às 12 mensagens recentes.
- Geração real pelo gateway e pelo serviço de conversa confirmada com qwen2.5:3b; a geração fria inicial levou cerca de 131 s.
- Persistência SQLite de mensagens com identificador de conversa e migração compatível.
- Pesquisa apenas de nomes no workspace configurado, sem abrir ou ler arquivos.
- Cliente MCP stdio experimental: descoberta, validação JSON Schema, allowlist, timeout e teste com servidor local.
- Documentação de inventário e limites MCP.

## Validação executada

- pytest -q: 27 passaram na validação final.
- ruff check .: passou.
- GUI: smoke test PySide6 offscreen passou; a janela foi criada e o event loop foi iniciado.
- CLI: validado em etapa anterior, permanece acessível com python -m noite --cli.
- Chamada Ollama real: gateway respondeu OK após elevar o timeout configurável para 180 s.

## Pendências

- MCP não está ligado à UI nem ao fluxo do chat. Não há tela de configuração/aprovação de servidores.
- Abertura de aplicativo continua indisponível; pesquisa lista nomes somente no workspace configurado.
- Não há streaming nem botão de cancelamento de geração.
- A interface MCP ainda não permite configurar/inspecionar servidores; a biblioteca de cliente é funcional e testada por stdio.
- Revisar teste de carregamento .env: verifica URL configurada; override de modelo por dotenv não está coberto.
- GUI foi smoke-tested offscreen, sem avaliação visual/interativa em sessão desktop.

## Execução

- Instalar: python -m pip install -e ".[desktop,dev,mcp]".
- GUI: python -m noite.
- CLI: python -m noite --cli.
- Testes: python -m pytest -q.
- Lint: ruff check .

## Git

- Branch atual: codex/stabilize-core.
- Base remota correta: Ninja7z/Noite-2.0, main 9af7993.
- Checkpoint local será criado nesta etapa; branch e PR serão publicados sem merge.
- Não fazer push, merge ou publicar até autorização explícita.

## Próxima ação

Executar testes e Ruff após mudanças finais, revisar diff, criar checkpoint local e entregar estado. Em continuação: ligar a configuração MCP à interface com confirmação explícita.
