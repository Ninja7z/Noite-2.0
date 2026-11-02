# Noite 2.0: mascote desktop e avaliação Gemma

Atualizado em 2026-11-02.

## Decisão de interface

O repositório não tem um frontend Node.js ativo (não há `package.json` de aplicação). A interface anterior é Python/PySide6, em `src/noite/ui.py` e `ui/`. Ela foi isolada como legado, sem apagar os módulos nem as builds de backup.

A interface principal passa a ser o mascote desktop flutuante implementado em `src/noite/mascot.py`.

- Robô original em pixel art, branco, visor escuro e olhos ciano/azuis.
- Janela Qt sem moldura e sempre no topo, arrastável pela própria figura.
- Clique abre/recolhe o painel de conversa; a posição é persistida por QSettings.
- Estados visuais: idle, thinking, working, done e error.
- O painel mostra atividade atual, status real do Ollama/modelo, streaming e entrada de mensagem.
- A conversa continua usando AssistantService, SQLite e o gateway local já existente. Não há uma segunda lógica de negócio no mascote.
- As operações MCP continuam com suas próprias políticas de autorização; a animação do mascote não é autorização.
- A UI PySide6 anterior permanece isolada como legado, acessível por `python -m noite --legacy-ui` ou `python run_ui.py --legacy`.

O mascote toma inspiração geral de um pet robótico de mesa, mas o desenho é original e não usa os assets ou a marca EMO/LivingAI.

## Por que isolar, não apagar agora

O checkout tem cinco executáveis em `dist` e múltiplas pastas de build. O launcher atual inicia `python -m noite` dentro deste checkout e do ambiente virtual; não é standalone. Os executáveis antigos também apontam para o mesmo checkout. Excluir `src/noite/ui.py`, componentes e assets agora poderia quebrar a recuperação ou os builds anteriores. O código antigo foi mantido acessível por entrada explícita. Remoção definitiva fica para uma etapa posterior, após validar o mascote e produzir um backup standalone verificável.

## Ambiente de inferência verificado

- CPU: Intel Core i7-3770, sem AVX2.
- GPU: GTX 1660 Super 6 GB.
- RAM: 16 GB DDR3.
- Ollama: 0.40.13.
- VRAM antes dos testes de modelos: cerca de 5,0 GiB livres, com aproximadamente 0,94 GiB já ocupados pelo desktop/driver.
- Modelos preexistentes: `qwen2.5:3b`, `qwen2.5vl:3b`, `deepseek-r1:1.5b`, `qwen3.5:4b`.
- Nenhum modelo existente foi removido ou substituído.

## Pesquisa externa: Gemma 4

O Google documenta Gemma 4 E2B, E4B, 12B, 26B A4B e 31B. O prefixo E significa parâmetros efetivos, não o total de parâmetros armazenados: E4B tem aproximadamente 4,5B efetivos, mas 8B com embeddings. E2B tem aproximadamente 2,3B efetivos, 5,1B com embeddings.

O Gemma 4 tem suporte nativo a function calling estruturado, melhoras em código e raciocínio, entrada de imagem e janela de contexto de 128K para E2B/E4B. E2B e E4B também recebem áudio para ASR e tradução de fala para texto; isso não significa saída de voz/TTS.

Estimativa oficial de memória Q4_0:
- Gemma 4 E2B: 2,9 GB, já incluindo 20% de overhead de carregamento.
- Gemma 4 E4B: 4,5 GB, já incluindo 20% de overhead de carregamento.

A própria documentação esclarece que esses números não incluem o runtime de inferência nem o KV cache/contexto. O E4B fica, portanto, muito próximo do limite prático desta GTX 1660 Super. O i7-3770 sem AVX2 também torna qualquer offload para CPU um risco de latência. O benchmark local abaixo é mais decisivo que a estimativa teórica.

Referências:
- https://ai.google.dev/gemma/docs/core/model_card_4
- https://ai.google.dev/gemma/docs/core?hl=pt-br
- https://ollama.com/library/gemma4

## Pesquisa externa: Gemma 3

Gemma 3 4B é multimodal (texto/imagem), tem contexto de até 128K e tamanho de download no catálogo Ollama de aproximadamente 3,4 GB. A documentação/model card oficial consultada não descreve suporte nativo estruturado a function calling para a família Gemma 3. Por isso, não presumir compatibilidade de tool calling apenas por ser capaz de gerar código.

Há variantes comunitárias fine-tuned para tool calls, como `orieg/gemma3-tools:4b-ft`, mas a própria página descreve foco em chamadas explícitas e otimização para RTX 3090 de 24 GB. Não é recomendação imediata para esta máquina.

FunctionGemma 270M é um modelo especializado para function calling, mas o Google diz que não é destinado a diálogo direto e espera fine-tuning para o conjunto de ferramentas/tarefas específico. Pode ser interessante futuramente como roteador de intenção, não como substituto autônomo do modelo conversacional.

Referências:
- https://ai.google.dev/gemma/docs/core/model_card_3
- https://ollama.com/library/gemma3
- https://ollama.com/orieg/gemma3-tools
- https://ai.google.dev/gemma/docs/functiongemma/model_card

