/**
 * Noite Desktop 2.0 - Ponto de Entrada do Processo Principal (Electron).
 */
'use strict';

const { app } = require('electron');
const { configureSessionSecurity } = require('./security');
const { createMascotWindow, getWindows } = require('./windows');
const { registerIpcHandlers, unregisterIpcHandlers } = require('./ipc');
const { setupTray, destroyTray } = require('./tray');
const { registerGlobalShortcuts, unregisterGlobalShortcuts } = require('./shortcuts');
const { BackendBridge } = require('./backend-bridge');

// Instância única no Windows
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  console.log('[App] Outra instância da Noite já está em execução. Encerrando esta.');
  app.quit();
} else {
  const backendBridge = new BackendBridge();

  app.on('second-instance', () => {
    const { chatWindow } = getWindows();
    if (chatWindow && !chatWindow.isDestroyed()) {
      if (chatWindow.isMinimized()) chatWindow.restore();
      chatWindow.show();
      chatWindow.focus();
    }
  });

  app.whenReady().then(() => {
    console.log('[App] Noite Desktop 2.0 inicializando...');

    // 1. Configura políticas de segurança HTTP/CSP
    configureSessionSecurity();

    // 2. Registra handlers IPC protegidos
    registerIpcHandlers(backendBridge);

    // 3. Registra atalhos globais (Alt+C)
    registerGlobalShortcuts();

    // 4. Inicializa o System Tray
    setupTray();

    // 5. Abre a janela do mascote
    createMascotWindow();

    console.log('[App] Noite Desktop inicializada com sucesso.');
  });

  // Não fecha a aplicação no Windows quando fechar as janelas (fica residente no mascote/tray)
  app.on('window-all-closed', () => {
    // Mantém viva na bandeja
  });

  // Encerramento limpo e seguro
  app.on('before-quit', () => {
    console.log('[App] Encerrando Noite Desktop com limpeza de recursos...');
    unregisterGlobalShortcuts();
    destroyTray();
    unregisterIpcHandlers();
  });
}
