/**
 * Noite Desktop 2.0 - Validador de Mensagens IPC.
 * Assegura que nenhum payload corrompido ou inesperado atinja o processo principal.
 */
'use strict';

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * Valida o payload de envio de mensagem de chat.
 * @param {any} payload Objeto recebido via IPC.
 * @returns {{ conversationId: string, prompt: string }} Payload validado.
 */
function validateSendMessagePayload(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new ValidationError('Payload deve ser um objeto.');
  }

  const { conversationId, prompt } = payload;

  if (typeof conversationId !== 'string' || !conversationId.trim()) {
    throw new ValidationError('conversationId deve ser uma string não vazia.');
  }

  if (typeof prompt !== 'string' || !prompt.trim()) {
    throw new ValidationError('prompt deve ser uma string não vazia.');
  }

  if (prompt.length > 50000) {
    throw new ValidationError('prompt excede o tamanho máximo permitido de 50.000 caracteres.');
  }

  return {
    conversationId: conversationId.trim(),
    prompt: prompt.trim()
  };
}

/**
 * Valida o payload de submissão de feedback.
 * @param {any} payload Objeto recebido via IPC.
 * @returns {{ messageId: number, rating: string|null }} Payload validado.
 */
function validateFeedbackPayload(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new ValidationError('Payload deve ser um objeto.');
  }

  const { messageId, rating } = payload;

  if (typeof messageId !== 'number' || !Number.isSafeInteger(messageId) || messageId <= 0) {
    throw new ValidationError('messageId deve ser um inteiro positivo válido.');
  }

  if (rating !== null && rating !== 'positive' && rating !== 'negative') {
    throw new ValidationError("rating deve ser 'positive', 'negative' ou null.");
  }

  return {
    messageId,
    rating
  };
}

/**
 * Valida o estado do mascote.
 * @param {any} state Estado solicitado.
 * @returns {string} Estado validado.
 */
function validateMascotState(state) {
  const allowed = ['idle', 'thinking', 'working', 'error', 'done', 'listening'];
  if (typeof state !== 'string' || !allowed.includes(state)) {
    throw new ValidationError(`Estado do mascote inválido: ${state}. Permitidos: ${allowed.join(', ')}`);
  }
  return state;
}

/**
 * Valida o identificador de conversa.
 * @param {any} conversationId ID da conversa.
 * @returns {string} ID validado.
 */
function validateConversationId(conversationId) {
  if (typeof conversationId !== 'string' || !conversationId.trim()) {
    throw new ValidationError('conversationId deve ser uma string não vazia.');
  }
  return conversationId.trim();
}

module.exports = {
  ValidationError,
  validateSendMessagePayload,
  validateFeedbackPayload,
  validateMascotState,
  validateConversationId
};
