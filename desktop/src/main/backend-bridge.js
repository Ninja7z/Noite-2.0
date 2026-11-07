/**
 * Noite Desktop 2.0 - Ponte Segura de Comunicação com o Backend da Noite.
 * Comunica-se com a API FastAPI local (porta 8766) via HTTP/SSE.
 *
 * Gerencia autenticação de sessão e token CSRF exclusivamente no processo
 * principal do Electron, sem expor credenciais ao Renderer.
 */
'use strict';

const http = require('node:http');

class BackendBridge {
  constructor(options = {}) {
    this.host = options.host || '127.0.0.1';
    this.port = options.port || 8766;
    this.baseUrl = `http://${this.host}:${this.port}`;
    this._activeRequests = new Map(); // conversationId -> http.ClientRequest

    // Estado de Sessão e Segurança (Exclusivo do Processo Principal)
    this._sessionCookie = null; // String "noite_web_session=<valor>"
    this._csrfToken = null;     // String token CSRF
    this._sessionPromise = null; // Mutex para inicialização/renovação única
  }

  /**
   * Garante que uma sessão válida e token CSRF estejam disponíveis.
   * Seguro contra múltiplas chamadas concorrentes.
   * @param {boolean} forceRefresh Força renovação da sessão.
   */
  async ensureSession(forceRefresh = false) {
    if (!forceRefresh && this._sessionCookie && this._csrfToken) {
      return { ok: true };
    }

    // Se já houver renovação em andamento, aguarda a mesma Promise
    if (this._sessionPromise) {
      return await this._sessionPromise;
    }

    this._sessionPromise = (async () => {
      try {
        const res = await this._rawHttpRequest('/web/session', {
          method: 'GET',
          timeout: 4000
        });

        if (res.statusCode < 200 || res.statusCode >= 300) {
          throw new Error(`Falha ao iniciar sessão local: HTTP ${res.statusCode}`);
        }

        // Extrai o cookie da sessão a partir de Set-Cookie
        const setCookieHeader = res.headers['set-cookie'];
        if (setCookieHeader) {
          const cookies = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
          for (const c of cookies) {
            const match = c.match(/noite_web_session=([^;]+)/i);
            if (match) {
              this._sessionCookie = `noite_web_session=${match[1]}`;
              break;
            }
          }
        }

        if (res.json && res.json.csrf) {
          this._csrfToken = res.json.csrf;
        }

        if (!this._sessionCookie || !this._csrfToken) {
          throw new Error('Backend não forneceu cookie de sessão ou token CSRF válidos.');
        }

        return { ok: true };
      } finally {
        this._sessionPromise = null;
      }
    })();

    return await this._sessionPromise;
  }

  /**
   * Executa requisição HTTP de baixo nível, retornando statusCode, headers,
   * corpo bruto e JSON (se houver).
   */
  async _rawHttpRequest(path, options = {}) {
    return new Promise((resolve, reject) => {
      const headers = {
        'Accept': options.accept || 'application/json',
        ...(options.headers || {})
      };

      let bodyData = null;
      if (options.body) {
        bodyData = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
        headers['Content-Type'] = 'application/json; charset=utf-8';
        headers['Content-Length'] = Buffer.byteLength(bodyData);
      }

      const reqOptions = {
        host: this.host,
        port: this.port,
        path: path,
        method: options.method || 'GET',
        headers: headers,
        timeout: options.timeout || 5000
      };

      const req = http.request(reqOptions, (res) => {
        let raw = '';
        res.setEncoding('utf-8');
        res.on('data', chunk => { raw += chunk; });
        res.on('end', () => {
          // Atualiza cookie se o backend renovou no Set-Cookie
          const setCookieHeader = res.headers['set-cookie'];
          if (setCookieHeader) {
            const cookies = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
            for (const c of cookies) {
              const match = c.match(/noite_web_session=([^;]+)/i);
              if (match) {
                this._sessionCookie = `noite_web_session=${match[1]}`;
                break;
              }
            }
          }

          let json = null;
          if (raw) {
            try {
              json = JSON.parse(raw);
            } catch (_) {}
          }

          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            raw: raw,
            json: json
          });
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Timeout de comunicação com o backend da Noite.'));
      });

      req.on('error', (err) => {
        reject(new Error(`Falha de conexão com o backend: ${err.message}`));
      });

      if (bodyData) {
        req.write(bodyData);
      }
      req.end();
    });
  }

