# Perfis de modelos Ollama — Noite 2.0-2 (GTX 1660 Super 6 GB)

**Status:** proposta de configuração e roteamento para testes. Este documento não altera o runtime, não baixa modelos e não promove automaticamente nenhum modelo a padrão.

**Hardware de referência:** GTX 1660 Super 6 GB, Intel i7-3770 sem AVX2, 16 GB RAM, Windows 11.

## Inventário local confirmado

Inventário consultado com `ollama list` em 04/11/2026:

| Modelo instalado | Tamanho em disco | Papel possível |
|---|---:|---|
| `qwen2.5:0.5b` | 397 MB | tarefas triviais; não usar como roteador autônomo |
| `qwen2.5:1.5b` | 986 MB | conversa rápida |
| `llama3.2:1b` | 1,3 GB | conversa curta |
| `qwen2.5:3b` | 1,9 GB | conversa geral e fallback |
| `qwen2.5-coder:1.5b` | 986 MB | código simples |
| `qwen2.5-coder:3b` | 1,9 GB | programação |
| `deepseek-r1:1.5b` | 1,1 GB | raciocínio leve |
| `qwen3.5:4b` | 3,3 GB | modelo geral principal e planejamento |
| `gemma3:4b` | 3,4 GB | modelo geral/visão, validar fluxo multimodal |
| `gemma4:e2b` | 4,6 GB | candidato experimental; VRAM muito apertada |
| `gemma4:e4b` | 6,6 GB | não recomendado para offload integral em 6 GB |
| `qwen2.5vl:3b` | 3,2 GB | especialista em visão |
| `nomic-embed-text:latest` | 274 MB | embeddings; não é modelo de conversa |

**Importante:** tamanho em disco não equivale à VRAM necessária. Pesos, cache KV, contexto e buffers também ocupam memória. O tamanho de `gemma4:e2b` já deixa pouca margem para contexto e buffers; usar somente em teste controlado. `gemma4:e4b` excede a VRAM física pelo tamanho do pacote e não deve ser selecionado para execução integral na GPU.

## 1. Perfil RÁPIDO

**Objetivo:** baixa latência, respostas curtas e tarefas simples.

| Prioridade | Modelo | Uso recomendado | Contexto inicial |
|---|---|---|---:|
| 1 | `qwen2.5:1.5b` | conversa curta e perguntas cotidianas | 4K |
| 2 | `llama3.2:1b` | respostas simples e diálogo leve | 4K |
| 3 | `qwen2.5:3b` | respostas rápidas que exigem mais qualidade | 4K |
| 4 | `qwen2.5:0.5b` | classificação auxiliar muito simples, nunca decisão crítica | 2K |
| 5 | `qwen2.5-coder:1.5b` | pequenos trechos e explicações de código | 4K |

Parâmetros iniciais:
- `temperature=0.65`
- `top_p=0.90`
- `top_k=40`
- `min_p=0.05`
- `repeat_penalty=1.05`
- `num_predict=512`
- `think=false` quando o modelo/API oferecer esse controle.

## 2. Perfil INTELIGENTE

**Objetivo:** análise, raciocínio, explicações, pesquisa local e documentos.

| Prioridade | Modelo | Especialidade | Contexto inicial |
|---|---|---|---:|
| 1 | `qwen3.5:4b` | inteligência geral, análise e planejamento | 8K |
| 2 | `deepseek-r1:1.5b` | raciocínio lógico leve e resolução de problemas | 8K |
| 3 | `gemma3:4b` | modelo geral alternativo e tarefas com imagem, se suportadas pelo fluxo | 4K |
| 4 | `qwen2.5:3b` | fallback geral já validado anteriormente | 8K |
| 5 | `gemma4:e2b` | avaliação experimental de raciocínio/multimodalidade; observar VRAM | 4K |
| 6 | `qwen2.5vl:3b` | interpretação de imagens | 4K |

Parâmetros iniciais:
- `temperature=0.60`
- `top_p=0.90`
- `top_k=40`
- `min_p=0.05`
- `repeat_penalty=1.05`
- `num_predict=2048`
- Thinking sob demanda, somente nos modelos e endpoints que anunciarem suporte. Em conversa normal, manter desligado.

