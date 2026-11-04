# Núcleo de segurança e permissões

**Estado:** primeira implementação da infraestrutura e painel de configuração. Não declarar o controle de todas as ferramentas concluído até a auditoria de todos os pontos de execução.

## Princípios

- O modelo propõe ações; o código decide se elas podem ser executadas.
- O padrão inicial é Sem acesso.
- Configurações de permissão são alteradas pela interface de configurações, não por mensagens ou saídas de ferramentas.
- Dados de arquivos, sites, terminais e MCP são conteúdo não confiável.
- Falha, configuração inválida ou ausência de permissão resulta em bloqueio.
- A aprovação é específica para uma ação, seus argumentos e seu recurso, tem validade curta e só pode ser usada uma vez.

## Perfis

- **Sem acesso:** nenhuma capacidade operacional liberada.
- **Acesso restrito:** somente leitura e escrita controlada de arquivos, se marcadas pelo usuário. Terminal, exclusão, aplicativos, rede e MCP permanecem bloqueados.
- **Acesso total configurável:** o usuário marca individualmente cada capacidade. Acesso total não desliga confirmação, auditoria ou validação.

## Componentes

- `models.py`: contratos tipados de ações, risco e decisões.
- `permission_manager.py`: carrega e persiste permissões em `<data_dir>/security/permissions.json`.
- `policy_engine.py`: decisão determinística ALLOW / DENY / REQUIRE_APPROVAL.
- `approval_manager.py`: aprovações temporárias, de uso único e vinculadas ao fingerprint exato da ação.
- `tool_guard.py`: ponto de execução que verifica política, consome aprovação e revalida revogação antes de chamar o executor.
- `path_guard.py`: valida caminho contido na raiz e rejeita traversal, symlinks e junctions.
- `audit_logger.py`: trilha SQLite em `<data_dir>/security/audit.sqlite3`, sem registrar argumentos brutos.
- `settings_dialog.py`: painel de controle operado pelo usuário, incluindo visualização do histórico.

## Risco inicial

- R0: leitura e consulta, sem confirmação se a capacidade estiver liberada.
- R1: alteração controlada em área autorizada, com registro.
- R2: execução de ferramenta ou aplicativo, exige aprovação.
- R3: ação destrutiva ou sensível, exige aprovação explícita.

R2 e R3 exigem token de aprovação. O token não é aceito se argumentos, recurso, agente, ferramenta ou operação forem alterados.

## Integração existente

A janela principal oferece **Configurações > Segurança e permissões**. O diálogo grava a política local.

Chamadas MCP feitas pelo diálogo de ferramentas agora verificam a capacidade MCP e exigem aprovação individual, além da aprovação da configuração do servidor já existente.

O núcleo ToolGuard está disponível para ser usado por futuras ferramentas e agentes. A auditoria do repositório ainda precisa localizar e migrar todos os pontos de execução existentes antes de afirmar que toda ação da Noite está protegida.

## Limites conhecidos e próximos passos

1. Separar o Policy Engine em processo/serviço de confiança menor que o agente; código malicioso executado no mesmo processo Python ainda pode tentar alterar arquivos locais.
2. Aplicar ACLs do Windows à configuração e ao banco de auditoria. SQLite não é inviolável contra o mesmo usuário do Windows.
3. Auditar todos os usos de `subprocess`, `os.system`, operações de arquivo, automação de UI, MCP e futuras ferramentas.
4. Conectar cada ferramenta ao ToolGuard; nenhuma ferramenta de agente deve receber acesso direto a executores.
5. Adicionar sandbox de processo com token restrito e limites de rede/arquivo. Job Objects controlam ciclo de vida e recursos, mas não são sandbox de segurança por si só.
6. Tratar aprovação R3 com confirmação gráfica separada; voz não deve ser o único fator.
7. Testar revogação concorrente, symlink/junction no Windows e falhas de armazenamento.

## Testes

