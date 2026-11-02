# Plano de UI — referência Noite 2.0

## Tokens amostrados das referências
- Escuro: fundo `#0A0B15`, superfície `#17162A`, borda `#292346`, texto `#F8F6FE`, secundário `#A3A5AC`, destaque `#4916BD`, sucesso `#18E066`.
- Claro: fundo `#FAF8FE`, superfície `#F1F1FD`, borda `#E7E4FB`, texto `#121334`, secundário `#6F6E9F`, destaque `#5531EB`, sucesso `#09D15E`.
- Tipografia: Segoe UI; escala 11/13/16/24/32/46 px; 400 para corpo, 600 para controles, 700 só na saudação.
- Espaços: 4/8/12/16/24/32; raios: janela 18, cards 14, chips 18, compositor 24; sombra só no compositor.
- Hierarquia: lua e “Boa noite!” são o único foco memorável; títulos de cards e metadados ficam discretos.

## Estrutura (larguras relativas)
```text
┌ Barra superior — 100%: marca | online | minimizar / maximizar / fechar ┐
├ Sidebar 17% ───┬ Centro 63% ──────────────────────┬ Direita 20% ──────┤
│ marca / menu   │ modo e conversa                  │ Destaques          │
│ sessões        │ lua + saudação                   │ Contexto Atual     │
│ privacidade    │ compositor + ações               │ Ferramentas        │
└────────────────┴ rodapé                           ┴───────────────────┘
```
- Alinhamento: sidebar e cards à esquerda; saudação, input e ações centralizados; painel direito alinhado à largura da coluna.
- Responsivo: preservar três regiões até 1000 px; reduzir margens e permitir rolagem nos painéis antes de ocultar conteúdo.

## Construção e validação
- Ordem: layout, tipografia/espaços, temas, ícones SVG, fundo decorativo, estados de interação.
- `theme.json` será fonte única dos tokens; comparar screenshot do app com as referências e corrigir diferenças antes da entrega.
- `ServiceClient` usa o núcleo real; `MockClient` só alimenta `--mock` para screenshot/teste.
