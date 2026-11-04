# Estado da integração MCP

Atualizado em 2026-11-04.

## Transporte e serviços

- Open WebUI instalado: 0.13.0, em `127.0.0.1:8080`.
- O código instalado utiliza MCP HTTP Streamable; não inicia servidores STDIO por `command/args`.
- Roblox Studio mantém o transporte STDIO nativo, publicado pelo `mcp-proxy 0.13.3` em `127.0.0.1:8768` (realocado para liberar `8766` à Noite Web).
- O servidor MCP da Noite é publicado em `127.0.0.1:8767/mcp`.
- A interface web principal da Noite ocupa `127.0.0.1:8766`; por isso o proxy Roblox foi movido para `127.0.0.1:8768`. A URL da conexão `roblox_studio` no banco Open WebUI foi migrada após backup SQLite consistente.
- As conexões cadastradas no Open WebUI usam os IDs `roblox_studio` e `noite_2_0`.

### Portas e inicialização

| Serviço | Endereço local |
|---|---|
| API OpenAI-compatible da Noite | `127.0.0.1:8765` |
| Noite Web | `127.0.0.1:8766` |
| MCP da Noite | `127.0.0.1:8767/mcp` |
| MCP Roblox (proxy) | `127.0.0.1:8768/servers/roblox_studio/mcp` |
| Open WebUI | `127.0.0.1:8080` |
| Ollama | `127.0.0.1:11434` |

`run_noite.ps1` inicia os servidores da Noite, chama o inicializador das duas pontes MCP e inicia o adaptador OpenAI + Open WebUI em modo sem navegador. Não inicia o mascote nem abre janelas. `run_noite.ps1 -Status` apenas consulta as portas e não inicia processos.

- A regra antiga de não integrar com Open WebUI foi arquivada em `docs/archive/AGENTS-legacy-20261102.md`. A diretriz atual permite manter Open WebUI como integração externa, sem tratá-lo como referência visual da interface principal.

## Configuração Open WebUI

- Tool Search permanece ativado, com limite de 400 caracteres.
- Cinco ferramentas Roblox ficam sempre carregadas: `list_roblox_studios`, `get_studio_state`, `get_console_output`, `search_game_tree` e `execute_luau`.
- As outras 29 ferramentas Roblox continuam adiadas e podem ser descobertas por Tool Search.
- As três ferramentas MCP da Noite continuam carregadas diretamente por estarem abaixo do limite.
- `noite_ask` usa uma conversa temporária exclusiva por chamada e a remove ao terminar; não compartilha histórico entre chats/usuários do Open WebUI.
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
- Revalidação do motor em 2026-11-04: `qwen3.5:4b` respondeu ao prompt de apresentação via API local do Ollama; `ollama ps` confirmou `100% GPU`, 3,1 GB no modelo, contexto 4096 e runner `llamacpp`. `nvidia-smi` mostrou 4.297 MiB / 6.144 MiB em uso, GPU a 42 °C. A inferência gerou 3.238 tokens internos/saída em 56,82 tokens/s; a resposta visível apresentou o modelo principal Noite 2.0-2. O comando interativo `ollama run` não exibiu saída no terminal remoto sem TTY, então a resposta foi validada pelo endpoint local equivalente. Isso valida inferência GPU básica, não remove a limitação anterior de chamadas com múltiplos schemas.
- Nenhum dos testes Gemma chamou `execute_luau`; todas as cadeias reais foram somente leitura. Nenhum objeto do jogo foi alterado.
- O modelo padrão da Noite não foi alterado. Gemma4 E2B e E4B estão instalados no Ollama, mas não foram definidos como padrão.

## Perfil de memória Ollama para GTX 1660 Super 6 GB (2026-11-04)

