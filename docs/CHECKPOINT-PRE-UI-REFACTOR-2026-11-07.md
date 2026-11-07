# Checkpoint pré-refatoração da interface

Data: 2026-11-07

## Objetivo

Preservar o estado funcional do núcleo web e da ponte Electron antes da refatoração ampla da interface.

## Escopo preservado

- API FastAPI do Noite Web, com sessão, cookie e proteção CSRF.
- Pipeline de feedback positivo/negativo e remoção de avaliação.
- Identificadores persistentes de mensagens e histórico associado.
- Ponte Electron para SSE, cancelamento de requisições e feedback.
- Contexto de memória e documentos indexados encaminhado ao modelo como referência não confiável.
- Frontend web e assets locais existentes, como referência de rollback.
- Testes automatizados do backend e desktop.

## Validação executada

- Ruff nos módulos centrais e testes relacionados: aprovado.
- Testes do pipeline de feedback e API web: 8 aprovados.
- Testes de memória e indexação: 40 aprovados.
- Testes selecionados do assistente/contexto: 5 aprovados.
- Testes Electron/Desktop: 49 aprovados.
- `git diff --check`: aprovado.

A suíte Python combinada foi interrompida durante uma tentativa de encerrar um processo de teste sem resposta; portanto, não é registrada como aprovada. A validação visual e a execução ponta a ponta do servidor Uvicorn ainda não foram concluídas.

## Higiene de publicação

- Não incluir `.env`, arquivos `.env.*`, chaves, backups locais, `Temporarios/`, `_backups/` ou `node_modules/`.
- Manter os assets de terceiros já utilizados pelo frontend em `landing/assets/vendor/`.
- Não forçar push nem reescrever histórico remoto.
- A refatoração da interface deve começar em uma branch própria a partir deste checkpoint.

## Próxima etapa

Refatorar a interface sem alterar o contrato da API, os eventos SSE, a autenticação de sessão/CSRF ou o contrato IPC do Electron. Executar os testes de contrato após cada etapa.
