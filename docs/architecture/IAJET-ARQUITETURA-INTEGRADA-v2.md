# Arquitetura Integrada e Fundamentos Científicos de Inteligência Artificial para o Ecossistema IAJET

**Versão:** 2.0  
**Data de consolidação:** Novembro de 2026  
**Escopo:** Fundamentos teóricos, adaptação de modelos, percepção multimodal, agentes MCP, inferência local em hardware restrito, segurança OWASP/NSA, avaliação RAGAS, conformidade regulatória (LGPD, PL 2338/2023, EU AI Act) e roteiro de implementação.

---

## Sumário

1. [Fundamentos Teóricos, Paradigmas de Aprendizado e Mecanismos de Raciocínio](#1-fundamentos-teóricos-paradigmas-de-aprendizado-e-mecanismos-de-raciocínio)
2. [Percepção Multimodal e Arquitetura de Agentes Autônomos](#2-percepção-multimodal-e-arquitetura-de-agentes-autônomos)
3. [Otimização de Hardware e Inferência Local em Ambientes Restritos](#3-otimização-de-hardware-e-inferência-local-em-ambientes-restritos)
4. [Protocolos de Segurança, Avaliação Contínua e Mitigação de Riscos Algorítmicos](#4-protocolos-de-segurança-avaliação-contínua-e-mitigação-de-riscos-algorítmicos)
5. [Governança Regulatória, Conformidade Legal e Roteiro de Implementação](#5-governança-regulatória-conformidade-legal-e-roteiro-de-implementação)
6. [Conclusões e Recomendações Arquiteturais](#6-conclusões-e-recomendações-arquiteturais)
7. [Referências Consolidadas](#7-referências-consolidadas)

---

## 1. Fundamentos Teóricos, Paradigmas de Aprendizado e Mecanismos de Raciocínio

A capacidade cognitiva de um sistema de IA não reside isoladamente no modelo de linguagem. Redes baseadas em Transformers e arquiteturas com roteamento dinâmico como *Mixture of Experts* (MoE) constituem o núcleo estatístico, mas a inteligência emergente depende da integração orgânica entre qualidade de dados, pipelines de alinhamento, memória externa, verificadores determinísticos e protocolos de execução segura.

### 1.1 Autoatenção e representações contextuais

O fundamento matemático do processamento de linguagem natural moderno repousa sobre o mecanismo de autoatenção (*self-attention*), que permite mapear relações contextuais de longa distância no espaço de *embeddings*. A adaptação do comportamento do modelo e a assimilação de novos domínios exigem, contudo, uma distinção clara entre modificar a distribuição estatística dos pesos e injetar contexto em tempo de execução.

### 1.2 Paradigmas de adaptação: horizontes computacionais e conceituais

| Metodologia de Adaptação | Mecanismo Primário de Atuação | Modificação em Pesos | Requisito Computacional | Escopo Principal de Aplicação |
|---|---|---|---|---|
| **Pré-treinamento** | Otimização estocástica em grande escala | Atualização total dos parâmetros originais | Elevado (clusters de GPUs) | Modelagem estatística de linguagem e conhecimento geral |
| **SFT** (*Supervised Fine-Tuning*) | Aprendizado supervisionado por pares instrução-resposta | Atualização total ou parcial dos pesos | Médio a Alto | Alinhamento sintático e formatação de saídas |
| **RLHF** (*Reinforcement Learning from Human Feedback*) | Treinamento de modelo de recompensa separado + otimização de política | Ajuste fino de alinhamento de política | Médio a Alto | Segurança, recusa de danos e tom comportamental |
| **DPO** (*Direct Preference Optimization*) | Otimização direta da política sobre dados de preferência condicional | Ajuste fino de alinhamento de política | Médio (50–60% mais econômico que RLHF) | Segurança, recusa de danos e tom comportamental |
| **GRPO** (*Group Relative Policy Optimization*) | Recompensas relativas em grupo, sem modelo crítico (*critic-free*) | Ajuste direcionado à política de raciocínio | Médio | Raciocínio matemático e lógico |
| **LoRA / QLoRA** | Decomposição matricial de baixo rank: ΔW = B · A | Pesos base congelados; treina matrizes de baixo rank | Baixo (QLoRA reduz VRAM em até 75% vs. LoRA) | Especialização de domínio e adequação a estilos específicos |

**Distinção crítica:** é um equívoco conceitual utilizar o ajuste fino de pesos como mecanismo de atualização factual. O *fine-tuning* consolida estilo, formato e tom comportamental; o conhecimento factual dinâmico deve ser suprido por arquiteturas de Geração Aumentada por Recuperação (RAG).

### 1.3 Raciocínio algorítmico e desacoplamento geração-validação

Abordagens como *Chain-of-Thought* (CoT) e *Tree of Thoughts* (ToT) induzem a rede a decompor problemas em etapas intermediárias. Contudo, a geração de uma cadeia explicativa fluida não garante exatidão lógica. Para mitigar alucinações em operações críticas, é necessário desacoplar a geração de hipóteses da validação lógica:

- **Modelo probabilístico** → gerador de propostas.
- **Compiladores, motores de execução de código e verificadores formais determinísticos** → confirmam a validade das etapas antes da efetivação de qualquer ação operacional.

---

## 2. Percepção Multimodal e Arquitetura de Agentes Autônomos

### 2.1 Alinhamento de representações heterogêneas

A multimodalidade transcende a simples união de modelos isolados de visão e fala. Pesquisas como **ImageBind**, **Flamingo** e **RT-2** demonstram a eficácia do alinhamento de representações heterogêneas — texto, imagem, áudio, vídeo e sinais térmicos ou de profundidade — em um único espaço de *embedding* compartilhado.

- **ImageBind** aprende um espaço de *embedding* conjunto para seis modalidades (imagem, texto, áudio, profundidade, térmico e IMU), usando a imagem como modalidade-âncora para vincular as demais.
- **Flamingo** introduz o *Perceiver Resampler*, que amostra características visuais por meio de consultas aprendidas via *cross-attention*, permitindo lidar com imagens e textos arbitrariamente intercalados.
- **RT-2** conecta percepção visual e ação motora, viabilizando a tradução de *tokens* visuais em comandos de controle para robôs.

Essa arquitetura permite que projeções visuais e auditivas sejam convertidas em *tokens* compreensíveis pelo núcleo de linguagem, viabilizando a conexão direta entre percepção sensorial e ações físicas ou digitais.

### 2.2 *Model Context Protocol* (MCP): especificação 2026-07-28

O **MCP**, introduzido pela Anthropic em novembro de 2024 e transferido para a **Agentic AI Foundation (AAIF)** sob a guarda da Linux Foundation, estabeleceu um padrão aberto para a integração entre aplicações hospedeiras (*Hosts*), clientes e servidores de ferramentas (*MCP Servers*).

A especificação **2026-07-28** é a maior revisão do protocolo desde o lançamento e finaliza a transição para uma **arquitetura totalmente *stateless***:

- **Handshake `initialize`/`initialized` e o cabeçalho `Mcp-Session-Id` foram removidos.** Cada requisição carrega sua própria versão de protocolo, identidade do cliente e capacidades.
- **Novos cabeçalhos `Mcp-Method` e `Mcp-Name`** expõem a operação no nível HTTP, permitindo que *load balancers* e *gateways* roteiem sem analisar o corpo da mensagem.
- **Qualquer instância de servidor pode responder a qualquer requisição**, eliminando afinidade de sessão e permitindo *scaling* horizontal, implantações *serverless* e *edge-ready*.
- O estado não desaparece: ele migra do protocolo para a aplicação, que o referencia explicitamente por IDs ou *handles*.

O MCP utiliza **JSON-RPC 2.0** sobre HTTPS e transporte HTTP *streamable* para viabilizar a descoberta dinâmica de capacidades em tempo de execução. A arquitetura subdivide as capacidades expostas em três primitivas principais:

| Primitiva | Definição | Exemplos |
|---|---|---|
| **Recursos (*Resources*)** | Dados passivos anexados ao contexto pelo servidor | Conteúdos de arquivos, logs de auditoria, esquemas de bancos de dados |
| **Ferramentas (*Tools*)** | Funções executáveis que o modelo pode invocar ativamente | Consultas em APIs, operações no sistema de arquivos, alterações de estado |
| **Prompts** | Modelos estruturados de instrução expostos pelo servidor | Guiar o usuário ou o agente em tarefas repetitivas |

**Fluxo de orquestração:** a aplicação hospedeira inicializa conexões com os servidores selecionados; o cliente solicita a lista de metadados das ferramentas (descrições e esquemas em JSON Schema); quando a consulta exige ação externa, o modelo gera uma chamada estruturada; a aplicação hospedeira intercepta o *payload*, aplica regras de segurança e governança, solicita confirmação humana quando o impacto é crítico e repassa a requisição ao servidor MCP; o servidor executa a ação e devolve o resultado para incorporação ao contexto do modelo.

---

## 3. Otimização de Hardware e Inferência Local em Ambientes Restritos

### 3.1 Perfil computacional da NVIDIA GeForce GTX 1660 Super

| Especificação | Valor |
|---|---|
| VRAM | 6 GB GDDR6 |
| Barramento de memória | 192 bits |
| Largura de banda | 336 GB/s |
| Arquitetura | Turing |
| *Tensor Cores* | Ausentes |
| Compute FP16 | 10,1 TFLOPS |
| TDP | 125 W |

A ausência de *Tensor Cores* torna inviável o treinamento de grandes modelos ou a inferência de arquiteturas densas em precisão nativa (FP16/BF16). A execução eficiente de LLMs depende de **quantização** e de motores como `llama.cpp` com formato **GGUF**.

### 3.2 Quantização GGUF e viabilidade na GTX 1660 Super

| Formato e Quantização | Tamanho do Modelo | Ocupação Estimada de VRAM | Desempenho na GTX 1660 Super | Viabilidade no IAJET |
|---|---|---|---|---|
| **GGUF Q4_K_M** | 3B | 2,5–3,2 GB | ~90 tok/s (referência de pico); alta velocidade | Viável; ideal para triagem, validação de sintaxe e roteamento |
| **GGUF Q4_K_M** | 7B | **~4,1 GB** (até ~5 GB com contexto) | **~30–40 tok/s** (decode); ~26–38 tok/s conforme modelo e contexto | **Limite máximo da VRAM**; adequado para RAG local e síntese de menor complexidade |
| **GGUF Q8_0** | 7B | ~7,5 GB | Baixa velocidade (exige *offload* parcial para RAM) | Inviável para tempo real; estouro de VRAM e paginação via PCIe |
| **GGUF Q4_K_M** | 14B | ~7,9–9,5 GB | Inviável | Excede a capacidade do hardware local; requer delegação remota |

**Observações empíricas:**

- Um modelo 7B em Q4_K_M ocupa aproximadamente **4,1 GB em disco** e requer cerca de **7 GB de RAM** para execução confortável, deixando margem para janelas de contexto de 2K–8K tokens.
- Em benchmarks públicos do `llama.cpp`, a GTX 1660 Super atinge **~38 tok/s** em decode para 7B Q4 e **~90 tok/s** para 3B Q4. Medições específicas com Qwen 2.5 7B Q4_K_M reportam **~30 tok/s** de decode com *time-to-first-token* de ~570 ms.

### 3.3 Topologia de inferência hierárquica e distribuída do IAJET

**Primeiro nível — *Edge Processing* (local):**

- Modelo de **3B a 7B** quantizado em **GGUF Q4_K_M** residente na VRAM de 6 GB.
- Atribuições: pré-processamento de requisições, classificação de intenções, RAG em bases locais, anonimização estrita de dados sensíveis.
- **Gerenciamento do KV Cache** com limites estritos de janela de contexto para impedir estouro de VRAM.

**Segundo nível — APIs remotas de alta capacidade:**

- Quando a complexidade analítica excede a capacidade cognitiva local ou exige janelas de contexto extensas, a requisição **anonimizada** é empacotada e roteada para APIs remotas.
- O resultado retornado pela nuvem é inspecionado e montado pela aplicação local antes de ser exibido ao usuário.

---

## 4. Protocolos de Segurança, Avaliação Contínua e Mitigação de Riscos Algorítmicos

### 4.1 OWASP Top 10 para Aplicações de LLM (2025/2026)

| Código | Categoria | Mecanismo de Ataque e Impacto | Controle Defensivo no IAJET |
|---|---|---|---|
| **LLM01** | *Prompt Injection* | Injeção de instruções maliciosas diretas ou indiretas para burlar regras do sistema. | Isolamento sintático entre instruções do sistema e dados de entrada; sanitização de *inputs*. |
| **LLM02** | *Sensitive Info Disclosure* | Exposição acidental de dados pessoais, segredos ou credenciais em saídas. | Filtros de DLP baseados em NER e anonimização preventiva em pipelines de pré-processamento. |
| **LLM03** | *Excessive Agency* | Concessão de autonomia e privilégios excessivos a agentes e ferramentas. | Princípio do menor privilégio; limites de escopo e aprovação humana para ações destrutivas. |
| **LLM04** | *Supply Chain Vulnerabilities* | Pacotes, modelos ou adaptadores de terceiros comprometidos. | Validação de proveniência, assinatura digital e inventário **AIBOM**. |
| **LLM05** | *Data and Model Poisoning* | Contaminação de dados de treino, *fine-tuning* ou bancos vetoriais com *backdoors*. | Checagem de integridade de adaptadores e auditoria de proveniência de bases RAG. |
| **LLM06** | *Unbounded Consumption* | Esgotamento financeiro ou de recursos (*Denial of Wallet*). | Limites *server-side* de tokens por requisição, orçamentos globais e *circuit breakers*. |
| **LLM07** | *Misinformation* | Aceitação acrítica de conteúdos alucinados ou incorretos em saídas. | Ancoragem de respostas em fontes RAG verificadas e validação antes da execução. |
| **LLM08** | *Hidden Context Exposure* | Exposição não autorizada de *prompts* de sistema ou dados de memória restrita. | Remoção total de segredos dos *prompts* e segregação de credenciais. |
| **LLM09** | *Vector & Embedding Weaknesses* | Manipulação de vetores de recuperação para forçar injeção de dados falsos em RAG. | Criptografia dos índices vetoriais e controles de acesso rigorosos nas coleções. |
| **LLM10** | *Improper Output Handling* | Renderização de conteúdo gerado sem sanitização, resultando em XSS ou RCE. | Parameterização de saídas, codificação de caracteres e sanitização antes do consumo *downstream*. |

### 4.2 Diretriz de segurança da NSA para MCP (maio de 2026)

Em **maio de 2026**, a **National Security Agency (NSA)** publicou uma diretriz de segurança focada no protocolo MCP, alertando contra riscos de **injeção indireta**, **envenenamento de ferramentas** (*Tool Poisoning*), **exfiltração de contexto entre servidores** e **alteração silenciosa de comportamento** (*silent behavior change*). A NSA observa que esses ataques passam por verificações clássicas de *zero trust* porque **não subvertem a identidade — subvertem o significado**.

### 4.3 Benchmark MCPTox (2025)

O **MCPTox** é o primeiro *benchmark* a avaliar sistematicamente a robustez de agentes contra *Tool Poisoning* em configurações MCP realistas. Ele foi construído sobre **45 servidores MCP reais e 353 ferramentas autênticas**, gerando **1.312 casos de teste maliciosos** em 10 categorias de risco.

**Resultados principais:**

- **o1-mini** atingiu taxa de sucesso de ataque de **72,8%**.
- Modelos mais capazes tendem a ser **mais suscetíveis**, pois o ataque explora sua superior capacidade de seguir instruções.
- A maior taxa de recusa entre os modelos avaliados (**Claude-3.7-Sonnet**) foi **inferior a 3%** — evidência de que o alinhamento de segurança existente é **ineficaz** contra ações maliciosas que usam ferramentas legítimas para operações não autorizadas.

### 4.4 Controle de segurança em três camadas para o ecossistema MCP no IAJET

1. **OAuth 2.1 + PKCE + RFC 8707 (Resource Indicators)** para qualquer servidor MCP remoto via HTTP. Impede ataques de *token passthrough* e garante que os *tokens* fiquem vinculados ao servidor de destino correto.
2. **Isolamento de servidores MCP locais** inicializados via subprocessos `stdio` sob *sandboxing* restrito por perfis **seccomp**, **AppArmor** ou contêineres leves baseados em **gVisor**, bloqueando acesso direto ao sistema de arquivos do hospedeiro e restringindo conexões de rede não autorizadas.
3. **Hashing imutável das definições e esquemas de ferramentas.** Quando a aplicação hospedeira detecta qualquer alteração no *hash* de um esquema previamente aprovado, a ferramenta é **desativada preventivamente** até nova revisão de código e autorização explícita do administrador, anulando ataques de *rug pull*.

### 4.5 Avaliação contínua com RAGAS

O **RAGAS** estrutura a auditoria de desempenho de pipelines RAG sobre quatro métricas fundamentais:

| Métrica | O que avalia | Dimensão auditada |
|---|---|---|
| **Precisão do Contexto (*Context Precision*)** | Proporção de fragmentos recuperados que são efetivamente relevantes para a pergunta. | Qualidade do *retriever* |
| **Revocação do Contexto (*Context Recall*)** | Capacidade de trazer todos os documentos necessários contidos na base para fundamentar a resposta. | Cobertura do *retriever* |
| **Fidelidade (*Faithfulness*)** | Grau em que a resposta gerada é estritamente derivada do contexto recuperado. | Alucinação factual do gerador |
| **Relevância da Resposta (*Answer Relevancy*)** | Assertividade do texto final em relação ao comando original do usuário. | Aderência do gerador à consulta |

A automação dessas métricas em pipelines de **CI/CD** protege o IAJET contra degradação de desempenho e elimina a dependência exclusiva de *benchmarks* públicos, sujeitos a contaminação por vazamento de dados e descontinuação de manutenção.

---

## 5. Governança Regulatória, Conformidade Legal e Roteiro de Implementação

### 5.1 PL 2338/2023 — Marco Legal da Inteligência Artificial (Brasil)

O **PL 2338/2023**, proposto pelo ex-Senador Rodrigo Pacheco e aprovado por unanimidade no Plenário do Senado Federal em **10 de dezembro de 2024**, ingressou na Câmara dos Deputados em **17 de março de 2025**. A matéria tramita na **Comissão Especial** sob a relatoria do Deputado **Aguinaldo Ribeiro (PP-PB)**.

**Status em novembro de 2026:**

- O relator já **apresentou o relatório**, mas ele **ainda não foi debatido** na Comissão Especial.
- O texto está na Comissão desde **maio de 2025**, em análise conjunta com **38 outros projetos**.
- Há risco de **arquivamento** caso a Comissão Especial não aprove o texto até o fim da legislatura, em **dezembro de 2026**.
- O calendário inicial previa parecer final em **19 de maio de 2026** e votação em Plenário em **27 de maio de 2026**, mas sofreu sucessivos adiamentos por impasses políticos e pelo calendário eleitoral de 2026.

**Estrutura regulatória baseada em risco:**

| Categoria de Risco | Definição no PL 2338/2023 | Exemplos Práticos | Requisitos e Obrigações de Conformidade |
|---|---|---|---|
| **Risco Excessivo (Proibido)** | Sistemas cujos impactos representem ameaça inaceitável a direitos fundamentais ou segurança. | Armas autônomas letais; pontuação social (*Social Scoring*) estatal; indução subliminar maliciosa. | Proibição total de desenvolvimento, comercialização ou operação no território nacional. |
| **Alto Risco** | Aplicações com potencial relevante de afetar saúde, segurança, emprego ou direitos civis. | Análise automatizada de crédito; triagem de recrutamento; diagnóstico médico; identificação biométrica. | Exigência de Avaliação de Impacto Algorítmico (AIA), governança de dados, auditorias e supervisão humana. |
| **Risco Baixo / Moderado** | Aplicações gerais que não se enquadram nas categorias de alto risco ou vedadas. | Assistentes virtuais de atendimento; filtros funcionais de spam; recomendação de conteúdo. | Deveres gerais de transparência, informando o usuário sobre a interação com IA. |

### 5.2 LGPD e atuação da ANPD

Paralelamente ao processo legislativo, a **ANPD** intensificou a fiscalização sobre operações de IA com base no arcabouço da **LGPD**. O **artigo 20 da LGPD** concede aos titulares o direito de solicitar a **revisão de decisões tomadas unicamente com base em tratamento automatizado**, bem como informações claras sobre os critérios e procedimentos utilizados pelo algoritmo.

**Sanções:** multas de até **2% do faturamento**, limitadas a **R$ 50 milhões por infração**.

**Sandbox regulatório da ANPD:**

- Em **2 de julho de 2026**, a ANPD publicou o **1º Relatório Parcial de Monitoramento** do sandbox de IA.
- Três empresas foram selecionadas: **Metatext** (segurança de agentes autônomos), **Synapse AI** (gestão ferroviária em tempo real) e **Prevvine Tecnologia** (IA médica).
- O sandbox opera até **dezembro de 2026**.

### 5.3 Cronograma do EU AI Act (referência internacional)

O **EU AI Act** (Regulamento (UE) 2024/1689) segue um calendário escalonado de conformidade:

| Data | Marco |
|---|---|
| **1 de agosto de 2024** | Entrada em vigor do Regulamento. |
| **2 de agosto de 2025** | Aplicação das regras para IA de propósito geral (GPAI). |
| **2 de agosto de 2026** | Aplicação da maioria das regras e início da *enforcement* para disposições aplicáveis. |
| **2 de agosto de 2027** | Aplicação das regras para IA de alto risco integrada em produtos regulados (Anexo I); prazo para cada Estado-Membro estabelecer pelo menos um sandbox regulatório de IA. |
| **Dezembro de 2027 / Agosto de 2028** | Prazos finais para obrigações de alto risco dos Anexos III e I, respectivamente, conforme ajustes do *AI Omnibus*. |

### 5.4 Roteiro de implementação do IAJET — quatro fases executivas

**Fase 1 — Governança de Dados e Higienização Preventiva**

- Rotinas locais de detecção e mascaramento de **PII** antes de qualquer indexação em bancos vetoriais ou envio a provedores de nuvem.
- Segregação rígida de credenciais: segredos **nunca** injetados em *prompts* de sistema ou contextos de agentes.

**Fase 2 — *Hardening* do Protocolo de Agentes (MCP)**

- Ambiente de execução dos servidores MCP com **OAuth 2.1** e validação rigorosa de audiência.
- Subprocessos locais isolados em *sandboxes* estritos (**seccomp/AppArmor/gVisor**).
- Barramento de autorização exigindo **aprovação humana** para chamadas de ferramentas de alto impacto.
- **Hashing imutável** de definições e esquemas de ferramentas, com desativação preventiva em caso de alteração.

**Fase 3 — Avaliação e Monitoramento Contínuo**

- Integração do **RAGAS** ao pipeline de CI/CD para verificação diária de **fidelidade**, **precisão do contexto**, **revocação do contexto** e **relevância da resposta**.
- Limites *server-side* de tokens e orçamentos globais para neutralizar **Denial of Wallet** (LLM06).

**Fase 4 — Adequação Regulatória e Auditoria Algorítmica**

- Documentação completa da **Avaliação de Impacto Algorítmico (AIA)**.
- Manutenção do inventário **AIBOM** dos componentes de software e modelos utilizados.
- Mecanismos de **explicabilidade** e **revisão humana** para atender ao **artigo 20 da LGPD** e às futuras exigências do **PL 2338/2023**.

---

## 6. Conclusões e Recomendações Arquiteturais

1. **Abordagem sistêmica da inteligência:** o LLM deve ser tratado como um motor probabilístico de inferência contido em uma arquitetura maior. A precisão e a utilidade do sistema dependem da inclusão de verificadores lógicos determinísticos, recuperação RAG bem avaliada e barramentos de controle de execução.

2. **Inferência local híbrida e adaptada ao hardware:** a GTX 1660 Super (6 GB VRAM) deve ser dedicada exclusivamente à inferência de modelos altamente quantizados (**3B a 7B em GGUF Q4_K_M**, ocupando ~2,5–5 GB), focados em tarefas de baixa latência: triagem, validação de sintaxe e sanitização de dados. Tarefas analíticas pesadas devem ser **anonimizadas localmente** e delegadas a modelos avançados via APIs remotas.

3. **Segurança *zero-trust* no protocolo MCP:** a integração de ferramentas via MCP precisa seguir rigorosamente os princípios de **isolamento em *sandbox***, **validação de esquemas por *hash* imutável**, **OAuth 2.1 com PKCE** e **intervenção humana obrigatória** para ações irreversíveis ou de alto risco. O alerta da NSA (maio/2026) e os resultados do MCPTox (72,8% de sucesso de ataque) tornam essas medidas **não negociáveis**.

4. **Governança e conformidade regulatória preventiva:** a adequação à **LGPD** e ao modelo de riscos do **PL 2338/2023** deve ocorrer desde as fases iniciais do desenvolvimento. A documentação da proveniência de dados, a transparência algorítmica e o direito à explicação protegem a aplicação contra penalidades administrativas da ANPD e preparam a infraestrutura para a vigência do Marco Legal da IA no Brasil.

---

## 7. Referências Consolidadas

1. **MCP 2026-07-28 (stateless):** VentureBeat, "MCP just got its biggest update ever" (28/07/2026); Lenses.io, "AGNTCon + MCPCon Europe 2026: five takeaways" (15/10/2026).
2. **MCPTox (2025):** Wang et al., "MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers," arXiv:2508.14925 (19/08/2025).
3. **NSA MCP Security Guidance (maio/2026):** NSA Cybersecurity Information Sheet; SafeBreach, "Does Your CTEM Program Have an AI Blind Spot?" (16/07/2026).
4. **PL 2338/2023:** Câmara dos Deputados, Radioagência (27/10/2026); TozziniFreire, "Sem Marco Legal, ANPD e setores avançam na regulação da IA" (21/08/2026).
5. **RAGAS:** Documentação oficial; métricas *context_precision*, *context_recall*, *faithfulness*, *answer_relevancy*.
6. **GTX 1660 Super / GGUF Q4_K_M:** FitMyLLM, benchmarks de setembro/2026; SitePoint, "Quantization Explained" (11/03/2026).
7. **ImageBind / Flamingo / RT-2:** Girdhar et al., "ImageBind: One Embedding Space To Bind Them All," CVPR 2023; Alayrac et al., "Flamingo," 2022.
8. **GRPO:** "From PPO to GRPO" — remoção do modelo crítico, *group-relative normalization* de recompensas.
9. **DPO vs. RLHF:** "Conditional Equivalence of DPO and RLHF," ICML 2026; Microsoft Learn, "Direct Preference Optimization" (11/02/2026).
10. **LoRA / QLoRA:** "Large Language Model Fine-tuning with Low-Rank Adaptation" (ACM, 2025); "Parameter-Efficient Fine-Tuning: LoRA, QLoRA, and DoRA" (Zenodo).
11. **EU AI Act:** AI Act Service Desk, calendário oficial de implementação (2024–2027).

---

> **Nota editorial:** Este documento registra a arquitetura e as afirmações técnicas conforme fornecidas pelo autor. Datas, versões de especificações, benchmarks, métricas e status legislativos devem ser verificados nas fontes primárias antes de orientar decisões de implementação ou conformidade.
