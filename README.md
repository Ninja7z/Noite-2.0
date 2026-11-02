# Noite 2.0

Assistente desktop local-first em português. O MVP inclui chat PySide6, respostas rápidas, gateway Ollama e histórico SQLite.

## Escopo inicial

- Núcleo assíncrono em Python, com contratos validados por Pydantic.
- Roteador determinístico para comandos simples e encaminhamento de conversas ao modelo local.
- LiteLLM como gateway; Ollama com `qwen2.5:3b` como modelo local inicial.
- Respostas do modelo aparecem em streaming; o usuário pode cancelar uma geração ativa.
- SQLite com FTS5 para histórico textual. A extensão vetorial fica para uma etapa posterior.
- Interface PySide6 funcional está disponível como extra opcional, com painel MCP para servidores stdio configurados localmente e chamadas aprovadas pelo usuário. Automação do Windows continua fora do MVP.
- Chamadas em nuvem ficam desativadas por padrão e exigem configuração explícita de credenciais.
- A interface PySide6 inclui Command Palette (`Ctrl+K`), temas escuro/claro/sistema, sidebar que inicia à esquerda e pode ser reposicionada, além do painel lateral Destaques/Contexto Atual/Ferramentas. O chat mostra o estado da geração; o bloco de pensamento só aparece se o modelo enviar esse campo.
- Ollama é o catálogo local; a busca pública Hugging Face só roda após solicitação e envia apenas o termo de pesquisa. Não há downloads automáticos.
- O terminal integrado exige ação explícita do usuário, limita o modo seguro a comandos de leitura no workspace e mantém modo avançado separado.
- Anexos TXT, MD, PY, JSON, CSV, XML, LOG, YAML, PDF, DOCX, XLSX e PPTX são extraídos sem execução e enviados em trechos limitados e relevantes.

## GLM-5.3-Flash opcional

O Ollama continua sendo o padrão local. O GLM é opcional, fica desativado por padrão e só recebe categorias de tarefa explicitamente autorizadas. Para ativar a API geral internacional da Z.ai, configure no `.env`:

```dotenv
NOITE_OFF_GRID=false
NOITE_GLM_ENABLED=true
NOITE_GLM_API_MODE=general
NOITE_GLM_TASK_CATEGORIES=summarization,classification
ZAI_API_KEY=
```

O identificador padrão é `zai/glm-5.3-flash`. O modo `general` usa `https://api.z.ai/api/paas/v4`. Para uma credencial do Coding Plan, selecione explicitamente `NOITE_GLM_API_MODE=coding_plan`, que usa `https://api.z.ai/api/coding/paas/v4`; os planos e credenciais não são intercambiáveis. A categoria deve ser reconhecida por uma regra determinística e aparecer em `NOITE_GLM_TASK_CATEGORIES`. Conversas sem categoria autorizada, conteúdo classificado como sensível e chamadas sem chave permanecem locais. Se a API falhar, o Noite tenta o Ollama local.

Chamadas GLM recebem somente a mensagem atual, sem histórico ou contexto de arquivos. Uso de tokens, latência, tentativas, provedor, categoria e custo quando calculável são registrados no log local sem prompts/respostas. Para desligar, use `NOITE_GLM_ENABLED=false` e remova `ZAI_API_KEY`. Veja [docs/MULTI_MODEL_ARCHITECTURE.md](docs/MULTI_MODEL_ARCHITECTURE.md) para limites atuais e testes.

O pipeline de voz, `sqlite-vec`, integração Roblox/Blender e demais componentes avançados pertencem às fases posteriores do relatório; não são necessários para iniciar o núcleo textual.

## Workspace e terminal integrado

Use **Abrir projeto…** para selecionar a pasta de trabalho. O dock **Projeto** mantém árvore e abas ao lado da conversa. Arquivos UTF-8 até 1 MB podem ser abertos, editados e salvos manualmente; `.env`, credenciais, binários, caminhos fora do workspace e mudanças externas posteriores à abertura são bloqueados. O editor oferece realce Python, busca/substituição no buffer, criação confirmada e checagem AST sem execução. A busca no projeto ocorre em background. O terminal PowerShell usa o workspace como diretório, limita leitura segura a caminhos internos e exige confirmação no modo avançado. Veja [docs/TERMINAL.md](docs/TERMINAL.md).

