# ADR-002 — Mascote é a interface principal

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (direção), arquitetura

## Contexto

- `docs/AGENTS.md` já declara o mascote flutuante como interface principal e a
  interface anterior como legado isolado.
- O mascote (`mascot.py`) já é funcional: converte pedidos em
  `AssistantService.respond`, mostra estado/atividade, expande painel de conversa,
  persiste posição e não importa o gateway de modelo.
- O dashboard anterior (`ui.py`, ~3.178 linhas) contém recursos que o mascote **não**
  tem: sidebar de conversas, editor (`ide.py`), terminal, Command Palette, temas.
- A validação visual manual em Windows continua pendente
  (`EVOLUTION_PROGRESS.md`).

## Decisão

O mascote é a experiência principal do produto. O dashboard permanece disponível
como **legado isolado** (`--legacy`/`--legacy-ui`), sem ser removido, até que a
interface nova seja validada em uso real. Remoção futura exige inventário de
dependências e plano de rollback.

Dashboard administrativo **não** é prioridade de investimento.

## Alternativas consideradas

- **Dashboard como interface principal:** contradiz a identidade do produto
  (assistente de companhia, não painel de controle). Rejeitado.
- **Duas aplicações equivalentes mantidas em paralelo:** dobra o custo de teste e
  garante divergência de comportamento. Rejeitado.
- **Remover o legado agora:** perde o único editor/terminal existente antes de
  existir substituto. Rejeitado.

## Consequências

- Existe uma decisão em aberto: como a IDE/terminal entra na experiência principal
  (opções A/B/C em `UI_ARCHITECTURE.md`). Precisa de ADR próprio antes da Fase 5.
- Recursos exclusivos do legado (temas, IDE, terminal) não podem ser perdidos por
  acidente: qualquer remoção exige confirmação de dependências.
- Toda melhoria de interface deve ser avaliada primeiro no mascote.

## Critério de revisão

Se, em uso real, o mascote não conseguir conduzir o fluxo de trabalho de projeto
sem abrir o dashboard, a decisão volta à mesa — com dados de uso, não por preferência.