  /**
   * Executa requisição HTTP JSON utilitária com autenticação de sessão e CSRF.
   * Preserva o contrato público retornando os dados decodificados.
   */
  async _requestJson(path, options = {}) {
    const isSessionEndpoint = path === '/web/session';

    // Garante que a sessão existe antes de rotas protegidas
    if (!isSessionEndpoint && !options.skipSessionCheck) {
      await this.ensureSession();
    }

    const headers = { ...(options.headers || {}) };

    if (!isSessionEndpoint && this._sessionCookie) {
      headers['Cookie'] = this._sessionCookie;
    }

    const method = (options.method || 'GET').toUpperCase();
    const isWriteMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
    if (!isSessionEndpoint && isWriteMethod && this._csrfToken) {
      headers['X-Noite-CSRF'] = this._csrfToken;
    }

    const res = await this._rawHttpRequest(path, {
      ...options,
      headers
    });

    // Trata expiração de sessão (401)
    if (res.statusCode === 401 && !options._isRetry && !isSessionEndpoint) {
      await this.ensureSession(true);
      return await this._requestJson(path, { ...options, _isRetry: true });
    }

    // Trata validação de CSRF expirada (403 específico de sessão)
    if (res.statusCode === 403 && !options._isRetry && !isSessionEndpoint) {
      const detail = (res.json && res.json.detail) ? String(res.json.detail) : '';
      if (detail.includes('Validação da sessão falhou') || detail.includes('CSRF')) {
        await this.ensureSession(true);
        return await this._requestJson(path, { ...options, _isRetry: true });
      }
      // Outros 403 (ex: "Mensagem não pertence à conversa ativa") NÃO são repetidos
      throw new Error(detail || 'Acesso negado.');
    }

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.json;
    }

