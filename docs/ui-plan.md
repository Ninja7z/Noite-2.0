# Plano de UI: mascote Noite 2.0

## Objetivo
- Substituir a janela de chat como interface padrão por um mascote desktop flutuante.
- Personagem original em pixel art, inspirado no conceito de robô de mesa branco com visor escuro e olhos azul-ciano do EMO; sem copiar assets/marca.
- Janela transparente, sem moldura, sempre visível, arrastável para qualquer ponto da tela e com posição persistida.
- Estado compacto: mascote + indicador de estado.
- Ao clicar: painel compacto com status Ollama/modelo, atividade recente, resposta/streaming e campo de mensagem.
- Expressões simples para ocioso, pensando, trabalhando, concluído e erro.
- Ações de alto risco continuam exigindo aprovação; mascote é observabilidade e entrada, não bypass de segurança.

## Arquitetura
- Preservar AssistantService, SQLite, gateway, ferramentas e contratos existentes.
- Nova UI em src/noite/mascot.py; execução padrão via python -m noite e launcher.
- Interface antiga isolada atrás de --legacy-ui/run_ui.py --legacy; não excluir enquanto launchers antigos dependerem do checkout.
- Worker Qt separado para chamadas assíncronas; sinais Qt para atualizar o mascote sem bloquear a thread visual.
- Posição persistida com QSettings; sem serviço de rede adicional.

## Validação
- Testes de lógica de estado, posição e worker com Qt offscreen.
- Rodar pytest, Ruff, compileall e git diff --check.
- Gerar um EXE com nome novo; não sobrescrever nem remover builds anteriores.
- Verificar visualmente inicialização, arrastar, expandir/recolher, envio e status real do Ollama.