## 3. Perfil AGENTE

**Objetivo:** selecionar o modelo adequado para planejar e executar fluxos com ferramentas autorizadas.

| Prioridade | Modelo | Papel no fluxo | Contexto inicial |
|---|---|---|---:|
| 1 | `qwen3.5:4b` | agente principal: interpretar pedido, planejar e solicitar ferramentas | 8K |
| 2 | `qwen2.5-coder:3b` | especialista de programação e revisão de código | 8K |
| 3 | `qwen2.5-coder:1.5b` | pequenas alterações e tarefas de código rápidas | 4K |
| 4 | `qwen2.5:3b` | agente auxiliar para tarefas gerais | 4K |
| 5 | `llama3.2:1b` | subtarefas simples e curtas | 4K |
| 6 | `gemma4:e2b` | candidato experimental para tool calling; validar antes de habilitar | 4K |

Parâmetros iniciais:
- `temperature=0.30`
- `top_p=0.85`
- `top_k=30`
- `min_p=0.05`
- `repeat_penalty=1.05`
- `num_predict=2048`
- Tool calling habilitado somente quando o modelo escolhido demonstrar suporte real no teste de integração.
- Thinking sob demanda; não forçar a saída de raciocínio para o parser de ferramentas.

**Regra de segurança:** o modelo apenas solicita uma ferramenta. A execução continua passando pelo fluxo confiável da Noite (`ToolGuard`, capability, nível de risco, validação e aprovação). Nenhum modelo pode conceder permissões ou executar ferramentas diretamente.

## Configuração global sugerida para a máquina

Aplicar inicialmente em ambiente de teste e medir antes de persistir no Windows:

```powershell
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

- Manter no máximo um modelo de geração carregado por vez; embeddings podem ser descarregados/carregados conforme a necessidade do RAG.
- Não fixar um contexto global alto. Enviar `num_ctx` por perfil/solicitação.
- Flash Attention e KV cache quantizado devem ser confirmados na versão instalada do Ollama.
- Não assumir que `q8_0` ou Flash Attention garantem que qualquer modelo caiba na VRAM.

## Roteamento sugerido

| Tipo de solicitação | Perfil | Modelo inicial |
|---|---|---|
| saudação, pergunta curta, resposta de voz | Rápido | `qwen2.5:1.5b` |
| comando trivial/classificação auxiliar | Rápido | `qwen2.5:0.5b` (não autoritativo) |
| conversa geral mais elaborada | Rápido | `qwen2.5:3b` |
| análise, planejamento e documentos | Inteligente | `qwen3.5:4b` |
| raciocínio lógico específico | Inteligente | `deepseek-r1:1.5b` |
| pergunta com imagem | Inteligente | `qwen2.5vl:3b` ou `gemma3:4b`, após validar o fluxo |
| programação | Agente | `qwen2.5-coder:3b` |
| alteração de arquivos/automação | Agente | `qwen3.5:4b` solicitando ferramentas |
| subtarefa curta | Agente | `llama3.2:1b` |

O roteamento deve permanecer determinístico em Python sempre que a intenção for clara. O LLM não deve escolher suas próprias permissões nem ser a autoridade de segurança. O modelo especialista é selecionado pela categoria; não se carregam todos os especialistas em paralelo.

## Restrições e validação antes de ativar

1. Consultar `/api/show` para cada tag e registrar família, parâmetros, template e capacidades declaradas.
2. Testar separadamente conversa normal, thinking, JSON estruturado, visão e tool calling; não inferir suporte pela família do modelo.
3. Medir latência fria/quente, tokens/s, RAM/VRAM de pico e proporção GPU/CPU via `ollama ps`.
4. Testar contextos 2K/4K/8K e só aumentar quando houver margem real de VRAM.
5. Manter o roteador determinístico atual; o Qwen 0.5B não foi aprovado como roteador autônomo no smoke test de 04/11/2026.
6. Registrar resultados em `docs/MODELS.md` e só então promover modelos no seletor da aplicação.

**Estado da integração:** documento de arquitetura/proposta adicionado. Nenhum código do roteador, seletor, gateway, variável persistente do Windows ou modelo instalado foi alterado por este documento.
