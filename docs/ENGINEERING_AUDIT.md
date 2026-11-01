# Auditoria de engenharia — 2026-11-01

## Escopo e evidências

Auditoria do checkout `C:\Users\crist\Noite-2.0\Noite-2.0-canonical`, branch `codex/stabilize-core`, commit inicial `fc62d00e95699bfc85b3a10872b107f65a04199a`. O checkout estava limpo e `origin` apontava para `Ninja7z/Noite-2.0`. O PR #1 estava aberto como draft, sem merge, com esse head.

- Python global: 3.14.7; ambiente `.venv`: 3.13.16.
- Dependências atuais incluem PySide6 6.12.0, LiteLLM 1.106.6, Pydantic 2.14.2, pytest 9.2.0 e Ruff 0.17.3.
- Configuração efetiva: Ollama em `http://127.0.0.1:11435`, modelo `qwen2.5:3b`, dados em `%USERPROFILE%\\.noite`, sem workspace configurado.
- Ollama respondeu HTTP 200; o modelo configurado apareceu na lista local.
- Banco real: 22 mensagens, todas em `conversation_id='default'`; tabelas `messages`, `messages_fts` e `noite_metadata`. Ainda não existe tabela de conversas.
- `.env` não está presente nem rastreado no checkout; o histórico inclui `.env` no commit `9af7993`. Inspecionei os campos sem revelar valores: a chave Anthropic estava vazia e os demais campos eram configurações locais. Não encontrei segredo preenchido. `.env.example` é rastreado.
- Baseline: `pytest -q` — 35 passaram; `ruff check .` — passou.
- GitHub Actions para `fc62d00` passou em Ubuntu e Windows; PR #1 permanece draft.

## Mapa da arquitetura atual

| Área | Estado | Evidência / limite |
|---|---|---|
| Interface | Parcialmente funcional | PySide6, chat, streaming, cancelamento, estado do Ollama e diálogo MCP. Três glifos da barra lateral são `QLabel`, não controles; projeto e conversa são etiquetas estáticas. |
| Conversas | Parcial | `messages.conversation_id` já existe, mas a UI fixa `default`; não há criação, índice lateral, renomeação, exclusão ou restauração da conversa ativa. |
| Núcleo de conversa | Funcional com limites | `AssistantService` roteia regras simples, respostas determinísticas e Ollama; cada requisição usa SQLite e contexto recente. |
| Identidade | Parcial | Há resposta determinística para “sobre a Noite”; “quem é você?” não está coberto e pode ser respondido pelo modelo. |
| Gateway | Funcional | LiteLLM assíncrono, Ollama local, streaming, timeout e mensagens de erro sanitizadas. |
| Roteador | Parcial | Regras para busca de nomes e intenção de abrir aplicativo; demais pedidos seguem ao chat. Não existe classificador de intenção local separado. |
| Ferramentas | Parcial | A busca retorna somente nomes dentro do workspace. Abrir aplicativo retorna que a ferramenta não está autorizada; não executa comandos arbitrários. |
| Banco e histórico | Parcial | SQLite persistente e FTS5 com triggers e migração de `conversation_id`; sem entidade de conversa, projeto ou estado ativo. |
| Memória | Parcial | Histórico textual pesquisável; não há memória semântica/procedural nem contexto estruturado por projeto. |
| Sistema de arquivos | Ausente para leitura/edição | A busca atual lista nomes; não há editor, explorador de projeto ou leitura seletiva de fontes. |
| Terminal e execução | Ausente na GUI | Existe CLI do assistente, mas não existe terminal de projeto, gerenciamento de subprocessos ou execução sob escopo de workspace. |
| Diagnósticos e testes | Ausente na GUI | Testes do próprio aplicativo existem; a UI não apresenta resultados, problemas, lint ou navegação para linhas. |
| Git | Ausente na UI | Não há visualização de status, diff, histórico ou ações locais Git. |
| MCP | Parcialmente funcional | Cliente stdio e diálogo manual; servidor confiável é configurado localmente e cada chamada exige confirmação. Não há integração específica do Roblox confirmada. |
| Agentes | Ausente | Não há agentes especializados ou coordenador; modelo local único é coerente com o hardware e deve ser preservado. |
| Logs | Parcial/ausente | Há `trace_id` no esquema das mensagens, mas não há pipeline de logs estruturado/observabilidade descrito nos módulos inspecionados. |
| Empacotamento | Parcial | `Noite.exe` é lançador dependente do checkout/venv, não pacote standalone. O erro QtWidgets em build congelado continua documentado. |

