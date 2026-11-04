(() => {
  "use strict";
  // Pré-integração de voz. O núcleo ainda não tem endpoint de áudio (integrations/openwebui/noite_api.py).
  // Quando o Open WebUI estiver ligado para transcrição (STT), basta:
  //   1. definir voice.available = true;
  //   2. implementar voice.transcribe(blob), que devolve o texto reconhecido;
  //   3. a gravação em si entra no handler do botão abaixo.
  const voice = {
    available: false,
    transcribe: null
  };
  window.NoiteVoice = voice;

  const button = document.querySelector("#mic-btn");
  if (!button) return;

  function notify(message) {
    const node = document.createElement("div");
    node.className = "toast";
    node.textContent = message;
    document.querySelector("#toast-region")?.append(node);
    window.setTimeout(() => node.remove(), 3400);
  }

  button.addEventListener("click", () => {
    if (!voice.available || typeof voice.transcribe !== "function") {
      notify("A voz ainda não está ligada. Ela será integrada pelo Open WebUI.");
      return;
    }
    // Gravação real entra aqui, quando a integração estiver pronta.
  });
})();
