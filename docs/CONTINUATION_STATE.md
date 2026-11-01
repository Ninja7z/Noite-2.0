# Estado de continuação

## Objetivo

Construir uma assistente desktop local-first funcional sem executar ações arbitrárias nem publicar sem autorização.

## Concluído nesta etapa

- Interface desktop PySide6 com chat, Enter/Shift+Enter, seleção de modelo por sessão, estado Ollama, histórico e worker em thread.
- Serviço de conversa com respostas determinísticas de saudação, despedida, ajuda, hora, data, status e identidade.
- Conversa livre conectada ao gateway Ollama e contexto limitado às 12 mensagens recentes.
- Persistência SQLite de mensagens com identificador de conversa e migração compatível.
- Cliente MCP stdio experimental: descoberta, validação JSON Schema, allowlist e timeout.
- Documentação de inventário e limites MCP.

## Validação executada

- pytest -q: 22 passaram.
- ruff check .: passou.
- GUI: smoke test PySide6 offscreen passou; a janela foi criada e o event loop foi iniciado.
- CLI: validado em etapa anterior, permanece acessível com python -m noite --cli.
- Chamada Ollama real: tentativa anterior excedeu timeout 30 s; ainda não há confirmação de geração bem-sucedida nesta etapa.

## Pendências

- MCP não está ligado à UI nem ao fluxo do chat. Não há tela de configuração/aprovação de servidores.
- Ferramentas locais de arquivo e abertura de aplicativo continuam indisponíveis.
- Não há streaming nem botão de cancelamento de geração.
- Validar chamada real ao Ollama no endpoint/modelo atual.
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
- Alterações desta etapa estão locais e sem commit ainda.
- Não fazer push, merge ou publicar até autorização explícita.

## Próxima ação

Executar testes e Ruff após mudanças finais, revisar diff, criar checkpoint local e entregar estado. Em continuação: validar geração Ollama, depois ligar a configuração MCP à interface com confirmação explícita.
