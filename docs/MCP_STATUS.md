# Estado de MCP

Há um cliente MCP local em `src/noite/mcp_client.py` e um painel de configuração na interface. A tela grava definições locais em `~/.noite/mcp_servers.json` (ou no `data_dir` configurado), inicia o servidor por stdio somente depois de confirmação e descobre as ferramentas publicadas.

Cada chamada requer aprovação humana em tempo de execução. A caixa de confirmação mostra o servidor, o nome da ferramenta e os argumentos JSON enviados; a chamada só é iniciada depois da resposta afirmativa. A UI permite escolher uma ferramenta descoberta, não encaminha mensagens do modelo para MCP, não passa o resultado MCP ao modelo e apresenta o retorno como texto externo não confiável. Os argumentos são validados pelo schema JSON do servidor e o cliente limita cada chamada à ferramenta aprovada naquela interação.

O comando e os argumentos do servidor são executados diretamente, sem shell. Configure somente executáveis locais que você confia. O comando pode executar código local com as permissões do usuário atual.

O teste de integração stdio usa um servidor de eco local. HTTP e descoberta automática de servidores não estão implementados; transporte remoto requer uma política de rede explícita.
