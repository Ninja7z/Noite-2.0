# ADR-001 — Local-first com nuvem opt-in

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (direção), arquitetura, engenharia

## Contexto

- Hardware alvo: i7-3770 (sem AVX2), GTX 1660 Super 6 GB, 16 GB RAM, Windows 11.
- O código atual já usa Ollama como padrão (`model_gateway.ask_local_model`) e o
  GLM apenas como rota opcional (`task_router.route_model` exige categoria
  autorizada, chave e `off_grid=false`).
- Privacidade é requisito de produto, não detalhe: o usuário precisa poder usar a
  Noite sem rede.

## Decisão

O modelo **local é o padrão e o fallback**. Uso de nuvem exige: opt-in explícito
na configuração, categoria de tarefa autorizada, chave presente e ausência de
conteúdo sensível. A nuvem recebe **somente a mensagem atual**, nunca histórico,
contexto de projeto, anexos, memória ou resultados de ferramentas.

## Alternativas consideradas

- **Cloud-first:** melhor qualidade por padrão, mas quebra privacidade, custo
  previsível e funcionamento offline. Rejeitado.
- **Híbrido automático (o roteador decide sempre pela “melhor” resposta):**
  transforma custo e privacidade em imprevisíveis. Rejeitado.
- **Local apenas, sem qualquer rota externa:** mais simples, mas impede tarefas
  auxiliares que o usuário pode querer autorizar. Preterido.

## Consequências

- A qualidade da Noite é limitada pelo modelo local: escolher modelo é decisão
  contínua, medida no hardware alvo (ver `MODEL_ROUTING.md`).
- Toda funcionalidade nova precisa funcionar offline; nuvem é incremento.
- Falha externa nunca pode impedir a conversa (fallback local obrigatório).
- Filtros de dado sensível permanecem heurísticos: o usuário é avisado disso.

## Critério de revisão

Reabrir apenas se o hardware alvo deixar de suportar um modelo local utilizável
(ex.: latência inaceitável para conversa) ou se o proprietário decidir que a
privacidade deixa de ser requisito primário.
