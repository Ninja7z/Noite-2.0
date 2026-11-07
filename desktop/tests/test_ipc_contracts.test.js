/**
 * Noite Desktop 2.0 - Testes de Contratos e Validação de Mensagens IPC.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const {
  ValidationError,
  validateSendMessagePayload,
  validateFeedbackPayload,
  validateMascotState,
  validateConversationId
} = require('../src/main/ipc-validator');

test('IPC Validator: validateSendMessagePayload', async (t) => {
  await t.test('aceita payload válido com conversationId e prompt', () => {
    const valid = validateSendMessagePayload({ conversationId: 'c1', prompt: 'Olá Noite' });
    assert.strictEqual(valid.conversationId, 'c1');
    assert.strictEqual(valid.prompt, 'Olá Noite');
  });

  await t.test('rejeita payload nulo ou não objeto', () => {
    assert.throws(() => validateSendMessagePayload(null), ValidationError);
    assert.throws(() => validateSendMessagePayload('string'), ValidationError);
  });

  await t.test('rejeita conversationId vazio ou não string', () => {
    assert.throws(() => validateSendMessagePayload({ conversationId: '', prompt: 'Olá' }), ValidationError);
    assert.throws(() => validateSendMessagePayload({ conversationId: 123, prompt: 'Olá' }), ValidationError);
  });

  await t.test('rejeita prompt vazio ou excessivamente longo', () => {
    assert.throws(() => validateSendMessagePayload({ conversationId: 'c1', prompt: '   ' }), ValidationError);
    const hugePrompt = 'a'.repeat(50001);
    assert.throws(() => validateSendMessagePayload({ conversationId: 'c1', prompt: hugePrompt }), ValidationError);
  });
});

test('IPC Validator: validateFeedbackPayload', async (t) => {
  await t.test('aceita ratings válidos: positive, negative, null', () => {
    assert.deepStrictEqual(validateFeedbackPayload({ messageId: 42, rating: 'positive' }), { messageId: 42, rating: 'positive' });
    assert.deepStrictEqual(validateFeedbackPayload({ messageId: 42, rating: 'negative' }), { messageId: 42, rating: 'negative' });
    assert.deepStrictEqual(validateFeedbackPayload({ messageId: 42, rating: null }), { messageId: 42, rating: null });
  });

  await t.test('rejeita messageId inválido, negativo ou float', () => {
    assert.throws(() => validateFeedbackPayload({ messageId: 0, rating: 'positive' }), ValidationError);
    assert.throws(() => validateFeedbackPayload({ messageId: -1, rating: 'positive' }), ValidationError);
    assert.throws(() => validateFeedbackPayload({ messageId: 1.5, rating: 'positive' }), ValidationError);
    assert.throws(() => validateFeedbackPayload({ messageId: '10', rating: 'positive' }), ValidationError);
  });

  await t.test('rejeita ratings arbitrários', () => {
    assert.throws(() => validateFeedbackPayload({ messageId: 10, rating: 'great' }), ValidationError);
    assert.throws(() => validateFeedbackPayload({ messageId: 10, rating: 123 }), ValidationError);
  });
});

test('IPC Validator: validateMascotState', async (t) => {
  await t.test('aceita todos os estados legítimos do mascote', () => {
    const states = ['idle', 'thinking', 'working', 'error', 'done', 'listening'];
    for (const s of states) {
      assert.strictEqual(validateMascotState(s), s);
    }
  });

  await t.test('rejeita estados desconhecidos ou injeção', () => {
    assert.throws(() => validateMascotState('sleeping'), ValidationError);
    assert.throws(() => validateMascotState(''), ValidationError);
    assert.throws(() => validateMascotState(null), ValidationError);
  });
});

test('IPC Validator: validateConversationId', async (t) => {
  await t.test('aceita e sanitiza ID válido', () => {
    assert.strictEqual(validateConversationId('  default  '), 'default');
  });

  await t.test('rejeita string vazia ou tipos inválidos', () => {
    assert.throws(() => validateConversationId(''), ValidationError);
    assert.throws(() => validateConversationId(null), ValidationError);
    assert.throws(() => validateConversationId(123), ValidationError);
  });
});
