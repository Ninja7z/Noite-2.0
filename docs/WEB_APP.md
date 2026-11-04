# Noite Web

A interface web da Noite 2.0 é o ambiente principal de interação no navegador. A rota raiz (/) abre diretamente o workspace, não uma página institucional. Conversação é uma das áreas da interface, ao lado da navegação para projetos, atividades, memória, ferramentas e configurações.

## Camadas

- landing/: frontend principal servido na raiz. Contém o shell da interface, navegação, experiência de conversa e áreas em estruturação.
- landing/assets/: estilos e scripts da interface principal. A camada de chat reutiliza a integração já existente.
- integrations/openwebui/web/: versão anterior/preview da interface de conversa, preservada em /app/ durante a transição.
- integrations/openwebui/noite_api.py: API local, sessão web e endpoints same-origin.
- AssistantService, Orchestrator e SQLite: conversas, histórico e atividades compartilhados.
- Open WebUI permanece como subsistema de capacidades e integrações, não como identidade visual da interface.

## Execução local

O serviço de integração existente continua em 127.0.0.1:8765.

Para executar a interface principal em desenvolvimento:

```powershell
Set-Location integrations/openwebui
..\..\.venv\Scripts\python.exe -m uvicorn noite_api:app --host 127.0.0.1 --port 8766
```

Abrir http://127.0.0.1:8766/ para acessar a interface principal. A rota /app/ mantém temporariamente a versão anterior para comparação durante a refatoração.

## Estado da interface

- Conversas: conectadas ao histórico SQLite e ao Orchestrator, com streaming SSE.
- Atividades: painel conectado aos eventos registrados durante as solicitações.
- Projetos, memória, ferramentas e configurações: navegação e estrutura visual inicial; ainda não conectadas às respectivas operações reais.
- Voz, anexos, visão e controle de aprovações: não fazem parte desta entrega visual.
- A identidade visual definitiva do mascote permanece em aberto. A interface usa um elemento abstrato de estado, não um personagem definido.

## Segurança e limites

- O servidor de desenvolvimento permanece vinculado a 127.0.0.1; não é exposto à rede local.
- A API key interna não é enviada ao navegador.
- Sessão com cookie HttpOnly, SameSite Strict e token CSRF para operações mutáveis.
- Origem e Host são validados; headers de segurança são aplicados.
- Ações sensíveis não são habilitadas pela interface web nesta etapa.
- A interface é responsiva, mas acesso pelo celular via rede local exige pareamento/autenticação e transporte seguro. Não abrir a porta na LAN sem essa camada.