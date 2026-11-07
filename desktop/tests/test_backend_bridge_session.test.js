/**
 * Noite Desktop 2.0 - Suíte de Testes de Autenticação, Sessão e CSRF do BackendBridge.
 * Cobre os 12 testes obrigatórios da Missão de Correção do Like.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { BackendBridge } = require('../src/main/backend-bridge');

/**
 * Cria um servidor mock HTTP para simular os contratos de segurança do FastAPI Noite.
 */
function createMockServer(port, handler) {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(port, '127.0.0.1', () => {
      resolve(server);
    });
  });
}

function closeServer(server) {
  return new Promise((resolve) => {
    server.close(() => resolve());
  });
}

test('Sessão e CSRF: 1. Criar sessão e extrair cookie', async () => {
  const port = 9101;
  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_mock_token_123; HttpOnly; Path=/; SameSite=strict');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_mock_token_abc', product: 'Noite 2.0' }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    assert.strictEqual(bridge._sessionCookie, null);
    assert.strictEqual(bridge._csrfToken, null);

    const result = await bridge.ensureSession();
    assert.strictEqual(result.ok, true);
    assert.strictEqual(bridge._sessionCookie, 'noite_web_session=sess_mock_token_123');
    assert.strictEqual(bridge._csrfToken, 'csrf_mock_token_abc');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 2. Requisição autenticada GET', async () => {
  const port = 9102;
  let receivedCookie = null;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_valid_get; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_valid_get' }));
    } else if (req.url === '/web/api/conversations') {
      receivedCookie = req.headers['cookie'];
      if (receivedCookie && receivedCookie.includes('noite_web_session=sess_valid_get')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify([{ id: 'conv-1', title: 'Conversa 1' }]));
      } else {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ detail: 'Sessão expirada.' }));
      }
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    const convs = await bridge.getConversations();
    assert.strictEqual(receivedCookie, 'noite_web_session=sess_valid_get');
    assert.strictEqual(convs.length, 1);
    assert.strictEqual(convs[0].id, 'conv-1');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 3. Like positivo (POST /web/api/feedback)', async () => {
  const port = 9103;
  let receivedCookie = null;
  let receivedCsrf = null;
  let receivedBody = '';

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_like_up; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_like_up' }));
    } else if (req.url === '/web/api/feedback' && req.method === 'POST') {
      receivedCookie = req.headers['cookie'];
      receivedCsrf = req.headers['x-noite-csrf'];
      req.on('data', chunk => { receivedBody += chunk; });
      req.on('end', () => {
        if (!receivedCookie || !receivedCsrf) {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ detail: 'Validação da sessão falhou.' }));
          return;
        }
        const parsed = JSON.parse(receivedBody);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, message_id: parsed.message_id, rating: parsed.rating }));
      });
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    const resp = await bridge.submitFeedback(42, 'positive');
    assert.strictEqual(resp.ok, true);
    assert.strictEqual(resp.message_id, 42);
    assert.strictEqual(resp.rating, 'positive');
    assert.strictEqual(receivedCookie, 'noite_web_session=sess_like_up');
    assert.strictEqual(receivedCsrf, 'csrf_like_up');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 4. Dislike negativo (POST /web/api/feedback)', async () => {
  const port = 9104;
  let receivedBody = '';

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_dislike; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_dislike' }));
    } else if (req.url === '/web/api/feedback' && req.method === 'POST') {
      req.on('data', chunk => { receivedBody += chunk; });
      req.on('end', () => {
        const parsed = JSON.parse(receivedBody);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, message_id: parsed.message_id, rating: parsed.rating }));
      });
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    const resp = await bridge.submitFeedback(88, 'negative');
    assert.strictEqual(resp.ok, true);
    assert.strictEqual(resp.message_id, 88);
    assert.strictEqual(resp.rating, 'negative');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 5. Remoção de feedback (rating null)', async () => {
  const port = 9105;
  let receivedBody = '';

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_neutral; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_neutral' }));
    } else if (req.url === '/web/api/feedback' && req.method === 'POST') {
      req.on('data', chunk => { receivedBody += chunk; });
      req.on('end', () => {
        const parsed = JSON.parse(receivedBody);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, message_id: parsed.message_id, rating: parsed.rating }));
      });
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    const resp = await bridge.submitFeedback(88, null);
    assert.strictEqual(resp.ok, true);
    assert.strictEqual(resp.message_id, 88);
    assert.strictEqual(resp.rating, null);
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 6. Envio de mensagem via SSE autenticado (sendPrompt)', async () => {
  const port = 9106;
  let sseCookie = null;
  let sseCsrf = null;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=sess_sse_auth; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_sse_auth' }));
    } else if (req.url === '/web/api/chat') {
      sseCookie = req.headers['cookie'];
      sseCsrf = req.headers['x-noite-csrf'];
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache'
      });
      res.write('event: chunk\ndata: {"text": "Olá mundo seguro"}\n\n');
      res.write('event: done\ndata: {"ok": true, "message_id": 999}\n\n');
      res.end();
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    let receivedChunk = '';
    let receivedDone = null;

    await new Promise((resolve, reject) => {
      bridge.sendPrompt('conv-sse', 'oi', {
        onChunk: (t) => { receivedChunk += t; },
        onDone: (d) => { receivedDone = d; resolve(); },
        onError: reject
      });
    });

    assert.strictEqual(receivedChunk, 'Olá mundo seguro');
    assert.strictEqual(receivedDone.message_id, 999);
    assert.strictEqual(sseCookie, 'noite_web_session=sess_sse_auth');
    assert.strictEqual(sseCsrf, 'csrf_sse_auth');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 7. Duas requisições simultâneas durante inicialização (mutex/concorrência)', async () => {
  const port = 9107;
  let sessionCalls = 0;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      sessionCalls++;
      setTimeout(() => {
        res.setHeader('Set-Cookie', 'noite_web_session=sess_mutex; Path=/');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ csrf: 'csrf_mutex' }));
      }, 50); // delay intencional para induzir corrida
    } else if (req.url === '/web/api/conversations') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify([{ id: 'c1' }]));
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    // Dispara duas requisições simultâneas sem sessão prévia
    const [r1, r2] = await Promise.all([
      bridge.getConversations(),
      bridge.getConversations()
    ]);

    assert.deepStrictEqual(r1, [{ id: 'c1' }]);
    assert.deepStrictEqual(r2, [{ id: 'c1' }]);
    // DEVE ter chamado /web/session apenas UMA única vez
    assert.strictEqual(sessionCalls, 1, 'A sessão deve ser inicializada apenas uma vez para requisições concorrentes');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 8. Sessão expirada (renovação automática em 401)', async () => {
  const port = 9108;
  let sessionCount = 1;
  let callCount = 0;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      sessionCount++;
      res.setHeader('Set-Cookie', `noite_web_session=sess_round_${sessionCount}; Path=/`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: `csrf_round_${sessionCount}` }));
    } else if (req.url === '/web/api/conversations') {
      callCount++;
      const cookie = req.headers['cookie'];
      if (cookie && cookie.includes('sess_round_2')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
      } else {
        // Primeira tentativa expira com 401
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ detail: 'Sessão expirada. Atualize a página.' }));
      }
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    // Injeta cookie obsoleto da rodada 1
    bridge._sessionCookie = 'noite_web_session=sess_round_1';
    bridge._csrfToken = 'csrf_round_1';

    const res = await bridge.getConversations();
    assert.strictEqual(res.success, true);
    assert.strictEqual(sessionCount, 2, 'Deve ter chamado /web/session para renovar a sessão expirada');
    assert.strictEqual(bridge._sessionCookie, 'noite_web_session=sess_round_2');
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 9. CSRF inválido (renovação automática se erro de CSRF)', async () => {
  const port = 9109;
  let sessionCount = 1;
  let feedbackCalls = 0;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      sessionCount++;
      res.setHeader('Set-Cookie', `noite_web_session=sess_csrf_${sessionCount}; Path=/`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: `csrf_valid_${sessionCount}` }));
    } else if (req.url === '/web/api/feedback') {
      feedbackCalls++;
      const csrf = req.headers['x-noite-csrf'];
      if (csrf === 'csrf_valid_2') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, rating: 'positive' }));
      } else {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ detail: 'Validação da sessão falhou.' }));
      }
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    // Injeta CSRF inválido
    bridge._sessionCookie = 'noite_web_session=sess_csrf_1';
    bridge._csrfToken = 'csrf_invalid_stale';

    const resp = await bridge.submitFeedback(10, 'positive');
    assert.strictEqual(resp.ok, true);
    assert.strictEqual(feedbackCalls, 2);
    assert.strictEqual(sessionCount, 2);
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 10. Mensagem pertencente a outra conversa (403 de negócio NÃO deve repetir)', async () => {
  const port = 9110;
  let sessionCalls = 0;
  let feedbackCalls = 0;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      sessionCalls++;
      res.setHeader('Set-Cookie', 'noite_web_session=sess_other; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'csrf_other' }));
    } else if (req.url === '/web/api/feedback') {
      feedbackCalls++;
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ detail: 'Mensagem não pertence à conversa ativa.' }));
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    await assert.rejects(async () => {
      await bridge.submitFeedback(999, 'positive');
    }, (err) => {
      assert.strictEqual(err.message, 'Mensagem não pertence à conversa ativa.');
      return true;
    });

    // NÃO deve ter feito retry!
    assert.strictEqual(feedbackCalls, 1, 'Erro de autorização de conversa não deve causar repetição automática');
    assert.strictEqual(sessionCalls, 1);
  } finally {
    await closeServer(mockServer);
  }
});

