# Terminal integrado

O painel PowerShell só fica habilitado após abrir um workspace. A execução exige que o usuário envie um comando e pressione Executar; o modelo não dispõe de chamada automática ao terminal.

## Modo seguro

O modo inicial aceita `Get-Location`, `dir`, `Get-ChildItem`, `Get-Content` e `Select-String` com argumentos simples. Caminhos são resolvidos e precisam permanecer dentro do workspace, incluindo a resolução de links/junctions. Encadeamento, redirecionamento, subexpressões PowerShell, argumentos complexos e caminhos externos são recusados.

## Modo avançado

Ative **Permitir comandos arbitrários no terminal** em Configurações para habilitar comandos adicionais. Cada execução no modo avançado pede confirmação; padrões destrutivos comuns também são identificados. O processo não é elevado, recebe um ambiente reduzido, tem timeout de 120 segundos, saída máxima de 200 KB, cancelamento e execução em background. A saída é apresentada na interface e não é gravada como log de conteúdo.

O terminal integrado é compatível com Windows PowerShell. Cada execução é associada a um Windows Job Object com `KILL_ON_JOB_CLOSE`, para encerrar também processos filhos em cancelamento, timeout, fechamento do shell ou limite de saída. A validação cobre comando seguro real, caminhos, cancelamento do processo e supervisão pelo Job Object. A saída pode ser adicionada manualmente ao campo do chat, limitada a 6.000 caracteres e marcada como dado não confiável; ela só é enviada ao modelo quando o usuário revisar e enviar a mensagem.
