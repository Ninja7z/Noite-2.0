# Inventário do projeto

## Checkout e baseline

- Repositório canônico: `Ninja7z/Noite-2.0`, branch de trabalho `codex/stabilize-core`.
- Base observada: commit `9af7993`; checkpoint local anterior: `3a4cc93`.
- Código existente antes desta etapa: CLI, configuração Pydantic, contratos de intenção, roteador simples, normalização, gateway LiteLLM/Ollama, tabela SQLite e FTS5 com triggers.
- Dependências atuais: LiteLLM, Pydantic, pydantic-settings, python-dotenv; extras desktop (PySide6 Essentials), windows (pywinauto) e dev (pytest, Ruff).
- Testes anteriores desta branch: 16 passaram e Ruff passou; a chamada real a Ollama anteriormente excedeu o timeout de 30 s.

## Materiais examinados

- `README.md`, `SECURITY.md`, `pyproject.toml`, `docs/roadmap.md`, fontes e testes.
- `Noite 2.0.pdf`: papéis e objetivo do projeto.
- PDF de arquitetura/pesquisa: MVP local com núcleo Python assíncrono, LiteLLM, Qwen 2.5 3B/Ollama, SQLite/FTS5; PySide6 como UI; voz, busca vetorial e integrações de criação de conteúdo em fases posteriores.
- `ia`: arquivo sem extensão cujo cabeçalho real é PDF 1.4; dump de código de 35 páginas visto na análise anterior, não executado.
- Buscas por `alterações.txt`, `alteracoes.txt` e `Fonte2(1).txt` no diretório do usuário não encontraram esses materiais.
- Materiais do telefone CrossDevice não foram lidos nesta etapa.

## Estado funcional após esta etapa

- GUI PySide6: chat, envio por botão/Enter, histórico visível, seleção do modelo por sessão, estado do Ollama e trabalho de rede fora da thread da UI.
- Respostas rápidas locais: saudação, despedida, ajuda, hora, data, estado e descrição da Noite.
- Conversa livre encaminhada ao gateway local; histórico SQLite limitado a 12 mensagens no contexto.
- Pesquisa de nomes somente sob workspace configurado; nenhum conteúdo de arquivo é lido.
- Cliente MCP stdio inicial com descoberta, validação, allowlist e teste contra servidor local; ainda não ligado à UI/chat.
- Abertura de aplicativos, voz, agentes, streaming e cancelamento não estão implementados.

## Decisões e limites

- UI inicia por padrão com `python -m noite`; CLI permanece disponível com `python -m noite --cli`.
- Nenhuma shell arbitrária é disponibilizada ao modelo.
- Não se migra nem se apaga automaticamente banco do usuário; a nova coluna de conversa é adicionada de modo compatível.
- O conteúdo de PDFs/dump legado é referência, não código executável.
