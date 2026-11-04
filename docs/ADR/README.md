# ADRs — decisões arquiteturais da Noite 2.0

Um ADR registra **uma** decisão relevante: contexto, decisão, alternativas
descartadas e consequências. Ele existe para que nenhuma decisão importante seja
alterada em silêncio.

## Modelo

```markdown
# ADR-NNN — Título curto

- **Status:** proposto | aceito | substituído por ADR-XXX | descontinuado
- **Data:** AAAA-MM-DD
- **Decisores:** proprietário, arquitetura, engenharia

## Contexto
Fatos verificáveis (com origem: código, medição, documentação oficial).

## Decisão
O que fica decidido, em uma frase, e as regras que decorrem dela.

## Alternativas consideradas
O que foi descartado e por quê.

## Consequências
Positivas, negativas, custos, o que passa a ser proibido.

## Critério de revisão
Evidência que justificaria reabrir a decisão.
```

## Índice

| ADR | Decisão | Status |
|---|---|---|
| [001](001-local-first.md) | Local-first com Ollama como padrão; nuvem opt-in | aceito |
| [002](002-mascot-interface.md) | Mascote é a interface principal; dashboard/IDE é legado isolado | aceito |
| [003](003-tool-authorization.md) | Autorização fora do modelo: `ToolGuard` único caminho de execução | aceito |
| [004](004-memory-storage.md) | SQLite + FTS5 primeiro; vetores condicionados a evidência | aceito |
| [005](005-model-provider.md) | Provedor atrás de um adaptador; LiteLLM não é obrigatório | aceito |
| [006](006-ide-no-mascote.md) | A IDE entra no mascote como painel com abas, em fatias | aceito |

## Regras

1. Um ADR novo é necessário para: trocar interface principal, mudar fronteira de
   autorização, mudar formato/retenção de memória, trocar provedor padrão de
   modelo, ou adotar nova dependência estrutural (ex.: banco vetorial).
2. ADR `aceito` só muda por outro ADR que o referencia; o antigo recebe
   `substituído por`.
3. Métricas externas (token/s, latência de transcrição, "servidor X é read-only")
   precisam de medição no hardware alvo ou fonte oficial antes de sustentar um ADR.
