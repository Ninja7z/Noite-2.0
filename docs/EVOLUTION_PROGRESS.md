# Progresso da evolução — Noite 2.0

## Fase atual

Estabilização das funcionalidades presentes concluída. O plano mestre ainda tem trabalho pendente nas Fases 4–8; esse estado não representa conclusão integral do produto.

## Ambiente e preservação

- Worktree de publicação: `publish/noite-ui-sanitized`, baseado em `origin/main` no commit `813a350618201452f3b60e3a0ba4bd42ce65613b`.
- Origem do conteúdo: branch local `ui-correcao`, HEAD `8572a37af5ce68ffaba0cc0a79ffb83816662169`, preservada sem alterações.
- O diff da publicação segue staged, sem commit ou push. As referências remotas não foram alteradas nesta preparação.
- O venv compartilhado foi reutilizado com `PYTHONPATH` direcionado ao `src` sanitizado; assim os testes não importaram o pacote editável da branch original.
- `.env` e o relatório de revisão estão fora da árvore atual. O histórico já existente em `origin/main` mantém suas versões antigas; esta branch não apaga nem reescreve esse histórico.
- `papeis-do-projeto.pdf` é mantido. O relatório de arquitetura com links Google Drive e `snapshot-legado.pdf` (na realidade, código Python) foram excluídos do conjunto de publicação e preservados localmente com hashes verificados.
- As entradas cronológicas abaixo registram estados anteriores da branch `ui-correcao`; suas referências antigas de branch, commit, porta e executável não descrevem o estado atual desta branch sanitizada.
- Hardware alvo registrado: Intel i7-3770 sem AVX2, GTX 1660 Super 6 GB, 16 GB DDR3, Windows 11 x64 e SSD SATA.

## Arquitetura observada

- UI PySide6 em `src/noite/ui.py`, com trabalho demorado em `QThread` e sinais Qt.
- `AssistantService` assíncrono controla conversas SQLite, roteamento, contexto e streaming.
- `model_gateway.py` usa LiteLLM para Ollama local e GLM opcional; GLM vem desligado por padrão e o modo off-grid força o roteamento local.
- Configuração usa Pydantic Settings e `.env`; tema atual está em `src/noite/theme.py`.
- IDE de projeto é um `QDockWidget`; ferramentas MCP stdio exigem aprovação humana.
- PyInstaller atual produz um lançador que depende do checkout e do `.venv`, não uma distribuição standalone.
- A UI já inclui Command Palette, painel de atividade, navegação e configurações de modelo; as quatro referências visuais ficam em `docs/reference/`.
- Documentos de continuidade antigos divergem do checkout atual em branch, commit e URL padrão Ollama; não foram tratados como estado autoritativo.
- Não foi encontrada pasta `.vscode` nos workspaces verificados. Dependências, modelos ou chamadas externas não foram adicionados.

## Baseline da Fase 1

Comandos executados em 2026-11-01 com o `.venv` existente:

| Comando | Resultado |
|---|---|
| `.venv\Scripts\python.exe -m compileall -q src` | Aprovado, exit 0 |
| `.venv\Scripts\ruff.exe check .` | Aprovado, exit 0 |
| `.venv\Scripts\python.exe -m pytest -q` | 177 passaram, 1 ignorado, exit 0 |
| `git diff --check` | Aprovado, exit 0; Git emitiu avisos de conversão LF/CRLF |

O Ollama e a conversa real local já haviam sido validados na recuperação anterior; a investigação não foi repetida.

## Resultado do portão da Fase 1

**Aprovado.** A baseline não introduziu falhas. A árvore contém alterações locais anteriores, todas preservadas.

## Fase 3 — fluidez e responsividade

- Streaming insere chunks como texto simples incrementalmente, sem reconstruir a conversa a cada 120 ms; Markdown é renderizado uma vez ao concluir.
- A reconstrução de histórico conserva a posição de leitura se o usuário não estava no fim e acompanha a resposta quando já estava no fim.
- Cancelamento real do worker assíncrono já estava implementado e foi preservado.
- Validação: teste de streaming passou; `pytest -q` — 178 passaram, 1 ignorado; Ruff passou. Compilação e `git diff --check` serão repetidos na estabilização.
- Resultado do portão: aprovado para seguir. Sem animações e sem dependências adicionais, para manter o uso leve no hardware alvo.

