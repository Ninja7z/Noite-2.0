# Plano mestre de engenharia — Noite 2.0

Este plano evolui o núcleo atual em fases pequenas. A execução não pula critérios de validação. Funcionalidades indisponíveis em APIs externas ficam explicitamente pendentes.

## Princípios permanentes

- Preservar o núcleo PySide6, `AssistantService`, Ollama, SQLite e MCP manual sempre que possível.
- Identidade Noite separada do nome/modelo do provedor.
- Histórico e contexto sempre escopados a uma conversa e a um projeto.
- Nenhuma execução arbitrária pelo modelo; nenhuma escrita silenciosa.
- Operações longas fora da UI; caminhos limitados ao workspace; aprovações antes de escrita/exclusão/execução.
- Uma inferência local de cada vez por padrão, respeitando 6 GB de VRAM.
- Não executar commit, push, merge, release ou exclusão remota sem autorização explícita.

## Fase 0 — Auditoria

- [x] Conferir checkout, branch, remotos, PR, Python, dependências, Ollama, SQLite e testes.
- [x] Ler código, documentação, segurança, build e referências de arquitetura.
- [x] Registrar fatos e lacunas em `ENGINEERING_AUDIT.md`.
- [x] Corrigir registros de continuação/inventário para o head e as conclusões atuais.

Critério: diagnóstico reproduzível com distinção entre comportamento atual e visão futura.

## Fase 1 — Núcleo e conversas

- [x] Adicionar entidade persistente de conversas, título, datas e conversa ativa; preservar mensagens legadas `default`.
- [x] Criar, listar, abrir, renomear e excluir conversa com confirmação; restaurar após reinício.
- [x] Atualizar título inicial a partir da primeira mensagem sem sobrescrever título renomeado pelo usuário.
- [x] Tornar a identidade e a resposta de modelo ativo determinísticas.
- [x] Substituir glifos acionáveis decorativos por botões acessíveis com ações reais.
- [x] Adicionar testes de migração, isolamento, CRUD, restauração e identidade.

Critério: histórico de A nunca aparece em B; CRUD persiste ao reiniciar e exclusão só afeta a conversa selecionada.

## Fase 2 — Estrutura da IDE