## Plano de avaliação local

Os candidatos devem ser testados pelo mesmo protocolo e não por impressão de conversa:

1. Chamada estruturada de uma ferramenta somente leitura.
2. Receber o resultado real da ferramenta e responder com base nele.
3. Planejar listagem do Studio e usar o UUID retornado, sem inventar identificadores.
4. Escolher a ferramenta correta entre cinco schemas.
5. Encadear duas ou três ferramentas com retorno entre chamadas.
6. Gerar Luau para uma operação de escrita sem executar a mutação.
7. Medir tempo até primeira chamada, tokens/s, RAM, VRAM e erro do runner.

Apenas chamadas realmente devolvidas como tool_calls e executadas pelo MCP contam como sucesso. Texto dizendo "vou usar a ferramenta" não conta.

## Resultado de benchmark local inicial

- `gemma4:e2b` foi baixado pelo Ollama (4,6 GB no catálogo local). Não foi definido como modelo padrão.
- Com uma única ferramenta real, o Gemma 4 E2B produziu `tool_calls` nativo com o nome exato `roblox_studio_list_roblox_studios`.
- Com cinco schemas reais disponíveis, o Gemma 4 E2B executou a sequência real no Roblox MCP: `list_roblox_studios` → recebeu UUID `25993e2f-61b5-4077-ab4c-8b8fe8588eae` → `get_studio_state` com o mesmo UUID → recebeu estado Edit → respondeu com base no retorno.
- A sequência real foi aprovada. Tempos após carregamento: primeira chamada 5,37 s; segunda chamada 0,94 s; resposta final 0,92 s. O primeiro carregamento frio levou cerca de 60,8 s, com 18 tokens de saída e taxa medida de aproximadamente 114 tokens/s após a carga.
- A cadeia real utilizou somente leitura. Nenhum `execute_luau` foi chamado e nenhum objeto foi alterado.
- Durante a execução, a GPU usou cerca de 4.017 MiB, deixando 1.950 MiB livres. Não houve falha do runner.
- `gemma4:e4b` foi baixado (6,6 GB) e também passou a sequência real de cinco ferramentas: `list_roblox_studios` → UUID real → `get_studio_state` → resposta final. Tempos: 104,63 s na primeira chamada fria (18 tokens, 47,6 tokens/s); com modelo aquecido, listagem 13,0 s, estado 5,84 s e resposta final 2,93 s. A GPU chegou a 5.571 MiB usados, deixando apenas 396 MiB livres.
- Comparação direta no mesmo PC e contexto 4096:
  - Gemma 4 E2B: 4,6 GB em disco; cadeia real aprovada; 5,37 s na primeira chamada aquecida, 0,94 s no estado e 0,92 s na resposta final; cerca de 4.017 MiB usados e 1.950 MiB livres.
  - Gemma 4 E4B: 6,6 GB em disco; cadeia real aprovada; 13,0 s / 5,84 s / 2,93 s; cerca de 5.571 MiB usados e 396 MiB livres.
  - Para GTX 1660 Super 6 GB + i7-3770 sem AVX2, E2B é a recomendação prática: menos latência e muito mais folga de VRAM. E4B funciona, mas deixa margem pequena para outras aplicações e demora mais no primeiro carregamento.
- `gemma3:4b` também foi baixado (3,4 GB). O endpoint Ollama rejeitou o payload com ferramenta (HTTP 400); `ollama show gemma3:4b` lista apenas `completion` e `vision`, sem capacidade de tools. Não é candidato a agente MCP nesta instalação.
- Os dois modelos Gemma 4 foram testados com schemas reais de cinco ferramentas e com execução MCP somente leitura. Nenhuma ferramenta de escrita foi chamada.
- O modelo padrão da Noite não foi alterado.

## Estado de validação do mascote

- `src/noite/mascot.py` criado.
- `python -m noite` e `python run_ui.py` passam a abrir o mascote.
- UI anterior acessível com `--legacy-ui` / `--legacy`.
- Teste de estado visual adicionado.
- Smoke test Qt offscreen aprovado: inicialização da janela, clique para expandir, segundo clique para recolher e encerramento limpo.
- Teste ponta a ponta aprovado: envio pelo painel do mascote → AssistantService → Ollama Qwen2.5:3b → streaming → resposta `NOITE_UI_OK` exibida no transcript.
- Esse teste revelou um bug de ciclo de vida no ponteiro do `DiagnosticsWorker` após `deleteLater`; corrigido com limpeza explícita do worker no sinal `finished`. Repetição do teste passou sem traceback.
- Suíte completa: 228 passed, 1 skipped.
- Ruff check: passou em `src`, `ui`, `run_ui.py` e `tests`.
- `compileall`: passou.
- `git diff --check`: passou.
- `ruff format --check` no repositório inteiro aponta 14 arquivos preexistentes não formatados, fora do escopo. Os arquivos alterados nesta etapa foram formatados.
- Ainda falta validar visualmente o posicionamento/arraste no desktop real.