test('Sessão e CSRF: 11. Falha de conexão', async () => {
  // Porta fechada
  const bridge = new BackendBridge({ port: 59999 });

  await assert.rejects(async () => {
    await bridge.getConversations();
  }, (err) => {
    assert.match(err.message, /Falha de conexão com o backend/);
    return true;
  });
});

test('Sessão e CSRF: 12. Verificar que nenhum segredo chega ao renderer', async () => {
  const port = 9112;

  const mockServer = await createMockServer(port, (req, res) => {
    if (req.url === '/web/session') {
      res.setHeader('Set-Cookie', 'noite_web_session=SUPER_SECRET_COOKIE_VAL_123456; Path=/');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ csrf: 'SUPER_SECRET_CSRF_VAL_654321', product: 'Noite 2.0' }));
    }
  });

  try {
    const bridge = new BackendBridge({ port });
    const health = await bridge.checkHealth();

    assert.strictEqual(health.online, true);
    // O retorno não deve conter nem cookie nem CSRF
    const serialized = JSON.stringify(health);
    assert.ok(!serialized.includes('SUPER_SECRET_COOKIE_VAL_123456'));
    assert.ok(!serialized.includes('SUPER_SECRET_CSRF_VAL_654321'));
    assert.ok(!serialized.includes('noite_web_session'));
    assert.ok(!serialized.includes('csrf'));
  } finally {
    await closeServer(mockServer);
  }
});
