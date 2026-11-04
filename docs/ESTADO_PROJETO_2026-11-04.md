# Noite 2.0-2 | Estado do projeto
**Data:** 04/11/2026  
**Checkpoint de continuidade:** prioridade em estabilizar o SSD antes de retomar testes de carga.

## 1. Prioridade atual: SSD
SSD SATA Mancer Reaper 480 GB (modelo mcr-rprf-480gb), driver storahci. Sintomas observados: 100% de atividade, baixa transferência (aprox. 0–7 MB/s), latência muito alta (20–5600 ms) e travamentos. O usuário relata que o problema começou durante testes de configuração do Ollama. Isso é um marco temporal relevante, mas ainda não comprova dano físico nem causalidade.

Após a última reinicialização, observações pontuais: estado SMART/Windows reportado como Healthy/OK; fila de disco 2; atividade 27%. Esses números são apenas uma amostra e não comprovam resolução. WSearch e SysMain estavam iniciados. O teste de isolamento preparado ainda não tem resultado confirmado.

**Regras:** não executar diskpart clean, não formatar, não reinstalar o Windows, não executar benchmarks ou cargas de modelos até estabilizar o armazenamento. Não declarar o SSD danificado sem evidências.

## 2. Serviços e portas
Último estado confirmado antes da reinicialização:
- Noite API: 8765, HTTP 200.
- Noite Web: 8766, HTTP 200.
- Roblox MCP Proxy: 8768, ativo.
- Open WebUI: 8080, HTTP 200.
- Ollama: 11434, versão anteriormente confirmada 0.40.14; após a última reinicialização a API precisa ser revalidada.
- Noite MCP: 8767, bloqueado pela ausência de NOITE_MCP_AUTH_TOKEN no ambiente. Não inventar, gerar ou substituir credencial sem autorização.

Evitar instâncias duplicadas de serviços.

## 3. Ollama
Variáveis de usuário configuradas:
- OLLAMA_NUM_PARALLEL=1
- OLLAMA_MAX_LOADED_MODELS=1
- OLLAMA_CONTEXT_LENGTH=4096
- OLLAMA_KEEP_ALIVE=5m
- OLLAMA_FLASH_ATTENTION=1
- OLLAMA_KV_CACHE_TYPE=q8_0

Qwen3.5:4b já foi validado anteriormente usando a GTX 1660 Super. Não carregar modelos nem iniciar testes até o SSD estar estável. Não baixar modelos nem trocar o modelo padrão sem autorização.

## 4. Arquitetura planejada do motor
Três perfis desejados, ainda não considerados implementados:
- Rápido: modelos leves e baixa latência.
- Inteligente: modelos com maior capacidade de raciocínio e fallback.
- Agente: modelos com ferramentas, execução controlada e aprovações.

Cada perfil deverá aceitar múltiplos modelos, parâmetros/contextos por modelo e fallback. O Model Router deverá selecionar o modelo conforme a tarefa. Segurança e aprovação de ferramentas permanecem sob controle do Python. Embeddings devem ser executados sequencialmente, sem competir com o modelo de geração.

## 5. RAG
Benchmark conhecido: 40 documentos Markdown, 166 chunks e 10 perguntas. Nomic Recall@5=0,80; FTS5 Recall@5=0,70. MRR Nomic=0,617; FTS5=0,600. Decisão: manter SQLite FTS5; não migrar para ChromaDB, Qdrant ou sqlite-vec neste momento.

Documentos de referência:
- docs/RAG_RETRIEVAL_BENCHMARK_2026-11-04.md
- scripts/benchmark_rag_retrieval.py
- docs/OLLAMA_PERFIS_6GB.md

## 6. Interface e integrações
Direção acordada: preservar a identidade visual e o método de construção atuais, evoluindo para Web App dinâmico, responsivo e com feedback em tempo real. Backend FastAPI e comunicação WebSocket orientada a eventos. Integração mais completa do Open WebUI. Mascote com atalho Alt+C para abrir/fechar e iniciar/encerrar tarefas. Não reconstruir a interface sem necessidade. Prioridade atual permanece no backend/estabilidade; não mexer no frontend sem pedido.

## 7. Próximas ações, em ordem
1. Revalidar SSD após reboot: latência, fila, throughput, processos de I/O e eventos do Windows.
2. Confirmar resultado do script scripts/ssd_isolation_admin.ps1 e do log build/ssd_isolation_result.txt; confirmar restauração automática de WSearch e SysMain.
3. Revalidar serviços e API do Ollama sem carregar modelos.
4. Resolver a credencial ausente do Noite MCP somente com autorização.
5. Depois da estabilidade do SSD, retomar testes comparativos de modelos/perfis e parâmetros, com medições controladas.
6. Implementar/integrar Model Router e os perfis Rápido, Inteligente e Agente.
7. Retomar integração completa do Open WebUI e evolução da interface conforme prioridade definida.

## 8. Ambiente
Raiz do projeto:
C:\Users\crist\Noite-2.0-worktrees\stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001

Python:
.venv\Scripts\python.exe

Script de isolamento:
scripts\ssd_isolation_admin.ps1

Log esperado:
build\ssd_isolation_result.txt

## 9. Regras de continuidade
- Não perder nem descartar decisões de arquitetura por causa da investigação do SSD.
- Não afirmar que algo foi corrigido sem verificação.
- Não executar ações destrutivas ou testes pesados sem necessidade/autorização.
- O checkpoint registra o último estado conhecido; serviços e processos devem ser revalidados após reinicialização.
