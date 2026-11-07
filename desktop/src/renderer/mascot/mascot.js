/**
 * Noite Desktop 2.0 - Lógica do Mascote Flutuante.
 */
'use strict';

document.addEventListener('DOMContentLoaded', async () => {
  const canvas = document.getElementById('robotCanvas');
  const bubble = document.getElementById('speechBubble');
  const robot = new RobotArt(canvas);

  robot.start();

  const stateLabels = {
    idle: 'Noite ativa',
    thinking: 'Pensando...',
    working: 'Gerando resposta...',
    done: 'Concluído!',
    error: 'Atenção necessária',
    listening: 'Ouvindo...'
  };

  function updateBubble(state, explicitText = null) {
    if (!bubble) return;
    const text = explicitText || stateLabels[state] || 'Noite 2.0';
    bubble.textContent = text;

    if (state !== 'idle' || explicitText) {
      bubble.classList.add('is-visible');
    } else {
      bubble.classList.remove('is-visible');
    }
  }

  // Interação com a API segura exposta pelo Preload
  if (window.noiteDesktop && window.noiteDesktop.mascot) {
    // 1. Obtém estado inicial
    try {
      const initialState = await window.noiteDesktop.mascot.getState();
      robot.setState(initialState);
      updateBubble(initialState);
    } catch (_) {}

    // 2. Inscreve-se em mudanças de estado
    window.noiteDesktop.mascot.onStateChange((state) => {
      robot.setState(state);
      updateBubble(state);
      if (state === 'done') {
        setTimeout(() => {
          if (robot.state === 'done') {
            robot.setState('idle');
            updateBubble('idle');
          }
        }, 2200);
      }
    });

    // 3. Clique no robô abre a janela principal do chat
    canvas.addEventListener('click', (e) => {
      e.stopPropagation();
      window.noiteDesktop.mascot.toggleChat();
    });
  }

  // Feedback de hover no mascote
  canvas.addEventListener('mouseenter', () => {
    updateBubble(robot.state, 'Clique para abrir o Chat (Alt+C)');
    bubble.classList.add('is-visible');
  });

  canvas.addEventListener('mouseleave', () => {
    if (robot.state === 'idle') {
      bubble.classList.remove('is-visible');
    } else {
      updateBubble(robot.state);
    }
  });
});
