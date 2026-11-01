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

O pipeline de voz, `sqlite-vec`, integração Roblox/Blender e demais componentes avançados pertencem às fases posteriores do relatório; não são necessários para iniciar o núcleo textual.

## IDE (em desenvolvimento)

Na janela, use **Abrir projeto…** para selecionar a pasta de trabalho. O dock **Projeto** mantém a árvore e abas ao lado da conversa. Nesta primeira etapa, arquivos UTF-8 até 1 MB podem ser abertos, editados e salvos manualmente; `.env`, credenciais, binários, arquivos fora do workspace e mudanças externas posteriores à abertura são bloqueados. O destaque de sintaxe inicial cobre Python. **Buscar no projeto** executa busca textual limitada em segundo plano e permite abrir o resultado na linha encontrada. O terminal, diagnósticos e operações de criação/exclusão ainda não estão implementados; acompanhe [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md).

## Ambiente Windows

Requer Python 3.11 ou superior. O ambiente validado para o app e o lançador nesta máquina usa Python 3.13.16.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[desktop,windows,dev]"
Copy-Item .env.example .env
```

O Ollama deve estar rodando localmente com o modelo configurado em `.env`. Não coloque chaves de API no Git; use o arquivo `.env`, que é ignorado.

Para iniciar o servidor CUDA no Windows quando a descoberta automática travar, use um terminal dedicado:

```powershell
$env:OLLAMA_VULKAN = '0'
$env:OLLAMA_HOST = 'http://127.0.0.1:11435'
ollama serve
```

Deixe esse terminal aberto enquanto usa o projeto. Em outro terminal:

```powershell
python -m noite
```

Para usar a interface de terminal, execute `python -m noite --cli`. Para ativar o painel MCP, instale `python -m pip install -e ".[mcp]"` e consulte [docs/MCP_STATUS.md](docs/MCP_STATUS.md). O modelo não escolhe nem chama ferramentas MCP; o usuário configura servidores locais e aprova cada execução na interface.

O executável local `Noite.exe` pode ser reconstruído com `scripts/build_windows.ps1 -CopyToDesktop`. Ele inicia este checkout pelo ambiente `.venv`; não é um instalador portátil e requer que Python e as dependências já estejam instalados. Consulte [docs/BUILD_WINDOWS.md](docs/BUILD_WINDOWS.md) para os limites do empacotamento Qt.

## Papéis do projeto

- ChatGPT: arquitetura e coordenação.
- Claude: engenharia e revisão de código.
- Codex: programação e implementação.
- Gemini: pesquisa e análise.
- Criador do projeto: proprietário e diretor.

## Segurança

Consulte [SECURITY.md](SECURITY.md) antes de adicionar ferramentas que leem arquivos ou controlam o Windows. Conteúdo recuperado de arquivos deve ser tratado como dado não confiável, nunca como instrução de sistema.
