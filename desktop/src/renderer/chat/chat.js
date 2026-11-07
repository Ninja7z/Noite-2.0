/**
 * Noite Desktop 2.0 - Lógica do Chat Codex para Desktop.
 */
'use strict';

document.addEventListener('DOMContentLoaded', async () => {
  // Elementos do DOM
  const btnMinimize = document.getElementById('btnMinimize');
  const btnMaximize = document.getElementById('btnMaximize');
  const btnClose = document.getElementById('btnClose');
  const conversationsList = document.getElementById('conversationsList');
  const btnNewChat = document.getElementById('btnNewChat');
  const messagesContainer = document.getElementById('messagesContainer');
  const emptyPlaceholder = document.getElementById('emptyPlaceholder');
  const promptInput = document.getElementById('promptInput');
  const btnSend = document.getElementById('btnSend');
  const btnStop = document.getElementById('btnStop');
  const btnPaste = document.getElementById('btnPaste');
  const activityStrip = document.getElementById('activityStrip');
  const activityText = document.getElementById('activityText');
  const backendStatusDot = document.querySelector('.backend-status-dot');
  const backendStatusName = document.getElementById('backendStatusName');
  const offlineBanner = document.getElementById('offlineBanner');
  const btnRetryConnection = document.getElementById('btnRetryConnection');
  const toastEl = document.getElementById('toast');

  // Estado da interface
  let activeConversationId = 'default';
  let isGenerating = false;
  let activeAssistantRow = null;
  let activeAssistantBubble = null;
  let activeThinkingContent = null;
  let currentRawText = '';
  let currentThinkingText = '';

  // Configuração do Marked com sanitização
  if (typeof marked !== 'undefined') {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
          try {
            return hljs.highlight(code, { language: lang }).value;
          } catch (_) {}
        }
        return code;
      }
    });
  }

  function showToast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add('is-visible');
    setTimeout(() => {
      toastEl.classList.remove('is-visible');
    }, 2400);
  }

  // ==========================================
  // 1. Controles da Janela do Windows
  // ==========================================
  if (window.noiteDesktop && window.noiteDesktop.window) {
    btnMinimize?.addEventListener('click', () => window.noiteDesktop.window.minimize());
    btnMaximize?.addEventListener('click', () => window.noiteDesktop.window.maximize());
    btnClose?.addEventListener('click', () => window.noiteDesktop.window.close());
  }

  // ==========================================
  // 2. Auto-redimensionamento do Textarea
  // ==========================================
  function autoResizeTextarea() {
    promptInput.style.height = 'auto';
    promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
  }
  promptInput.addEventListener('input', autoResizeTextarea);

  btnPaste?.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text) return;
      const start = promptInput.selectionStart;
      const end = promptInput.selectionEnd;
      promptInput.value = promptInput.value.slice(0, start) + text + promptInput.value.slice(end);
      promptInput.selectionStart = promptInput.selectionEnd = start + text.length;
      promptInput.focus();
      autoResizeTextarea();
      showToast('Conteúdo colado!');
    } catch (_) {
      showToast('Permissão da área de transferência negada.');
    }
  });

  // ==========================================
  // 3. Verificação do Backend
  // ==========================================
  async function checkBackend() {
    if (!window.noiteDesktop || !window.noiteDesktop.system) return;
    try {
      const status = await window.noiteDesktop.system.getStatus();
      if (status && status.online) {
        backendStatusDot?.classList.remove('is-down');
        backendStatusName.textContent = 'Backend Conectado';
        offlineBanner?.classList.add('is-hidden');
      } else {
        backendStatusDot?.classList.add('is-down');
        backendStatusName.textContent = 'Backend Offline';
        offlineBanner?.classList.remove('is-hidden');
      }
    } catch (_) {
      backendStatusDot?.classList.add('is-down');
      backendStatusName.textContent = 'Backend Offline';
      offlineBanner?.classList.remove('is-hidden');
    }
  }

  btnRetryConnection?.addEventListener('click', async () => {
    showToast('Tentando reconexão...');
    await checkBackend();
    await loadConversations();
  });

  // ==========================================
  // 4. Conversas e Histórico
  // ==========================================
  async function loadConversations() {
    if (!window.noiteDesktop || !window.noiteDesktop.chat) return;
    try {
      const res = await window.noiteDesktop.chat.getConversations();
      const list = Array.isArray(res) ? res : (res && res.conversations ? res.conversations : []);
      renderConversationsList(list);
    } catch (_) {}
  }

  function renderConversationsList(list) {
    if (!conversationsList) return;
    conversationsList.innerHTML = '';

    if (!list.length) {
      list = [{ id: 'default', title: 'Conversa Principal' }];
    }

    list.forEach(item => {
      const el = document.createElement('div');
      el.className = `conversation-item ${item.id === activeConversationId ? 'is-active' : ''}`;
      el.textContent = item.title || 'Conversa sem título';
      el.title = item.title || '';
      el.addEventListener('click', () => switchConversation(item.id));
      conversationsList.appendChild(el);
    });
  }

  async function switchConversation(id) {
    if (activeConversationId === id) return;
    activeConversationId = id;
    if (window.noiteDesktop && window.noiteDesktop.chat && window.noiteDesktop.chat.selectConversation) {
      try {
        await window.noiteDesktop.chat.selectConversation(id);
      } catch (_) {}
    }
    await loadConversations();
    await loadHistory(id);
  }

  btnNewChat?.addEventListener('click', async () => {
    const newId = `conv_${Date.now()}`;
    activeConversationId = newId;
    if (window.noiteDesktop && window.noiteDesktop.chat && window.noiteDesktop.chat.selectConversation) {
      try {
        await window.noiteDesktop.chat.selectConversation(newId);
      } catch (_) {}
    }
    messagesContainer.innerHTML = '';
    emptyPlaceholder?.classList.remove('is-hidden');
    loadConversations();
    promptInput.focus();
  });

  async function loadHistory(convId) {
    messagesContainer.innerHTML = '';
    emptyPlaceholder?.classList.add('is-hidden');

    try {
      const res = await window.noiteDesktop.chat.getHistory(convId);
      const messages = res && res.messages ? res.messages : [];
      if (!messages.length) {
        emptyPlaceholder?.classList.remove('is-hidden');
        return;
      }

      messages.forEach(msg => {
        if (msg.role === 'user') {
          appendUserMessage(msg.content);
        } else {
          const msgId = msg.id || msg.message_id || null;
          appendAssistantMessage(msg.content, msgId, msg.rating);
        }
      });
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (_) {}
  }

  // ==========================================
  // 5. Renderização de Mensagens
  // ==========================================
  function appendUserMessage(text) {
    emptyPlaceholder?.classList.add('is-hidden');
    const row = document.createElement('div');
    row.className = 'message-row is-user';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function appendAssistantMessage(content = '', messageId = null, initialRating = null) {
    emptyPlaceholder?.classList.add('is-hidden');
    const row = document.createElement('div');
    row.className = 'message-row is-assistant';
    if (messageId) row.dataset.messageId = String(messageId);

    const header = document.createElement('div');
    header.className = 'assistant-header';
    header.innerHTML = `
      <div class="assistant-avatar">N</div>
      <div class="assistant-name">Noite</div>
    `;
    row.appendChild(header);

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble markdown-body';
    renderMarkdownContent(bubble, content);
    row.appendChild(bubble);

    // Toolbar de Ações / Feedback
    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const btnUp = document.createElement('button');
    btnUp.className = `action-btn btn-thumbs-up ${initialRating === 'positive' ? 'is-active-up' : ''}`;
    btnUp.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg> Útil`;

    const btnDown = document.createElement('button');
    btnDown.className = `action-btn btn-thumbs-down ${initialRating === 'negative' ? 'is-active-down' : ''}`;
    btnDown.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/></svg>`;

    const btnCopy = document.createElement('button');
    btnCopy.className = 'action-btn btn-copy';
    btnCopy.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copiar`;

    btnCopy.addEventListener('click', async () => {
      await navigator.clipboard.writeText(content);
      showToast('Resposta copiada!');
    });

    // Handler de feedback persistente com debounce e guard contra cliques concorrentes
    let isSubmittingFeedback = false;

    async function handleVote(targetRating) {
      if (isSubmittingFeedback) return;

      const mid = Number(row.dataset.messageId);
      if (!Number.isSafeInteger(mid) || mid <= 0) {
        showToast('ID da mensagem não disponível ainda.');
        return;
      }

      const isUpSelected = btnUp.classList.contains('is-active-up');
      const isDownSelected = btnDown.classList.contains('is-active-down');

      let nextRating = targetRating;
      if (targetRating === 'positive' && isUpSelected) nextRating = null;
      if (targetRating === 'negative' && isDownSelected) nextRating = null;

      isSubmittingFeedback = true;
      btnUp.disabled = true;
      btnDown.disabled = true;

      try {
        await window.noiteDesktop.chat.submitFeedback(mid, nextRating);
        btnUp.classList.toggle('is-active-up', nextRating === 'positive');
        btnDown.classList.toggle('is-active-down', nextRating === 'negative');
        showToast(nextRating ? 'Feedback registrado.' : 'Feedback removido.');
      } catch (err) {
        // Sanitiza erros para não expor tokens ou detalhes sensíveis
        const rawMsg = err ? (err.message || String(err)) : 'Erro na requisição.';
        const cleanMsg = rawMsg.replace(/([a-zA-Z0-9_-]{24,})/g, '[REDACTED]');
        showToast(`Erro ao registrar feedback: ${cleanMsg}`);
      } finally {
        isSubmittingFeedback = false;
        btnUp.disabled = false;
        btnDown.disabled = false;
      }
    }

    btnUp.addEventListener('click', () => handleVote('positive'));
    btnDown.addEventListener('click', () => handleVote('negative'));

    actions.appendChild(btnUp);
    actions.appendChild(btnDown);
    actions.appendChild(btnCopy);
    row.appendChild(actions);

    messagesContainer.appendChild(row);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return { row, bubble };
  }

  function renderMarkdownContent(container, text) {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
      const rawHtml = marked.parse(text);
      container.innerHTML = DOMPurify.sanitize(rawHtml);
      // Injeta toolbars nos blocos de código
      container.querySelectorAll('pre code').forEach(block => {
        const pre = block.parentElement;
        if (!pre.querySelector('.code-toolbar')) {
          const lang = block.className.replace('language-', '') || 'código';
          const toolbar = document.createElement('div');
          toolbar.className = 'code-toolbar';
          toolbar.innerHTML = `
            <span>${lang}</span>
            <button class="copy-code-btn">Copiar</button>
          `;
          toolbar.querySelector('.copy-code-btn').addEventListener('click', async () => {
            await navigator.clipboard.writeText(block.textContent);
            showToast('Código copiado!');
          });
          pre.insertBefore(toolbar, block);
        }
      });
    } else {
      container.textContent = text;
    }
  }

  // ==========================================
  // 6. Envio de Mensagem e Streaming
  // ==========================================
  async function sendMessage() {
    const text = promptInput.value.trim();
    if (!text || isGenerating) return;

    isGenerating = true;
    promptInput.value = '';
    autoResizeTextarea();
    btnSend.classList.add('is-hidden');
    btnStop.classList.remove('is-hidden');

    appendUserMessage(text);

    // Prepara bolha do assistente em streaming
    const res = appendAssistantMessage('');
    activeAssistantRow = res.row;
    activeAssistantBubble = res.bubble;
    currentRawText = '';
    currentThinkingText = '';
    activeThinkingContent = null;

    try {
      await window.noiteDesktop.chat.sendMessage(activeConversationId, text);
    } catch (err) {
      isGenerating = false;
      btnSend.classList.remove('is-hidden');
      btnStop.classList.remove('is-hidden');
      renderMarkdownContent(activeAssistantBubble, `⚠️ **Erro:** ${err.message}`);
    }
  }

  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnSend?.addEventListener('click', sendMessage);

  btnStop?.addEventListener('click', async () => {
    if (window.noiteDesktop && window.noiteDesktop.chat) {
      await window.noiteDesktop.chat.cancelMessage(activeConversationId);
      finishGeneration();
      showToast('Geração cancelada.');
    }
  });

  function finishGeneration(doneData = null) {
    isGenerating = false;
    btnSend.classList.remove('is-hidden');
    btnStop.classList.add('is-hidden');
    activityStrip?.classList.add('is-hidden');

    if (doneData && doneData.message_id && activeAssistantRow) {
      activeAssistantRow.dataset.messageId = String(doneData.message_id);
    }
    loadConversations();
  }

  // ==========================================
  // 7. Inscrição em Listeners IPC de Streaming
  // ==========================================
  if (window.noiteDesktop && window.noiteDesktop.chat) {
    window.noiteDesktop.chat.onChunk((data) => {
      if (data.conversationId !== activeConversationId || !activeAssistantBubble) return;
      currentRawText += data.text;
      renderMarkdownContent(activeAssistantBubble, currentRawText);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });

    window.noiteDesktop.chat.onThinking((data) => {
      if (data.conversationId !== activeConversationId || !activeAssistantRow) return;
      currentThinkingText += data.text;

      if (!activeThinkingContent) {
        const details = document.createElement('details');
        details.className = 'thinking-box';
        details.open = true;
        details.innerHTML = `<summary>Pensamento da Noite</summary><div class="thinking-content"></div>`;
        activeAssistantRow.insertBefore(details, activeAssistantBubble);
        activeThinkingContent = details.querySelector('.thinking-content');
      }
      activeThinkingContent.textContent = currentThinkingText;
    });

    window.noiteDesktop.chat.onActivity((data) => {
      if (activityStrip && activityText && data.activity) {
        activityStrip.classList.remove('is-hidden');
        activityText.textContent = data.activity.summary || 'Processando ferramentas...';
      }
    });

    window.noiteDesktop.chat.onDone((data) => {
      if (data.conversationId === activeConversationId) {
        finishGeneration(data);
      }
    });

    window.noiteDesktop.chat.onError((data) => {
      if (data.conversationId === activeConversationId && activeAssistantBubble) {
        renderMarkdownContent(activeAssistantBubble, `⚠️ **Erro:** ${data.message}`);
        finishGeneration();
      }
    });
  }

  // Inicialização
  await checkBackend();
  await loadConversations();
  promptInput.focus();
});
