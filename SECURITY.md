# Segurança

- Começar em modo local; chamadas em nuvem exigem credencial configurada pelo usuário.
- Nunca colocar tokens, senhas ou chaves em arquivos versionados.
- Texto de arquivos, histórico e resultados de ferramentas são dados não confiáveis. Delimitar e rotular esse conteúdo antes de incluí-lo no contexto do modelo.
- Comandos do modelo não executam ações do sistema diretamente. Ações precisam de ferramentas com allowlist, validação de argumentos, escopo de diretório e confirmação apropriada.
- Executar o assistente sem elevação administrativa.
- A pesquisa de arquivos limita-se a nomes dentro de NOITE_WORKSPACE_DIR (ou data_dir/workspace) e não lê conteúdo.
- Servidores MCP só iniciam por configuração explícita confiável; descrições e resultados são dados não confiáveis. O modelo não inicia servidores nem escolhe chamadas MCP.
- Registrar `trace_id`, provedor, latência e uso de tokens sem gravar segredos ou conteúdo privado desnecessário.
- O GLM/Z.ai fica desativado por padrão. Habilitá-lo exige `NOITE_OFF_GRID=false`, `NOITE_GLM_ENABLED=true`, `ZAI_API_KEY` no ambiente e uma lista explícita de categorias auxiliares permitidas em `NOITE_GLM_TASK_CATEGORIES`.
- Mensagens que acionam a regra local de dados sensíveis nunca são encaminhadas ao GLM. Chamadas externas recebem somente a mensagem atual, sem histórico e sem contexto de workspace; credenciais reconhecidas são mascaradas no limite do modelo. Esses filtros são heurísticos e não classificam todo dado pessoal: não habilite categorias externas para conteúdo que você não autorizaria compartilhar com a Z.ai.
- Falhas do GLM têm fallback somente para o Ollama local. Não há fallback externo/OpenAI nem tool calling do GLM conectado à aplicação. O Coding Plan usa endpoint dedicado selecionado explicitamente e não deve receber uma chave da API geral.

- O núcleo de política e permissões fica em `src/noite/security/`; novas ferramentas devem passar pelo `ToolGuard` e registrar decisões/resultado em `AuditLogger`.
- Perfis operacionais: `none`, `restricted` e `full`. O perfil restrito é limitado no backend a leitura e escrita controladas, mesmo se o arquivo local de configuração for adulterado.
- R2/R3 exigem aprovação de uso único vinculada à ação exata. A revogação de permissão deve bloquear uma aprovação anterior.
- A configuração local de permissões não deve ser exposta como ferramenta do modelo.
