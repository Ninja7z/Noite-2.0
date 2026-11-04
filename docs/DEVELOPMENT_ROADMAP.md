# Roadmap de desenvolvimento — Noite 2.0

**Status:** normativo. Substitui a ordem de fases de `MASTER_PLAN.md` (que fica
preservado como histórico). Uma fase só é marcada `concluída` quando **todos** os
gates passam; testes unitários sozinhos não bastam.

## Ordem das fases

| Fase | Objetivo | Gate de aceite |
|---|---|---|
| **0** | **Contrato do produto** — visão, arquitetura, ADRs, sem contradições entre documentos | `docs/README.md` + ADR-001..005 aceitos; nenhum documento contradiz outro |
| **1** | **Fundação de segurança** — um único caminho de execução, um único validador de caminho, auditoria íntegra, aprovação vinculada, reversibilidade declarada | teste de segurança: execução fora do `ToolGuard` **falha** para terminal, arquivo e MCP; permissão revogada falha; aprovação de outra ação falha |
| **2** | **Núcleo inteligente** — gateway, personalidade persistente, histórico, contexto relevante, erros de provedor | conversa multi-turno coerente, offline, com identidade estável ao trocar o modelo |
| **3** | **Memória** — histórico, fatos/preferências, memória de projeto, documental; retenção e exclusão | recupera o relevante sem cruzar projeto e sem inventar lembrança; "esquecer" verificável no banco |
| **4** | **Ferramentas e autonomia** — proposta, diff, aprovação, undo | tarefa multi-arquivo investigada, proposta, aprovada, aplicada, testada e desfeita |
| **5** | **Interface definitiva** — mascote como centro (conversa, estados, aprovação, notificações, privacidade) | funciona continuamente sem abrir o legado; validação manual registrada |
| **6** | **Integrações** — Git, Roblox Studio, Blender (começa read-only) | integrações isoladas, incapazes de contornar permissões centrais |
| **7** | **Voz, visão e multimodalidade** | benchmark no hardware alvo com latência e consumo documentados |
| **8** | **Distribuição e homologação** — instalador, atualização, recuperação, regressão | instalação limpa em Windows funciona sem ambiente de desenvolvimento |

Estado atual: **Fase 0** publicada (PR 001 + ADR-006) e **Fase 1 em andamento**
(PR 002 e 003 concluídos: terminal + MCP no caminho único, caminho e auditoria
unificados; PR 004 e 005 pendentes).
Fase 1 continua bloqueante para qualquer ferramenta nova.

## Mapa das dívidas → fases

| Dívida (de `SYSTEM_ARCHITECTURE.md`) | Fase |
|---|---|
| D1 `ToolGuard` cobre 1 ponto | 1 |
| D2 dois validadores de caminho | 1 — fechada no PR 003 |
| D3 permissão paralela no orquestrador | 1 — fechada no PR 003 |
| D5 auditoria por subquery | 1 — fechada no PR 003 |
| D7 redação privada compartilhada | 1 (limpeza) |
| D4 IDE só no legado | 5 (com decisão em `UI_ARCHITECTURE.md`) |
| D6 terminal Windows-only | 4 (com D6 como requisito de CI) |

## Sequência de PRs

Cada PR: uma decisão, revisável em menos de uma hora, CI verde, sem misturar
documentação com comportamento.

| PR | Objetivo | Fase | Depende de |
|---|---|---|---|
| 001 | Consolidar visão e arquitetura oficial (**este**) | 0 | — |
| 002 | Centralizar autorização no `ToolGuard` (fechar D1) | 1 | 001 |
| 003 | Caminhos, permissões e auditoria: validador único, sem permissão paralela, resultado por tentativa (D2, D3, D5) | 1 | 002 |
| 004 | Endurecer testes de segurança e regressão (D7, caminhos, FTS, Windows-only) | 1 | 003 |
| 005 | CI e testes de segurança (inclui Windows-only e extra `openwebui`) | 1 | 002-004 |
| 006 | Escrita controlada com diff, aprovação e undo (Fase 4 mínimo) | 4 | 002-005 |
| 007 | Consolidar núcleo conversacional e memória (Fases 2-3) | 2-3 | 005 |
| 008 | Validar interface do mascote (Fase 5, conforme decisão de ADR) | 5 | 007 |
| 009 | Integrações especializadas: Git, Roblox, Blender (read-only primeiro) | 6 | 008 |
| 010 | Voz, multimodalidade e distribuição | 7-8 | 009 |

## Definition of Done por PR

1. Teste que falha antes e passa depois (ou teste de caracterização explícito).
2. `pytest -q` e `ruff check .` verdes **localmente**.
3. CI remoto verde (quando o PR for aberto).
4. Sem mudança de contrato silenciosa: se alterar arquitetura, ADR incluído.
5. Nota no PR: o que mudou, o que **não** mudou, e qual dívida foi fechada/aberta.

## Regras de processo

- Branch por PR; sem push/merge sem autorização explícita do proprietário.
- Nenhuma IA promove hipótese técnica a decisão arquitetural sem evidência ou
  aprovação humana.
- Relatório de pesquisa (ex.: o PDF de arquitetura) é **insumo**, não plano; cada
  afirmação precisa ser reproduzida no repositório antes de virar requisito.
- Fase 6 e 7 podem ficar `pendente` se dependerem de terceiros (servidor MCP real,
  hardware, licenças) — declarar isso é aceitável; fingir conclusão não é.
