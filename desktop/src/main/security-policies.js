/**
 * Noite Desktop 2.0 - Políticas de Segurança Puras (sem dependência do Electron).
 * Separado de security.js para permitir testes unitários sem processo Electron.
 */
'use strict';

/**
 * Opções de webPreferences obrigatórias para qualquer BrowserWindow da Noite Desktop.
 * @param {string} preloadPath Caminho absoluto para o script de preload.
 * @returns {object} WebPreferences estritamente seguro.
 */
function getSecureWebPreferences(preloadPath) {
  return {
    preload: preloadPath,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInWorker: false,
    nodeIntegrationInSubFrames: false,
    sandbox: true,
    webSecurity: true,
    allowRunningInsecureContent: false,
    experimentalFeatures: false,
    enableRemoteModule: false,
    navigateOnDragDrop: false
  };
}

/**
 * Política de Segurança de Conteúdo (CSP) rígida para a Noite Desktop.
 * Restringe todas as origens a 'self' e conexões de rede exclusivamente
 * ao backend FastAPI local (porta 8766).
 */
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self' http://127.0.0.1:8766 http://localhost:8766",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'"
].join('; ');

module.exports = {
  getSecureWebPreferences,
  CONTENT_SECURITY_POLICY
};
