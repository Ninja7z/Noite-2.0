# Benchmark inicial de recuperação documental — 2026-11-04

## Objetivo

Comparar embeddings locais com `nomic-embed-text` e busca lexical SQLite FTS5 antes de decidir se o Noite deve adotar um índice vetorial. O teste não instala dependências, não cria banco persistente e não altera o fluxo de produção.

## Corpus e método

- 40 documentos Markdown do diretório `docs/`, excluindo `docs/archive/`.
- 166 trechos de até 1.400 caracteres, com sobreposição de 220 caracteres.
- 10 perguntas em português, com documento esperado definido previamente.
- `nomic-embed-text` via API local do Ollama.
- Prefixos usados: `search_document:` nos trechos e `search_query:` nas perguntas.
- FTS5 consultado com OR entre os termos da pergunta e ordenação por `rank`.
- Avaliação por documento esperado em Recall@5 e MRR@5.

Script reproduzível: `scripts/benchmark_rag_retrieval.py`.

## Resultados

| Métrica | Nomic embeddings | SQLite FTS5 |
|---|---:|---:|
| Recall@5 | 0,80 | 0,70 |
| MRR@5 | 0,617 | 0,600 |

Medições do Nomic nesta máquina:

- Indexação inicial dos 166 trechos: 42.866,8 ms.
- Embedding da pergunta: p50 47,8 ms; p95 65,4 ms.
- Modelo de embeddings observado pelo Ollama: 100% GPU, aproximadamente 335 MB de memória de modelo.

## Interpretação e decisão

O ganho observado de Recall@5 foi de 10 pontos percentuais (0,80 contra 0,70), ou 14,3% relativo sobre o FTS5. O ganho de MRR foi pequeno. O resultado não alcança o critério de adoção estabelecido no ADR-004: melhoria de recall de pelo menos 20%, além de latência adicional inferior a 200 ms.

**Decisão: não adotar sqlite-vec, ChromaDB ou outro banco vetorial nesta etapa.** Manter SQLite/FTS5 e a extração local de anexos. Reavaliar somente com um conjunto maior de perguntas reais, avaliação de Recall@10, medição explícita de latência de recuperação p50/p95 e atualização incremental do índice.

## Limitações

- Apenas 10 perguntas e 40 documentos; resultado exploratório, não prova estatística.
- O rótulo esperado é o nome do documento, não um julgamento humano de relevância de cada trecho.
- O tempo de indexação é uma carga inicial em lote; atualização incremental ainda não foi medida.
- O teste não mede geração de resposta, fidelidade das citações ou qualidade final do RAG.
- A medição de 48 ms é do embedding da consulta; a latência total de recuperação precisa ser medida separadamente antes de qualquer adoção.

## Segurança e impacto

- Todas as chamadas foram feitas ao Ollama local.
- Nenhum conteúdo foi enviado a provedor externo.
- Nenhum banco de produção foi criado ou alterado.
- Nenhum modelo foi instalado ou removido.
- O benchmark não iniciou agentes, Open WebUI ou servidores do Noite.
