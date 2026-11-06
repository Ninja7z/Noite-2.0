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
    } else {
      const wrap = document.createElement("div");
      wrap.className = "message-content";
      wrap.textContent = content;
      article.append(wrap);
    }
    els.messages.append(article);
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
    for (const item of payload.messages) addMessage(item.role === "assistant" ? "assistant" : "user", item.content);
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
      currentAssistant._text.textContent += data.text || "";
      els.messages.scrollTop = els.messages.scrollHeight;
    } else if (type === "activity") {
      appendActivity(data, true);
    } else if (type === "error") {
      if (currentAssistant) {
        currentAssistant.classList.remove("pending");
        currentAssistant.classList.add("message-error");
        if (!currentAssistant._text.textContent) currentAssistant._text.textContent = data.message;
      } else addMessage("assistant", data.message, {error:true});
      toast(data.message, true);
    } else if (type === "done") {
      if (currentAssistant) currentAssistant.classList.remove("pending");
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
    currentAssistant = addMessage("assistant", "", {pending:true});
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
        const hadPartial = Boolean(currentAssistant._text.textContent);
        currentAssistant.classList.remove("pending");
        currentAssistant.classList.add(cancelled ? "message-cancelled" : "message-error");
        if (meta) meta.textContent = cancelled ? "Noite · interrompida" : "Noite · falha";
        if (!hadPartial) {
          currentAssistant._text.textContent = message;
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
      await refreshBootstrap();      await loadMessages(state.activeId);
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