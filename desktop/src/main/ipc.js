/**
 * Noite Desktop 2.0 - Roteador IPC Seguro do Processo Principal.
 */
'use strict';

const { ipcMain, BrowserWindow } = require('electron');
const {
  validateSendMessagePayload,
  validateFeedbackPayload,
  validateMascotState,
  validateConversationId
} = require('./ipc-validator');
const { toggleChatWindow, getWindows } = require('./windows');

let currentMascotState = 'idle';

function registerIpcHandlers(backendBridge) {
  // ==========================================
  // Controle de Janelas
  // ==========================================

  ipcMain.handle('noite:window:minimize', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.minimize();
    return true;
  });

  ipcMain.handle('noite:window:maximize', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      if (win.isMaximized()) {
        win.unmaximize();
      } else {
        win.maximize();
      }
      return win.isMaximized();
    }
    return false;
  });

  ipcMain.handle('noite:window:close', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.close();
    return true;
  });

  ipcMain.handle('noite:window:is-maximized', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    return win ? win.isMaximized() : false;
  });

  // ==========================================
  // Controle do Mascote
  // ==========================================

  ipcMain.handle('noite:mascot:set-state', (event, state) => {
    const validState = validateMascotState(state);
    currentMascotState = validState;

    // Notifica todas as janelas sobre a mudança de estado
    const { mascotWindow, chatWindow } = getWindows();
    if (mascotWindow && !mascotWindow.isDestroyed()) {
      mascotWindow.webContents.send('noite:mascot:state-changed', validState);
    }
    if (chatWindow && !chatWindow.isDestroyed()) {
      chatWindow.webContents.send('noite:mascot:state-changed', validState);
    }
    return validState;
  });

  ipcMain.handle('noite:mascot:get-state', () => {
    return currentMascotState;
  });

  ipcMain.handle('noite:mascot:toggle-chat', () => {
    toggleChatWindow();
    return true;
  });

  // ==========================================
  // Mensagens e Streaming
  // ==========================================

  ipcMain.handle('noite:chat:send', async (event, payload) => {
    const { conversationId, prompt } = validateSendMessagePayload(payload);

    // Altera o estado do mascote para thinking
    currentMascotState = 'thinking';
    const { mascotWindow, chatWindow } = getWindows();
    if (mascotWindow && !mascotWindow.isDestroyed()) {
      mascotWindow.webContents.send('noite:mascot:state-changed', 'thinking');
    }

    backendBridge.sendPrompt(conversationId, prompt, {
      onChunk: (text) => {
        if (currentMascotState !== 'working') {
          currentMascotState = 'working';
          if (mascotWindow && !mascotWindow.isDestroyed()) {
            mascotWindow.webContents.send('noite:mascot:state-changed', 'working');
          }
        }
        event.sender.send('noite:chat:chunk', { conversationId, text });
      },
      onThinking: (text) => {
        event.sender.send('noite:chat:thinking', { conversationId, text });
      },
      onActivity: (activity) => {
        event.sender.send('noite:chat:activity', { conversationId, activity });
      },
      onDone: (data) => {
        currentMascotState = 'done';
        if (mascotWindow && !mascotWindow.isDestroyed()) {
          mascotWindow.webContents.send('noite:mascot:state-changed', 'done');
          // Retorna para idle após breve confirmação
          setTimeout(() => {
            if (currentMascotState === 'done') {
              currentMascotState = 'idle';
              if (!mascotWindow.isDestroyed()) {
                mascotWindow.webContents.send('noite:mascot:state-changed', 'idle');
              }
            }
          }, 2400);
        }
        event.sender.send('noite:chat:done', { conversationId, ...data });
      },
      onError: (err) => {
        currentMascotState = 'error';
        if (mascotWindow && !mascotWindow.isDestroyed()) {
          mascotWindow.webContents.send('noite:mascot:state-changed', 'error');
          setTimeout(() => {
            if (currentMascotState === 'error') {
              currentMascotState = 'idle';
              if (!mascotWindow.isDestroyed()) {
                mascotWindow.webContents.send('noite:mascot:state-changed', 'idle');
              }
            }
          }, 3000);
        }
        event.sender.send('noite:chat:error', { conversationId, message: err.message });
      }
    });

    return { started: true, conversationId };
  });

  ipcMain.handle('noite:chat:cancel', (event, conversationId) => {
    const validId = validateConversationId(conversationId);
    const stopped = backendBridge.cancelPrompt(validId);
    currentMascotState = 'idle';
    const { mascotWindow } = getWindows();
    if (mascotWindow && !mascotWindow.isDestroyed()) {
      mascotWindow.webContents.send('noite:mascot:state-changed', 'idle');
    }
    return stopped;
  });

  ipcMain.handle('noite:chat:get-conversations', async () => {
    return await backendBridge.getConversations();
  });

  ipcMain.handle('noite:chat:get-history', async (event, conversationId) => {
    const validId = validateConversationId(conversationId);
    return await backendBridge.getHistory(validId);
  });

  ipcMain.handle('noite:chat:select-conversation', async (event, conversationId) => {
    const validId = validateConversationId(conversationId);
    return await backendBridge.selectConversation(validId);
  });

  ipcMain.handle('noite:chat:submit-feedback', async (event, payload) => {
    const { messageId, rating } = validateFeedbackPayload(payload);
    return await backendBridge.submitFeedback(messageId, rating);
  });

  ipcMain.handle('noite:system:get-status', async () => {
    return await backendBridge.checkHealth();
  });
}

function unregisterIpcHandlers() {
  const channels = [
    'noite:window:minimize',
    'noite:window:maximize',
    'noite:window:close',
    'noite:window:is-maximized',
    'noite:mascot:set-state',
    'noite:mascot:get-state',
    'noite:mascot:toggle-chat',
    'noite:chat:send',
    'noite:chat:cancel',
    'noite:chat:get-conversations',
    'noite:chat:get-history',
    'noite:chat:select-conversation',
    'noite:chat:submit-feedback',
    'noite:system:get-status'
  ];

  for (const ch of channels) {
    ipcMain.removeHandler(ch);
  }
}

module.exports = {
  registerIpcHandlers,
  unregisterIpcHandlers
};
