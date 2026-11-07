(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const state = { csrf: "", activeId: "", conversations: [], busy: false, providerMode: "nightly" };
  const els = {
    list: $("#conversation-list"), messages: $("#messages"), welcome: $("#welcome"),
    input: $("#message-input"), form: $("#composer"), send: $("#send-btn"),
    title: $("#current-title"), model: $("#model-status"), modelName: $("#model-name"),
    sideStatus: $("#side-status"), presence: $("#presence-indicator"),
    systemTag: $("#system-tag"), systemTitle: $("#system-title"),
    systemDescription: $("#system-description"), activity: $("#activity-list"),
    sidebar: $("#sidebar"), scrim: $("#mobile-scrim"),
    panel: $("#activity-panel")
  };

  function toast(message, error) {
    const node = document.createElement("div");
    node.className = "toast" + (error ? " error" : "");
    node.textContent = message;
    $("#toast-region").append(node);
    window.setTimeout(() => node.remove(), 3400);
  }

  async function api(path, options) {
    options = options || {};
    const headers = new Headers(options.headers || {});
    if (state.csrf && options.method && options.method !== "GET") headers.set("X-Noite-CSRF", state.csrf);
    if (options.body) headers.set("Content-Type", "application/json; charset=utf-8");
    const response = await fetch(path, Object.assign({credentials:"same-origin"}, options, {headers}));
    if (!response.ok) {
      let detail = "Falha " + response.status;
      try { const body = await response.json(); detail = body.detail || body.message || detail; } catch {}
      throw new Error(detail);
    }
    return response;
  }


  const providerButton = $("#provider-switch");
  const providerMenu = $("#provider-menu");
  const providerLabel = $("#provider-label");
  const providerNote = $("#provider-menu-note");
  const reasoningToggle = $("#reasoning-toggle");
  const reasoningNote = $("#reasoning-note");
  const permissionNote = $("#permission-note");

  function renderProvider(mode, configured) {
    state.providerMode = mode === "cloud" ? "cloud" : "nightly";
    providerLabel.textContent = state.providerMode === "cloud" ? "Cloud" : "Nightly";
    providerButton.querySelector(".provider-glyph").textContent = state.providerMode === "cloud" ? "☁" : "◒";
    reasoningToggle.disabled = state.providerMode === "cloud";
    reasoningNote.textContent = state.providerMode === "cloud"
      ? "Disponível no Nightly para modelos locais compatíveis."
      : "Mais tempo para tarefas complexas, em modelos locais compatíveis.";
    document.querySelectorAll(".provider-option").forEach(option => {
      option.classList.toggle("active", option.dataset.provider === state.providerMode);
    });
    providerNote.textContent = state.providerMode === "cloud"
      ? "Gemini Cloud ativo. Novas mensagens usam a API do Google."
      : configured ? "Nightly ativo. Inferência local via Ollama."
      : "Nightly ativo. Configure GEMINI_API_KEY para liberar Cloud.";
    providerNote.classList.toggle("error", state.providerMode === "cloud" && !configured);
  }

  async function changeProvider(mode) {
    if (state.busy) { toast("Aguarde a resposta atual terminar para trocar o ambiente."); return; }
    try {
      const response = await api("/web/api/provider", {
        method: "POST", body: JSON.stringify({mode})
      });
      const data = await response.json();
      renderProvider(data.mode, data.gemini_configured);
      providerMenu.hidden = true;
      providerButton.setAttribute("aria-expanded", "false");
      toast(data.mode === "cloud" ? "Cloud ativado. Novas mensagens usarão Gemini." : "Nightly ativado. Modelos locais.");
      await refreshBootstrap();
    } catch (error) {
      providerNote.textContent = error.message;
      providerNote.classList.add("error");
      toast(error.message, true);
    }
  }

  providerButton.addEventListener("click", async () => {
    providerMenu.hidden = !providerMenu.hidden;
    providerButton.setAttribute("aria-expanded", String(!providerMenu.hidden));
    if (!providerMenu.hidden) {
      try {
        const response = await api("/web/api/provider");
        const data = await response.json();
        renderProvider(data.mode, data.gemini_configured);
        await loadSettings();
      } catch (error) { providerNote.textContent = error.message; }
    }
  });
  document.querySelectorAll(".provider-option").forEach(option => {
    option.addEventListener("click", () => changeProvider(option.dataset.provider));
  });
  document.addEventListener("click", event => {
    if (!event.target.closest(".provider-wrap")) {
      providerMenu.hidden = true;
      providerButton.setAttribute("aria-expanded", "false");
    }
  });

  function renderSettings(data) {
    if (reasoningToggle) reasoningToggle.checked = Boolean(data.reasoning_enabled);
    const profile = data.permission_profile || "none";
    document.querySelectorAll(".permission-option").forEach(option => {
      const active = option.dataset.profile === profile;
      option.classList.toggle("active", active);
      option.setAttribute("aria-pressed", String(active));
    });
    const descriptions = {
      none: "Sem acesso. Nenhuma ferramenta pode ser executada.",
      restricted: "Acesso restrito: leitura e escrita de arquivos. Outros recursos permanecem bloqueados.",
      full: "Acesso total habilitado. Ações de alto risco ainda exigem confirmação."
    };
    if (permissionNote) permissionNote.textContent = descriptions[profile] || descriptions.none;
  }

  async function loadSettings() {
    const response = await api("/web/api/settings");
    renderSettings(await response.json());
  }

  async function updateSettings(payload) {
    const response = await api("/web/api/settings", {
      method: "POST", body: JSON.stringify(payload)
    });
    renderSettings(await response.json());
  }

  reasoningToggle.addEventListener("change", async () => {
    const requested = reasoningToggle.checked;
    reasoningToggle.disabled = true;
    try {
      await updateSettings({reasoning_enabled: requested});
      toast(requested ? "Raciocínio estendido ativado." : "Raciocínio estendido desativado.");
    } catch (error) {
      reasoningToggle.checked = !requested;
      toast(error.message, true);
    } finally {
      reasoningToggle.disabled = state.providerMode === "cloud";
    }
  });

  document.querySelectorAll(".permission-option").forEach(option => {
    option.addEventListener("click", async () => {
      const profile = option.dataset.profile;
      if (profile === "full" && !window.confirm(
        "Acesso total libera todas as capacidades disponíveis. Ações de alto risco ainda pedem confirmação. Deseja continuar?"
      )) return;
      document.querySelectorAll(".permission-option").forEach(item => item.disabled = true);
      try {
        await updateSettings({permission_profile: profile});
        toast("Permissões atualizadas.");
      } catch (error) {
        toast(error.message, true);
      } finally {
        document.querySelectorAll(".permission-option").forEach(item => item.disabled = false);
      }
    });
  });

  function renderConversations() {
    els.list.replaceChildren();
    if (!state.conversations.length) {
      const empty = document.createElement("div");
      empty.className = "activity-empty";
      empty.textContent = "Suas conversas aparecerão aqui.";
      els.list.append(empty);
      return;
    }
    for (const conversation of state.conversations) {
      const row = document.createElement("div");
      row.className = "conversation-item" + (conversation.id === state.activeId ? " active" : "");
      const icon = document.createElement("span");
      icon.className = "conv-icon";
      icon.textContent = "◌";
      const title = document.createElement("span");
      title.className = "conv-title";
      title.textContent = String(conversation.title || "Nova conversa").replace(/\s+/g, " ").trim().slice(0,120);
      const menu = document.createElement("button");
      menu.className = "conv-menu";
      menu.type = "button";
      menu.textContent = "🗑";
      menu.title = "Excluir conversa";
      menu.setAttribute("aria-label", "Excluir: " + title.textContent);
      menu.addEventListener("click", async (event) => {
        event.stopPropagation();
        const action = "e";
        if (!action) return;
        if (action.trim().toLowerCase() === "r") {
          const next = window.prompt("Novo nome da conversa:", conversation.title);
          if (!next || !next.trim()) return;
          try {
            await api("/web/api/conversations/" + encodeURIComponent(conversation.id), {
              method:"PATCH", body:JSON.stringify({title:next.trim()})
            });
            await refreshBootstrap();
          } catch (error) { toast(error.message, true); }
        } else if (action.trim().toLowerCase() === "e") {
          if (!window.confirm("Excluir esta conversa e suas mensagens? Esta ação não pode ser desfeita.")) return;
          try {
            await api("/web/api/conversations/" + encodeURIComponent(conversation.id), {method:"DELETE"});
            await refreshBootstrap();
            await loadMessages(state.activeId);
          } catch (error) { toast(error.message, true); }
        }
      });
      row.append(icon, title, menu);
      row.addEventListener("click", () => selectConversation(conversation.id));
      els.list.append(row);
    }
  }

  function showWelcome(show) {
    if (show) {
      els.messages.replaceChildren(els.welcome);
      els.welcome.hidden = false;
    } else if (els.welcome.isConnected) {
      els.welcome.remove();
    }
  }

  function addMessage(role, content, options) {
    options = options || {};
    showWelcome(false);
    const article = document.createElement("article");
    article.className = "message " + role + (options.pending ? " pending" : "") + (options.error ? " message-error" : "");
    article._role = role;
    article._conversationId = options.conversationId || state.activeId;
    article._promptText = options.prompt || "";
    if (role === "user") article._rawText = content || "";
    if (role === "assistant") {
      const avatar = document.createElement("div");
      avatar.className = "message-avatar";
      avatar.textContent = "n.";
      const wrap = document.createElement("div");
      wrap.className = "message-content";
      const meta = document.createElement("span");
      meta.className = "message-meta";
      meta.textContent = "Noite";
      const text = document.createElement("div");
      text.className = "message-text";
      text.textContent = content || "";
      wrap.append(meta, text);
      article.append(avatar, wrap);
      article._text = text;
      article._rawText = content || "";
    } else {
      const wrap = document.createElement("div");
      wrap.className = "message-content";
      wrap.textContent = content;
      article.append(wrap);
    }
    els.messages.append(article);
    if (role === "assistant" && article._rawText) renderAssistantMessage(article, true);
    els.messages.scrollTop = els.messages.scrollHeight;
    return article;
  }

  async function loadMessages(id) {
    if (!id) return;
    const response = await api("/web/api/conversations/" + encodeURIComponent(id) + "/messages");
    const payload = await response.json();
    els.messages.replaceChildren();
    if (!payload.messages.length) {
      els.messages.append(els.welcome);
      els.welcome.hidden = false;
      return;
    }
    els.welcome.hidden = true;
    let previousUser = "";
    for (const item of payload.messages) {
      const role = item.role === "assistant" ? "assistant" : "user";
      const article = addMessage(role, item.content);
      article._conversationId = id;
      if (item.id != null) article.dataset.messageId = String(item.id);
      if (role === "user") previousUser = item.content || "";
      else {
        article._promptText = previousUser;
        article._feedback = item.rating || "";
        attachMessageActions(article);
      }
    }
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  async function selectConversation(id) {
    if (id === state.activeId) { closeMobilePanels(); return; }
    try {
      await api("/web/api/conversations/" + encodeURIComponent(id) + "/select", {method:"POST"});
      state.activeId = id;
      const selected = state.conversations.find(item => item.id === id);
      els.title.textContent = selected ? selected.title : "Nova conversa";
      renderConversations();
      await loadMessages(id);
      closeMobilePanels();
    } catch (error) { toast(error.message, true); }
  }

  async function refreshBootstrap() {
    const response = await api("/web/api/bootstrap");
    const data = await response.json();
    window.dispatchEvent(new CustomEvent("noite:bootstrap", {detail: data}));
    if (data.provider) renderProvider(data.provider.mode, data.provider.gemini_configured);
    state.activeId = data.active_conversation_id;
    state.conversations = data.conversations || [];
    const active = state.conversations.find(item => item.id === state.activeId);
    els.title.textContent = active ? active.title : "Nova conversa";
    renderConversations();
    const model = data.model || {};
    const cloudMode = state.providerMode === "cloud";
    const connected = cloudMode
      ? Boolean(data.provider && data.provider.gemini_configured)
      : model.server === "up" && model.model_installed === true;
    els.model.classList.toggle("online", connected);
    els.model.classList.toggle("offline", !connected);
    els.model.querySelector("span:last-child").textContent = cloudMode
      ? connected ? "Gemini Cloud disponível" : "Configure a API Gemini"
      : model.server !== "up" ? "Ollama desconectado"
      : model.model_installed ? "Nightly pronto" : "Nightly aguardando modelo";
    els.modelName.textContent = cloudMode ? "Gemini Cloud" : connected ? "Nightly" : "Nightly offline";
    els.sideStatus.textContent = connected ? "Pronta para conversar" :
      cloudMode ? "Configure a API Gemini" :
      model.server !== "up" ? "Aguardando Ollama" : "Modelo não instalado";
    els.presence.classList.toggle("online", connected);
    els.systemTag.textContent = connected ? "SISTEMA PRONTO" : "VERIFICAR CONEXÃO";
    els.systemTitle.textContent = connected ? "Tudo em sintonia" :
      cloudMode ? "API Gemini não configurada" :
      model.server !== "up" ? "O motor local está offline" : "Falta carregar o modelo";
    els.systemDescription.textContent = connected
      ? cloudMode ? "Gemini Cloud está pronto para novas mensagens." : "Nightly está pronto. Seleção de modelos conforme a tarefa."
      : cloudMode ? "Configure GEMINI_API_KEY no ambiente local da Noite."
      : model.server !== "up" ? "Nightly não consegue alcançar o Ollama."
      : "Nightly está aguardando um modelo disponível.";
    renderActivities(data.activities || []);
  }

  function renderActivities(items) {
    els.activity.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "activity-empty";
      empty.textContent = "Suas atividades aparecerão aqui durante a conversa.";
      els.activity.append(empty);
      return;
    }
    for (const item of items.slice(-12).reverse()) appendActivity(item, false);
  }

  function appendActivity(item, prepend) {
    const empty = els.activity.querySelector(".activity-empty");
    if (empty) empty.remove();
    const node = document.createElement("div");
    node.className = "activity-item";
    const symbol = document.createElement("span");
    symbol.className = "activity-symbol";
    symbol.textContent = item.state === "failed" ? "!" : item.state === "completed" ? "✓" : "·";
    const body = document.createElement("div");
    const title = document.createElement("b");
    title.textContent = item.summary || item.operation || "Atividade";
    const detail = document.createElement("small");
    const date = item.occurred_at ? new Date(item.occurred_at) : null;
    const timestamp = date && !Number.isNaN(date.valueOf())
      ? date.toLocaleTimeString("pt-BR", {hour:"2-digit",minute:"2-digit","second":"2-digit"})
      : "";
    const duration = Number.isFinite(item.duration_ms) && item.duration_ms >= 0
      ? item.duration_ms < 1000
        ? Math.round(item.duration_ms) + " ms"
        : (item.duration_ms / 1000).toFixed(2).replace(".", ",") + " s"
      : "";
    const stateLabel = item.state === "started" ? "Em andamento"
      : item.state === "failed" ? "Falhou"
      : item.state === "cancelled" ? "Cancelada"
      : item.state === "completed" ? "Concluída" : "";
    detail.textContent = [
      item.operation || "Noite",
      timestamp,
      duration,
      stateLabel
    ].filter(Boolean).join(" · ");
    body.append(title, detail);
    node.append(symbol, body);
    if (prepend) els.activity.prepend(node); else els.activity.append(node);
    while (els.activity.children.length > 12) els.activity.lastElementChild.remove();
  }

  function handleEvent(type, data) {
    if (type === "token") {
      if (!currentAssistant) currentAssistant = addMessage("assistant", "", {pending:true});
      currentAssistant._rawText = (currentAssistant._rawText || "") + (data.text || "");
      scheduleAssistantRender(currentAssistant, false);
      els.messages.scrollTop = els.messages.scrollHeight;
    } else if (type === "activity") {
      appendActivity(data, true);
    } else if (type === "error") {
      if (currentAssistant) {
        currentAssistant.classList.remove("pending");
        currentAssistant.classList.add("message-error");
        if (!currentAssistant._rawText) currentAssistant._rawText = data.message || "Falha na gera\u00e7\u00e3o.";
        flushAssistantRender(currentAssistant, true);
      } else addMessage("assistant", data.message, {error:true});
      toast(data.message, true);
    } else if (type === "done") {
      if (currentAssistant) {
        currentAssistant.classList.remove("pending");
        if (data.message_id != null) currentAssistant.dataset.messageId = String(data.message_id);
        flushAssistantRender(currentAssistant, true);
        attachMessageActions(currentAssistant);
      }
    }
  }

  function parseSSE(buffer) {
    const events = buffer.split(/\r?\n\r?\n/);
    const rest = events.pop() || "";
    for (const block of events) {
      const lines = block.split(/\r?\n/);
      const event = lines.find(line => line.startsWith("event:"))?.slice(6).trim();
      const dataLine = lines.filter(line => line.startsWith("data:")).map(line => line.slice(5).trim()).join("\n");
      if (!event || !dataLine) continue;
      try { handleEvent(event, JSON.parse(dataLine)); } catch (error) { console.error("Noite SSE:", error); }
    }
    return rest;
  }

  let currentAssistant = null;

  function splitThinking(raw, finalize) {
    let remaining = String(raw || "");
    let visible = "";
    const thoughts = [];
    while (remaining) {
      const lower = remaining.toLowerCase();
      const openAt = lower.indexOf("<think>");
      if (openAt < 0) {
        if (!finalize) {
          let hold = 0;
          for (let size = 1; size <= Math.min(6, lower.length); size++) {
            if ("<think>".startsWith(lower.slice(-size))) hold = size;
          }
          visible += remaining.slice(0, remaining.length - hold);
        } else visible += remaining;
        break;
      }
      visible += remaining.slice(0, openAt);
      const contentStart = openAt + 7;
      const closeAt = lower.indexOf("</think>", contentStart);
      if (closeAt < 0) {
        thoughts.push(remaining.slice(contentStart));
        break;
      }
      thoughts.push(remaining.slice(contentStart, closeAt));
      remaining = remaining.slice(closeAt + 8);
    }
    return {visible, thinking: thoughts.join("\n\n")};
  }

  function renderAssistantMessage(article, finalize) {
    if (!article || !article._text) return;
    const parsed = splitThinking(article._rawText || "", Boolean(finalize));
    article._visibleText = parsed.visible;
    article._thinkingText = parsed.thinking;
    article._text.replaceChildren();

    if (parsed.thinking) {
      const details = document.createElement("details");
      details.className = "thinking-container";
      details.open = !finalize;
      const summary = document.createElement("summary");
      summary.className = "thinking-header";
      const icon = document.createElement("span");
      icon.className = "thinking-icon";
      icon.textContent = "✧";
      const label = document.createElement("span");
      label.textContent = finalize ? "Pensamento do agente" : "Pensando...";
      summary.append(icon, label);
      const content = document.createElement("div");
      content.className = "thinking-content";
      content.textContent = parsed.thinking;
      details.append(summary, content);
      article._text.append(details);
    }

    const markdown = document.createElement("div");
    markdown.className = "message-markdown";
    article._markdown = markdown;
    if (!window.marked || typeof window.marked.parse !== "function" || !window.DOMPurify) {
      markdown.textContent = parsed.visible;
    } else {
      try {
        const html = window.marked.parse(parsed.visible, {gfm:true, breaks:true});
        markdown.innerHTML = window.DOMPurify.sanitize(html, {USE_PROFILES:{html:true}});
        if (window.hljs && typeof window.hljs.highlightElement === "function") {
          markdown.querySelectorAll("pre code").forEach(code => window.hljs.highlightElement(code));
        }
        if (finalize) addCodeCopyControls(markdown);
      } catch (error) {
        console.error("Noite Markdown:", error);
        markdown.textContent = parsed.visible;
      }
    }
    if (parsed.visible || !parsed.thinking) article._text.append(markdown);
  }

  const ACTION_ICONS = {
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"></rect><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"></path>',
    retry: '<path d="M20 7v5h-5"></path><path d="M19 12a7 7 0 1 1-2-5l3 5"></path>',
    up: '<path d="M7 10v10H3V10h4Z"></path><path d="M7 10 12 3a2 2 0 0 1 2 2l-1 5h6a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7"></path>',
    down: '<path d="M7 14V4H3v10h4Z"></path><path d="m7 14 5 7a2 2 0 0 0 2-2l-1-5h6a2 2 0 0 0 2-2l-2-7a2 2 0 0 0-2-1H7"></path>',
    fork: '<path d="M6 3v12"></path><path d="M6 7h7a4 4 0 0 1 4 4v1"></path><path d="m14 9 3 3 3-3"></path><path d="M6 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"></path><path d="M6 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"></path>'
  };

  function actionButton(name, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "message-action";
    button.title = label;
    button.setAttribute("aria-label", label);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.7");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.innerHTML = ACTION_ICONS[name];
    svg.setAttribute("aria-hidden", "true");
    button.append(svg);
    return button;
  }

  async function copyPlainText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const field = document.createElement("textarea");
    field.value = value;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.append(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Não foi possível copiar.");
  }

  function attachMessageActions(article) {
    if (!article || article._role !== "assistant" || article.classList.contains("pending")) return;
    const wrap = article.querySelector(".message-content");
    if (!wrap || wrap.querySelector(":scope > .message-actions")) return;
    const bar = document.createElement("div");
    bar.className = "message-actions";

    const copy = actionButton("copy", "Copiar resposta");
    copy.addEventListener("click", async () => {
      try {
        await copyPlainText(article._visibleText ?? article._rawText ?? "");
        copy.classList.add("is-success");
        copy.title = "Copiado";
        toast("Resposta copiada.");
        window.setTimeout(() => { copy.classList.remove("is-success"); copy.title = "Copiar resposta"; }, 1400);
      } catch (error) { toast(error.message || "Falha ao copiar.", true); }
    });
    bar.append(copy);

    if (article._promptText) {
      const retry = actionButton("retry", "Tentar novamente");
      retry.addEventListener("click", () => forkConversation(article, false, true));
      bar.append(retry);
    }

    const positive = actionButton("up", "Boa resposta");
    const negative = actionButton("down", "Resposta ruim");
    positive.classList.toggle("is-selected", article._feedback === "positive");
    negative.classList.toggle("is-selected", article._feedback === "negative");
    async function submitFeedback(rating) {
      const messageId = Number(article.dataset.messageId);
      if (!Number.isSafeInteger(messageId) || messageId <= 0) { toast("ID da mensagem ainda não disponível.", true); return; }
      const nextRating = article._feedback === rating ? null : rating;
      positive.disabled = true; negative.disabled = true;
      try {
        await api("/web/api/feedback", {method:"POST", body:JSON.stringify({message_id:messageId, rating:nextRating})});
        article._feedback = nextRating || "";
        positive.classList.toggle("is-selected", article._feedback === "positive");
        negative.classList.toggle("is-selected", article._feedback === "negative");
        toast(article._feedback ? "Feedback salvo." : "Feedback removido.");
      } catch (error) { toast(error.message || "Falha ao salvar feedback.", true); }
      finally { positive.disabled = false; negative.disabled = false; }
    }
    positive.addEventListener("click", () => submitFeedback("positive"));
    negative.addEventListener("click", () => submitFeedback("negative"));
    bar.append(positive, negative);

    const fork = actionButton("fork", "Ramificar conversa a partir daqui");
    fork.addEventListener("click", () => forkConversation(article, true, false));
    bar.append(fork);
    wrap.append(bar);
  }

  async function forkConversation(target, includeTarget, regenerate) {
    if (state.busy) { toast("Aguarde a geração terminar antes de ramificar."); return; }
    const nodes = Array.from(els.messages.querySelectorAll(":scope > .message"));
    const targetIndex = nodes.indexOf(target);
    if (targetIndex < 0) return;
    let selected = nodes.slice(0, includeTarget ? targetIndex + 1 : targetIndex);
    if (regenerate && selected.length && selected[selected.length - 1]._role === "user") selected = selected.slice(0, -1);
    const messages = selected.map(node => ({
      role: node._role,
      content: node._role === "assistant"
        ? (node._rawText || "")
        : (node._rawText || node.querySelector(".message-content")?.textContent || "")
    })).filter(item => ["user", "assistant"].includes(item.role));
    const sourceId = target._conversationId || state.activeId;
    const prompt = target._promptText || "";
    try {
      const response = await api("/web/api/conversations/" + encodeURIComponent(sourceId) + "/fork", {
        method: "POST",
        body: JSON.stringify({messages})
      });
      const branch = await response.json();
      state.activeId = branch.id;
      await refreshBootstrap();
      await loadMessages(branch.id);
      closeMobilePanels();
      if (regenerate && prompt) await sendMessage(prompt, {conversationId: branch.id});
      else toast("Ramificação criada com o histórico preservado.");
    } catch (error) { toast(error.message || "Não foi possível ramificar.", true); }
  }

  function scheduleAssistantRender(article, finalize) {
    if (!article) return;
    article._finalizeRender = Boolean(article._finalizeRender || finalize);
    if (article._renderFrame) return;
    article._renderFrame = window.requestAnimationFrame(() => {
      article._renderFrame = 0;
      const shouldFinalize = article._finalizeRender;
      article._finalizeRender = false;
      renderAssistantMessage(article, shouldFinalize);
    });
  }

  function flushAssistantRender(article, finalize) {
    if (!article) return;
    if (article._renderFrame) window.cancelAnimationFrame(article._renderFrame);
    article._renderFrame = 0;
    article._finalizeRender = false;
    renderAssistantMessage(article, Boolean(finalize));
  }

  function addCodeCopyControls(container) {
    container.querySelectorAll("pre").forEach(pre => {
      if (pre.querySelector(":scope > .code-toolbar")) return;
      const code = pre.querySelector("code");
      if (!code) return;
      const match = (code.className || "").match(/(?:^|\s)language-([\w+#.-]+)/i);
      const language = match ? match[1] : "c\u00f3digo";
      const toolbar = document.createElement("div");
      toolbar.className = "code-toolbar";
      const label = document.createElement("span");
      label.className = "code-language";
      label.textContent = language;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "code-copy";
      button.textContent = "Copiar";
      button.addEventListener("click", async () => {
        const value = code.textContent || "";
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
          } else {
            const field = document.createElement("textarea");
            field.value = value;
            field.setAttribute("readonly", "");
            field.style.position = "fixed";
            field.style.opacity = "0";
            document.body.append(field);
            field.select();
            const copied = document.execCommand("copy");
            field.remove();
            if (!copied) throw new Error("Copy unavailable");
          }
          button.textContent = "Copiado!";
          button.classList.add("copied");
          window.setTimeout(() => { button.textContent = "Copiar"; button.classList.remove("copied"); }, 1600);
        } catch (error) {
          button.textContent = "Falhou";
          window.setTimeout(() => { button.textContent = "Copiar"; }, 1600);
        }
      });
      toolbar.append(label, button);
      pre.prepend(toolbar);
    });
  }

  async function sendMessage(text, options) {
    options = options || {};
    if (state.busy || !text.trim()) return;
    const requestConversationId = options.conversationId || state.activeId;
    state.busy = true;
    state.abortController = new AbortController();
    els.send.disabled = false;
    els.send.textContent = "■";
    els.send.classList.add("is-stop");
    els.send.setAttribute("aria-label", "Cancelar geração");
    els.send.title = "Cancelar resposta";
    els.input.disabled = false;
    if (!options.userAlreadyVisible) addMessage("user", text.trim());
    currentAssistant = addMessage("assistant", "", {
      pending:true, prompt:text.trim(), conversationId:requestConversationId
    });
    const meta = currentAssistant.querySelector(".message-meta");
    if (meta) meta.textContent = "Noite · pensando";
    try {
      const response = await api("/web/api/chat", {
        method:"POST",
        body:JSON.stringify({message:text.trim(), conversation_id:requestConversationId}),
        signal:state.abortController.signal
      });
      if (!response.body) throw new Error("O navegador não conseguiu abrir o fluxo de resposta.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, {stream:true});
        buffer = parseSSE(buffer);
      }
      buffer += decoder.decode();
      if (buffer.trim()) parseSSE(buffer + "\n\n");
      if (currentAssistant) {
        currentAssistant.classList.remove("pending");
        if (meta) meta.textContent = "Noite";
      }
    } catch (error) {
      const cancelled = error.name === "AbortError";
      const message = cancelled
        ? "Geração interrompida. Você pode continuar a conversa ou tentar novamente."
        : error.message || "Não foi possível concluir a resposta.";
      if (currentAssistant) {
        const hadPartial = Boolean(currentAssistant._rawText);
        currentAssistant.classList.remove("pending");
        currentAssistant.classList.add(cancelled ? "message-cancelled" : "message-error");
        if (meta) meta.textContent = cancelled ? "Noite · interrompida" : "Noite · falha";
        if (!hadPartial) {
          currentAssistant._rawText = message;
          flushAssistantRender(currentAssistant, true);
          if (!cancelled) {
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "message-retry";
            retry.textContent = "↻ Tentar novamente";
            retry.addEventListener("click", () => {
              retry.remove();
              sendMessage(text, {
                conversationId: requestConversationId,
                userAlreadyVisible: true
              });
            });
            currentAssistant.querySelector(".message-content").append(retry);
          }
        } else {
          flushAssistantRender(currentAssistant, true);
          const status = document.createElement("small");
          status.className = "message-status";
          status.textContent = message;
          currentAssistant.querySelector(".message-content").append(status);
        }
      }
      toast(cancelled ? "Geração interrompida." : message, !cancelled);
    } finally {
      state.busy = false;
      state.abortController = null;
      els.send.disabled = false;
      els.send.textContent = "↑";
      els.send.classList.remove("is-stop");
      els.send.setAttribute("aria-label", "Enviar mensagem");
      els.send.title = "Enviar mensagem";
      els.input.disabled = false;
      if (currentAssistant && !currentAssistant.classList.contains("pending")) {
        attachMessageActions(currentAssistant);
      }
      currentAssistant = null;
      await refreshBootstrap().catch(() => {});
      if (state.activeId === requestConversationId) {
        await loadMessages(requestConversationId).catch(() => {});
      }
    }
  }

  async function newConversation() {
    try {
      const response = await api("/web/api/conversations", {method:"POST"});
      const item = await response.json();
      state.activeId = item.id;
      await refreshBootstrap();
      await loadMessages(state.activeId);
      window.dispatchEvent(new CustomEvent("noite:new-chat"));
      els.input.focus();
      closeMobilePanels();
    } catch (error) { toast(error.message, true); }
  }

  function closeMobilePanels() {
    els.sidebar.classList.remove("open");
    els.panel.classList.remove("open");
    els.scrim.classList.remove("show");
  }
  function openPanel(panel) {
    closeMobilePanels();
    panel.classList.add("open");
    els.scrim.classList.add("show");
  }

  async function init() {
    try {
      const response = await fetch("/web/session", {credentials:"same-origin"});
      if (!response.ok) throw new Error("Não foi possível iniciar a sessão local.");
      const session = await response.json();
      state.csrf = session.csrf;
      await refreshBootstrap();
      await loadMessages(state.activeId);
    } catch (error) {
      toast(error.message, true);
      els.sideStatus.textContent = "Falha ao iniciar sessão";
    }
  }

  els.form.addEventListener("submit", event => {
    event.preventDefault();
    if (state.busy) {
      state.abortController?.abort();
      return;
    }
    const value = els.input.value;
    if (!value.trim()) return;
    els.input.value = "";
    els.input.style.height = "auto";
    if (els.count) els.count.textContent = "";
    sendMessage(value);
  });
  // Clipboard helper: insert at the caret and reuse the textarea auto-resize handler.
  const pasteBtn = document.getElementById("paste-btn");
  if (pasteBtn && els.input) {
    pasteBtn.addEventListener("click", async () => {
      try {
        if (!navigator.clipboard || !navigator.clipboard.readText) {
          toast("\u00c1rea de transfer\u00eancia indispon\u00edvel neste contexto.", true);
          return;
        }
        const pasted = await navigator.clipboard.readText();
        if (!pasted) { toast("\u00c1rea de transfer\u00eancia vazia."); return; }
        const input = els.input;
        const start = input.selectionStart ?? input.value.length;
        const end = input.selectionEnd ?? start;
        input.setRangeText(pasted, start, end, "end");
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
        pasteBtn.classList.add("is-success");
        window.setTimeout(() => pasteBtn.classList.remove("is-success"), 1200);
      } catch (error) {
        toast("Permiss\u00e3o da \u00e1rea de transfer\u00eancia negada.", true);
      }
    });
  }

  els.input.addEventListener("input", () => {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(160, els.input.scrollHeight) + "px";
    if (els.count) els.count.textContent = els.input.value.length ? els.input.value.length + "/12000" : "";
  });
  els.input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!state.busy) els.form.requestSubmit();
    }
  });
  $("#new-chat").addEventListener("click", newConversation);
  $("#open-sidebar").addEventListener("click", () => openPanel(els.sidebar));
  $("#close-sidebar").addEventListener("click", closeMobilePanels);
  $("#activity-toggle").addEventListener("click", () => openPanel(els.panel));
  $("#activity-close").addEventListener("click", closeMobilePanels);
  els.scrim.addEventListener("click", closeMobilePanels);
  document.querySelectorAll(".suggestion").forEach(button => {
    button.addEventListener("click", () => {
      els.input.value = button.dataset.prompt || "";
      els.input.focus();
      els.input.dispatchEvent(new Event("input"));
    });
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      newConversation();
    }
    if (event.key === "Escape") closeMobilePanels();
  });
  init();
})();