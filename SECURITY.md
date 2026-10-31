# Segurança

- Começar em modo local; chamadas em nuvem exigem credencial configurada pelo usuário.
- Nunca colocar tokens, senhas ou chaves em arquivos versionados.
- Texto de arquivos, histórico e resultados de ferramentas são dados não confiáveis. Delimitar e rotular esse conteúdo antes de incluí-lo no contexto do modelo.
- Comandos do modelo não executam ações do sistema diretamente. Ações precisam de ferramentas com allowlist, validação de argumentos, escopo de diretório e confirmação apropriada.
- Executar o assistente sem elevação administrativa.
- Registrar `trace_id`, provedor, latência e uso de tokens sem gravar segredos ou conteúdo privado desnecessário.