## Fase 2 — redesign visual e experiência

- Implementados temas escuro, claro e automático, com atualização em tempo real e persistência via `QSettings`.
- Sidebar realmente reposicionável à esquerda, direita ou topo; o topo usa navegação horizontal e mantém conversa e painel de atividade lado a lado.
- Persistência do modelo local, endpoint Ollama, posição da sidebar, tema e visibilidade do painel de atividade.
- Configurações apresentam controles de aparência/modelo e acesso às ferramentas locais MCP; seleção de modelo permanece integrada ao seletor existente.
- Teste Qt cobre troca de posição, tema e persistência; um caso também valida layout na largura mínima configurada.
- Open WebUI consultado como referência oficial; padrões de navegação e continuidade de conversa orientaram a divisão da área principal. Nenhum código ou dependência foi copiado.
- Validação: `pytest -q` — 178 passaram, 1 ignorado; `ruff check .`, `python -m compileall -q src` e `git diff --check` passaram. Execuções Qt parciais abortaram em combinações específicas; a suíte completa passou depois que o isolamento dos testes foi corrigido.
- Resultado do portão: aprovado para continuar. Teste visual manual completo em Windows continua pendente de estabilização final.

## Próxima ação

Retomar a Fase 4 do `MASTER_PLAN.md`: indexação incremental segura, contexto escopado e fluxo de proposta/aprovação/undo para alterações. Depois, avançar pelas Fases 5–8. Itens dependentes de servidor MCP Roblox real, avaliação de hardware/privacidade para voz e visão e instalador Windows completo ainda não foram implementados nem aprovados como concluídos.

## Estabilização desta rodada — 2026-11-01

- Corrigido `_update_project_context_status`: removida referência a `project_label`, que não existe no `NoiteWindow` e causava exceção ao selecionar workspace. Teste de regressão adicionado.
- Painel de atividade, terminal seguro, anexos locais (incluindo PDF via QtPdf), recuperação lexical de trechos, catálogo de metadados Hugging Face, preferências visuais/modelo e ícone foram exercitados pelos testes existentes.
- `pytest -q`: **209 passaram, 1 ignorado**, exit 0. `ruff check .`, `python -m compileall -q src tests` e `git diff --check`: exit 0. O format check direcionado ainda detecta formatação em cinco arquivos (`attachments.py`, `hf_catalog.py`, `terminal.py`, `ui.py`, `test_attachments.py`); não houve reformat em massa.
- Teste visual no Windows: janela abre, status informa Ollama conectado em `127.0.0.1:11434` e `qwen2.5:3b`; prompt curto enviado pela UI do EXE final recebeu `OK` em 7,9 s. A execução anterior encontrou e motivou a correção do atributo de projeto ausente.
- Consulta manual do catálogo público retornou cinco GGUF Q4_K_M e tamanhos em disco de 1,80–1,96 GiB; nenhum peso foi baixado. Isso não é benchmark de RAM/VRAM nem prova de AVX2.
- EXE final: `dist/Noite-2.0-Evolution-20261101-final.exe`, 8.681.583 bytes, SHA-256 `B9040F23CBF80779B13EF4DC2C690DE722B31D9CABAD31DB8478DDA481A7EC1B`. É um launcher dependente deste checkout e `.venv`, não pacote standalone. Os dois EXEs anteriores foram preservados.
- Não houve instalação/atualização de dependências, chamada GLM/Z.ai, commit, push, merge ou publicação.

## Escopo ainda pendente do plano mestre

- Fase 4: indexação incremental, fluxo de aprovação para patch multi-arquivo, undo/backup por operação e revalidação durante escrita.
- Fase 5: painel de estado/diff/histórico Git e operações locais reversíveis.
- Fase 6: observador Roblox condicionado à disponibilidade/capacidades do servidor MCP real.
- Fase 7: comparação/benchmark local de voz e visão, além de consentimento/retensão/edição de memória semântica.
- Fase 8: instalação e atualização em Windows limpo com rollback; matriz visual completa. O EXE atual prova execução neste checkout, mas não instalação limpa.

