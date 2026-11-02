# Arquitetura multimodelos: estado inicial

## Componentes atuais

- `AssistantService` mantém histórico SQLite e usa o gateway LiteLLM.
- Ollama é o provedor local padrão e continua atendendo conversas comuns e qualquer tarefa sem autorização explícita de nuvem.
- `task_router.py` classifica algumas tarefas auxiliares com regras determinísticas. Pedidos com múltiplas categorias ficam locais. Não faz uma chamada de LLM para decidir o provedor.
- GLM-5.3-Flash é opcional. O roteador e o próprio gateway revalidam a allowlist, `NOITE_GLM_ENABLED=true`, `NOITE_OFF_GRID=false`, presença de `ZAI_API_KEY`, a categoria e o bloqueio heurístico de sensibilidade antes de qualquer chamada.
- Falhas do GLM retornam ao Ollama local. A chamada externa nunca recebe histórico nem contexto do workspace.

## Configuração da Z.ai

Crie uma chave padrão da API na conta Z.ai e forneça `ZAI_API_KEY` como variável de ambiente ou no `.env` local ignorado pelo Git. Não coloque a chave em código, logs ou documentação.

`NOITE_GLM_API_MODE=general` seleciona a API geral em `https://api.z.ai/api/paas/v4`. `NOITE_GLM_API_MODE=coding_plan` seleciona o endpoint de Coding Plan em `https://api.z.ai/api/coding/paas/v4`. Use a credencial correspondente à modalidade. A API geral é o modo padrão.

Exemplo de ativação deliberada:

```dotenv
NOITE_OFF_GRID=false
NOITE_GLM_ENABLED=true
NOITE_GLM_MODEL=zai/glm-5.3-flash
NOITE_GLM_API_MODE=general
NOITE_GLM_TASK_CATEGORIES=summarization,classification
NOITE_GLM_TIMEOUT_SECONDS=60
NOITE_GLM_MAX_RETRIES=1
ZAI_API_KEY=...
```

Para remover o GLM do roteamento, defina `NOITE_GLM_ENABLED=false` ou deixe `NOITE_GLM_TASK_CATEGORIES` vazia. Conversa geral não é delegada ao GLM automaticamente.

## Privacidade e telemetria

O gateway constrói a requisição externa com uma instrução fixa e apenas o turno corrente; ele não aceita uma lista arbitrária de mensagens. Histórico, arquivos e resultados de ferramentas não são anexados. A redação cobre chaves nomeadas, Authorization/Bearer/Basic, blocos PEM, tokens conhecidos, JWTs e credenciais de URL. O roteador também mantém local conteúdo com credenciais detectadas, e-mail, CPF/CNPJ, telefone ou termos de saúde/finanças/endereço. São heurísticas: dados pessoais escritos de formas não reconhecidas ou conteúdo sensível sem indicadores ainda podem escapar; para dados que exigem garantia forte, use apenas Ollama.

O gateway registra `trace_id`, provedor, modelo, categoria, status, latência, tentativas, tokens de entrada/saída/cache e custo USD quando o catálogo do LiteLLM calcula esse valor. Prompt e resposta não são registrados. O cálculo pode ficar indisponível para respostas sem dados de uso ou preço no catálogo.

Retentativas são limitadas a `NOITE_GLM_MAX_RETRIES` (0 a 2, padrão 1), somente para timeout, conexão, rate limit e erros HTTP 5xx. O timeout total limita as tentativas combinadas. Credenciais inválidas e outros erros do provedor não entram em retry. O fallback é sempre local.

## Limites da entrega atual

O roteador classifica apenas os tipos explícitos no módulo e usa categorias habilitadas pelo usuário; não estima custo/latência para selecionar dinamicamente entre vários provedores. OpenAI não está integrado, disponibilidade de rede não é sondada antes da chamada e ainda não há painel de consumo. Nenhuma chamada real foi feita nesta implementação. Tool calling do GLM não está conectado à aplicação.

LiteLLM 1.106.6, já fixado no `uv.lock`, reconhece `zai/glm-5.3-flash` em seu catálogo local; não foi necessária atualização de dependência.
