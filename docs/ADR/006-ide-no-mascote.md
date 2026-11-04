# ADR-006 — A IDE entra no mascote como painel com abas (em fatias)

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (decisão), arquitetura
- **Relaciona-se a:** ADR-002 (mascote é a interface principal)

## Contexto

- O `ADR-002` fixou o mascote como interface principal, mas deixou em aberto como
  o fluxo de projeto (árvore de arquivos, editor, terminal) entra na experiência
  principal — `UI_ARCHITECTURE.md` listava as opções A/B/C.
- Hoje `ide.py` (`ProjectDock`) só é importado por `ui.py` (legado). O mascote é
  uma janela de 136×136 que expande um painel compacto de conversa.
- Sem essa decisão, a Fase 5 não pode ser planejada nem aceita.

## Decisão

**Opção A:** o mascote expande para um painel com abas **Conversa · Atividade ·
Projeto**, em fatias incrementais:

1. **Fatia 1 (read-only):** árvore do workspace + visualização de arquivo (somente
   leitura), reaproveitando `workspace.read_workspace_text` sob o caminho único de
   autorização (`ToolGuard`, PR 002).
2. **Fatia 2 (edição controlada):** editar/salvar com proposta, aprovação e undo
   (Fase 4/PR 006), sem regressão do editor atual.
3. **Fatia 3 (terminal):** terminal restrito ao workspace, atrás do `ToolGuard`,
   nunca por caminho direto.

Enquanto a paridade não existir, o `ProjectDock` do legado permanece funcional e
intocado; a remoção do legado não faz parte desta decisão.

## Alternativas consideradas

- **B — janela de projeto separada:** menos risco visual, porém mantém duas
  janelas e a fragmentação que a visão de produto quer eliminar. Preterida.
- **C — projeto só no legado:** mais barato agora, mas contraria o ADR-002 (o
  usuário precisaria de duas interfaces para trabalhar). Rejeitada.

## Consequências

- `ide.py` será portado em fatias; nada é reescrito "de uma vez".
- O painel do mascote precisa suportar abas e conteúdo pesado sem travar a UI:
  leitura de arquivo e busca continuam **fora** da thread visual.
- Critérios de aceite da Fase 5 passam a incluir: abrir projeto, visualizar arquivo
  e editar/salvar com aprovação — tudo sem abrir o legado.
- Risco aceito: painel único em tela pequena pode ficar apertado; medir em DPI
  100%/150% antes de promover.

## Critério de revisão

Se a validação manual em hardware alvo mostrar que o painel único prejudica o uso
em telas pequenas (ou que a árvore+editor tornam a conversa secundária), reabrir
com dados de uso — a alternativa B fica registrada como plano de contingência.