Não declarar essas fases completas até implementar e validar cada critério em `MASTER_PLAN.md`.

## Ajustes de interface visual — 2026-11-01

- As configurações agora ficam em uma área rolável e responsiva, com tamanho mínimo reduzido para 420×360; os grupos e campos continuam acessíveis em janelas compactas.
- A moldura nativa cinza foi substituída por barra própria integrada ao tema, com mover, minimizar, maximizar, fechar e alça de redimensionamento. A janela usa base 1672×941, ajusta-se à área útil da tela e mantém mínimo 920×620.
- A navegação reforça a marca da lua, a hierarquia Noite/2.0 e as sessões recentes; a tela inicial usa marca e tipografia maiores. O painel de contexto/atividade e as funções existentes foram preservados.
- A geração em streaming agora registra início, conclusão, erro ou cancelamento observáveis; a etapa de apresentação final também é registrada. Não há exposição de raciocínio privado. O scroll manual permanece estável durante a chegada de trechos.
- Testes de regressão cobrem configurações compactas, barra frameless, atividade de geração e preservação da posição de leitura.
- A UI permanece conectada ao `AssistantService`/Ollama local real; não foi introduzido `MockClient` no app funcional.
- Captura manual do EXE final em Windows 11 (1366×768): janela arredondada/frameless, controles próprios, navegação à esquerda, entrada visível e status `Online`; maximizar/restaurar foram acionados. A checagem de inicialização foi concluída. O Ollama local reportou `qwen2.5:3b`.
- Diferenças ainda visíveis em relação à imagem: o painel à direita prioriza contexto/atividade real em vez do banner de destaques e lista de ferramentas; os chips e ícones usam os recursos funcionais existentes; o fundo ainda não tem as ondas e estrelas da referência. Esta rodada não substituiu o `AssistantService` por um mock e não criou um segundo app desconectado.
- Validação final após os ajustes de janela: `pytest -q` — 211 passaram, 1 ignorado; `ruff check .`, `python -m compileall -q src tests` e `git diff --check` passaram. O último comando informou apenas avisos de conversão LF/CRLF existentes no checkout.
- EXE separado gerado e aberto: `dist/Noite-2.0-ReferenceFit-20261101.exe`, 8.679.371 bytes, SHA-256 `7EA383AD7C842DCD88DCDA6FECB32A25293ECF1D34A63B95DFB3DC392D78844E`. Build PyInstaller é lançador dependente do checkout e `.venv`; EXEs anteriores foram preservados.
- O teste de interface confirmou início e status do backend, mas nenhuma nova mensagem foi enviada nesta rodada; a validação de conversa real permanece a execução local já registrada na seção de estabilização.

## Continuidade da correção visual — 2026-11-01

- Comparação visual executada em modo `--mock` a 1366×768; referência original é 1672×941. O mock existe apenas para comparação e não altera a preferência persistida. A janela do cliente real abriu e exibiu Ollama `Online` com `qwen2.5:3b`.
- Validação local do `ServiceClient` em `127.0.0.1:11434`, modelo `qwen2.5:3b`: modelo instalado, um chunk recebido e resposta `OK`. Isso valida a chamada do cliente de serviço, não uma mensagem enviada pela interface real.
- Validação final: `.venv\Scripts\python.exe -m pytest -q` — **215 passaram, 1 ignorado**, exit 0; `.venv\Scripts\ruff.exe check .` — aprovado, exit 0; `compileall -q src ui run_ui.py tests` — exit 0; `git diff --check` — exit 0.
- EXE gerado e inicializado: `dist/Noite-2.0-UI-ReferenceFit-20261101.exe`, 8.681.241 bytes, SHA-256 `BEF3A2153A328984DA58D7AE9EF825A893007A0E427F28E48ED3A8C2BC950815`. É lançador dependente do checkout e `.venv`, não instalador/autônomo. EXEs anteriores foram preservados.
- Diferenças/limites observados: a conta real mantém a posição de sidebar previamente salva (topo); a comparação mock usa sidebar à esquerda. O avatar fotográfico é representado por inicial; o banner usa ilustração vetorial em vez de fotografia; calculadora e pesquisa web aparecem sem ação implementada; captura do tema claro e gesto manual de redimensionamento não foram validados visualmente. A captura disponível não permite declarar paridade pixel a pixel.
- Estado Git preservado na branch `ui-correcao`, HEAD `2176ec5`; sem commit, push, merge ou operação remota. Alterações locais e arquivos novos continuam no working tree.

