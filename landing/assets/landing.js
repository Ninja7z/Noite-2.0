(() => {
  "use strict";
  const root = document.documentElement;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Alterna entre a landing ("landing") e a área de trabalho ("app").
  function setMode(mode) {
    root.dataset.mode = mode;
    history.replaceState(null, "", mode === "app" ? "#app" : location.pathname + location.search);
    window.scrollTo(0, 0);
    if (mode === "app") document.querySelector("#message-input")?.focus();
  }

  document.querySelectorAll("[data-go]").forEach(element => {
    element.addEventListener("click", event => {
      event.preventDefault();
      setMode(element.dataset.go);
    });
  });

  // Primeira mensagem enviada pela landing: abre a área de trabalho e envia pelo fluxo existente.
  const heroForm = document.querySelector("#hero-composer");
  const heroInput = document.querySelector("#hero-input");
  heroForm?.addEventListener("submit", event => {
    event.preventDefault();
    const text = heroInput.value.trim();
    if (!text) {
      heroInput.focus();
      return;
    }
    heroInput.value = "";
    setMode("app");
    const input = document.querySelector("#message-input");
    input.value = text;
    input.dispatchEvent(new Event("input"));
    document.querySelector("#composer").requestSubmit();
  });

  // Ciclo de trabalho: exemplo ilustrativo, sem dados reais.
  const cycle = document.querySelector("#cycle");
  const trace = document.querySelector("#cycle-trace");
  const card = document.querySelector(".cycle-card");
  const items = cycle ? [...cycle.children] : [];
  const steps = [
    "Janela ativa: Bloco de Notas, sem alterações pendentes.",
    "Pedido entendido: escrever um resumo no documento aberto.",
    "Dois passos. A digitação precisa da sua aprovação.",
    "Aprovado. Digitando o texto no documento.",
    "Conteúdo confirmado na janela. Nada mais foi alterado."
  ];
  let current = 0;

  function showStep(index) {
    current = index;
    items.forEach((item, i) => {
      item.classList.toggle("is-current", i === index);
      item.classList.toggle("is-done", i < index);
    });
    if (trace) trace.textContent = steps[index];
  }

  showStep(0);
  if (!reduceMotion && items.length) {
    let timer = null;
    const start = () => {
      if (!timer) timer = setInterval(() => showStep((current + 1) % items.length), 60000);
    };
    const stop = () => {
      clearInterval(timer);
      timer = null;
    };
    card?.addEventListener("mouseenter", stop);
    card?.addEventListener("mouseleave", start);
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    start();
  }

  // Espelha o status real do modelo (preenchido por app.js) no hero da landing.
  const source = document.querySelector("#model-status");
  const target = document.querySelector("#hero-status");
  const modelName = document.querySelector("#model-name");
  function mirrorStatus() {
    if (!source || !target) return;
    const label = source.querySelector("span:last-child")?.textContent || "";
    const name = modelName?.textContent || "";
    const hasName = name && name !== "Consultando…" && name !== "Não identificado";
    target.classList.toggle("online", source.classList.contains("online"));
    target.classList.toggle("offline", source.classList.contains("offline"));
    target.querySelector(".hero-status-text").textContent = hasName ? label + " · " + name : label;
  }
  const shell = document.querySelector("#workspace");
  if (shell) {
    new MutationObserver(mirrorStatus).observe(shell, {subtree: true, childList: true, characterData: true, attributes: true});
  }
  mirrorStatus();
})();
