/**
 * Noite Desktop 2.0 - Testes da Ponte de Backend (SSE, HTTP e Cancelamento).
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { BackendBridge } = require('../src/main/backend-bridge');

test('BackendBridge: Despacho de Pacotes SSE', async (t) => {
  const bridge = new BackendBridge();

  await t.test('despacha evento chunk corretamente', () => {
    let received = '';
    bridge._dispatchSsePacket('chunk', { text: 'Olá mundo' }, {
      onChunk: (txt) => { received = txt; }
    });
    assert.strictEqual(received, 'Olá mundo');
  });

  await t.test('despacha evento thinking corretamente', () => {
    let thought = '';
    bridge._dispatchSsePacket('thinking', { text: 'Calculando...' }, {
      onThinking: (txt) => { thought = txt; }
    });
    assert.strictEqual(thought, 'Calculando...');
  });

  await t.test('despacha evento activity corretamente', () => {
    let act = null;
    bridge._dispatchSsePacket('activity', { summary: 'Consultando arquivo' }, {
      onActivity: (a) => { act = a; }
    });
    assert.deepStrictEqual(act, { summary: 'Consultando arquivo' });
  });

  await t.test('despacha evento done com message_id', () => {
    let doneData = null;
    bridge._dispatchSsePacket('done', { ok: true, conversation_id: 'c1', message_id: 123 }, {
      onDone: (d) => { doneData = d; }
    });
    assert.strictEqual(doneData.message_id, 123);
    assert.strictEqual(doneData.ok, true);
  });

  await t.test('despacha evento error como exceção Error tratada', () => {
    let caught = null;
    bridge._dispatchSsePacket('error', { message: 'Falha no gateway' }, {
      onError: (err) => { caught = err; }
    });
    assert.ok(caught instanceof Error);
    assert.strictEqual(caught.message, 'Falha no gateway');
  });
});

test('BackendBridge: Cancelamento de Requisições', async (t) => {
  const bridge = new BackendBridge();
  let destroyed = false;
  bridge._activeRequests.set('active-conv', {
    destroy: () => { destroyed = true; }
  });

  await t.test('cancelPrompt encerra a requisição ativa e a remove do mapa', () => {
    const res = bridge.cancelPrompt('active-conv');
    assert.strictEqual(res, true);
    assert.strictEqual(destroyed, true);
    assert.strictEqual(bridge._activeRequests.has('active-conv'), false);
  });

  await t.test('cancelPrompt retorna false para conversas inexistentes', () => {
    const res = bridge.cancelPrompt('unknown-conv');
    assert.strictEqual(res, false);
  });
});