## Correção visual e entrega — 2026-11-02

- Painel direito limitado a Destaques, Contexto Atual e Ferramentas; atividade removida. Largura adaptável, diretório com reticências centrais, banner quebrável e recolhimento abaixo de 1200 px.
- Barra superior sem marca duplicada; mensagens sem cartões, rótulos Você/Noite e copiar em blocos Markdown/código.
- Pensamento só aparece quando o Ollama fornece o campo nativo. A detecção é feita por metadados e o gateway usa `think=true` no streaming compatível; `qwen2.5:3b` instalado não anuncia suporte. Nenhum modelo foi baixado.
- Janela frameless com resize por bordas/cantos, tamanho inicial limitado à tela, scrollbars finas com auto-hide, streaming em blocos e redução de animações consultada no Windows.
- Validação final: `pytest -vv -x` — 222 passaram, 1 ignorado (symlink externo não suportado nesse teste no Windows); `ruff check .`, `compileall -q src ui run_ui.py tests` e `git diff --check` passaram.
- Capturas mock de comparação geradas para 1280×720 e 1672×941, dark/light, pensamento aberto/fechado na pasta de revisão externa ao repositório `Noite-ui-review-20261102`. A janela real abriu e mostrou Ollama Online com `qwen2.5:3b`; a conversa real está registrada na seção de ajustes solicitados abaixo.
- Diferenças conhecidas: ilustração vetorial de notebook em vez de fotografia;  cantos/título do Qt não são pixel idênticos. O pensamento real não pôde ser exibido com o modelo instalado.
- Build: `dist\Noite.exe`, 8.681.064 bytes, SHA-256 `23E9D181FCAFB5EFE43CD61A022C74F214151D91B1A8BF7614ACEAA63B89E53D`; inicialização confirmou status local Online. Build é launcher dependente do checkout e do `.venv`, não instalador standalone.
- Atalho de desktop `Noite.lnk` atualizado e relido: aponta para esse `Noite.exe`, diretório de trabalho do worktree e `assets\noite.ico`.
- Permanecem quatro EXEs antigos em `dist`; a tentativa de removê-los foi rejeitada pelo executor e não foi repetida por outra via.
- Registro histórico: na ocasião, as alterações locais da branch `ui-correcao` foram preservadas sem commit ou push. O estado atual da publicação está descrito no início deste documento.


## Ajustes solicitados — 2026-11-02

- Sidebar inicia à esquerda, ignorando a preferência anterior; a seleção da tela de configurações continua disponível durante a sessão.
- Título do banner em duas linhas explícitas. Abaixo de 340 px, a ilustração cede espaço ao texto para evitar quebra extra.
- Teste de layout estreito atualizado e validado. Suíte: 222 passaram, 1 ignorado. Ruff, compilação e diff check aprovados.
- Mensagem enviada pela UI com `ServiceClient` e `qwen2.5:3b`: pergunta “Responda apenas: integração real confirmada.”; a resposta “integração real confirmada.” apareceu no chat. O EXE novo abriu e mostrou a conversa salva.
- Novo `dist\Noite.exe`: 8.679.768 bytes; SHA-256 `0FCCE2695CCB10B540FA24BA6E67CD8AC70E6905D725E507CF8049EBC221CCD8`. Atalho da Área de Trabalho relido e apontando ao build, ao diretório correto e ao ícone `assets\noite.ico`.
- Os quatro builds antigos continuam em `dist`, aguardando confirmação explícita para remoção.
