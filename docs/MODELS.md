# Gerenciamento de modelos

O Ollama local é o backend padrão. O painel de modelos consulta `/api/tags`, mostra nome, tamanho em disco, família, parâmetros e quantização quando esses campos estão disponíveis. O modelo ativo pode ser escolhido na barra superior ou em Configurações e a seleção persiste localmente.

A consulta ao Hugging Face é opcional e manual. A pesquisa envia somente o termo digitado ao endpoint público de metadados e lista até cinco resultados de geração de texto. Para resultados GGUF, consulta também metadados públicos de arquivos para sugerir uma quantização e tamanho em disco. A Noite não baixa modelos, pesos, cartões ou arquivos de configuração. A página do modelo só abre após ação do usuário.

## Avaliação de hardware

O computador de referência tem 6 GB de VRAM, 16 GB de RAM e i7-3770 sem AVX2. O tamanho do arquivo GGUF no Hub representa somente armazenamento, não memória de inferência. A Noite prioriza Q4_K_M e outras variantes Q4 pequenas quando há metadados; a recomendação continua condicionada a backend compatível com CPU sem AVX2, contexto, memória livre e camadas carregadas na GPU. As mensagens não são benchmarks.

O `qwen2.5:3b` local foi validado anteriormente por conversa real neste computador. Nenhum download foi iniciado pela interface.