## Diagnóstico dos relatos

1. **Novas conversas:** confirmado. A persistência tem coluna de conversa, mas a UI usa ID fixo e o banco não registra metadados das conversas.
2. **Gerenciamento do histórico:** confirmado como ausente. Só mensagens são persistidas; nenhum CRUD de conversas.
3. **Identidade Qwen:** confirmado como risco. “Sobre a Noite” é determinístico, mas perguntas naturais de identidade/modelo não são tratadas; a resposta recai no LLM.
4. **Botões laterais:** confirmado em parte. A maioria dos glifos é texto estático; MCP é o único controle lateral claramente ligado a uma ação. Não há projeto, busca global, explorador nem configurações na UI.
5. **Experiência visual:** a composição escura atual é uma referência, mas o app continua sendo chat com sidebar, não a IDE multi-painel solicitada.
6. **Executável:** confirmado como lançador local, não standalone. Não confundir a validação do lançador com distribuição autônoma.
7. **IDE:** confirmado como ausente: editor, abas, terminal, painel inferior, diagnósticos, diff e contexto real de projeto ainda não existem.

## Documentação e arquitetura de referência

O README e os documentos atuais descrevem o núcleo local-first e suas restrições de segurança. `docs/roadmap.md` ainda apresenta expansão como fase futura. `docs/CONTINUATION_STATE.md` e `docs/PROJECT_INVENTORY.md` continham hashes e estado de Git antigos; devem ser alinhados ao checkout corrente. O relatório PDF de arquitetura analisa o protótipo legado, não comprova capacidades do checkout atual; sua recomendação de desacoplar UI/núcleo é compatível com a separação já existente entre PySide6, serviço e gateway.

## Componentes reutilizáveis

- `AssistantService`, roteador, gateway LiteLLM e contratos Pydantic.
- SQLite, migração já existente, FTS5 e histórico por `conversation_id`.
- `TaskThread`, stream/cancelamento e encerramento coordenado da janela.
- Painel MCP com aprovação explícita, cliente stdio e limites documentados.
- Tema visual atual, layout escuro e controles de envio/estado.

## Componentes para evolução/refatoração

- Criar entidade/metadados de conversa e estado ativo persistente sem regravar o histórico existente.
- Substituir elementos estáticos da navegação por ações funcionais e acessíveis.
- Extrair serviços de conversa/projeto/editor/execução da classe `NoiteWindow` conforme as fases avançarem.
- Implementar contexto de workspace por recuperação seletiva antes de conectar o LLM a operações de código.
- Isolar terminal e operações de escrita em API de permissões/propostas; nunca executar texto arbitrário do modelo.

## Riscos e restrições

- Não misturar histórico de sessões: toda consulta/escrita deve usar o ID ativo explicitamente.
- O banco real contém dados do usuário; migrações devem ser aditivas e testadas numa cópia antes de tocar nos dados reais.
- Comandos de terminal e escrita de arquivos elevam o risco; usar workspace canônico, proposta/diff, confirmação e cancelamento de subprocesso.
- Projetos grandes podem exceder o contexto; usar indexação incremental e seleção limitada de arquivos.
- i7-3770, GTX 1660 Super 6 GB e 16 GB RAM favorecem um modelo local ativo por vez, operações assíncronas e dependências leves.
- Capacidade do MCP do Roblox permanece a confirmar com documentação e servidor real; não assumir que fornece Explorer, Output ou Play mode.

## Plano e critérios de aprovação

Ver [MASTER_PLAN.md](MASTER_PLAN.md). A execução começa pela Fase 1: persistência real de conversas e identidade determinística. Critério: duas conversas isoladas, CRUD com confirmação, restauração após reinício, migração compatível do banco existente e testes passando. Não fazer commit, push, merge ou alteração remota sem nova autorização específica.

## Situação após a auditoria

Este documento preserva o diagnóstico do início (HEAD `fc62d00`). Depois da inspeção, as lacunas da Fase 1 foram implementadas localmente: conversas independentes/CRUD, identidade e ações laterais. A base do usuário foi migrada após cópia de segurança e verificação de integridade. A Fase 2 começou com abertura segura de workspace, árvore e editor inicial; o estado atual e a validação mais recente estão em `CONTINUATION_STATE.md` e `ENGINEERING_LOG.md`. O PR não foi alterado; alterações locais continuam sem commit.
