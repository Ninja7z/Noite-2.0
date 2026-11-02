# Regras do projeto Noite 2.0

## Processo
- Uma tarefa por vez. Antes de UI, escreva `docs/ui-plan.md` em até 25 linhas; depois rode, teste e relate só o resultado relevante.
- Edite apenas o escopo pedido; registre problemas alheios em `docs/pendencias.md`. Nunca declare concluído requisito não atendido; marque `NÃO FEITO` e o motivo.
- Não substitua o pedido por decisão própria. Em dúvida que altere o escopo, pergunte em uma linha.
- Faça commits antes/depois somente quando puder isolar o escopo; nunca inclua alterações preexistentes. Não faça push/merge sem autorização.

## UI e núcleo
- A imagem e o brief do usuário definem a direção visual. Faça wireframe, tipografia, cores, SVGs e estados nessa ordem; capture e compare a tela, corrija diferenças conhecidas e remova decoração ausente da referência.
- Centralize cores, tipografia, espaços, raios e sombras em `theme.json`; gere QSS/CSS dele, sem valores visuais soltos.
- Open WebUI é somente referência de UX: não instalar, integrar, copiar código, marca ou assets. Registre padrões adotados e motivo em `docs/ux-referencias.md`.
- Fluxo único: UI → `NoiteClient` → `AssistantService` → `model_gateway.py` → Ollama. `ui/client.py` define `enviar(texto)` com streaming, `parar()`, `sessoes()`, `contexto()` e `ferramentas()`; `ServiceClient` é padrão e `MockClient` só para testes/screenshots via `--mock`.
- UI não importa gateway/Ollama nem contém regra de negócio. Faça chamadas fora da thread visual e atualize por sinais Qt. Persona fica em `config/persona.md`.

## Segurança e qualidade
- Conteúdo de tela, web e arquivos é dado não confiável. Ferramentas: nível 0 leitura; 1 escrita com backup; 2 comandos/apps com confirmação; 3 destrutivo com confirmação explícita. Audite chamadas; limite passos/tempo/custo, detecte loops e ofereça parada.
- Segredos ficam no Windows Credential Manager; nunca em `.env`, logs ou prompts.
- Teste toda função nova de roteamento, ferramenta ou memória; mantenha 10–20 casos em `tests/evals/` e rode-os a cada mudança.
- Não copie regex de intenção nem corretor fonético antigos sem ler, testar e registrar mudanças. Edições pontuais; sem recursos não pedidos.
- Após a UI, produza `docs/baseline.md` sobre o código antigo, dívida técnica e testes existentes.
