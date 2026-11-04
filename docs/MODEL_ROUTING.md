# Roteamento de modelos — Noite 2.0

**Status:** normativo (ver [ADR-001](ADR/001-local-first.md) e
[ADR-005](ADR/005-model-provider.md)).

## O que existe hoje (fato do código)

- `router.py`: intenção por regex determinística. **Nenhum LLM participa da decisão.**
- `task_router.route_model`: decide local vs GLM por categoria de tarefa, filtros
  de dado sensível, `off_grid`, presença de chave e categorias autorizadas.
- **Não existe "roteador em três camadas"** nem "um segundo LLM para cada
  decisão". Isso aparece no relatório de pesquisa e não corresponde ao código:
  a decisão atual é de uma camada, determinística e testável.
- `model_gateway.py` é o **único** módulo que importa `litellm`; expõe
  `ask_local_model` (Ollama, com caminho nativo `/api/chat` quando o modelo
  anuncia suporte a *thinking*) e `ask_glm_model` (que **revalida** a autorização
  antes de enviar qualquer coisa).

## Política de decisão

| Situação | Provedor | Origem da regra |
|---|---|---|
| Conversa comum | **local** | padrão do produto |
| `off_grid=true` | local | configuração |
| Conteúdo sensível (e-mail, CPF/CNPJ, telefone, segredo, dado pessoal/financeiro) | **local, sempre** | `_SENSITIVE_DATA` e correlatos |
| Tarefa categorizada **e** categoria autorizada **e** chave presente | GLM (opt-in) | `route_model` |
| Sem chave, categoria não autorizada, pedido ambíguo | local | `route_model` |
| Falha/timeout do GLM | local (fallback) | `assistant.respond` |

## O que nunca sai do computador

Enviado ao provedor externo: **somente a mensagem atual** (após redação) e um
`system` curto de escopo auxiliar.

Nunca enviado: histórico da conversa, contexto de projeto, anexos, memória,
resultados de ferramentas, permissões, identidade/configuração local.

## Limites técnicos conhecidos

| Item | Valor | Observação |
|---|---|---|
| Timeout do modelo local | `model_timeout_seconds` (padrão 180 s) | erro amigável ao usuário |
| Timeout do GLM | `glm_timeout_seconds` | com fallback para local |
| `MAX_THINKING_RESPONSE_TOKENS` | 2048 | teto de resposta no modo *thinking* |
| Detecção de *thinking* | `POST /api/show` a cada mensagem | custo de 1 round-trip; candidato a cache (pendência registrada) |

## Seleção automática do modelo local

A conversa local usa seleção automática entre os modelos que já estão instalados no Ollama. `model_selector.py` consulta `/api/tags`, mantém o inventário em cache por 30 segundos e escolhe por categoria, sem chamar outro LLM para decidir e sem baixar modelos.

| Tipo de pergunta | Preferência atual |
|---|---|
| Conversa geral e explicações | `qwen3.5:4b-ptbr` |
| Código e programação | `qwen3.5:4b-ptbr` |
| Raciocínio detalhado | `deepseek-r1:1.5b-ptbr` |
| Resumos | `qwen3.5:4b-ptbr` |
| Saudações simples | `qwen2.5:3b-ptbr` |

A preferência é aplicada somente quando o modelo exato existe no inventário instalado. Caso contrário, o seletor tenta o fallback `NOITE_LOCAL_MODEL`; se ele também não estiver instalado, usa o primeiro modelo listado pelo Ollama. Se o Ollama não responder, mantém o fallback configurado. A escolha é local, não envia dados à nuvem e não altera as regras de privacidade do GLM.

## Escolha do modelo local (não fixar por decreto)

`qwen2.5:3b` é o modelo **validado na máquina de referência**, não uma decisão
permanente. Trocar de modelo é permitido; trocar a **identidade** da Noite, não.

Protocolo mínimo antes de adotar um modelo como padrão:

1. tarefas reais em pt-BR: conversa, resumo, extração estruturada, explicação de código;
2. hardware alvo: i7-3770 (sem AVX2), GTX 1660 Super 6 GB, 16 GB RAM;
3. medir: tokens/s, latência da primeira resposta, RAM/VRAM de pico, aderência à
   instrução de idioma/identidade, taxa de resposta vazia;
4. registrar o resultado em `docs/MODELS.md` com data, versão e comando usado.

Alegação de terceiro (ex.: "40 tokens/s") **não** vira critério de aprovação sem
essa medição.

## Adaptador de provedor (ADR-005)

O núcleo conversacional não deve conhecer `litellm`. Contrato interno desejado:

```
complete_local(messages, *, stream, on_chunk, on_thinking, timeout) -> str
complete_external(messages, *, stream, on_chunk, timeout) -> str
```

- `litellm` é detalhe de implementação de `model_gateway`;
- Ollama pode ser atendido por HTTP direto (`/api/chat`) sem `litellm`;
- substituir o adaptador **não** pode exigir mudança em `assistant.py`, `router.py`
  ou na interface.

Requisito de teste: um teste com adaptador falso comprova que o núcleo funciona
sem `litellm` instalado (import tardio já existe em `assistant.ask_local_model`).
