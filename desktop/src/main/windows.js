/**
 * Noite Desktop 2.0 - Gerenciador de Janelas (Mascote e Chat).
 */
'use strict';

const path = require('node:path');
const { BrowserWindow, screen } = require('electron');
const { getSecureWebPreferences, applySecurityPolicies } = require('./security');

let mascotWindow = null;
let chatWindow = null;

const PRELOAD_PATH = path.resolve(__dirname, '../preload/index.js');
const RENDERER_DIR = path.resolve(__dirname, '../renderer');

/**
 * Cria ou recupera a janela flutuante do Mascote.
 */
function createMascotWindow() {
  if (mascotWindow && !mascotWindow.isDestroyed()) {
    mascotWindow.show();
    return mascotWindow;
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  // Posição inicial: canto inferior direito da tela
  const defaultWidth = 148;
  const defaultHeight = 148;
  const initialX = screenWidth - defaultWidth - 32;
  const initialY = screenHeight - defaultHeight - 32;

  mascotWindow = new BrowserWindow({
    width: defaultWidth,
    height: defaultHeight,
    x: initialX,
    y: initialY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    focusable: true,
    title: 'Noite Mascote',
    webPreferences: getSecureWebPreferences(PRELOAD_PATH)
  });

  applySecurityPolicies(mascotWindow);

  mascotWindow.loadFile(path.join(RENDERER_DIR, 'mascot/mascot.html'));

  mascotWindow.on('closed', () => {
    mascotWindow = null;
  });

  return mascotWindow;
}

/**
 * Cria ou recupera a janela principal de conversação Codex.
 */
function createChatWindow() {
  if (chatWindow && !chatWindow.isDestroyed()) {
    chatWindow.show();
    chatWindow.focus();
    return chatWindow;
  }

  chatWindow = new BrowserWindow({
    width: 980,
    height: 740,
    minWidth: 680,
    minHeight: 520,
    frame: false, // Custom Titlebar
    backgroundColor: '#0d1117',
    show: false,
    title: 'Noite 2.0',
    webPreferences: getSecureWebPreferences(PRELOAD_PATH)
  });

  applySecurityPolicies(chatWindow);

  chatWindow.loadFile(path.join(RENDERER_DIR, 'chat/chat.html'));

  chatWindow.once('ready-to-show', () => {
    chatWindow.show();
    chatWindow.focus();
  });

  chatWindow.on('closed', () => {
    chatWindow = null;
  });

  return chatWindow;
}

/**
 * Alterna a visibilidade da janela de Chat.
 */
function toggleChatWindow() {
  if (!chatWindow || chatWindow.isDestroyed()) {
    return createChatWindow();
  }

  if (chatWindow.isVisible()) {
    if (chatWindow.isFocused()) {
      chatWindow.hide();
    } else {
      chatWindow.focus();
    }
  } else {
    chatWindow.show();
    chatWindow.focus();
  }
  return chatWindow;
}

/**
 * Retorna as janelas ativas.
 */
function getWindows() {
  return { mascotWindow, chatWindow };
}

module.exports = {
  createMascotWindow,
  createChatWindow,
  toggleChatWindow,
  getWindows
};
