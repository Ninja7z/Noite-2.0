# Estado de MCP

Há um cliente MCP local inicial em src/noite/mcp_client.py: conecta por stdio usando o SDK oficial, inicializa a sessão, descobre schemas e chama ferramenta explicitamente autorizada após validação JSON Schema.

Próxima etapa para MCP:

1. Integrar configuração e conexão/desconexão à interface.
2. Adicionar confirmação humana por chamada na interface.
3. Testar ciclo de vida do processo stdio com um servidor de teste real.
4. Adicionar suporte a transporte HTTP somente com política de rede explícita.

O modelo não inicia servidores nem escolhe ferramentas. O chamador constrói a configuração confiável MCPServer; chamadas fora de allowed_tools são negadas. Conteúdo retornado é texto externo e não é inserido automaticamente no prompt. Servidores MCP seguem desativados no fluxo de chat até existir configuração e aprovação na interface.
