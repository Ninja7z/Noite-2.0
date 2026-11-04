# Pesquisa e plano de expansão de capacidades — Noite 2.0

**Data:** 2026-11-04  
**Status:** pesquisa e proposta de execução; não significa que as capacidades abaixo já estejam implementadas.

## Objetivo

Expandir funções, integrações, desempenho e experiência visual mantendo a Noite local-first, modular, auditável e segura. O núcleo Python continua dono da identidade, memória, permissões, contexto e orquestração. Open WebUI é infraestrutura de capacidades; não substitui o produto Noite.

## Estado verificado nesta revisão

- Histórico e conversas persistem em SQLite; FTS5 e triggers já indexam o texto.
- Existe `store.search_messages()`, mas a busca ainda não está exposta na interface web.
- A web app tem streaming SSE para chat e eventos de atividade durante a requisição.
- A tela principal tem navegação inicial para conversas, atividades, projetos, memória, ferramentas e configurações; várias áreas ainda são estrutura visual, não CRUD conectado.
- `pyproject.toml` não declara ChromaDB nem uma dependência de embeddings.
- ADR-004 já decidiu manter SQLite + FTS5 e adiar vetores até evidência medida. Não instalar ChromaDB agora nem migrar dados para outro armazenamento.

## Decisões técnicas recomendadas

### 1. Busca e memória pesquisável
1. Expor FTS5 por API autenticada da sessão, com limite, snippets, ranking e filtro por conversa/projeto.
2. Apresentar busca em Conversas/Memória, com resultado abrindo a mensagem original e exibindo conversa, data e trecho.
3. Adicionar paginação por cursor baseada em ID/ordem estável. Evitar OFFSET profundo em histórico longo.
4. Aplicar exclusão verificável e testes de isolamento entre conversas/projetos.
5. Construir memória explícita e revisável (fatos/preferências e notas por projeto) com origem, data, escopo, confirmação, edição e exclusão. Conteúdo de web/arquivos nunca grava memória automaticamente.

### 2. Recuperação semântica: ChromaDB
ChromaDB é um banco vetorial local útil quando a busca precisa reconhecer paráfrases e significado, não apenas termos. Contudo, sua instalação adiciona dependências e armazenamento separado; o projeto já tem uma decisão arquitetural explícita para não adotar vetores sem benchmark.

**Experimento futuro, não instalação imediata:**
- Criar conjunto real de consultas e resultados esperados, sem incluir segredos.
- Comparar FTS5, FTS5 + reranking leve e um índice vetorial local.
- Medir recall@10, latência p50/p95, RAM, VRAM, tamanho do índice e custo de atualização.
- Usar o mesmo corpus e critérios; registrar falhas e acertos.
- Reabrir ADR-004 somente se ganho de recall for >=20%, latência adicional <200 ms e o processamento permanecer local.
- Avaliar primeiro sqlite-vec conforme ADR-004. ChromaDB pode ser protótipo comparativo, não fonte primária da memória.
- Embeddings remotos ficam desativados por padrão e exigem consentimento explícito por conteúdo.

### 3. Fluxo de atividade em tempo real
- Manter SSE para streaming e notificações servidor → navegador. O chat já usa SSE; não trocar para WebSocket sem necessidade real de comunicação bidirecional.
- Separar eventos tipados: modelo, busca, ferramenta, aprovação, execução, conclusão/erro/cancelamento.
- Acrescentar heartbeat, reconexão e IDs de evento; não enviar tokens, caminhos privados ou argumentos sensíveis ao painel.
- Consolidar em um fluxo global por sessão apenas quando múltiplos painéis realmente precisarem da mesma fonte.
- Tornar estados reais e acessíveis; não apresentar conteúdo demonstrativo como atividade verdadeira.

### 4. CUA e execução confiável
- Construir um ciclo observação → plano → proposta → aprovação → execução → verificação → relatório.
- Ações de leitura e escrita separadas; escritas mostram diff e opção de desfazer.
- Ferramentas rodam sob escopo de workspace, com timeout, cancelamento, limites de saída e auditoria de metadados.
- CUA visual começa com captura e inspeção sob demanda. Clique/teclado ficam atrás de aprovação e ToolGuard; nunca confiar diretamente em instruções encontradas em páginas ou arquivos.
- Não habilitar comandos arbitrários apenas porque o modelo os sugeriu.

