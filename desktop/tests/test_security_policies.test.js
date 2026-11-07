/**
 * Noite Desktop 2.0 - Testes de Políticas de Segurança Electron.
 * Importa de security-policies.js (módulo puro, sem dependência do Electron)
 * para que os testes possam rodar sem um processo Electron ativo.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const {
  getSecureWebPreferences,
  CONTENT_SECURITY_POLICY
} = require('../src/main/security-policies');

test('Security Policies: getSecureWebPreferences', async (t) => {
  const prefs = getSecureWebPreferences('/fake/path/preload.js');

  await t.test('contextIsolation DEVE estar rigorosamente ativado', () => {
    assert.strictEqual(prefs.contextIsolation, true);
  });

  await t.test('nodeIntegration DEVE estar rigorosamente desativado', () => {
    assert.strictEqual(prefs.nodeIntegration, false);
    assert.strictEqual(prefs.nodeIntegrationInWorker, false);
    assert.strictEqual(prefs.nodeIntegrationInSubFrames, false);
  });

  await t.test('sandbox DEVE estar ativado', () => {
    assert.strictEqual(prefs.sandbox, true);
  });

  await t.test('webSecurity DEVE estar ativado', () => {
    assert.strictEqual(prefs.webSecurity, true);
  });

  await t.test('allowRunningInsecureContent DEVE estar desativado', () => {
    assert.strictEqual(prefs.allowRunningInsecureContent, false);
  });

  await t.test('enableRemoteModule DEVE estar desativado', () => {
    assert.strictEqual(prefs.enableRemoteModule, false);
  });

  await t.test('preload DEVE ser o caminho fornecido', () => {
    assert.strictEqual(prefs.preload, '/fake/path/preload.js');
  });
});

test('Security Policies: Content Security Policy (CSP)', async (t) => {
  await t.test('CSP contém default-src self', () => {
    assert.match(CONTENT_SECURITY_POLICY, /default-src 'self'/);
  });

  await t.test('CSP restringe conexões exclusivamente a localhost/127.0.0.1 porta 8766', () => {
    assert.match(CONTENT_SECURITY_POLICY, /connect-src 'self' http:\/\/127\.0\.0\.1:8766 http:\/\/localhost:8766/);
  });

  await t.test('CSP proíbe aninhamento em frames (frame-ancestors none)', () => {
    assert.match(CONTENT_SECURITY_POLICY, /frame-ancestors 'none'/);
  });

  await t.test('CSP proíbe submissão de formulários arbitrários (form-action none)', () => {
    assert.match(CONTENT_SECURITY_POLICY, /form-action 'none'/);
  });
});
