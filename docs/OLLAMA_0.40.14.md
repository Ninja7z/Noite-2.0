# Ollama 0.40.14 — verificação na máquina Noite 2.0

**Verificado em:** 03/11/2026  
**Versão reportada pelo CLI local:** `ollama version is 0.40.14`

## Mudanças upstream relevantes

Segundo as notas oficiais da versão v0.40.14:

- `ollama launch claude` aplica o limite de tokens de saída do modelo ao Claude Code, evitando o limite padrão de 128k para modelos cloud.
- `ollama launch codex` verifica o roteamento ChatGPT antes de configurar e apresenta erro claro quando o roteamento não está disponível.
- Endpoints compatíveis com OpenAI deixam de sobrescrever os samplers empacotados do modelo quando o cliente não envia `temperature` ou `top_p`.
- Respostas de busca web cloud em `/api/chat` são decodificadas corretamente, inclusive respostas comprimidas.
- `/v1/responses` preserva conteúdo de entrada legível, incluindo recusas anteriores do assistente.
- O aplicativo pode tentar novamente falhas de desconexão do ChatGPT.

Fonte: https://github.com/ollama/ollama/releases/tag/v0.40.14

## Estado observado na máquina

O comando `ollama list` retornou:

| Modelo | Tamanho em disco |
|---|---:|
| gemma3:4b | 3.4 GB |
| gemma4:e4b | 6.6 GB |
| gemma4:e2b | 4.6 GB |
| qwen3.5:4b | 3.3 GB |
| deepseek-r1:1.5b | 1.1 GB |
| qwen2.5vl:3b | 3.2 GB |
| qwen2.5:3b | 1.9 GB |

O comando `ollama ps` mostrou naquele momento:

- Modelo carregado: `qwen2.5:3b`
- Memória reportada pelo processo: 2.2 GB
- Processador: 100% GPU
- Contexto: 4096 tokens
- Runner: llama.cpp

Esses valores são uma fotografia do momento da inspeção, não um benchmark.

## Impacto esperado na Noite

A atualização é positiva para integrações de agentes Codex/Claude e compatibilidade de API. As notas desta versão não anunciam um aumento específico de tokens/s para GTX 1660 Super nem uma mudança que resolva limitações de AVX2 do i7-3770.

Para a Noite local, manter o endpoint padrão em `http://127.0.0.1:11434` e o modo local como padrão. A opção de exposição à rede do Ollama deve continuar desligada enquanto não houver uma necessidade explícita de acesso remoto.

Não ativar fallback externo automaticamente. A versão do Ollama não altera as permissões do núcleo Noite: chamadas de ferramentas continuam passando pelo Policy Engine.

## Sobre ollama launch codex / claude

Esses comandos configuram integrações do Ollama com agentes de programação. Não transformam o modelo local Nemotron em um modelo mais inteligente e não adicionam AVX2 à CPU.

A rota Codex descrita nas notas verifica o encaminhamento ChatGPT. Portanto, deve ser tratada como integração de agente/serviço, não como aceleração local garantida da GTX 1660 Super.

Antes de habilitar qualquer agente de código, restringir seu workspace, revisar permissões de terminal e arquivos e manter o gerenciador de permissões da Noite independente do modelo.

A versão também foi confirmada diretamente no endpoint local `GET /api/version`, que retornou `{"version":"0.40.14"}`.
