# Estado da integração MCP

Atualizado em 2026-11-02.

## Transporte e serviços

- Open WebUI instalado: 0.12.5, em `127.0.0.1:8080`.
- O código instalado utiliza MCP HTTP Streamable; não inicia servidores STDIO por `command/args`.
- Roblox Studio mantém o transporte STDIO nativo, publicado pelo `mcp-proxy 0.13.3` em `127.0.0.1:8766`.
- O servidor MCP da Noite é publicado em `127.0.0.1:8767/mcp`.
- As conexões cadastradas no Open WebUI usam os IDs `roblox_studio` e `noite_2_0`.
- A regra antiga de não integrar com Open WebUI foi arquivada em `docs/archive/AGENTS-legacy-20261102.md`. A diretriz atual permite manter Open WebUI como integração externa, sem tratá-lo como referência visual da interface principal.

## Configuração Open WebUI

- Tool Search permanece ativado, com limite de 400 caracteres.
- Cinco ferramentas Roblox ficam sempre carregadas: `list_roblox_studios`, `get_studio_state`, `get_console_output`, `search_game_tree` e `execute_luau`.
- As outras 29 ferramentas Roblox continuam adiadas e podem ser descobertas por Tool Search.
- As três ferramentas MCP da Noite continuam carregadas diretamente por estarem abaixo do limite.
- `chat.tool_permissions.enable` permanece ativado.
- A preferência da conta foi definida em `user.settings.ui.params.tool_approval_mode=ask`. Novos chats salvos herdam Ask for approval.
- Para operações Roblox, usar conversas salvas, não Temporary Chat, pois o caminho de aprovação depende de um chat salvo nesta versão instalada.
- Os perfis `qwen2.5:3b` e `qwen253b` continuam com `function_calling=native`, contexto 4096 e temperature 0.1.
- Os system prompts Qwen foram reforçados com nomes exatos das ferramentas e instruções para obter o UUID pela listagem.
- Antes de cada alteração no banco do Open WebUI foi criado um backup SQLite consistente. Os backups estão em `%LOCALAPPDATA%\OpenWebUI\data\` com os prefixos `webui.db.backup-before-noite-tools-*`, `webui.db.backup-before-roblox-prompt-*`, `webui.db.backup-before-qwen-numctx-*`, `webui.db.backup-before-user-approval-default-*` e `webui.db.backup-before-roblox-prompt-v2-*`.

## Validação de ferramentas e modelos

- Descoberta MCP do Roblox: 34 ferramentas.
- A seleção real do Open WebUI foi reproduzida com o código instalado: cinco ferramentas Roblox carregadas diretamente, 29 adiadas; três ferramentas da Noite carregadas diretamente.
- Qwen2.5:3b chama corretamente `roblox_studio_list_roblox_studios` quando essa é a única ferramenta apresentada.
- Limitação Qwen2.5: com cinco ferramentas disponíveis, pode chamar `get_studio_state` antes da listagem e preencher `studio_id` com o texto `list_roblox_studios`. Não é confiável como planejador autônomo para essa sequência.
- Gemma 4 E2B: passou uma cadeia real no Roblox MCP com cinco schemas disponíveis: listou o Studio, recebeu UUID real, chamou `get_studio_state` com esse UUID, recebeu o estado Edit e respondeu com base no retorno.
- Gemma 4 E4B: também passou a mesma cadeia real, somente leitura.
- Comparação no PC atual, contexto 4096:
  - E2B: 4,6 GB em disco; cadeia real aprovada; chamadas aquecidas de 5,37 s, 0,94 s e 0,92 s; cerca de 4.017 MiB de VRAM usados, 1.950 MiB livres.
  - E4B: 6,6 GB em disco; cadeia real aprovada; chamadas aquecidas de 13,0 s, 5,84 s e 2,93 s; cerca de 5.571 MiB de VRAM usados, apenas 396 MiB livres.
  - E2B é a recomendação prática para a GTX 1660 Super 6 GB. E4B funciona, mas deixa margem muito pequena para outros aplicativos.
- Gemma 3 4B: o endpoint Ollama rejeitou a definição de ferramenta com HTTP 400. Não é candidato a agente MCP nesta instalação.
- Qwen3.5:4b continua experimental. Com uma ferramenta funcionou; com cinco schemas alterou o nome de ferramenta e, em outro teste, o runner encerrou com `GGML_ASSERT(ctx->mem_buffer != NULL)` / `0xc0000409`.
- Nenhum dos testes Gemma chamou `execute_luau`; todas as cadeias reais foram somente leitura. Nenhum objeto do jogo foi alterado.
- O modelo padrão da Noite não foi alterado. Gemma4 E2B e E4B estão instalados no Ollama, mas não foram definidos como padrão.

## Próximos passos

1. Criar/validar um perfil Gemma 4 E2B no Open WebUI com function calling nativo e aprovação Ask.
2. Confirmar visualmente, dentro de uma conversa salva do Open WebUI, a cadeia real listagem → UUID → estado. Os testes atuais usaram Ollama e o cliente MCP real com os mesmos schemas, não uma conversa visual do Open WebUI.
3. Depois, implementar uma camada determinística no backend da Noite como guardrail para resolver o Studio, validar UUID, inspecionar antes de alterar e verificar depois.
4. Testar uma operação de escrita somente com pedido concreto e aprovação explícita.

Os endpoints MCP não expõem necessariamente uma rota `/health`; ausência de `/health` não indica falha do transporte. As verificações HTTP de saúde retornaram 200 para Open WebUI e Noite API.
