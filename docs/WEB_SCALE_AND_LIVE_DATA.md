# Escala da interface, busca e dados em tempo real

**Status:** decisão de arquitetura e implementação incremental. Não confundir os itens já existentes com os próximos passos.

## O que já existe no repositório

- Histórico e conversas persistem em SQLite (src/noite/store.py).
- messages_fts já é uma tabela FTS5 com sincronização por triggers de insert/update/delete e rebuild inicial.
- store.search_messages() já consulta o índice, mas a busca ainda não está conectada à interface web.
- A conversa web já transmite tokens e eventos de atividade por SSE no endpoint de chat. Portanto, não precisamos trocar isso por WebSockets para fazer o chat funcionar.
- O fluxo de conversas da interface já recebe o bootstrap e carrega mensagens; confirmar paginação atual antes de ampliar o histórico.

## Decisões

### 1. Busca de conversas e memória: SQLite FTS5

Reutilizar o índice existente, sem adicionar outro mecanismo de busca ou banco. A busca deve retornar mensagens relevantes com conversa, data, trecho/snippet e identificador da mensagem; clicar no resultado abre a conversa e posiciona o histórico perto da mensagem encontrada.

- Query parametrizada e normalização/escape da sintaxe FTS5 no backend.
- Filtros opcionais por conversa, período e papel.
- Limite inicial de resultados pequeno e paginação por cursor.
- Triggers mantêm o índice sincronizado com exclusões.
- A busca lexical é a primeira etapa. Busca vetorial fica adiada até benchmark demonstrar ganho real, conforme ADR-004.

### 2. Histórico grande: paginação por cursor

Não carregar centenas de milhares de mensagens de uma vez e não usar OFFSET profundo. Ordenar por id estável e carregar blocos, por exemplo 50 mensagens, com cursor before_id/after_id. Usar consultas indexadas e incluir conversation_id no filtro.

A interface deve preservar a posição de rolagem quando insere mensagens antigas. Cursor é a fonte de verdade da navegação; não depender de números de página.

### 3. Virtual scrolling

Adotar quando o histórico longo estiver ligado à UI: renderizar apenas as mensagens visíveis e uma pequena margem. Medir o custo real primeiro. Mensagens com altura variável (código, anexos, texto longo) exigem medição de altura e correção do scroll anchoring para não causar saltos.

Não virtualizar o painel de atividades curto, que tem limite de itens e não precisa dessa complexidade.

### 4. SSE para eventos unidirecionais

Manter SSE para eventos que o servidor envia ao navegador: tokens, etapas da execução, mudança de estado, conclusão e erro. O navegador continua enviando comandos por HTTP normal. WebSockets só entram se surgir necessidade comprovada de comunicação bidirecional contínua.

Para eventos globais (não vinculados a uma resposta de chat), planejar um único stream por sessão, com tipos de evento explícitos, heartbeat, reconexão e limpeza ao sair da página. Evitar abrir uma conexão SSE por widget/coluna.

### 5. Temperatura, clima e localização

O navegador só solicita geolocalização após ação/permissão explícita. Coordenadas não são persistidas nem enviadas ao histórico de conversa por padrão. Consultar o serviço de clima via HTTP, limitar frequência e guardar cache temporário; exibir cidade/região e hora da atualização, com estados de carregamento, erro e localização negada.

Clima é dado contextual auxiliar, não uma etapa de execução. A atividade do Unite deve vir do stream de eventos da própria Noite, não ser simulada com textos de clima.

### 6. Mensagens dinâmicas e templates

As mensagens de saudação são conteúdo de interface, não memória nem histórico. Manter templates e variáveis em código/configuração local, com seleção determinística e composição de variações. SQLite/FTS5 não é necessário para gerar centenas ou milhares de combinações; FTS5 serve para pesquisar conteúdo salvo.

Separar claramente:
- texto decorativo/saudação;
- dados reais (hora, clima, status do Unite);
- eventos reais de execução;
- mensagens e lembranças persistidas.

## Sequência recomendada

1. Expor busca FTS5 com endpoint limitado e resultados com contexto.
2. Adicionar cursor à leitura do histórico e cobrir com testes de ordenação, duplicação e exclusão.
3. Ligar busca à área Memória/Conversas, com navegação para a mensagem de origem.
4. Implementar virtual scrolling e testar históricos grandes com dados sintéticos.
5. Consolidar SSE de atividade global se a interface precisar de atualizações fora de uma resposta de chat.
6. Adicionar cache/atualização do clima com consentimento e estados visíveis.

## Referências técnicas

- SQLite FTS5: https://www.sqlite.org/fts5.html
- MDN Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- MDN Using SSE: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