**Decisão do editor:** começar com `QPlainTextEdit` + `QSyntaxHighlighter` nativos do Qt. O controle é otimizado para texto e suporta realce; mantém o binding PySide6 já instalado sem nova dependência. QScintilla tem recursos avançados, mas os bindings oficiais publicados são PyQt e o projeto usa licença GPLv3/comercial. Fontes: [Qt for Python — QPlainTextEdit](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QPlainTextEdit.html), [Qt for Python — QSyntaxHighlighter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QSyntaxHighlighter.html), [Riverbank — QScintilla e licença](https://www.riverbankcomputing.com/software/qscintilla/intro).

- [x] Comparar componentes de editor PySide6/Qt compatíveis com Python 3.11+ e licença do projeto.
- [x] Abrir workspace com caminho visível e reabrir último workspace.
- [x] Buscar texto no projeto fora da thread da UI, com limites de leitura/resultados, filtros de segredos/dependências e navegação para arquivo/linha.
- [x] Explorador com leitura e criação de arquivo/pasta na raiz, sempre após confirmação; criação não sobrescreve itens.
- [x] Editor com abas, numeração de linhas, destaque básico Python, busca no arquivo, dirty marker, undo/redo nativo e salvamento explícito.
- [x] Implementar primeira fatia: abrir texto UTF-8 menor que 1 MB em abas, linha atual/números, destaque básico de Python, marcador de alteração e salvamento explícito com proteção contra alteração externa.
- [x] Bloquear leitura e escrita de padrões comuns de credenciais e rejeitar caminhos fora do workspace, links simbólicos da árvore, binários e arquivos grandes; `.env.example` permanece legível.
- [x] Navegação à linha por resultado da busca global e preservação de BOM/terminadores de linha.
- [x] Busca e substituição básica no arquivo aberto, apenas no buffer, com undo em um passo.
- [ ] Renomeação/exclusão com confirmação e busca/substituição avançadas. Segurança de operações de arquivo descrita em `WORKSPACE_OPERATIONS_SECURITY.md`; rename/delete aguardam revisão antes da implementação.

Critério: abrir, editar, salvar, fechar e reabrir arquivo real em workspace de teste sem perda de dados.

## Fase 3 — Terminal e qualidade

- [x] Terminal PowerShell por subprocesso, workspace obrigatório, saída incremental, timeout, limite de saída, cancelamento e supervisão da árvore por Windows Job Object.
- [x] Mostrar saída combinada stdout/stderr, erro e código de saída; não elevar privilégios.
- [x] Modo seguro com allowlist de leitura e caminho resolvido dentro do workspace; subexpressões e encadeamento bloqueados.
- [x] Modo avançado do usuário separado, com confirmação de comandos destrutivos.
- [ ] Adicionar painel Problemas, integrações configuráveis de Ruff/pytest e navegação para arquivo/linha.
- [x] Diagnóstico inicial de sintaxe Python por AST no buffer atual, sem executar código, com navegação para linha/coluna.
- [ ] Mostrar e cancelar execução de testes sem bloquear Qt.

Critério: comando benigno real executa em projeto de teste, processo longo pode ser interrompido e UI continua responsiva. Os diagnósticos automáticos Ruff/pytest permanecem fora desta entrega.

## Fase 4 — Contexto de projeto e programação controlada

- [x] Recuperação lexical inicial do buffer ativo e de até três arquivos relevantes; limitada a 5.000 caracteres, somente em modo off-grid, com segredos comuns mascarados e conteúdo marcado como dado não confiável.
- [ ] Indexar caminhos e símbolos incrementalmente, respeitando ignore/secret patterns e limites de tamanho.
- [ ] Ler somente arquivos selecionados como relevantes; nunca incluir `.env`, credenciais, binários ou conteúdo ignorado.
- [ ] Usar contexto do projeto/editor/seleção/terminal/testes no `AssistantService`.
- [ ] Preparar plano e diff antes de escrever; mostrar a proposta; pedir aprovação por conjunto de arquivos.
- [ ] Criar backup/undo local por operação e registrar ações sem conteúdo sensível.
- [ ] Revalidar escopo de cada caminho antes e durante aplicação.

Critério: tarefa multi-arquivo num projeto de teste é investigada, proposta, aprovada, aplicada, testada e desfeita.

## Fase 5 — Git local

- [ ] Apresentar branch, status, diff por arquivo e histórico de commits.
- [ ] Oferecer operações locais reversíveis e com confirmação.
- [ ] Bloquear push/merge/remotos sem autorização explícita.

Critério: diff compreensível e operação local controlada; nenhum acesso remoto automático.

## Fase 6 — Roblox Studio

- [ ] Confirmar documentação oficial do MCP e capacidades reais da versão disponível.
- [ ] Implementar observação somente leitura e mostrar origem/limitações dos dados.
- [ ] Mapear Explorer/scripts/propriedades/seleção/Output somente se expostos pelo servidor real.
- [ ] Exigir aprovação por alteração, execução, Play mode ou escrita.

Critério: investigar projeto Roblox real em read-only e verificar que nenhuma chamada de escrita ocorre sem consentimento.

## Fase 7 — Voz, visão e memória

- [ ] Comparar Silero VAD, openWakeWord, faster-whisper e Piper no hardware real antes de instalar.
- [ ] Separar memória episódica do histórico; definir consentimento, retenção, edição e exclusão para memória semântica/procedural.
- [ ] Avaliar captura autorizada de tela, modelos multimodais e custo de VRAM/latência.

Critério: benchmark reproduzível, consumo aceitável, controles de privacidade testados.

## Fase 8 — Distribuição e acabamento

- [ ] Validar estratégia de empacotamento Qt em ambiente Windows limpo.
- [ ] Instalar/atualizar mantendo `%USERPROFILE%\\.noite`; rollback e logs de falha.
- [ ] Avaliação visual/interativa completa no Windows e matriz de regressão.

Critério: iniciar por instalação/atalho em Windows limpo, usar funções centrais e preservar dados após atualização.

## Estado

- Fase atual: 4 — contexto de projeto e programação controlada.
- Fases 0–3: base, conversas, IDE inicial, fluidez/terminal e atividade implementados em partes; ver `EVOLUTION_PROGRESS.md` para teste e limites.
- Fase 2: editor, busca, criação confirmada, sidebar reposicionável, Command Palette, temas e configurações presentes. Rename/delete continuam fora do escopo autorizado.
- Fase 3: terminal PowerShell seguro e diagnóstico AST presentes; painel Problemas e execução/cancelamento não bloqueante de pytest/Ruff seguem pendentes.
- Fase 4–8: incompletas; não avançar o status sem satisfazer os critérios de cada fase. Detalhes e próxima tarefa em `EVOLUTION_PROGRESS.md`.
- Revisar `TEST_MATRIX.md` e `CONTINUATION_STATE.md` ao concluir cada fase.
