/**
 * Noite Desktop 2.0 - Preload Seguro com contextBridge.
 * NUNCA expõe o ipcRenderer ou módulos Node diretamente ao Renderer.
 */
'use strict';

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Cria uma ponte segura com canais permitidos e sanitização de listeners.
 */
const api = {
  // Controle de Janela
  window: {
    minimize: () => ipcRenderer.invoke('noite:window:minimize'),
    maximize: () => ipcRenderer.invoke('noite:window:maximize'),
    close: () => ipcRenderer.invoke('noite:window:close'),
    isMaximized: () => ipcRenderer.invoke('noite:window:is-maximized')
  },

  // Controle e Eventos do Mascote
  mascot: {
    getState: () => ipcRenderer.invoke('noite:mascot:get-state'),
    setState: (state) => ipcRenderer.invoke('noite:mascot:set-state', state),
    toggleChat: () => ipcRenderer.invoke('noite:mascot:toggle-chat'),
    onStateChange: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, state) => callback(state);
      ipcRenderer.on('noite:mascot:state-changed', subscription);
      return () => ipcRenderer.removeListener('noite:mascot:state-changed', subscription);
    }
  },

  // Operações de Chat e Conversação
  chat: {
    sendMessage: (conversationId, prompt) => {
      return ipcRenderer.invoke('noite:chat:send', { conversationId, prompt });
    },
    cancelMessage: (conversationId) => {
      return ipcRenderer.invoke('noite:chat:cancel', conversationId);
    },
    getConversations: () => {
      return ipcRenderer.invoke('noite:chat:get-conversations');
    },
    getHistory: (conversationId) => {
      return ipcRenderer.invoke('noite:chat:get-history', conversationId);
    },
    selectConversation: (conversationId) => {
      return ipcRenderer.invoke('noite:chat:select-conversation', conversationId);
    },
    submitFeedback: (messageId, rating) => {
      return ipcRenderer.invoke('noite:chat:submit-feedback', { messageId, rating });
    },

    // Listeners de streaming SSE
    onChunk: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, data) => callback(data);
      ipcRenderer.on('noite:chat:chunk', subscription);
      return () => ipcRenderer.removeListener('noite:chat:chunk', subscription);
    },
    onThinking: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, data) => callback(data);
      ipcRenderer.on('noite:chat:thinking', subscription);
      return () => ipcRenderer.removeListener('noite:chat:thinking', subscription);
    },
    onActivity: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, data) => callback(data);
      ipcRenderer.on('noite:chat:activity', subscription);
      return () => ipcRenderer.removeListener('noite:chat:activity', subscription);
    },
    onDone: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, data) => callback(data);
      ipcRenderer.on('noite:chat:done', subscription);
      return () => ipcRenderer.removeListener('noite:chat:done', subscription);
    },
    onError: (callback) => {
      if (typeof callback !== 'function') return () => {};
      const subscription = (_event, data) => callback(data);
      ipcRenderer.on('noite:chat:error', subscription);
      return () => ipcRenderer.removeListener('noite:chat:error', subscription);
    }
  },

  // Informações do Sistema e Backend
  system: {
    getStatus: () => ipcRenderer.invoke('noite:system:get-status')
  }
};

// Exposição isolada no window.noiteDesktop
contextBridge.exposeInMainWorld('noiteDesktop', api);
