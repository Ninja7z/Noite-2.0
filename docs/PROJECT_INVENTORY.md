# Inventário do projeto

## Checkout e Git

- Checkout: `C:\Users\crist\Noite-2.0\Noite-2.0-canonical`.
- Branch: `codex/stabilize-core`, HEAD `dc5e2b9` (`Record streaming validation results`).
- Repositório oficial confirmado: [`Ninja7z/Noite-2.0`](https://github.com/Ninja7z/Noite-2.0).
- PR #1 (`codex/stabilize-core` → `main`) está aberto como draft, sem merge. O head publicado é `dc5e2b9` (`Record streaming validation results`).
- O `origin` deste checkout ainda aponta para o endereço antigo `cristnzx/Noite-2.0`; use o repositório oficial ao sincronizar. O repositório oficial foi confirmado pelo usuário e está acessível via integração GitHub.

## Arquitetura atual

- Python 3.11+; validação local neste Windows com Python 3.13.16.
- Núcleo local-first: roteador determinístico, contratos Pydantic, `AssistantService` assíncrono e gateway LiteLLM para Ollama (`qwen2.5:3b` por padrão).
- Interface PySide6 com chat, seleção do modelo por sessão, estado do Ollama, streaming, cancelamento e encerramento coordenado de QThread.
- Histórico em SQLite com FTS5 e sincronização por triggers; armazenamento padrão em `%USERPROFILE%\.noite`.
- Painel MCP stdio com configuração local, descoberta após confirmação e aprovação humana de cada chamada. O modelo não seleciona nem invoca ferramentas.
- Ferramentas locais limitadas à consulta de nomes de arquivos na pasta de trabalho configurada; não existe execução arbitrária de comandos.
- Voz, Vosk, CustomTkinter, ChromaDB, automação do Windows e integração Roblox não fazem parte do código atual. O material do Gemini descreve uma arquitetura alternativa/legada, não as dependências deste checkout.

## Validação registrada

- `pytest -q`: 35 testes passaram.
- `ruff check .`: passou.
- CLI `python -m noite --cli`: inicia; chamada real a Ollama retornou `TESTE_OK` nesta continuação.
- UI real no Windows: a versão reformulada exibiu `Ollama conectado` e respondeu `UI_OK` via Ollama; os testes de ciclo de vida e MCP continuam passando.
- GitHub Actions: a validação previamente registrada para `dc5e2b9` passou em Ubuntu e Windows (Ruff, testes e smoke test do CLI). As alterações locais de UI/empacotamento ainda precisam de nova validação remota após publicação.
- `.env` não está rastreado; `.env.example` é o único arquivo dessa família versionado.

## Empacotamento Windows

- `Noite.exe` em `C:\Users\crist\OneDrive\Desktop\Noite.exe` é um lançador local que inicia o checkout e `.venv`; não é portátil nem inclui Python, dependências, Ollama ou pesos do modelo.
- O histórico e as configurações ficam fora do executável e sobrevivem à sua substituição.
- Um congelamento completo do Qt falhou no ambiente atual. O diagnóstico e a reprodução estão em `docs/BUILD_WINDOWS.md`.

## Materiais de referência

- `docs/reference/papeis-do-projeto.pdf`, `docs/reference/snapshot-legado.pdf` e `docs/reference/pesquisa-arquitetura-original.pdf` são documentos de referência; não são importados nem executados pelo aplicativo.
- Os três arquivos foram movidos para `docs/reference/` e receberam nomes legíveis, preservando o conteúdo. O snapshot legado é um PDF que antes não tinha extensão; o arquivo de pesquisa também tinha nome malformado.
- `docs/PROJECT_INVENTORY.md` e `docs/CONTINUATION_STATE.md` devem ser atualizados junto de mudanças funcionais.