- Estado observado: `qwen3.5:4b` carregado com 3,1 GB, `100% GPU`, contexto 4096, runner `llamacpp`; `nvidia-smi` observou 4.297 MiB / 6.144 MiB em uso e GPU a 42 °C durante a verificação. Isso comprova inferência integral na GPU no cenário testado, não garante todos os tamanhos de contexto ou cargas concorrentes.
- Configuração persistente aplicada no escopo do usuário Windows: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=4096`, `OLLAMA_KEEP_ALIVE=5m`, `OLLAMA_FLASH_ATTENTION=1` e `OLLAMA_KV_CACHE_TYPE=q8_0`. Nenhuma variável de escopo Machine foi alterada.
- Ollama Desktop foi reiniciado após as alterações. API voltou a responder em `127.0.0.1:11434`, versão `0.40.14` (versão estável publicada em 2026-11-03).
- Log do servidor confirmou `Flash Attention enabled` e `flash attention is enabled`; o backend lista suporte a quantizações FA `q8_0-q8_0`. O modelo carregou sem erro após ativar ambas as opções.
- Teste pós-reinício carregou `qwen3.5:4b` com contexto 4096; `ollama ps` confirmou `3.1 GB`, `100% GPU`, runner `llamacpp`, com keep-alive aproximado de 5 minutos. `nvidia-smi` observou 4.350 MiB usados / 1.617 MiB livres e 46 °C durante a inferência. Uma chamada curta mediu 58,58 tokens/s, mas não retornou texto visível com limite de geração de 32 tokens; não usar esse teste isolado como benchmark ou validação de qualidade. A resposta funcional anterior permanece validada pelo teste completo registrado acima.
- `OLLAMA_NUM_PARALLEL=1` explicita o padrão atual de uma requisição por modelo. `OLLAMA_MAX_LOADED_MODELS=1` impede múltiplos modelos residentes, favorecendo a troca sequencial de especialistas em 6 GB.
- Não usar `OLLAMA_KEEP_ALIVE=0` como padrão: descarregar a cada chamada aumenta latência e repetição de carregamentos. Descarregar explicitamente modelos quando necessário.
- Flash Attention e cache KV `q8_0` estão ativos e passaram pelo teste de carregamento. A memória e a qualidade devem continuar sendo monitoradas em contextos maiores e em tarefas reais.
- Arquitetura recomendada para esta GPU: um modelo residente por vez; papéis de especialista podem compartilhar o modelo principal ou alternar sequencialmente entre modelos, em vez de manter três modelos simultâneos. Concorrência de requisições aumenta a memória de contexto; o Ollama pode enfileirar solicitações ou descarregar modelos quando não há memória suficiente.
- Correção do inventário: `nomic-embed-text` aparece com 274 MB no `ollama list` desta máquina, não 78 MB como indicado no guia. A lista local é a referência para o artefato instalado.
- Nenhuma outra variável de ambiente foi alterada; nenhum modelo foi instalado/removido, CrewAI não foi instalado e nenhum agente foi iniciado.

## Próximos passos

1. Criar/validar um perfil Gemma 4 E2B no Open WebUI com function calling nativo e aprovação Ask.
2. Confirmar visualmente, dentro de uma conversa salva do Open WebUI, a cadeia real listagem → UUID → estado. Os testes atuais usaram Ollama e o cliente MCP real com os mesmos schemas, não uma conversa visual do Open WebUI.
3. Depois, implementar uma camada determinística no backend da Noite como guardrail para resolver o Studio, validar UUID, inspecionar antes de alterar e verificar depois.
4. Testar uma operação de escrita somente com pedido concreto e aprovação explícita.

Os endpoints MCP não expõem necessariamente uma rota `/health`; ausência de `/health` não indica falha do transporte. As verificações HTTP de saúde retornaram 200 para Open WebUI e Noite API.


## Ponte de chamadas nativas de ferramentas (2026-11-04)

- O endpoint `/v1/chat/completions` agora recebe schemas OpenAI `tools` do Open WebUI, valida tipo, quantidade, tamanho, nomes e `tool_choice`, e encaminha a solicitação ao endpoint nativo `/api/chat` do Ollama.
- O adaptador converte as chamadas nativas do Ollama para `assistant.tool_calls` no formato OpenAI, tanto em resposta JSON quanto em SSE.
- `tool_choice=required` e a seleção explícita de uma função agora são verificadas na resposta: se o modelo não emitir a chamada exigida ou escolher outra função, a API retorna erro em vez de fingir que cumpriu o contrato.
- O retorno da ferramenta enviado pelo Open WebUI é convertido novamente para o formato de mensagens do Ollama, permitindo o ciclo chamada → execução MCP → resultado → resposta final.
- O adaptador não executa ferramentas. O Open WebUI continua responsável pela execução MCP, pelas permissões da conta e pelo fluxo Ask for approval. Chamadas para ferramentas que não foram anunciadas ao modelo são rejeitadas.
- O caminho de ferramentas usa exclusivamente o modelo local configurado e a API nativa do Ollama. Não envia schemas, histórico ou resultados de ferramentas para Gemini/GLM.
- Imagens inline OpenAI `image_url`/`input_image` em data URL PNG/JPEG/WebP são convertidas para o campo `images` do Ollama e analisadas localmente por `NOITE_VISION_MODEL` (padrão `qwen2.5vl:3b`). Limites: quatro imagens, 4 MB por imagem e 8 MB no total. URLs externas são rejeitadas; imagens e tool calling precisam ser enviados em turnos separados.
- Validação concluída: 55 testes direcionados passaram; a suíte completa passou com 365 testes e 3 skips; Ruff passou nos arquivos alterados; o modelo configurado `qwen2.5:3b` gerou uma chamada real para `noite_status`; uma segunda chamada real recebeu a mensagem assistant/tool e respondeu com base no resultado. O endpoint completo da Noite também foi exercitado diretamente, sem iniciar servidor, e retornou `finish_reason=tool_calls`.
- O caminho de ferramentas não substitui a validação visual final em uma conversa salva do Open WebUI. O serviço Open WebUI não foi iniciado nesta sessão.
- Revalidação incremental desta etapa: os 62 testes de Open WebUI/model gateway passaram, incluindo o caso de modelo de visão ausente; Ruff, compilação Python e `git diff --check` passaram. Nenhum servidor foi iniciado.

### Limitações ainda abertas

- O caminho de chat com imagens é separado do orquestrador padrão e usa o modelo de visão local; o RAG e os anexos documentais do Open WebUI ainda precisam de validação ponta a ponta.
- Chamadas de ferramentas via Gemini/GLM/Cloud não estão habilitadas. O fluxo seguro atual é local.
- Áudio recebido como transcrição textual pode seguir pelo chat normal; o transporte de áudio bruto e TTS integrado não foi validado nesta ponte.

## Recuperação documental e benchmark inicial (2026-11-04)

- A interface desktop já integra `attachments.py`: extrai TXT/MD/JSON/CSV/XML/LOG/YAML, PDF, DOCX, XLSX e PPTX em worker, seleciona trechos relevantes e limita o contexto a 12 mil caracteres por mensagem (até 3 mil por arquivo). O conteúdo é delimitado e explicitamente tratado como dado não confiável.
- A ponte Open WebUI preserva contexto RAG que chega em mensagens `system`/`developer`, limita o material a 12 mil caracteres e o reclassifica como contexto de referência não confiável antes de anexá-lo à mensagem do usuário. O Open WebUI faz a extração/recuperação dos anexos quando File Context está habilitado; o formato exato e a experiência visual ainda precisam de validação ponta a ponta.
- Benchmark exploratório: 40 documentos Markdown, 166 trechos e 10 perguntas. Nomic local obteve Recall@5 0,80 e MRR@5 0,617; SQLite FTS5 obteve Recall@5 0,70 e MRR@5 0,600. A indexação em lote levou 42,9 s; embedding da consulta p50 47,8 ms / p95 65,4 ms.
- O ganho de Recall@5 foi de 10 pontos percentuais (14,3% relativo), abaixo do critério de pelo menos 20% do ADR-004. Não adotar banco vetorial nesta etapa. Repetir com perguntas reais e conjunto maior antes de decidir. Detalhes em `docs/RAG_RETRIEVAL_BENCHMARK_2026-11-04.md`; script reproduzível em `scripts/benchmark_rag_retrieval.py`.
- Validação geral mais recente: 378 testes passaram, 3 foram ignorados e houve um aviso de depreciação do Starlette/httpx. Os 54 testes direcionados de anexos, Open WebUI e store também passaram.
- Nenhum banco vetorial ou dependência foi instalado; nenhum agente ou servidor foi iniciado.

### Observação de residência de modelos durante o benchmark

- O benchmark carregou `nomic-embed-text` localmente. Ao restaurar `qwen3.5:4b`, `ollama ps` mostrou temporariamente os dois modelos residentes, apesar de `OLLAMA_MAX_LOADED_MODELS=1` estar presente no escopo User.
- Para devolver a máquina ao estado esperado de inferência principal, executei `ollama stop nomic-embed-text:latest`. Verificação final: somente `qwen3.5:4b`, 100% GPU, contexto 4096; NVIDIA reportou 4349 MiB usados, 1618 MiB livres e 42 °C.
- **Pendente:** investigar por que o limite de modelos residentes não foi aplicado nessa transição antes de depender dele como garantia rígida. Até lá, descarregar explicitamente o modelo de embeddings após o benchmark.

### Correção de inicialização do Ollama (2026-11-04, verificação efetiva)

- A auditoria do log revelou que a instância anterior do Ollama havia herdado um ambiente antigo do processo Explorer: apesar das variáveis existirem no escopo User, o servidor iniciou com `OLLAMA_MAX_LOADED_MODELS=0`, `OLLAMA_CONTEXT_LENGTH=0`, Flash Attention `false` e KV cache vazio. Portanto, a configuração persistida ainda não estava efetiva naquela instância.
- Corrigi a inicialização: encerrei somente os processos do Ollama e relancei o aplicativo a partir de um processo PowerShell que carregou explicitamente as seis variáveis do escopo User. A API voltou em `0.40.14`.
- O novo log de inicialização confirmou: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=4096`, `OLLAMA_KEEP_ALIVE=5m`, `OLLAMA_FLASH_ATTENTION=true` e `OLLAMA_KV_CACHE_TYPE=q8_0`.
- O runner real do Qwen confirmou `--flash-attn on`, `--cache-type-k q8_0`, `--cache-type-v q8_0`; o log do KV cache reportou 68 MiB no total (34 MiB K + 34 MiB V) para contexto 4096.
- Teste de alternância: carreguei `nomic-embed-text` via `/api/embed` (768 dimensões), depois solicitei Qwen. Com o limite efetivo em 1, `ollama ps` terminou mostrando somente `qwen3.5:4b`, 100% GPU, contexto 4096. Estado final da GPU após o teste anterior: cerca de 4296 MiB usados, 1671 MiB livres, 41 °C.
- A configuração agora está confirmada no processo do servidor e no runner, não apenas no Registro do Windows. Nenhum modelo foi instalado/removido e o modelo padrão da Noite não foi alterado.

- Teste de geração com `think=false` (mesmo modo que o gateway aplica ao Qwen3.5 no chat normal): resposta curta em português concluída, 15 tokens em 252,3 ms, aproximadamente 59,5 tokens/s. Os testes com limite de saída muito baixo e thinking padrão podem consumir o orçamento em raciocínio e deixar `response` vazio; não usar esse caso como benchmark de qualidade.
