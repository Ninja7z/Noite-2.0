# ADR-004 — SQLite + FTS5 primeiro; vetores só com evidência

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (direção), arquitetura

## Contexto

- O histórico já é SQLite com FTS5 (`store.py`: tabela `messages`, índice
  `messages_fts` com triggers de insert/delete/update, tabela `conversations`,
  `noite_metadata`).
- **Não existe nenhum código de vetores/embeddings** no repositório.
- O hardware alvo é modesto (16 GB RAM, 6 GB VRAM): embedding local consome RAM e
  tempo de indexação.
- Risco principal de memória não é "não achar": é **inventar lembrança** e misturar
  projetos.

## Decisão

1. SQLite é a fonte única de memória local.
2. FTS5 é o mecanismo de busca inicial (histórico e, depois, memória de projeto).
3. Busca vetorial fica **adiada**, e só entra com critério medido:
   - recall@10 ≥ 20% superior ao FTS5 nas tarefas reais do usuário; **e**
   - latência adicional < 200 ms por consulta no hardware alvo; **e**
   - execução local (`sqlite-vec` no mesmo arquivo, embeddings locais, sem envio
     de conteúdo para fora).
4. Camadas de memória (histórico, fatos/preferências, projeto, documental) são
   separadas por escopo; memória nunca é compartilhada entre projetos.

## Alternativas consideradas

- **ChromaDB / FAISS:** mais um armazenamento e mais uma dependência para
  duplicar o que o SQLite já faz; nenhuma necessidade demonstrada. Rejeitado.
- **Vetorial desde o início:** aumenta custo, complexidade e superfície de
  vazamento sem prova de ganho. Rejeitado.
- **Nuvem para embeddings:** contradiz ADR-001. Rejeitado.

## Consequências

- Antes de adotar vetores, é preciso rodar e registrar o experimento (corpus real,
  métricas, comando) — inclusive o resultado negativo.
- FTS5 exige cuidado com idioma (tokenização) e com exclusão (trigger já cobre).
- Exclusão de memória precisa ser verificável no banco, não só na UI.

## Critério de revisão

Reabrir quando existir corpus real suficiente para medir e o experimento mostrar
ganho nos três critérios acima. Sem medição, a resposta continua "não".