Anexe arquivos pelo botão ou arraste-os para a caixa de mensagem. A extração ocorre em background; quatro arquivos por mensagem, até 5 MB por arquivo, no máximo 40 mil caracteres extraídos por arquivo e 12 mil caracteres enviados no total. Em documentos longos, trechos são selecionados por palavras da pergunta. PDF digitalizado sem texto requer OCR, que ainda não está incluído. Consulte [docs/ATTACHMENTS.md](docs/ATTACHMENTS.md).

Configurações guardam tema, modelo/endereço Ollama, visibilidade do painel lateral e opções do terminal. A sidebar inicia à esquerda; pode ser reposicionada na sessão atual. A tela de modelos mostra a lista local e consulta o catálogo Hugging Face somente após uma busca explícita; consulte [docs/SETTINGS.md](docs/SETTINGS.md) e [docs/MODELS.md](docs/MODELS.md).

## Interface desktop e Ollama

Ollama deve estar instalado e em execução em `http://127.0.0.1:11434`. O modelo validado nesta máquina foi `qwen2.5:3b`:

```powershell
ollama pull qwen2.5:3b
ollama serve
```

Em outro terminal, inicie a interface real (usa `ServiceClient` e o núcleo da Noite):

```powershell
python run_ui.py
```

`python run_ui.py --mock` inicia dados fixos apenas para screenshots e testes. O mock não é o modo padrão. Após instalar o pacote com o extra desktop, use `noite` para abrir a interface fora do checkout. Para a CLI, use `python -m noite --cli`.

## Ambiente Windows

Requer Python 3.11 ou superior. O ambiente validado para o app e o lançador nesta máquina usa Python 3.13.16.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[desktop,windows,dev]"
Copy-Item .env.example .env
```

O Python 3.13.16, Windows 11, interface e modelo `qwen2.5:3b` foram usados na validação local. O projeto declara suporte a Python 3.11 ou superior. Não coloque chaves de API no Git; `.env` é ignorado.

Para instalar as dependências exatas do lockfile, use `uv sync --locked --extra desktop --extra mcp --extra dev`. A CI valida Python 3.11 e 3.13 em Windows e Ubuntu.

Para iniciar o servidor local do Ollama, use um terminal dedicado:

```powershell
$env:OLLAMA_VULKAN = '0'
ollama serve
```

Deixe esse terminal aberto enquanto usa o projeto. Em outro terminal:

```powershell
python -m noite
```

Para usar a interface de linha de comando, execute `python -m noite --cli`. Para ativar o painel MCP, instale `python -m pip install -e ".[mcp]"` e consulte [docs/MCP_STATUS.md](docs/MCP_STATUS.md). O modelo não escolhe nem chama ferramentas MCP; o usuário configura servidores locais e aprova cada execução na interface.

## Testes e limites conhecidos

Execute `pytest -q`, `ruff check .`, `python -m compileall -q src ui run_ui.py tests` e `git diff --check`. Na validação desta entrega no Windows: 222 testes passaram e 1 foi ignorado por depender de symlink externo não suportado nesse ambiente.

O bloco de pensamento não aparece com `qwen2.5:3b`, que não anuncia esse campo. O PDF digitalizado ainda requer OCR; não há instalador standalone, e o EXE atual é apenas um lançador dependente deste checkout, do `.venv`, de Python/dependências e do Ollama local. Veja [docs/EVOLUTION_PROGRESS.md](docs/EVOLUTION_PROGRESS.md) para recursos ainda pendentes e o estado de continuidade.

O executável lançador recebe a lua roxa e pode ser construído sem sobrescrever um artefato anterior, por exemplo `scripts/build_windows.ps1 -Name Noite-2.0-Evolution-20261101`. Ele inicia este checkout pelo `.venv`; não é um instalador portátil e requer Python, dependências e Ollama instalados. Consulte [docs/BUILD_WINDOWS.md](docs/BUILD_WINDOWS.md).

## Papéis do projeto

- ChatGPT: arquitetura e coordenação.
- Claude: engenharia e revisão de código.
- Codex: programação e implementação.
- Gemini: pesquisa e análise.
- Criador do projeto: proprietário e diretor.

## Segurança

Consulte [SECURITY.md](SECURITY.md) antes de adicionar ferramentas que leem arquivos ou controlam o Windows. Conteúdo recuperado de arquivos deve ser tratado como dado não confiável, nunca como instrução de sistema.
