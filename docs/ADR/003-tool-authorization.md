# ADR-003 — Autorização fora do modelo: `ToolGuard` é o único caminho

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (direção), arquitetura, engenharia

## Contexto

- O núcleo de segurança já existe e está testado (`noite.security`, 17 casos em
  `tests/test_security_core.py`): `PolicyEngine`, `ApprovalManager`,
  `AuditLogger`, `path_guard`, perfis de permissão.
- **Cobertura real hoje é 1 ponto:** apenas a chamada MCP passa por `ToolGuard`
  (`ui.py:3107`). Terminal e arquivos são chamados diretamente pela UI legada.
- Conteúdo de arquivo/web/ferramenta é não confiável e pode conter instruções
  (prompt injection). Instrução em prompt não é fronteira de segurança.
- Um servidor MCP não é "read-only por natureza": quem define o que pode ser
  chamado é a política local, não a documentação do servidor.

## Decisão

Três planos permanecem separados e inegociáveis:

1. **Inteligência** (modelo) pode *propor* uma ação.
2. **Autorização** (`ToolGuard` + `PolicyEngine`) decide se ela pode ocorrer.
3. **Execução** (executor) apenas executa o que foi autorizado.

Regras que decorrem:

- Nenhum executor pode ser chamado fora do `ToolGuard` — nem por prompt, roteador,
  orquestrador, UI ou servidor MCP.
- Toda ferramenta declara `Capability`, `operation`, `resource` e `RiskLevel`.
- Permissão padrão é **Sem acesso**; política só muda pela interface de configurações.
- Aprovação é emitida apenas pela UI confiável, vinculada ao *fingerprint* exato da
  ação, de uso único e validade curta.
- Auditoria registra metadados da decisão e do resultado, nunca conteúdo sensível.
- Cada ferramenta declara se a ação é reversível; o produto não promete undo do que
  não pode desfazer (`SECURITY_ARCHITECTURE.md`).

## Alternativas consideradas

- **Instruções no prompt ("não execute comandos"):** depende de o modelo obedecer.
  Insuficiente por definição. Rejeitado.
- **Confiar na lista de ferramentas do servidor MCP:** o servidor é terceiro; a
  política precisa ser local. Rejeitado como fonte única.
- **Sandbox de processo como substituto do `ToolGuard`:** complementar, não
  substituto — não responde "esta ação foi aprovada para este recurso?".

## Consequências

- D1–D3 (ver `SYSTEM_ARCHITECTURE.md`) são **bloqueantes**: nenhuma ferramenta nova
  entra antes de terminal, arquivo e MCP passarem pelo caminho único.
- Custo de desenvolvimento maior por ferramenta (declarar risco, aprovar, auditar).
  É intencional.
- Teste de segurança obrigatório: executar fora do guard **deve falhar**.

## Critério de revisão

Não previsto para flexibilizar. Só endurecer (ex.: ACL de sistema de arquivos,
sandbox de processo, separação de processo do Policy Engine).