A suíte `tests/test_security_core.py` cobre perfis, persistência, decisões, aprovações de uso único, revogação, ToolGuard, trilha de auditoria e caminhos.

## Contrato para novas ferramentas

Toda ferramenta nova deve:
1. Declarar uma Capability, operação, recurso e RiskLevel.
2. Construir ActionRequest com argumentos estruturados e validados.
3. Invocar ToolGuard, nunca chamar o executor diretamente a partir do agente.
4. Usar ApprovalManager somente em um fluxo de aprovação originado pela interface confiável.
5. Registrar a execução pelo AuditLogger.
6. Tratar o retorno do executor como dado não confiável.

Não adicionar atalhos de execução ao orquestrador, ao roteador, ao prompt ou a servidores MCP. O ToolGuard é a fronteira de despacho.

O contexto recuperado do workspace foi movido para o conteúdo da mensagem do usuário, serializado como JSON e rotulado como dado não confiável. Ele não é mais inserido como uma segunda mensagem `system`. Essa separação reduz a autoridade aparente de conteúdo externo, mas não substitui o Policy Engine nem a validação das ferramentas.

## Estado verificado em 2026-11-04 (HEAD `ed025f3`)

O núcleo está implementado e testado (`tests/test_security_core.py`, 17 casos).
O que **não** está completo é a cobertura: o `ToolGuard` é instanciado em
**um único** ponto de execução.

### Inventário de pontos de execução

| Ponto | Executa | Passa por `ToolGuard`? | Origem |
|---|---|---|---|
| Chamada MCP | processo MCP stdio | **sim** | `GuardedTools.execute` (PR 002) |
| Terminal | PowerShell com Job Object | **sim** (PR 002) | `GuardedTools.run_terminal` |
| Escrita de arquivo | `workspace.save_workspace_text` (atômico) | não | `ide.py:777` |
| Criação de arquivo/pasta | `workspace.create_workspace_*` | não | `ide.py:594`, `ide.py:619` |
| Busca no projeto | leitura de arquivos | não | `ide.py:216`, `assistant` (`tools.py`) |
| Iniciar Ollama | `subprocess.Popen` | não (ação explícita do usuário) | `assistant.start_ollama_server` |
| Abrir mascote | `subprocess.Popen` | não | `integrations/openwebui/noite_api.py:131` |
| Alteração de permissões | arquivo JSON | não se aplica (fluxo de configuração) | `security/permission_manager.py` |

Garantias adicionais desde o PR 003: caminho validado por componente nos dois
validadores (symlink/junction), resultado de execução auditado por `id` da
tentativa (retry não confunde linhas) e aprovações expiradas podadas.

Capacidades declaradas em `Capability` (files.read/write/delete, terminal,
applications, network, mcp): hoje **apenas `mcp.call` é avaliada na prática**.
As demais existem no modelo de política, mas os executores correspondentes não
as consultam.

### Consequência prática

Terminal e MCP já obedecem à política: sem `terminal.execute` ou `mcp.call`
concedidos, a chamada é negada, auditada e visível na interface (PR 002). O que
ainda falta é a **escrita/criação de arquivos do editor legado** (`ide.py`), que
continua chamando o executor direto — é uma exceção declarada e vigiada pelo
teste `tests/test_execution_boundary.py`, que falha se aparecer um novo ponto de
execução. Essa exceção fecha junto com a migração do editor para o painel do
mascote (ADR-006, fatia 2 / PR 006).

### Caminho único de execução (alvo da Fase 1)

```
Solicitação → Orquestrador → Proposta de ferramenta → ToolGuard → PolicyEngine
           → validação de parâmetros → aprovação (se R2/R3) → executor → auditoria
```

Critério de aceite: um teste tenta executar terminal, escrita de arquivo e MCP
**sem** `ToolGuard` e falha; com permissão revogada, falha; com aprovação emitida
para outra ação, falha.


## Reversibilidade por classe de ação

