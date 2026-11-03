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
