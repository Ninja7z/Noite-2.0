/**
 * Noite Desktop 2.0 - Módulo de Segurança Central do Processo Principal.
 * Aplica contextIsolation, proíbe nodeIntegration, restringe navegação e injeta CSP.
 *
 * As políticas puras (sem Electron) vivem em security-policies.js para permitir
 * testes unitários sem um processo Electron ativo.
 */
'use strict';

const { shell, session } = require('electron');
const {
  getSecureWebPreferences,
  CONTENT_SECURITY_POLICY
} = require('./security-policies');

/**
 * Configura filtros de navegação e CSP para uma janela.
 * @param {Electron.BrowserWindow} win Instância da janela.
 */
function applySecurityPolicies(win) {
  if (!win || !win.webContents) return;

  const contents = win.webContents;

  // Bloqueia qualquer tentativa de navegação no renderer
  contents.on('will-navigate', (event, navigationUrl) => {
    if (navigationUrl !== contents.getURL()) {
      event.preventDefault();
      console.warn(`[Segurança] Navegação não autorizada bloqueada: ${navigationUrl}`);
    }
  });

  // Links externos (ex: markdown do chat) abrem no navegador padrão do sistema operacional
  contents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      shell.openExternal(url).catch(err => {
        console.error('[Segurança] Falha ao abrir link externo:', err);
      });
    }
    return { action: 'deny' };
  });

  // Bloqueia anexação de webview
  contents.on('will-attach-webview', (event) => {
    event.preventDefault();
    console.warn('[Segurança] Tentativa de anexo de Webview bloqueada.');
  });
}

/**
 * Injeta cabeçalhos CSP globais para sessões HTTP locais.
 * @param {Electron.Session} targetSession Sessão do Electron (padrão session.defaultSession).
 */
function configureSessionSecurity(targetSession = session.defaultSession) {
  if (!targetSession || !targetSession.webRequest) return;

  targetSession.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    responseHeaders['Content-Security-Policy'] = [CONTENT_SECURITY_POLICY];
    responseHeaders['X-Content-Type-Options'] = ['nosniff'];
    responseHeaders['X-Frame-Options'] = ['DENY'];
    callback({ responseHeaders });
  });
}

module.exports = {
  getSecureWebPreferences,
  applySecurityPolicies,
  configureSessionSecurity,
  CONTENT_SECURITY_POLICY
};
