# Noite 2.0-2: recuperação pós-restauração do Windows
Atualizado em 2026-11-04. Documento de reconstrução do ambiente, sem tokens nem senhas.

## Projeto e Git
- Repositório: https://github.com/Ninja7z/Noite-2.0
- Branch principal de snapshot: baseline/noite-2.0-core-2026-11-03
- Worktree principal: C:\Users\crist\Noite-2.0-worktrees\stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001
- Worktree paralelo de hardening: C:\Users\crist\Noite-2.0-worktrees\audit-integration-20261104
- Branch paralelo: claude/security-hardening-20261104
- Projeto Python. Ambiente Windows 11, Python 3.12.10. Open WebUI instalado diretamente via Python, sem Docker.
- Dependências versionadas: pyproject.toml, uv.lock; exemplo de configuração: .env.example.
- Não copiar .venv, caches, build, dist, __pycache__ nem bancos locais como código-fonte.

## Hardware de referência
- Intel Core i7-3770, sem AVX2.
- NVIDIA GTX 1660 Super, 6 GB VRAM.
- 16 GB RAM DDR3.
- SSD SATA Mancer Reaper 480 GB.

## Ollama
- Serviço local: http://127.0.0.1:11434
- Versão observada em diagnóstico anterior: 0.40.14 (em 02/11 foi observada 0.40.13).
- Variáveis de usuário configuradas:
  - OLLAMA_NUM_PARALLEL=1
  - OLLAMA_MAX_LOADED_MODELS=1
  - OLLAMA_CONTEXT_LENGTH=4096
  - OLLAMA_FLASH_ATTENTION=1
  - OLLAMA_KV_CACHE_TYPE=q8_0
- Política desejada: um modelo carregado por vez; manter inferência local na GPU quando o modelo couber na VRAM. Qwen3.5:4b foi observado usando GTX 1660 Super sem dividir inferência com CPU.
- Inventário confirmado por ollama list em 04/11/2026:
  - nomic-embed-text:latest (274 MB)
  - llama3.2:1b (1.3 GB)
  - qwen2.5-coder:3b (1.9 GB)
  - deepseek-r1:1.5b (1.1 GB)
  - qwen3.5:4b (3.3 GB)
  - qwen2.5-coder:1.5b (986 MB)
  - qwen2.5:1.5b (986 MB)
  - qwen2.5:0.5b (397 MB)
  - gemma3:4b (3.4 GB)
  - gemma4:e4b (6.6 GB)
  - gemma4:e2b (4.6 GB)
  - qwen2.5vl:3b (3.2 GB)
  - qwen2.5:3b (1.9 GB)
- Variantes -ptbr criadas/discutidas anteriormente: gemma3:4b-ptbr, gemma4:e4b-ptbr, gemma4:e2b-ptbr, qwen3.5:4b-ptbr, deepseek-r1:1.5b-ptbr, qwen2.5vl:3b-ptbr, qwen2.5:3b-ptbr. Confirmar após reinstalação quais ainda são necessárias; elas não apareceram no inventário final de ollama list.
- Modelos são grandes blobs locais do Ollama e NÃO foram adicionados ao Git. Rebaixá-los após reinstalar Ollama. Comandos de exemplo:
  ollama pull qwen3.5:4b
  ollama pull deepseek-r1:1.5b
  ollama pull qwen2.5-coder:3b
  ollama pull llama3.2:1b
  ollama pull nomic-embed-text
  Outros nomes estão no inventário acima.

## Serviços e portas (último arranjo conhecido)
- Noite API: 127.0.0.1:8765
- Open WebUI: 127.0.0.1:8080
- Ollama: 127.0.0.1:11434
- Roblox MCP proxy: 127.0.0.1:8766
- Noite MCP: 127.0.0.1:8767/mcp
- Em snapshot mais recente o proxy Roblox foi visto na porta 8768; verificar scripts/start_mcp_servers.ps1 e docs/MCP_STATUS.md antes de iniciar para evitar colisão. O log recovery/diagnostics/mcp-error-2026-11-04.log registra conflito de bind na 8766.
- Scripts de inicialização: procurar Start-Noite-OpenWebUI.ps1 e start_mcp_servers.ps1 em scripts/ e no histórico; run_noite.ps1 está na raiz.
- Open WebUI connections conhecidas: noite_2_0 -> http://127.0.0.1:8767/mcp; roblox_studio -> http://127.0.0.1:8766/servers/roblox_studio.
- MCP tools conhecidos: noite_status, noite_search_workspace(query, limit=20), noite_ask(prompt).
- Branch de hardening altera MCP para exigir NOITE_MCP_TOKEN (mín. 24 caracteres), Authorization: Bearer <token>, loopback e bloqueio de Origin externo. Após restaurar, gerar token novo:
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  Configurar o mesmo token no ambiente do servidor e na conexão MCP do Open WebUI. Nunca salvar o valor do token no Git.