    let detail = `HTTP ${res.statusCode}`;
    if (res.json && res.json.detail) {
      detail = res.json.detail;
    }
    throw new Error(detail);
  }

  /**
   * Inspeciona se a Noite API está ativa e operante, testando a inicialização de sessão.
   */
  async checkHealth() {
    try {
      await this.ensureSession();
      // Não expõe cookies ou tokens no objeto de retorno
      return { online: true, data: { product: 'Noite 2.0' } };
    } catch (err) {
      return { online: false, error: err.message };
    }
  }

  /**
   * Recupera a lista de conversas persistidas no SQLite.
   * Suporta fallback para /web/api/bootstrap caso o processo ativo não exponha
   * a rota dedicada /web/api/conversations.
   */
  async getConversations() {
    try {
      return await this._requestJson('/web/api/conversations');
    } catch (err) {
      if (err.message.includes('404') || err.message.includes('Not Found')) {
        const boot = await this._requestJson('/web/api/bootstrap');
        return boot && boot.conversations ? boot.conversations : [];
      }
      throw err;
    }
  }

  /**
   * Altera a conversa ativa na sessão do backend.
   */
  async selectConversation(conversationId) {
    return this._requestJson(`/web/api/conversations/${encodeURIComponent(conversationId)}/select`, {
      method: 'POST'
    });
  }

  /**
   * Recupera o histórico estendido de uma conversa.
   */
  async getHistory(conversationId) {
    return this._requestJson(`/web/api/conversations/${encodeURIComponent(conversationId)}/messages`);
  }

  /**
   * Salva feedback em uma mensagem (positive, negative ou null).
   */
  async submitFeedback(messageId, rating) {
    return this._requestJson('/web/api/feedback', {
      method: 'POST',
      body: { message_id: messageId, rating }
    });
  }

  /**
   * Cancela uma requisição de streaming em andamento.
   */
  cancelPrompt(conversationId) {
    const existing = this._activeRequests.get(conversationId);
    if (existing) {
      try {
        existing.destroy();
      } catch (_) {}
      this._activeRequests.delete(conversationId);
      return true;
    }
    return false;
  }

  /**
   * Dispara prompt e consome streaming SSE (/web/api/chat) com autenticação de sessão e CSRF.
   */
  sendPrompt(conversationId, prompt, callbacks = {}) {
    const { onChunk, onThinking, onActivity, onDone, onError } = callbacks;

    // Cancela requisição anterior desta mesma conversa se existir
    this.cancelPrompt(conversationId);

    const payload = JSON.stringify({
      conversation_id: conversationId,
      prompt: prompt
    });

    const dispatchError = (err) => {
      this._activeRequests.delete(conversationId);
      if (onError) onError(err);
    };

    // Garante que a sessão existe antes de conectar ao SSE
    this.ensureSession().then(() => {
      const reqOptions = {
        host: this.host,
        port: this.port,
        path: '/web/api/chat',
        method: 'POST',
        headers: {
          'Accept': 'text/event-stream',
          'Content-Type': 'application/json; charset=utf-8',
          'Content-Length': Buffer.byteLength(payload),
          'Cookie': this._sessionCookie || '',
          'X-Noite-CSRF': this._csrfToken || ''
        }
      };

      let buffer = '';

      const req = http.request(reqOptions, (res) => {
        if (res.statusCode !== 200) {
          let errBody = '';
          res.on('data', d => { errBody += d; });
          res.on('end', () => {
            let msg = `Erro da API: HTTP ${res.statusCode}`;
            try {
              const parsed = JSON.parse(errBody);
              if (parsed && parsed.detail) msg = parsed.detail;
            } catch (_) {
              if (errBody) msg = `${msg} - ${errBody}`;
            }
            dispatchError(new Error(msg));
          });
          return;
        }

        res.setEncoding('utf-8');

        res.on('data', (chunk) => {
          buffer += chunk;
          const lines = buffer.split('\n');
          buffer = lines.pop(); // Mantém linha incompleta no buffer

          let currentEvent = 'message';
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            if (trimmed.startsWith('event:')) {
              currentEvent = trimmed.slice(6).trim();
            } else if (trimmed.startsWith('data:')) {
              const rawData = trimmed.slice(5).trim();
              try {
                const data = JSON.parse(rawData);
                this._dispatchSsePacket(currentEvent, data, { onChunk, onThinking, onActivity, onDone, onError });
              } catch (_) {
                if (currentEvent === 'chunk' && onChunk) onChunk(rawData);
              }
            }
          }
        });

        res.on('end', () => {
          this._activeRequests.delete(conversationId);
        });

        res.on('error', (err) => {
          dispatchError(err);
        });
      });

      req.on('error', (err) => {
        dispatchError(err);
      });

      this._activeRequests.set(conversationId, req);
      req.write(payload);
      req.end();
    }).catch(err => {
      dispatchError(new Error(`Falha de autenticação ao conectar streaming: ${err.message}`));
    });

    return true;
  }

  _dispatchSsePacket(event, data, callbacks) {
    const { onChunk, onThinking, onActivity, onDone, onError } = callbacks;

    switch (event) {
      case 'chunk':
        if (onChunk && data && data.text) onChunk(data.text);
        break;
      case 'thinking':
        if (onThinking && data && data.text) onThinking(data.text);
        break;
      case 'activity':
        if (onActivity && data) onActivity(data);
        break;
      case 'done':
        if (onDone) onDone(data);
        break;
      case 'error':
        if (onError) onError(new Error(data && data.message ? data.message : 'Erro na geração.'));
        break;
      default:
        if (data && data.type === 'chunk' && onChunk) onChunk(data.text);
        if (data && data.type === 'done' && onDone) onDone(data);
        break;
    }
  }
}

module.exports = { BackendBridge };
