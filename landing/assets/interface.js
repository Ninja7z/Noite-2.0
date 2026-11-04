(() => {
  "use strict";
  const chat = document.querySelector(".chat-column");
  const nav = [...document.querySelectorAll(".workspace-link")];
  const title = document.querySelector("#current-title");
  const newChatSmall = document.querySelector("#new-chat-small");
  const views = {
    chat: {title:"Nova conversa"},
    activity: {title:"Atividades"},
    projects: {title:"Projetos", icon:"▦", heading:"Projetos", description:"Um espaço para reunir arquivos, conversas e contexto de cada trabalho. A estrutura visual está sendo preparada antes da integração com os dados reais.", state:"ESTRUTURA EM DESENVOLVIMENTO"},
    memory: {title:"Memória", icon:"◈", heading:"Memória", description:"Consulta e organização das memórias persistentes da Noite. Esta área será conectada ao armazenamento local e à recuperação contextual.", state:"INTEGRAÇÃO PENDENTE"},
    tools: {title:"Ferramentas", icon:"⌘", heading:"Ferramentas", description:"Agentes, ferramentas, integrações e capacidades disponíveis para a Noite. A interface será ligada às permissões e ao catálogo real de recursos.", state:"INTEGRAÇÃO PENDENTE"},
    settings: {title:"Configurações", icon:"⚙", heading:"Configurações", description:"Modelos, comportamento, permissões, conexões e preferências da interface. Os controles só serão exibidos quando estiverem ligados às configurações reais.", state:"ESTRUTURA EM DESENVOLVIMENTO"}
  };
  let placeholder;
  let lastContentView = "chat";
  let lastChatTitle = title?.textContent || "Nova conversa";
  function showView(key) {
    const view = views[key];
    if (!view) return;
    document.querySelector("#sidebar")?.classList.remove("open");
    document.querySelector("#activity-panel")?.classList.remove("open");
    document.querySelector("#mobile-scrim")?.classList.remove("show");
    nav.forEach(button => button.classList.toggle("is-active", button.dataset.view === key));
    if (key === "activity") {
      nav.forEach(button => button.classList.remove("is-active"));
      document.querySelector('[data-view="activity"]')?.classList.add("is-active");
      document.querySelector("#activity-panel")?.classList.add("open");
      document.querySelector("#mobile-scrim")?.classList.add("show");
      return;
    }
    lastContentView = key;
    chat.dataset.view = key;
    if (key === "chat") {
      placeholder?.remove();
      placeholder = null;
      if (title) title.textContent = lastChatTitle;
      return;
    }
    if (!placeholder) {
      placeholder = document.createElement("section");
      placeholder.className = "workspace-placeholder";
      chat.prepend(placeholder);
    }
    placeholder.innerHTML = '<div class="placeholder-icon"></div><h1></h1><p></p><span class="placeholder-state"></span>';
    placeholder.querySelector(".placeholder-icon").textContent = view.icon;
    placeholder.querySelector("h1").textContent = view.heading;
    placeholder.querySelector("p").textContent = view.description;
    placeholder.querySelector(".placeholder-state").textContent = view.state;
    if (title) title.textContent = view.title;
  }
  // Clicar de novo numa área já ativa (Atividades, Projetos...) volta para o chat.
  nav.forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.view;
    if (key !== "chat" && button.classList.contains("is-active")) {
      showView("chat");
      return;
    }
    showView(key);
  }));
  // Barra lateral: "pinned" (fixa) ou "auto" (some sozinha; aparece ao encostar o mouse na faixa de ícones).
  const html = document.documentElement;
  const sidebarEl = document.querySelector("#sidebar");
  const railEl = document.querySelector(".rail");
  const sidebarToggle = document.querySelector("#sidebar-toggle");
  let hideTimer = null;
  function revealSidebar() {
    clearTimeout(hideTimer);
    if (html.dataset.sidebar === "auto") sidebarEl?.classList.add("reveal");
  }
  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => sidebarEl?.classList.remove("reveal"), 180);
  }
  function setSidebarMode(mode) {
    html.dataset.sidebar = mode;
    sidebarEl?.classList.remove("reveal");
    sidebarToggle?.setAttribute("aria-pressed", String(mode === "auto"));
  }
  sidebarToggle?.addEventListener("click", () => {
    setSidebarMode(html.dataset.sidebar === "auto" ? "pinned" : "auto");
  });
  [railEl, sidebarEl].forEach(element => {
    element?.addEventListener("mouseenter", revealSidebar);
    element?.addEventListener("mouseleave", scheduleHide);
  });

  // Painel de atividade: "pinned" (acoplado) ou "auto" (some sozinho; aparece ao encostar na borda direita).
  const activityEl = document.querySelector("#activity-panel");
  const activityPin = document.querySelector("#activity-pin");
  const activityEdge = document.querySelector("#activity-edge");
  let activityTimer = null;
  function revealActivity() {
    clearTimeout(activityTimer);
    if (html.dataset.activity === "auto") activityEl?.classList.add("open");
  }
  function scheduleHideActivity() {
    clearTimeout(activityTimer);
    if (html.dataset.activity !== "auto") return;
    activityTimer = setTimeout(() => activityEl?.classList.remove("open"), 180);
  }
  function setActivityMode(mode) {
    html.dataset.activity = mode;
    activityPin?.setAttribute("aria-pressed", String(mode === "auto"));
  }
  activityPin?.addEventListener("click", () => {
    setActivityMode(html.dataset.activity === "auto" ? "pinned" : "auto");
  });
  [activityEdge, activityEl].forEach(element => {
    element?.addEventListener("mouseenter", revealActivity);
    element?.addEventListener("mouseleave", scheduleHideActivity);
  });

  newChatSmall?.addEventListener("click", () => {
    showView("chat");
    document.querySelector("#new-chat")?.click();
  });
  document.querySelector("#new-chat")?.addEventListener("click", () => showView("chat"));
  document.querySelector("#activity-toggle")?.addEventListener("click", () => {
    nav.forEach(button => button.classList.toggle("is-active", button.dataset.view === "activity"));
  });
  function restoreContentNav() {
    nav.forEach(button => button.classList.toggle("is-active", button.dataset.view === lastContentView));
  }
  document.querySelector("#activity-close")?.addEventListener("click", restoreContentNav);
  document.querySelector("#mobile-scrim")?.addEventListener("click", restoreContentNav);
  document.querySelector("#composer")?.addEventListener("submit", () => showView("chat"));
  document.querySelector("#conversation-list")?.addEventListener("click", event => {
    if (event.target.closest(".conversation-item")) showView("chat");
  });
  const observer = new MutationObserver(() => {
    if (chat.dataset.view === "chat" && title) lastChatTitle = title.textContent;
  });
  if (title) observer.observe(title, {childList:true,subtree:true,characterData:true});
  chat.dataset.view = "chat";
})();