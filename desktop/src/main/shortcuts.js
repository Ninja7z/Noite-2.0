/**
 * Noite Desktop 2.0 - Atalhos Globais no Windows.
 */
'use strict';

const { globalShortcut } = require('electron');
const { toggleChatWindow } = require('./windows');

function registerGlobalShortcuts() {
  const registered = globalShortcut.register('Alt+C', () => {
    toggleChatWindow();
  });

  if (!registered) {
    console.warn('[Atalhos] Falha ao registrar o atalho global Alt+C.');
  } else {
    console.log('[Atalhos] Atalho global Alt+C registrado com sucesso.');
  }
}

function unregisterGlobalShortcuts() {
  globalShortcut.unregisterAll();
}

module.exports = {
  registerGlobalShortcuts,
  unregisterGlobalShortcuts
};