## Arquitetura acordada
- Open WebUI como front-end conversacional; Noite como backend/orquestrador; agentes e subagentes; mascote EMO transparente/overlay, sem janela de fundo. Preservar interface/landing antiga como referência/backup.
- Projeto com Python, Ollama, memória, agentes especializados, integrações e frontend web.
- UI web dinâmica: preservar identidade visual e método atual, tornar responsiva, reativa, com feedback em tempo real; backend FastAPI e eventos via WebSocket.
- Noite API e WebUI já responderam HTTP 200 em validação anterior.
- Testes no worktree principal: 341 passed, 3 skipped, 1 warning em 44.40 s (log arquivado).
- Recursos MCP / anexos / terminal e hardening estão no código e testes; verificar branches publicadas.

## Aplicativos e ferramentas escolhidos para reinstalar
- Selecionados: Edge, Discord, WhatsApp Desktop, ChatGPT Desktop, Codex, Cursor e VS Code.
- Bruno foi aceito para teste de APIs.
- Fast Node Manager (fnm) foi recomendado para gerenciar Node.js.
- Telegram foi desmarcado; CMake ficou desmarcado.
- Instaladores que estavam em Downloads (não incluídos no Git):
  AnyDesk.exe
  ChatGPT Installer.exe
  Cline_0.0.49_x64-setup.exe
  CursorUserSetup-x64-3.27.22.exe
  GeminiSetup.exe
  RobloxPlayerInstaller-X6WFF294JD.exe
  Microsoft.Services.Store.winmd (componente auxiliar, não instalador independente)
- Cursor e Cline tinham respectivamente ~229 MB e ~133 MB, acima do limite normal de arquivo individual do GitHub. Não versionar binários de instaladores. Baixar novamente de seus sites oficiais após restaurar. AnyDesk/ChatGPT/Gemini/Roblox também não foram incluídos como binários.

## Arquivos de referência preservados neste repositório
- recovery/reference-downloads/: guia de integração/arquitetura e relatório de melhorias arquiteturais.
- assets/reference-imports/mascot/: imagens de referência da mascote.
- assets/reference-imports/interface/: imagens, PDFs e listas de links de referências de interface.
- recovery/diagnostics/: logs de testes e log de conflito de porta MCP.
- PDFs em publication-excluded-docs-... devem ser comparados com os arquivos copiados para referência; originais permaneceram fora da publicação anterior.

## Itens deliberadamente NÃO publicados no Git
- .env e quaisquer chaves/tokens/senhas; criar novamente e guardar no Windows Credential Manager/ambiente local.
- webui.db e demais bancos locais de usuário: podem conter sessões, conversas, credenciais e dados privados.
- .venv, caches, build, dist, logs temporários sem valor diagnóstico, executáveis e modelos Ollama.
- Dumps de memória, arquivos de paginação e arquivos pessoais.
- Não apagar o backup local até validar a restauração e os serviços.

## Passos de reconstrução resumidos
1. Instalar Python 3.12 e Git.
2. Clonar https://github.com/Ninja7z/Noite-2.0 e selecionar baseline/noite-2.0-core-2026-11-03; também buscar claude/security-hardening-20261104.
3. Criar ambiente virtual e instalar dependências conforme README/pyproject.toml/uv.lock.
4. Instalar Ollama, restaurar as variáveis listadas e executar os ollama pull necessários.
5. Instalar Open WebUI via Python e reconstruir as conexões MCP; configurar token novo, nunca reutilizar segredo antigo.
6. Configurar .env a partir de .env.example, iniciar API/WebUI/MCP pelos scripts versionados e validar as portas.
7. Executar pytest e validar nvidia-smi + ollama ps.
