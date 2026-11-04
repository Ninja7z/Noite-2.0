# Arquitetura de interface — Noite 2.0

**Status:** normativo (ver [ADR-002](ADR/002-mascot-interface.md)).

## Interface principal: o mascote

`mascot.py` (`MascotWindow`) é a experiência central, não um enfeite:

- janela flutuante 136×136, sem moldura, sempre no topo, arrastável;
- posição persistida em `QSettings`;
- estados visuais: `idle`, `thinking`, `working`, `done`, `error` (o visor comunica
  o que a Noite está fazendo);
- clique expande um painel compacto com `transcript` (`QTextBrowser`), campo de
  entrada e botão de envio;
- atalho global `Alt+C` no Windows (`GlobalHotkeyWorker`), não registrado em
  ambiente headless;
- diagnóstico de Ollama em thread própria, a cada abertura do painel.

Identidade visual: robô branco de mesa, visor escuro, olhos azul-ciano em pixel
art, **original** — não copiar assets ou marca de terceiros.

## Interface legada (isolada)

`ui.py` (`NoiteWindow`) + `ui/client.py` + `ide.py` formam o dashboard completo:
sidebar de conversas, editor com realce Python, terminal, painel de atividade,
Command Palette e diálogo MCP.

- abre apenas com `--legacy` (`run_ui.py`) ou `--legacy-ui` (`python -m noite`);
- permanece como fallback até a nova interface ser validada em uso real;
- não é removida sem inventário de dependências e rollback (regra de `AGENTS.md`).

## Regras de thread e atualização (invariantes de UI)

| Regra | Como é cumprida |
|---|---|
| Nada de rede/modelo na thread visual | `AssistantWorker`, `DiagnosticsWorker`, `TaskThread` (`QThread`) emitem sinais |
| UI atualiza só por sinal Qt | `chunk`, `activity`, `completed`, `failed` |
| Streaming não reconstrói a conversa por token | inserção incremental; lote de 50 ms no mascote; lote por timer no legado |
| Cancelamento real | `_cancelled` no worker + evento/parada do executor; texto final marcado como cancelado |
| Fechar durante execução não corrompe estado | `_close_pending`/`_workers` com espera coordenada |

## Aprovação de ação na interface

Hoje a única aprovação de ferramenta existe no diálogo MCP do legado
(`MCPDialog` → `QMessageBox.question` → `ApprovalManager`).

Alvo (Fase 1 + Fase 5): a aprovação acontece **na interface principal**, com
resumo legível da ação (o que, onde, com quais parâmetros), origem do pedido e
botões explícitos. Negação é registrada em auditoria e exibida inline — nunca em
modal bloqueante (já corrigido no legado).

## IDE no mascote — decidido (ADR-006)

Decisão: **opção A** — o mascote expande para um painel com abas
(Conversa · Atividade · Projeto), implementado em fatias: (1) árvore + leitura,
(2) edição com aprovação e undo, (3) terminal atrás do `ToolGuard`.
Detalhes, alternativas e critério de revisão em
[ADR-006](ADR/006-ide-no-mascote.md).

| Opção | Descrição | Estado |
|---|---|---|
| A | Mascote expande para painel com abas (Conversa / Atividade / Projeto) | **escolhida** |
| B | Mascote + janela de projeto separada | contingência registrada |
| C | Mascote só conversa; projeto continua exclusivo do legado | rejeitada (contraria ADR-002) |

Enquanto a paridade não existir, o `ProjectDock` do legado permanece funcional e
intocado.

## Dívidas de interface

| # | Dívida | Evidência |
|---|---|---|
| U1 | Tema (`theme.py`, tokens visuais) é usado só pelo legado; o mascote tem cores próprias | `theme.py` importado em `ui.py` apenas |
| U2 | `NoiteWindow` concentra ~2.350 linhas em uma classe | `ui.py:343-2692` |
| U3 | Aprovação de ação só existe no legado | `MCPDialog._call_selected` |
| U4 | Não há teste de acessibilidade (foco, leitor de tela, contraste) | ausência em `tests/` |

## Critérios de aceite da Fase 5

1. Conversa, estados e aprovação funcionam no mascote **sem** abrir o legado.
2. Nenhum travamento perceptível: streaming fluido em hardware alvo.
3. Cancelar durante geração deixa o estado consistente (sem texto duplicado).
4. Funciona em DPI 100% e 150% e com o painel em tela pequena.
5. Validação manual registrada (data, build, máquina) — teste automatizado não
   substitui a validação visual.
