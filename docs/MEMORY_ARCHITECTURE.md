# Arquitetura de memória — Noite 2.0

**Status:** normativo (ver [ADR-004](ADR/004-memory-storage.md)). Muitas camadas
abaixo são **proposta**, não código existente — isso está marcado em cada linha.

## Princípio

Memória é do usuário: **consentida, escopada, inspecionável e excluível**. A Noite
não inventa lembrança, não mistura projetos e não guarda segredo.

## Camadas

| # | Camada | Conteúdo | Hoje | Alvo |
|---|---|---|---|---|
| 1 | Histórico de conversa | mensagens, ordem, papel | `messages` (SQLite) | mantido |
| 2 | Conversas | título, título travado, ativa | `conversations` | mantido |
| 3 | Fatos e preferências | nome, idioma, estilo, rotinas | **não existe** | `memory_facts` com consentimento |
| 4 | Memória de projeto | decisões, comandos, arquivos-chave por workspace | **não existe** (só recuperação lexical efêmera) | escopo por caminho do projeto |
| 5 | Conhecimento documental | anexos e trechos indexados | extração por mensagem (`attachments.py`) + `messages_fts` | índice incremental do workspace |
| 6 | Semântica (vetores) | embeddings | **nenhum** | adiada até haver evidência (ADR-004) |

## Orçamentos atuais (fato, verificável no código)

- Histórico enviado ao modelo: 12 mensagens, orçamento de 6.000 caracteres
  (`assistant._trim_history`, `MAX_CONTEXT_CHARS`).
- Contexto de projeto: até 3 arquivos, 5.000 caracteres, recuperação lexical,
  somente leitura (`workspace.retrieve_workspace_context`).
- FTS5 hoje é busca textual de histórico (`store.search_messages`) e **não está
  exposta na interface** — não é RAG.

## Regras de escopo e isolamento

1. Nunca cruzar conversas: A não vê B (coberto por `tests/test_store.py`).
2. Nunca cruzar projetos: memória de projeto é chaveada pelo caminho do workspace.
3. Conteúdo recuperado entra como **dado não confiável**, nunca como `system`.
4. Memória não é contexto: recuperar memória não autoriza ação alguma.

## Escrita de memória (proposta)

Uma memória só é gravada quando:

- o usuário declara explicitamente ("lembre que..."), **ou**
- o usuário confirma uma proposta na interface.

Toda linha de memória carrega: `origem` (conversa/mensagem), `escopo`, `criado_em`,
`confirmado_em`, `confianca` e `validade`. Fato conflitante substitui o anterior,
preservando histórico (nunca sobrescrita silenciosa).

## Exclusão e retenção

| Operação | Estado |
|---|---|
| Excluir conversa | implementado: apaga mensagens + registro e escolhe a próxima ativa (`store.delete_conversation`) |
| Excluir memória individual / por escopo / "esquecer tudo" | **proposta** (Fase 3) |
| Retenção | padrão indefinida para histórico local; configurável por camada |
| Auditoria | registra **metadados** de ação, nunca conteúdo (coerente com `audit_logger`) |

Exclusão precisa ser **verificável**: teste que apaga e relê o banco confirmando
ausência, incluindo o índice FTS (trigger `messages_ad` já cobre isso).

## Segredos

Redação acontece no limite do modelo (`_redact_secret_values`). Memória **não
guarda segredo**: se o texto a gravar casar com padrão de credencial, a gravação é
recusada e o usuário é avisado — nunca "salva mascarado".

## Critério para adotar busca vetorial (ADR-004)

Adotar somente se, no corpus real do usuário e no hardware alvo:

1. recall@10 da busca vetorial superar o FTS5 em **≥ 20%** nas tarefas reais; e
2. latência adicional por consulta for **< 200 ms**; e
3. rodar **localmente** (`sqlite-vec` no mesmo arquivo SQLite, embeddings locais).

Sem essas três condições, FTS5 permanece. Guardar o experimento em `docs/`.

## Riscos e testes-alvo

- **Alucinação de memória:** toda lembrança exibida deve citar origem e data.
- **Vazamento entre projetos:** teste com dois workspaces distintos.
- **Retenção silenciosa:** teste de "esquecer" com releitura do banco.
- **Memória envenenada:** conteúdo de arquivo/web não pode criar memória por si só.
