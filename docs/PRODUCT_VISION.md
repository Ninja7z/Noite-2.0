# Visão de produto — Noite 2.0

**Status:** normativo. Decisões marcadas como *fixado* foram estabelecidas na
revisão de produto de 2026-11-04; promoção para *aprovado* exige confirmação
explícita do proprietário (checklist no fim).

## O que estamos construindo

Uma assistente pessoal de desktop, local-first, em português brasileiro, com
identidade própria (a Noite), que conversa naturalmente e executa tarefas reais
no computador do usuário **sem nunca se autorizar sozinha**.

O produto se apoia em três pilares. Os três são obrigatórios: qualquer decisão
técnica que reforce um deles enfraquecendo outro está errada.

| Pilar | O que exige | Como sabemos que existe (verificável) |
|---|---|---|
| **Identidade** | A Noite se apresenta e responde de forma consistente, em pt-BR, independentemente do modelo/provedor ativo | Teste de identidade com o modelo local trocado; nenhuma resposta deve "virar" o provedor |
| **Inteligência** | Entender o pedido, manter contexto da conversa/projeto e planejar antes de agir | Conversa multi-turno coerente; recuperação de contexto correto; uso de nuvem só quando autorizado e vantajoso |
| **Autonomia** | Converter pedido em ação real (arquivo, terminal, integração) com proposta, aprovação, execução e reversão quando possível | Tarefa multi-arquivo aprovada, aplicada, testada e desfeita; nenhuma ação fora do `ToolGuard` |

**A tecnologia serve à Noite; a Noite não é limitada pela tecnologia escolhida.**
Trocar Ollama, LiteLLM, PySide6 ou SQLite não pode mudar a identidade do produto.

## Decisões fixadas

| Decisão | Estado | Consequência prática |
|---|---|---|
| Mascote flutuante é a interface principal | fixado | O dashboard/IDE completo é legado isolado; ver [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md) |
| Local-first (Ollama como padrão) | fixado | Sem rede a conversa continua funcionando |
| GLM opcional, sem contexto automático | fixado | Só categoria autorizada + mensagem atual; ver [MODEL_ROUTING.md](MODEL_ROUTING.md) |
| `ToolGuard` obrigatório e centralizado | fixado | Nenhum executor acessível fora dele; ver [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md) |
| SQLite + FTS5 como memória inicial | fixado | Sem dependência vetorial; ver [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) |
| Memória vetorial (`sqlite-vec` etc.) | adiado | Só entra com evidência de ganho mensurável (critério no ADR-004) |
| Voz, visão e multimodalidade | roadmap | Nunca requisito para a Noite ser considerada funcional |
| Roblox Studio / Blender | roadmap | Começa por leitura/inspeção; escrita só via `ToolGuard` |
| Dashboard administrativo completo | não priorizado | Não competir com a experiência do mascote |
| Instalador standalone | objetivo final | Fase 8; hoje o `Noite.exe` é launcher dependente do checkout |
| Segurança antes de ampliar autonomia | fixado | Fase de segurança precede novas ferramentas |
| GitHub como fonte oficial | fixado | Trabalho em branch + PR pequeno; nada de "commit único de 200 arquivos" |

## Regra de decisão permanente

Antes de aceitar qualquer mudança, responder por escrito:

> **Isso torna a Noite uma assistente melhor para o usuário — ou apenas adiciona
> uma tecnologia ao repositório?**

Se a resposta for a segunda, a mudança não entra.

## Não-objetivos explícitos

- Framework próprio de agentes complexo, com LLM decidindo permissões.
- LLM no meio de operação simples e determinística (abrir arquivo, listar diretório).
- Busca vetorial como obrigação antes de provar necessidade.
- Personalidade que dependa de um provedor específico.
- Acesso irrestrito ao sistema operacional, mesmo com "acesso total" habilitado.
- Misturar interface, memória, orquestração e execução em um único módulo.
- Priorizar dashboard administrativo em detrimento do mascote.
- Considerar voz/visão requisito de funcionalidade.

## Definição de pronto do produto (não da fase)

A Noite 2.0 está "pronta para uso" quando, em **Windows limpo**:

1. instala por instalador/atalho sem o ambiente de desenvolvimento;
2. mantém uma conversa coerente em pt-BR com Ollama offline;
3. executa uma tarefa real de arquivo/código com proposta, aprovação e reversão;
4. não executa nenhuma ação fora do `ToolGuard` (verificado por teste de segurança);
5. preserva histórico, memória e permissões após atualização;
6. tem a matriz de regressão aprovada, incluindo validação visual do mascote.

Enquanto qualquer item acima falhar, o produto está em desenvolvimento — mesmo
que todas as fases anteriores pareçam "concluídas".

## Checklist de aprovação do proprietário

- [ ] Confirmar os 12 itens da tabela "Decisões fixadas"
- [ ] Confirmar que voz/visão permanecem fora do caminho crítico
- [ ] Confirmar a definição de pronto acima como critério de "final"
