# ADR-005 — Provedor de modelo atrás de adaptador; LiteLLM não é obrigatório

- **Status:** aceito
- **Data:** 2026-11-04
- **Decisores:** proprietário (direção), arquitetura, engenharia

## Contexto

- Hoje `litellm` é importado **em um único módulo** (`model_gateway.py`), para
  Ollama local (`acompletion`) e para o GLM opcional, além de
  `completion_cost` para métricas.
- LiteLLM traz dependências pesadas (ex.: `boto3`/`botocore`, `tokenizers`,
  `huggingface-hub`) para um produto que, no caminho padrão, só conversa com o
  Ollama em `127.0.0.1:11434` por HTTP.
- O núcleo conversacional (`assistant.py`, `router.py`) já não importa `litellm`
  diretamente: os imports do gateway são tardios.
- O relatório de pesquisa propunha LiteLLM como peça central; o código atual o
  trata como detalhe de implementação. A divergência precisa ficar registrada.

## Decisão

- O núcleo conhece apenas um **contrato interno de provedor**:
  `complete_local(...)` e `complete_external(...)`, com streaming por callback
  (`on_chunk`, `on_thinking`) e timeout explícito.
- `model_gateway.py` é o adaptador; `litellm` é uma **implementação possível**, não
  um requisito do produto.
- Trocar de adaptador não pode exigir mudança em `assistant.py`, `router.py`,
  `task_router.py` ou na interface.
- Um teste com adaptador falso deve provar que a conversa funciona **sem** litellm
  instalado.

## Alternativas consideradas

- **LiteLLM em qualquer módulo que chame modelo:** acopla o núcleo a uma biblioteca
  grande e a mudanças de ABI. Rejeitado.
- **Remover LiteLLM imediatamente:** viável para Ollama (HTTP direto), mas perderia
  métricas de custo do GLM antes de existir alternativa. Preterido (fazer por
  etapas, com teste de equivalência).
- **Cliente HTTP próprio para tudo, inclusive GLM:** mais código de manutenção do
  que o necessário neste momento.

## Consequências

- Redução de dependências passa a ser possível sem reescrever o produto.
- O adaptador continua responsável por: streaming, detecção de *thinking*
  (`/api/show`), tradução de erros para mensagens amigáveis e métricas sem conteúdo.
- Métricas de custo deixam de ser obrigatórias quando o provedor não informar uso;
  ausência de dado deve ser registrada como indisponível, nunca estimada em silêncio.

## Critério de revisão

Reabrir quando o adaptador próprio cobrir também o GLM (custo e uso) — nesse
momento, avaliar a remoção definitiva de `litellm`; ou se o LiteLLM quebrar
compatibilidade em atualização.
