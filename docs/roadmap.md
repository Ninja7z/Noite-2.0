# Roadmap do MVP

## Fases 1 a 4 — MVP

1. Núcleo CLI, contratos Pydantic, configurações locais e histórico SQLite/FTS5.
2. Roteamento hierárquico: regras determinísticas primeiro, classificador local depois e provedor de nuvem somente quando habilitado.
3. Ferramentas Windows restritas a uma pasta de trabalho, com validação e execução sem elevação administrativa.
4. Interface simples em PySide6 conectada ao núcleo por uma interface local desacoplada.

## Fases 5 a 8 — expansão

- Voz local: VAD, wake word, faster-whisper e Piper TTS.
- Busca vetorial local via SQLite e `sqlite-vec`.
- Integrações específicas para Roblox Studio e Blender.
- Avaliações automatizadas, telemetria com `trace_id` e controles de privacidade completos.

Não instalar os componentes da expansão até a fase correspondente; isso reduz o peso do ambiente e evita dependências desnecessárias no MVP.
