# Guia de Referências Visuais: Interfaces de IA, Cloud IDEs, Claude & Codex

Este documento consolida as especificações visuais, descrições técnicas de UI/UX e os links diretos e plataformas de referência das principais interfaces de Inteligência Artificial para desenvolvedores.

---

## 1. Ambientes Estilo Anthropic Claude (Artifacts & Workbench)

### 1.1. Claude Artifacts (Interface Split-Screen)
* **Descrição Visual:** Layout de tela dividida em duas colunas verticais. O lado esquerdo é dedicado à conversa em linguagem natural (prompting/instruções). O lado direito abre um painel interativo desacoplado ("Artifact") que renderiza aplicações React, documentos em Markdown, SVG ou código HTML/CSS em tempo real.
* **Componentes de UI:** Drawer deslizante, alternador entre modo "Code" e modo "Preview", botões de cópia rápida e exportação.
* **URLs de Referência:**
  * Documentação Oficial e Exemplos: [https://academy.claude.com/tutorials/build-custom-artifacts-with-claude](https://academy.claude.com/tutorials/build-custom-artifacts-with-claude)
  * Galeria Visual no PageFlows: [https://pageflows.com/screens/27333d81-4ebe-457d-bde5-ab3b2b7cce42/](https://pageflows.com/screens/27333d81-4ebe-457d-bde5-ab3b2b7cce42/)

### 1.2. Claude Workbench (Console de Engenharia de Prompt)
* **Descrição Visual:** Console técnico de alta densidade de informação em tema escuro. Possui um painel fixo para definição do *System Prompt*, um campo central para testes de histórico de mensagens e uma barra lateral direita com seletores numéricos para ajuste fino de parâmetros do modelo (`Temperature`, `Max Tokens`, `Top P`, `Stop Sequences`).
* **URLs de Referência:**
  * Anthropic Developer Console: [https://console.anthropic.com](https://console.anthropic.com)

---

## 2. Consoles Estilo OpenAI Codex & Playgrounds

### 2.1. OpenAI Playground (Console de Modelos de Código)
* **Descrição Visual:** Interface minimalista focada no fluxo de escrita contínua. Conta com seletores para troca de modelos (ex: GPT-4o, Codex/Chat Completions), controles deslizantes de parâmetros na barra lateral e um visualizador de tokens utilizados.
* **URLs de Referência:**
  * OpenAI Platform Playground: [https://platform.openai.com/playground](https://platform.openai.com/playground)
  * Guia de Ferramentas AI Atlas: [https://ai-atlas-tools.com/tools/gpt-3-playground-openai/](https://ai-atlas-tools.com/tools/gpt-3-playground-openai/)

### 2.2. Codex Agent Consoles & Execução Autônoma
* **Descrição Visual:** Visualizador de árvore de tarefas e gerenciamento de *threads* autônomas. Apresenta o status de execução de scripts em segundo plano, terminal com saída de erros em real-time e botões de controle de contexto (Workspace Local vs. Branch na Nuvem).
* **URLs de Referência:**
  * Exemplos da OpenAI API Platform: [https://platform.openai.com/examples](https://platform.openai.com/examples)

---

## 3. Assistentes Inline e IDEs Nativas (Cursor & Copilot)

### 3.1. Cursor IDE (Editor Nativo com IA Integrada)
* **Descrição Visual:** Modificação direta do VS Code/Electron com painel lateral acoplado para chat contextual. Suporta menções como `@Files`, `@Folder`, `@Git` e exibe alterações no arquivo-fonte via *Inline Diffs* (linhas verdes para inserção, vermelhas para remoção) acompanhadas por botões flutuantes de aceitação.
* **URLs de Referência:**
  * Site Oficial do Cursor: [https://www.cursor.com](https://www.cursor.com)
  * Discussões de UX e Interface no Forum Cursor: [https://forum.cursor.com](https://forum.cursor.com)

### 3.2. GitHub Copilot & Chat Panel
* **Descrição Visual:** Painel flutuante ou lateral integrado a editores (VS Code, Visual Studio, JetBrains). Possui barra de prompt inferior com suporte a comandos acionados por prefixos (`/explain`, `/tests`, `/fix`).
* **URLs de Referência:**
  * GitHub Copilot Product Page: [https://github.com/features/copilot](https://github.com/features/copilot)

---

## 4. Cloud IDEs e Plataformas Web de Programação

### 4.1. Bolt.new & StackBlitz (WebContainers & UI Generativa)
* **Descrição Visual:** IDE executada 100% no navegador. Divide a tela entre um assistente de IA conversacional à esquerda e um ambiente Node.js/WebContainer executando a aplicação full-stack com servidor local virtual à direita.
* **URLs de Referência:**
  * Plataforma Bolt.new: [https://bolt.new](https://bolt.new)
  * StackBlitz WebContainers: [https://stackblitz.com](https://stackblitz.com)

### 4.2. Replit Agent Workspace
* **Descrição Visual:** Interface em modo escuro focada no ciclo completo de desenvolvimento (planejamento de arquitetura, instalação de pacotes, escrita de código e deploy automático na nuvem). Mostra o passo a passo de raciocínio do agente em tempo real.
* **URLs de Referência:**
  * Replit Environment: [https://replit.com](https://replit.com)

---

## 5. Galerias de Design e Repositórios Visuais de UI

* **Mobbin Web & App UI Patterns:** [https://mobbin.com](https://mobbin.com)
* **Dribbble (Tag AI IDE):** [https://dribbble.com/tags/ai-ide](https://dribbble.com/tags/ai-ide)
* **Behance AI Code Editor Projects:** [https://www.behance.net/search/projects?search=ai%20code%20editor](https://www.behance.net/search/projects?search=ai%20code%20editor)