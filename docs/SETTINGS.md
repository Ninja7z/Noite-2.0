# Configurações da interface

Configurações ficam em `QSettings` por usuário Windows. A tela salva imediatamente as opções aceitas e restaura-as no próximo início.

- Aparência: escuro, claro e automático conforme o esquema de cores do sistema.
- Navegação: esquerda, direita ou superior; a posição superior usa disposição horizontal.
- Ollama: modelo local e endpoint HTTP. O padrão é `http://127.0.0.1:11434`.
- Painel de progresso: recolhido até abertura manual, abrir durante operação, ou sempre visível.
- Terminal: modo avançado separado e desativado por padrão.
- Ferramentas MCP: configuração e aprovação permanecem em diálogo próprio.

Os estados de progresso são eventos observados do aplicativo, com duração medida localmente. Nenhum chain-of-thought é solicitado ou exibido.
