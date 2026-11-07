/**
 * Noite Desktop 2.0 - Renderizador de Pixel Art do Robô Mascote.
 * Baseado estritamente nas geometrias originais de MascotFace (src/noite/mascot.py).
 */
'use strict';

class RobotArt {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = 'idle';
    this.isBlinking = false;
    this._phase = 0;
    this._animFrame = null;
    this._timer = null;

    // Configuração de renderização pixelada limpa
    this.ctx.imageSmoothingEnabled = false;
  }

  start() {
    this._timer = setInterval(() => {
      this._phase = (this._phase + 1) % 8;
      this.isBlinking = this._phase === 0;
      this.render();
    }, 900);
    this.render();
  }

  stop() {
    if (this._timer) clearInterval(this._timer);
    if (this._animFrame) cancelAnimationFrame(this._animFrame);
  }

  setState(newState) {
    this.state = newState;
    this.render();
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.clearRect(0, 0, w, h);

    const side = Math.min(w, h);
    const scale = Math.max(1, Math.floor(side / 30));
    const x0 = Math.floor((w - 26 * scale) / 2);
    const y0 = Math.floor((h - 27 * scale) / 2);

    const px = (x, y, pw, ph, color) => {
      ctx.fillStyle = color;
      ctx.fillRect(x0 + x * scale, y0 + y * scale, pw * scale, ph * scale);
    };

    // 1. Antena e módulos de áudio laterais
    px(12, 0, 2, 2, '#26334f');
    px(11, 1, 4, 1, '#9fb8ee');
    px(2, 8, 2, 9, '#26334f');
    px(22, 8, 2, 9, '#26334f');
    px(1, 10, 2, 5, '#37c8ff');
    px(23, 10, 2, 5, '#37c8ff');

    // 2. Silhueta do capacete branco
    px(7, 3, 12, 1, '#202a43');
    px(4, 4, 18, 1, '#202a43');
    px(3, 5, 20, 2, '#dce6ff');
    px(2, 7, 22, 11, '#202a43');
    px(3, 18, 20, 2, '#202a43');
    px(5, 20, 16, 1, '#202a43');
    px(5, 5, 16, 1, '#ffffff');
    px(4, 6, 18, 2, '#f8faff');
    px(3, 8, 20, 9, '#f8faff');
    px(4, 17, 18, 2, '#f8faff');
    px(6, 19, 14, 1, '#c9d6f5');
    px(6, 7, 14, 1, '#c8d6f8');

    // 3. Visor de vidro escuro
    px(5, 8, 16, 9, '#111a31');
    px(6, 8, 14, 1, '#263454');
    px(6, 16, 14, 1, '#1e2a49');
    px(7, 9, 12, 6, '#0b1328');
    px(8, 9, 2, 1, '#34466e');

    // 4. Olhos e expressões em pixel art azul-ciano
    let eyeColor = (this.state === 'working' || this.state === 'thinking') ? '#69e8ff' : '#46bfff';
    if (this.state === 'error') eyeColor = '#ff708e';
    if (this.state === 'done') eyeColor = '#7cf4bd';

    if (this.isBlinking && this.state !== 'thinking') {
      // Olhos piscando (traço horizontal)
      px(8, 12, 3, 1, eyeColor);
      px(15, 12, 3, 1, eyeColor);
    } else if (this.state === 'thinking') {
      // Olhar curioso para cima/lado
      px(8, 10, 3, 4, eyeColor);
      px(15, 9, 3, 4, eyeColor);
    } else if (this.state === 'error') {
      // Olhar de preocupação / erro
      px(8, 10, 3, 3, eyeColor);
      px(15, 10, 3, 3, eyeColor);
      px(8, 9, 1, 1, eyeColor);
      px(17, 9, 1, 1, eyeColor);
    } else if (this.state === 'done') {
      // Olhos sorridentes em arco
      px(8, 11, 3, 2, eyeColor);
      px(15, 11, 3, 2, eyeColor);
    } else {
      // Olhar normal idle
      px(8, 10, 3, 4, eyeColor);
      px(15, 10, 3, 4, eyeColor);
    }

    // 5. Corpo, ombros, braços e pés
    px(8, 21, 10, 1, '#202a43');
    px(7, 22, 12, 4, '#202a43');
    px(8, 22, 10, 3, '#f3f6ff');
    px(5, 22, 2, 3, '#202a43');
    px(4, 23, 3, 2, '#dce6ff');
    px(20, 22, 2, 3, '#202a43');
    px(19, 23, 3, 2, '#dce6ff');
    px(10, 23, 1, 2, '#4dcfff');
    px(15, 23, 1, 2, '#4dcfff');
    px(8, 26, 4, 1, '#202a43');
    px(14, 26, 4, 1, '#202a43');
    px(7, 27, 5, 1, '#aebde0');
    px(14, 27, 5, 1, '#aebde0');

    // 6. LED de estado no peito
    px(12, 24, 2, 1, eyeColor);
  }
}

// Exportação compatível com navegador e testes
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RobotArt };
}