### 5. Integrações prioritárias
Ordem sugerida:
1. Ollama: inventário de modelos, saúde, latência, streaming e seleção de modelo disponível.
2. Open WebUI: adaptador com capacidades explicitamente selecionadas; credenciais permanecem no servidor e ferramentas passam por política da Noite.
3. MCP: descoberta e registro de ferramentas confiáveis, escopo por servidor, esquema validado, timeout, aprovação e logs redigidos.
4. Git: status/diff/log read-only primeiro; aplicar mudanças com revisão e undo.
5. Windows: abrir app, inspecionar janela e automações de UI em modo assistido.
6. Roblox Studio e Blender: integração read-only inicial; escrever/rodar só depois de delimitar ferramentas e permissões reais.
7. Voz local: STT/TTS sob demanda, interrupção e push-to-talk; medir memória/latência antes de manter modelos carregados.
8. Visão e arquivos: OCR/descrição de imagem e extração de documentos em tarefas isoladas, limites de tamanho e confirmação de acesso.

### 6. Desempenho
- Inicialização lazy para integrações e dependências pesadas.
- I/O, indexação, diagnósticos e chamadas externas em workers/async; UI nunca bloqueada.
- Cache com TTL para estado de integrações e resultados repetidos; invalidar em mudanças.
- Indexação incremental por hash, limite de arquivos e exclusões explícitas.
- Uma inferência local principal por vez no hardware atual (GTX 1660 Super 6 GB / 16 GB RAM); não manter vários modelos grandes residentes.
- Medir tempo de startup, primeiro token, tokens/s, uso de RAM/VRAM, latência de busca e duração de ferramenta.
- Usar histórico com paginação e virtualização somente quando o volume justificar, preservando posição de rolagem.

### 7. Interface e experiência
- Manter tela limpa e hierarquia visual baixa; detalhes avançados aparecem sob demanda.
- Converter áreas estáticas em vistas funcionais, começando por Conversas, Busca, Projetos e Atividade.
- Estados de carregamento/vazio/erro claros; teclado, foco, leitores de tela e movimento reduzido.
- Layout responsivo para desktop e celular; acesso pela rede local só depois de pareamento, autenticação e transporte seguro.
- Mascote desktop permanece como presença opcional, sem duplicar a interface web.
- Separar visual de demonstração de telemetria real; usar dados reais sempre que conectados.

## Sequência incremental proposta

| Etapa | Entrega | Gate |
|---|---|---|
| A | Busca FTS5 na API e interface, snippets, filtros, testes | isolamento e escaping validados |
| B | Cursor pagination no histórico | ordem estável e testes de limites |
| C | Memória explícita, editável e apagável | origem/escopo/consentimento verificados |
| D | Fluxo SSE de atividade tipado e reconectável | não bloqueia chat nem expõe segredo |
| E | Git read-only + diff/undo de mudanças | todas as mutações sob ToolGuard |
| F | Adaptadores Open WebUI/MCP com política central | ferramenta não contorna autorização |
| G | CUA Windows, visão e automação assistida | plano/aprovação/verificação reproduzíveis |
| H | Benchmark de memória vetorial (ChromaDB como comparativo) | ADR revisado com métricas reais |
| I | Voz, OCR, indexação incremental e polimento responsivo | perf e acessibilidade registradas |

Cada etapa deve ser implementada como mudança pequena e testável. Não instalar dependências grandes, alterar o banco real, abrir portas para a LAN, iniciar/encerrar processos do usuário ou fazer commit/push sem autorização específica.

## Fontes consultadas

- SQLite FTS5: https://www.sqlite.org/fts5.html
- ChromaDB Getting Started: https://github.com/chroma-core/docs/blob/main/docs/getting-started.md
- ChromaDB Usage Guide (PersistentClient): https://github.com/chroma-core/docs/blob/main/docs/usage-guide.md
- Open WebUI extensibility: https://docs.openwebui.com/features/extensibility/
- Open WebUI MCP: https://docs.openwebui.com/features/extensibility/mcp/
- Open WebUI server-side tool calling: https://docs.openwebui.com/reference/server-side-tool-calling/
- MDN Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events