Nem toda ação pode ser desfeita. O sistema precisa reconhecer isso **antes** de
prometer "undo" ao usuário.

| Classe | Reversível? | Estratégia |
|---|---|---|
| Edição de arquivo no workspace | sim | hash anterior já verificado em `save_workspace_text`; undo por regravação do backup |
| Criação de arquivo/pasta | sim | remoção do item recém-criado (somente se vazio) |
| Exclusão de arquivo | **não** | confirmação explícita; nunca prometer undo |
| Comando de terminal | **não** | efeitos externos ao app; confirmação e escopo limitado |
| Chamada MCP de escrita | depende | declarado por ferramenta; padrão: irreversível |
| Mensagem enviada / ação em aplicativo | **não** | nunca prometer reversão |
| Alteração de permissão | sim | valor anterior persistido; reversão pela interface |

## Proteções exigidas antes de ampliar autonomia

1. **Path security** — um único validador: traversal, symlink e junction
   rejeitados, caminho sempre contido na raiz autorizada (`workspace.py` e
   `security/path_guard.py` seguem a mesma regra desde o PR 003).
2. **Execution security** — processo, argumentos, diretório, tempo e volume de
   saída limitados.
3. **Approval security** — aprovação vinculada a ação + parâmetros + fingerprint,
   uso único, validade curta, emitida só pela UI confiável.
4. **Recovery** — classe de reversibilidade declarada por ferramenta (tabela acima).

Referência de decisão: [ADR-003](ADR/003-tool-authorization.md).

## Comparação com a branch de auditoria (2026-11-01)

Fonte comparada: `origin/audit/local-snapshot-2026-11-01` (`b125fa1`, base
`0b9ca3a`), confrontada com a linha de trabalho atual.

**Conteúdo da branch:** 19 arquivos, +5.050 linhas, **todos artefatos** sob
`audit-expanded/` e `audit-snapshots/` — diffs de revisão, cópias de `src/` e
`tests/` como texto, `working-tree.diff`, `git-status.txt`, `validation-report.txt`
e um zip em base64. **Nenhuma alteração em `src/` ou `tests/` reais** (a
varredura por caminhos `^(src|tests)/` retorna vazio).

### Achados propostos x estado do código atual

| Achado da revisão | Estado na linha atual |
|---|---|
| Redação de URL com userinfo, incluindo IPv6 malformado | implementado (`_redact_url`); verificado: `http://user:s3nh4@[::1/x` → `http://[REDACTED]@[::1/x` |
| `Bearer`, `Basic` e bloco de chave privada | implementado (`_BEARER_VALUE`, `_BASIC_VALUE`, `_PRIVATE_KEY_BLOCK`) |
| Segredo em atribuição, com aspas e comentário | implementado (`_SECRET_VALUE`, `_QUOTED_SECRET`, `_redact_sensitive_assignments`) |
| Parâmetro sensível em query string | implementado (`_is_sensitive_query_key` via `urlsplit`) |

### Decisão

**Não integrar a árvore da branch de auditoria ao produto.** O merge é
mecanicamente possível (sem conflitos), mas adicionaria 19 dumps duplicados e
zero código — violaria a regra "isso torna a Noite melhor?". A branch permanece
publicada como prova de revisão; o conteúdo equivalente já está em
`src/noite/workspace.py` desde o baseline `76d7c91`.

### Branches comparadas

| Branch | Relação | Ação |
|---|---|---|
| `codex/stabilize-core` (`0b9ca3a`) | **ancestral** da linha atual | nada a integrar; PR #1 fica obsoleto |
| `audit/local-snapshot-2026-11-01` (`b125fa1`) | 19 commits à frente, só artefatos | não integrar (acima) |
| `main` (`813a350`) | 24 à frente / 3 atrás | 3 commits só removem `.env.example`, um zip de revisão e o binário `ia`; **não mesclar sem decisão** porque o README instrui copiar `.env.example` |
