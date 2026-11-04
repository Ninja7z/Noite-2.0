# Benchmark exploratório de modelos locais

Data: 04/11/2026  
Hardware: GTX 1660 Super 6 GB, Intel i7-3770, 16 GB DDR3, Windows 11, Ollama.

> Smoke test exploratório, não benchmark científico. As medições incluem carregamento frio e poucas amostras. Não usar tokens/s isoladamente como critério de qualidade.

## Modelos instalados nesta rodada

- `qwen2.5:0.5b` (~397 MB): candidato a classificador/router.
- `qwen2.5:1.5b` (~986 MB): candidato FAST.
- `qwen2.5-coder:1.5b` (~986 MB): candidato a código rápido.
- `deepseek-r1:1.5b` (~1.1 GB): raciocínio leve, já instalado anteriormente.
- `qwen3.5:4b` (~3.3 GB): principal candidato geral, já instalado anteriormente.

Os modelos foram descarregados da VRAM após os testes. Permanecem instalados no Ollama.

## Resultados observados

| Modelo | Primeira resposta | Geração | Observação |
|---|---:|---:|---|
| Qwen 2.5 0.5B | 12,33 s a frio; 0,04–0,48 s nas próximas classificações | 54,5 tok/s na primeira; ~175–200 tok/s nas seguintes | Só 1/5 intenções classificadas corretamente. Não aprovar como router autônomo. |
| Qwen 2.5 1.5B | 9,50 s a frio | 91,6 tok/s | Resposta geral em pt-BR coerente; amostra insuficiente para promoção. |
| Qwen 2.5 Coder 1.5B | 22,00 s a frio | 104,2 tok/s | Gerou função Python correta com type hints e docstring. |
| DeepSeek R1 Distill 1.5B | 26,42 s a frio | 141,7 tok/s | Resposta de raciocínio limitada pelo teto de 150 tokens do teste. |
| Qwen 3.5 4B | 23,75 s a frio no teste nativo corrigido | 48 tokens em 0,92 s após carregar | Resposta correta com `think=false`; sem isso, a chamada de teste anterior preencheu o canal de thinking e deixou o conteúdo visível vazio. |

## Decisões

1. **Não usar o Qwen 2.5 0.5B como autoridade de roteamento.** Ele é muito rápido depois de aquecido, mas errou classificação de código, raciocínio e ferramentas. Uma saída JSON válida não garante uma decisão correta.
2. **O Router principal continua em Python.** Regras determinísticas cuidam de hora/data, abrir aplicativos, operações de arquivo e intenções inequívocas. Um LLM só deve ser consultado quando a intenção for realmente ambígua.
3. **Qwen 2.5 1.5B e Coder 1.5B ficam instalados para experimentos.** Não foram promovidos a modelos padrão com base em uma única amostra.
4. **Qwen 3.5 4B permanece como candidato principal.** O gateway foi corrigido para solicitar `think=false` em conversas normais com Qwen 3.5, preservando thinking explícito quando o fluxo solicitar.
5. **Evitar manter vários especialistas grandes carregados ao mesmo tempo.** Durante o teste combinado, a VRAM chegou perto do limite de 6 GB. O gerenciador deve manter, no máximo, o roteador leve (quando sua qualidade for aprovada) e um especialista ativo. Por ora, o roteamento determinístico evita reservar VRAM para o 0.5B.

## Próximos testes

- Avaliar o Qwen 1.5B como classificador com um conjunto maior e saída estruturada.
- Medir latência quente/fria com várias rodadas e contexto representativo.
- Comparar Qwen 3.5 4B com e sem thinking explícito em tarefas reais.
- Só então promover modelos no `model_selector.py`.
