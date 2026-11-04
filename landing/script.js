(() => {
  const localAppLink = document.querySelector(".local-app-link");
  if (localAppLink && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    localAppLink.href = window.location.protocol + "//" + window.location.hostname + ":8766/app/";
    localAppLink.hidden = false;
  }

  const menuButton = document.querySelector(".menu-toggle");
  const navLinks = document.querySelector(".nav-links");

  if (menuButton && navLinks) {
    menuButton.addEventListener("click", () => {
      const open = menuButton.getAttribute("aria-expanded") !== "true";
      menuButton.setAttribute("aria-expanded", String(open));
      menuButton.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
      navLinks.classList.toggle("is-open", open);
    });
    navLinks.querySelectorAll("a").forEach(link => {
      link.addEventListener("click", () => {
        menuButton.setAttribute("aria-expanded", "false");
        menuButton.setAttribute("aria-label", "Abrir menu");
        navLinks.classList.remove("is-open");
      });
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        menuButton.setAttribute("aria-expanded", "false");
        menuButton.setAttribute("aria-label", "Abrir menu");
        navLinks.classList.remove("is-open");
        menuButton.focus();
      }
    });
  }

  const demos = {
    files: {
      prompt: "Encontre os arquivos mais pesados da minha pasta Downloads.",
      title: "Plano de leitura",
      description: "Vou analisar os itens da pasta Downloads e ordenar os maiores primeiro.",
      command: 'workspace.list_files("Downloads")',
      count: "3 resultados de exemplo",
      rows: [
        ["ZIP", "backup-projeto.zip", "890 MB", "zip"],
        ["DIR", "node_modules", "1,2 GB", "folder"],
        ["CRX", "chrome_dump.crx", "2,4 GB", "file"]
      ],
      footer: "Nenhum arquivo foi alterado"
    },
    project: {
      prompt: "Me explica como esse projeto está organizado.",
      title: "Leitura do workspace",
      description: "Vou mapear as pastas principais e resumir a estrutura sem modificar nenhum arquivo.",
      command: 'workspace.inspect(".")',
      count: "3 áreas de exemplo",
      rows: [
        ["SRC", "src/noite", "Core", "file"],
        ["TST", "tests", "Testes", "folder"],
        ["DOC", "docs", "Documentação", "zip"]
      ],
      footer: "Inspeção somente de leitura"
    }
  };

  const prompt = document.getElementById("demo-prompt");
  const title = document.getElementById("action-title");
  const description = document.getElementById("action-description");
  const command = document.getElementById("demo-command");
  const results = document.getElementById("demo-results");
  const tabs = document.querySelectorAll(".demo-tab");
  const footer = document.querySelector(".action-footer span:first-child");
  const count = document.querySelector(".result-heading span");

  function renderDemo(key) {
    const demo = demos[key];
    if (!demo || !prompt || !results) return;
    prompt.textContent = demo.prompt;
    title.textContent = demo.title;
    description.textContent = demo.description;
    command.textContent = demo.command;
    footer.innerHTML = '<i></i> ' + demo.footer;
    count.textContent = demo.count;
    results.querySelectorAll(".file-row").forEach(row => row.remove());
    demo.rows.forEach(([type, name, size, kind]) => {
      const row = document.createElement("div");
      row.className = "file-row";
      const typeEl = document.createElement("span");
      typeEl.className = "file-type " + kind;
      typeEl.textContent = type;
      const nameEl = document.createElement("span");
      nameEl.className = "file-name";
      nameEl.textContent = name;
      const sizeEl = document.createElement("b");
      sizeEl.textContent = size;
      row.append(typeEl, nameEl, sizeEl);
      results.append(row);
    });
    tabs.forEach(tab => {
      const active = tab.dataset.demo === key;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-pressed", String(active));
    });
  }

  tabs.forEach(tab => tab.addEventListener("click", () => renderDemo(tab.dataset.demo)));
  renderDemo("files");

  const revealTargets = document.querySelectorAll(".principle-card, .capability-card, .architecture-stack");
  if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealTargets.forEach(target => {
      target.classList.add("reveal");
      observer.observe(target);
    });
  }
})();