## Pesquisa adicional — capacidades que valem entrar agora

Esta seção foi acrescentada após nova pesquisa em 2026-11-04. São recomendações para implementação incremental, não declarações de que o código já foi alterado.

### J. Observabilidade local por execução (prioridade alta)

Adicionar um `run_id` estável e spans/eventos de baixo custo para cada execução: início/fim, modelo/provedor, tempo até primeiro token, duração total, ferramenta chamada, duração, resultado (sucesso/erro/cancelado) e contagem de tokens quando o backend fornecer. Não registrar prompt, resposta, argumento de ferramenta, caminho de arquivo ou segredo por padrão. Exportação opcional; experiência local deve funcionar sem collector nem conta externa. A interface Atividade pode consumir esse registro para exibir gargalos reais.

Implementar primeiro com o sistema de eventos/log estruturado existente, sem tornar OpenTelemetry uma dependência obrigatória. Avaliar API OTel opcional depois, com export desligado por padrão e opção explícita de consentimento. OpenTelemetry/MCP oferece instrumentação por spans; a captura de conteúdo sensível deve permanecer desativada. Referências: https://opentelemetry.io/docs/demo/services/agent/ e https://py.sdk.modelcontextprotocol.io/run/opentelemetry/.

### K. Cancelamento, timeout e limite de saída (prioridade alta)

Garantir que geração, busca, ferramenta e execução CUA aceitem cancelamento e timeout, com estados propagados até a UI. Limitar tamanho de saída de ferramentas e manter resumo + referência local para conteúdo extenso. Testar que cancelar uma geração não deixa subprocesso ou indicador de atividade preso.

### L. Diagnóstico de saúde sem travar interface (prioridade alta)

Adicionar uma tela/ação de diagnóstico que verifique, sob demanda: API Noite, Ollama, modelo selecionado, SQLite/FTS5, diretório de projeto e integrações conectadas. Mostrar estado, duração e sugestão concreta; usar cache curto e chamadas assíncronas. Não iniciar serviços ou alterar configurações automaticamente.

### M. Contrato de eventos tipados (prioridade alta)

Formalizar eventos internos com `run_id`, `event_id`, timestamp, tipo, status e payload mínimo validado. Eventos possíveis: `run.started`, `model.first_token`, `tool.started`, `approval.required`, `tool.finished`, `run.cancelled`, `run.failed`, `run.finished`. SSE segue como transporte da web; o contrato interno não depende do transporte e permite UI desktop/web compartilhar eventos.

### N. Testes de resiliência (prioridade alta)

Acrescentar testes para servidor Ollama indisponível, stream interrompido, cliente desconectado, ferramenta excedendo timeout, cancelamento, banco bloqueado e conteúdo de ferramenta contendo instruções maliciosas. Cada falha deve terminar em estado recuperável, sem vazar dados ou contornar ToolGuard.

### O. Experimento de busca semântica (prioridade média, sem instalar dependências ainda)

Antes de escolher ChromaDB ou sqlite-vec, montar dataset sintético e um conjunto pequeno de consultas de avaliação não sensíveis. Comparar FTS5 atual com alternativas por recall@k, qualidade de resultados, latência p50/p95, RAM, tamanho em disco e custo de atualização. Embeddings só localmente neste experimento. ChromaDB usa HNSW e índice brute-force como buffer; o custo de embedding e atualização pode ser relevante, então comparar pipeline completo, não somente a busca. Referência: https://cookbook.chromadb.dev/faq/.

### Sequência prática revisada

1. Expor busca FTS5 à API e interface com snippets, filtro de conversa, limites e testes de isolamento.
2. Adicionar `run_id` + eventos tipados e alimentar Atividade com estado real.
3. Garantir cancelamento/timeouts/limites e testes de falha.
4. Cursor pagination para histórico e, depois, virtualização medida.
5. Diagnóstico de saúde assíncrono.
6. Benchmark vetorial isolado. Só após métricas decidir ChromaDB/sqlite-vec.

Critério geral: manter recursos opcionais e lazy; adicionar dependência nova somente se uma função concreta não puder ser atendida pelo que já existe e o benefício medido justificar o custo.
