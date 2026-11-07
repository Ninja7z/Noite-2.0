/**
 * Noite Desktop 2.0 - Integração com Bandeja do Sistema (Windows Tray).
 */
'use strict';

const path = require('node:path');
const { Tray, Menu, app } = require('electron');
const { toggleChatWindow, getWindows, createMascotWindow } = require('./windows');

let tray = null;

function setupTray() {
  if (tray) return tray;

  const iconPath = path.resolve(__dirname, '../../../assets/noite.ico');

  try {
    tray = new Tray(iconPath);
  } catch (err) {
    console.warn('[Tray] Não foi possível carregar o ícone da bandeja:', err.message);
    return null;
  }

  tray.setToolTip('Noite 2.0 - Assistente Desktop');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Abrir Noite (Alt+C)',
      click: () => toggleChatWindow()
    },
    {
      label: 'Alternar Mascote',
      click: () => {
        const { mascotWindow } = getWindows();
        if (mascotWindow && !mascotWindow.isDestroyed()) {
          if (mascotWindow.isVisible()) {
            mascotWindow.hide();
          } else {
            mascotWindow.show();
          }
        } else {
          createMascotWindow();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Sair da Noite',
      click: () => {
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    toggleChatWindow();
  });

  return tray;
}

function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}

module.exports = {
  setupTray,
  destroyTray
};
