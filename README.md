# Noite 2.0

Assistente desktop em português, desenvolvido em etapas para o hardware previsto no relatório do projeto.

## Escopo inicial

- Núcleo assíncrono em Python, com contratos validados por Pydantic.
- Roteador determinístico para comandos simples e encaminhamento de conversas ao modelo local.
- LiteLLM como gateway; Ollama com `qwen2.5:3b` como modelo local inicial.
- SQLite com FTS5 para histórico textual. A extensão vetorial fica para uma etapa posterior.
- Interface PySide6 e automação do Windows são dependências opcionais do MVP.
- Chamadas em nuvem ficam desativadas por padrão e exigem configuração explícita de credenciais.

O pipeline de voz, `sqlite-vec`, integração Roblox/Blender e demais componentes avançados pertencem às fases posteriores do relatório; não são necessários para iniciar o núcleo textual.

## Ambiente Windows

Requer Python 3.11 ou superior. No computador atual, Python 3.14.7 está instalado.

```powershell
py -3.14 -m venv .venv
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

## Papéis do projeto

- ChatGPT: arquitetura e coordenação.
- Claude: engenharia e revisão de código.
- Codex: programação e implementação.
- Gemini: pesquisa e análise.
- Criador do projeto: proprietário e diretor.

## Segurança

Consulte [SECURITY.md](SECURITY.md) antes de adicionar ferramentas que leem arquivos ou controlam o Windows. Conteúdo recuperado de arquivos deve ser tratado como dado não confiável, nunca como instrução de sistema.
