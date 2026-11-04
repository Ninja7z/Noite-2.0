(() => {
  "use strict";
  // Textos dinâmicos: digitam e apagam em ciclo. Com "reduzir movimento", mostram o texto atual sem animação.
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Contexto vindo da própria Noite (app.js dispara "noite:bootstrap" a cada atualização).
  const ctx = {userName: "", conversations: [], activeTitle: "", modelOk: false, weather: null, weatherTried: false};
  window.addEventListener("noite:bootstrap", event => {
    const data = event.detail || {};
    ctx.userName = data.user_name || "";
    ctx.conversations = data.conversations || [];
    const active = ctx.conversations.find(item => item.id === data.active_conversation_id);
    ctx.activeTitle = active ? String(active.title || "") : "";
    const model = data.model || {};
    ctx.modelOk = model.server === "up" && model.model_installed === true;
  });

  // Digita/apaga em ciclo; retorna um avanço imediato para eventos como "Novo chat".
  function cycleText(getPhrases, write, options) {
    const opts = Object.assign({typeSpeed: 60, erase: 30, pause: 60000, gap: 450}, options || {});
    let index = 0, pos = 0, deleting = false, timer = null;
    const schedule = delay => { clearTimeout(timer); timer = window.setTimeout(step, delay); };
    const step = () => {
      const phrases = getPhrases();
      if (!phrases.length) { schedule(1000); return; }
      if (index >= phrases.length) index = 0;
      const phrase = phrases[index];
      if (reduceMotion) { write(phrase); schedule(5000); return; }
      if (!deleting) {
        pos += 1; write(phrase.slice(0, pos));
        if (pos >= phrase.length) { deleting = true; schedule(opts.pause); }
        else schedule(opts.typeSpeed);
      } else {
        pos -= 1; write(phrase.slice(0, pos));
        if (pos <= 0) { deleting = false; index = (index + 1) % phrases.length; schedule(opts.gap); }
        else schedule(opts.erase);
      }
    };
    const advance = () => {
      const phrases = getPhrases();
      if (!phrases.length) return;
      index = (index + 1) % phrases.length;
      const phrase = phrases[index];
      pos = phrase.length; deleting = true; write(phrase);
      schedule(opts.pause);
    };
    step();
    return advance;
  }

  // Saudação, nome e horário vêm de agora e do Windows.
  function greeting(now) {
    const hour = now.getHours();
    if (hour >= 5 && hour < 12) return "Bom dia";
    if (hour >= 12 && hour < 18) return "Boa tarde";
    return "Boa noite";
  }
  function displayName() {
    const name = ctx.userName || "";
    return name ? name.charAt(0).toUpperCase() + name.slice(1) : "";
  }
  function clock(now) {
    return now.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});
  }

  function titlePhrases() {
    const now = new Date();
    const who = displayName();
    const list = ["O que vamos fazer?", greeting(now) + (who ? ", " + who : "") + ".", "Pronta quando você estiver.", "Qual é o próximo passo?", "Vamos tirar uma ideia do papel?", "Pode mandar, estou aqui.", "Seu próximo projeto começa agora.", "Vamos resolver algo juntos?", "No que posso ajudar agora?", "Um novo chat, novas possibilidades.", "Vamos nessa?"];
    if (ctx.activeTitle && ctx.activeTitle !== "Nova conversa") {
      const short = ctx.activeTitle.length > 40 ? ctx.activeTitle.slice(0, 40) + "…" : ctx.activeTitle;
      list.push("Retomar \u201c" + short + "\u201d?");
    }
    return list;
  }

  const openingStarts = [
    "Vamos", "Bora", "Pronta para", "Que tal", "Hora de", "Podemos", "Seu próximo passo é", "Que ideia vamos", "Vamos juntos", "É hora de"
  ];
  const openingActions = [
    "tirar uma ideia do papel", "resolver uma tarefa", "organizar seus projetos", "explorar uma possibilidade",
    "construir algo novo", "dar vida ao seu plano", "destravar aquele problema", "transformar planos em ação",
    "começar por aqui", "fazer acontecer", "pensar em uma solução", "colocar a mão na massa",
    "avançar no projeto", "simplificar seu dia", "encontrar um caminho", "criar algo útil",
    "investigar esse assunto", "dar o próximo passo", "deixar tudo mais claro", "fazer essa ideia crescer"
  ];
  const openingEnds = ["?", " hoje?", " agora?", " juntos?", " por aqui?", " com calma?", " de um jeito simples?"];
  function titlePhrases() {
    const now = new Date();
    const who = displayName();
    const list = [
      "O que vamos fazer?", greeting(now) + (who ? ", " + who : "") + ".",
      "Pronta quando você estiver.", "Qual é o próximo passo?", "Pode mandar, estou aqui.",
      "No que posso ajudar agora?", "Vamos nessa?", "Um novo chat, novas possibilidades."
    ];
    for (const start of openingStarts) for (const action of openingActions) for (const end of openingEnds) list.push(start + " " + action + end);
    if (ctx.activeTitle && ctx.activeTitle !== "Nova conversa") {
      const short = ctx.activeTitle.length > 40 ? ctx.activeTitle.slice(0, 40) + "…" : ctx.activeTitle;
      list.push("Retomar “" + short + "”?");
    }
    return list;
  }

  const subTemplates = [
    now => "Agora são " + clock(now) + ".",
    now => "Seu horário local: " + clock(now) + ".",
    now => "Hoje é " + now.toLocaleDateString("pt-BR", {weekday:"long", day:"2-digit", month:"long"}) + ".",
    () => ctx.modelOk ? "Unite está pronto para uso." : "Unite está preparando o ambiente.",
    () => ctx.conversations.length ? ctx.conversations.length + (ctx.conversations.length === 1 ? " conversa no histórico." : " conversas no histórico.") : "Seu histórico começa aqui.",
    () => ctx.weather ? "Agora, " + ctx.weather.temperature + "°C em " + ctx.weather.place + "." : "Clima local disponível se você permitir a localização."
  ];
  const subOpeners = ["Estou por aqui", "Seu espaço está pronto", "Pode começar", "Vamos organizar as ideias", "Tudo em sintonia", "Um novo começo", "Seu assistente está à disposição", "Vamos dar forma ao plano", "A conversa está aberta", "Seu próximo passo começa aqui"];
  const subClosers = ["para ajudar.", "quando quiser.", "sem pressa.", "vamos nessa.", "com você.", "é só escrever.", "vamos fazer acontecer.", "pronta para começar.", "pode mandar.", "vamos nessa juntos."];
  function subPhrases() {
    const now = new Date();
    const list = subTemplates.map(template => template(now));
    for (const opener of subOpeners) for (const closer of subClosers) list.push(opener + ", " + closer);
    return [...new Set(list)];
  }

  const welcomeTitle = document.querySelector(".welcome-title");
  if (welcomeTitle) {
    const advanceTitle = cycleText(titlePhrases, text => { welcomeTitle.textContent = text; }, {pause: 60000});
    window.addEventListener("noite:new-chat", advanceTitle);
  }
  const welcomeSub = document.querySelector(".welcome-sub");
  if (welcomeSub) {
    const advanceSub = cycleText(subPhrases, text => { welcomeSub.textContent = text; }, {pause: 60000});
    window.addEventListener("noite:new-chat", advanceSub);
    welcomeSub.title = "Clique para permitir a localização e consultar o clima atual.";
    welcomeSub.style.cursor = "pointer";
    welcomeSub.addEventListener("click", async () => {
      if (ctx.weather || ctx.weatherTried || !navigator.geolocation) return;
      ctx.weatherTried = true;
      welcomeSub.textContent = "Consultando o clima com sua permissão…";
      navigator.geolocation.getCurrentPosition(async position => {
        try {
          const {latitude, longitude} = position.coords;
          const weatherResponse = await fetch("https://api.open-meteo.com/v1/forecast?latitude=" + latitude + "&longitude=" + longitude + "&current=temperature_2m&timezone=auto");
          if (!weatherResponse.ok) throw new Error("weather");
          const weatherData = await weatherResponse.json();
          const geoResponse = await fetch("https://geocoding-api.open-meteo.com/v1/reverse?latitude=" + latitude + "&longitude=" + longitude + "&language=pt&format=json");
          const geoData = geoResponse.ok ? await geoResponse.json() : {};
          const place = geoData.results?.[0]?.name || "sua região";
          ctx.weather = {temperature: Math.round(weatherData.current.temperature_2m), place};
          advanceSub();
        } catch {
          ctx.weatherTried = false;
          welcomeSub.textContent = "Não consegui consultar o clima agora. Tente novamente.";
        }
      }, () => {
        ctx.weatherTried = false;
        welcomeSub.textContent = "Localização não autorizada. Clique para tentar novamente.";
      }, {timeout:10000, maximumAge:300000});
    });
  }

  // Status discreto da barra lateral: continua mudando enquanto ela estiver aberta.
  const sideStatus = document.querySelector("#side-status");
  if (sideStatus) {
    const sidebarLines = [
      "Unite está pronto para uso.", "Pronta para conversar.", "Pode mandar sua próxima ideia.",
      "Aguardando seu próximo comando.", "Tudo pronto por aqui.", "Vamos continuar?",
      "Seu espaço está preparado.", "Pode começar quando quiser.", "Noite está à disposição.",
      "Vamos transformar ideia em ação.", "Pronta para ajudar.", "Seu próximo passo começa aqui."
    ];
    cycleText(() => ctx.modelOk ? sidebarLines : [sideStatus.textContent || "Conectando ao motor local."],
      text => { if (ctx.modelOk) sideStatus.textContent = text; },
      {typeSpeed: 35, erase: 20, pause: 7000, gap: 250});
  }

  // Campo de mensagem: o placeholder vai mudando com exemplos.
  const input = document.querySelector("#message-input");
  if (input) {
    const examples = [
      "Peça qualquer coisa à Noite",
      "Resuma os arquivos desta pasta",
      "Explique este erro do terminal",
      "Organize os meus projetos",
      "Ajude a revisar este código"
    ];
    cycleText(() => examples, text => input.setAttribute("placeholder", text), {pause: 60000});
  }

  // Botão "Novo chat": o rótulo também alterna.
  const newChatLabel = document.querySelector("#new-chat-label");
  if (newChatLabel) {
    const labels = ["Novo chat", "Começar algo novo", "Nova tarefa"];
    cycleText(() => labels, text => { newChatLabel.textContent = text; }, {typeSpeed: 70, erase: 35, pause: 7000});
  }
})();
