"""Shared dark-violet visual identity for the Noite desktop interface.

Design tokens extraídos das referências em docs/reference/:
fundo quase-preto azulado, painéis arredondados em violeta profundo,
primária roxa em gradiente, texto lavanda e estados em verde/âmbar/vermelho.
"""

DARK_THEME = """
QWidget { background: #0f0d1e; color: #ece9fb; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { background: transparent; }
QWidget#appRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121024, stop:1 #0d0b1c);
    border: 1px solid #302858; border-radius: 18px; }
QWidget#mainPane { background: transparent; }
QFrame#windowChrome { background: #100e1e; border-bottom: 1px solid #262048;
    border-top-left-radius: 18px; border-top-right-radius: 18px; }
QLabel#chromeMoon { color: #8b5cff; font-size: 25px; }
QLabel#chromeName { color: #f2eefc; font-size: 14px; font-weight: 650; }
QLabel#chromeVersion { color: #8d85b0; font-size: 11px; }
QPushButton#windowControl, QPushButton#windowCloseControl {
    background: transparent; color: #d5d0e8; border: 0; border-radius: 8px;
    min-width: 38px; max-width: 38px; min-height: 30px; max-height: 30px;
    padding: 0; font-size: 15px; }
QPushButton#windowControl:hover { background: #282344; }
QPushButton#windowCloseControl:hover { background: #b83250; color: white; }

/* ---------- Barra lateral ---------- */
QWidget#sidebar { background: #161228; border-right: 1px solid #262048; }
QWidget#iconRail { background: #161228; border-right: 1px solid #262048; }
QLabel#brandMark { background: transparent; color: #8b6bff; border: 0;
    font-size: 26px; font-weight: 600; padding: 0; }
QLabel#sideTitle { font-size: 19px; font-weight: 650; color: #f2eefc; }
QPushButton#navButton { background: transparent; color: #b9b2d6; text-align: left;
    border: 0; border-radius: 10px; padding: 10px 14px; font-size: 13px; }
QPushButton#navButton:hover { background: #221b44; color: #ffffff; }
QPushButton#navButton:pressed { background: #2a2154; }
QPushButton#sideButton { background: transparent; color: #cbc6e2; text-align: left;
    border: 0; border-radius: 9px; padding: 0 10px; }
QPushButton#sideButton:hover { background: #241d47; color: white; }
QPushButton#sideButton:disabled { color: #6b6588; background: transparent; }
QLabel#sectionLabel, QLabel#contextSection { color: #8d85b0; font-size: 10px;
    font-weight: 700; padding-top: 13px; letter-spacing: 1px; background: transparent; }
QLabel#projectTile, QLabel#contextFile { color: #b4acce; padding: 2px 4px; }
QListWidget#conversationList, QListWidget#activityEvents { background: transparent; border: 0;
    outline: 0; color: #d5d0e8; }
QListWidget#conversationList::item, QListWidget#activityEvents::item {
    padding: 9px 10px; border-radius: 9px; margin: 1px 0; }
QListWidget#conversationList::item:selected, QListWidget#activityEvents::item:selected {
    background: #2b2354; color: #ffffff; }
QListWidget#conversationList::item:hover, QListWidget#activityEvents::item:hover {
    background: #221b44; }
QFrame#privacyCard { background: #191430; border: 1px solid #2b2350; border-radius: 14px; }
QLabel#sideNote { color: #a49dc4; font-size: 11px; border: 0; padding: 0; }
QLabel#privacyTitle { color: #e6e1f5; font-size: 12px; font-weight: 600; }

QLabel#title { font-size: 16px; font-weight: 650; color: #f2eefc; }
QLabel#conversationTitle { color: #b9b2d6; font-size: 12px; }
QLabel#status { color: #c8c1e2; background: #191430; border: 1px solid #2b2350;
    border-radius: 12px; padding: 6px 12px; font-size: 11px; }
QComboBox#modelPill { background: #191430; border: 1px solid #35295e; border-radius: 17px;
    padding: 7px 14px; color: #e9e3f0; font-size: 12px; min-width: 180px; }
QComboBox#modelPill:hover { border-color: #7c5cff; }
QComboBox#modelPill::drop-down { border: 0; width: 22px; }
QComboBox#modelPill QAbstractItemView { background: #1a1630; border: 1px solid #35295e;
    selection-background-color: #2b2354; color: #ece9fb; outline: 0; }
QToolButton#railButton, QToolButton#collapseNavigationButton,
QToolButton#toggleActivityButton, QToolButton#activityDetailsToggle {
    color: #a49dc4; background: transparent; border: 0; border-radius: 9px; padding: 7px; }
QToolButton#railButton { font-size: 17px; min-height: 32px; }
QToolButton#railButton:hover, QToolButton#collapseNavigationButton:hover,
QToolButton#toggleActivityButton:hover, QToolButton#activityDetailsToggle:hover {
    color: #fff; background: #221b44; }

/* ---------- Estado vazio ---------- */
QLabel#welcomeMark { color: #8b6bff; font-size: 88px; }
QLabel#welcomeTitle { color: #f4f0fd; font-size: 44px; font-weight: 700; }
QLabel#welcomeHint { color: #a49dc4; font-size: 23px; }
QFrame#ollamaBanner { background: #241d3f; border: 1px solid #4c3a7d; border-radius: 14px; }
QLabel#ollamaBannerText { color: #e3ddf5; font-size: 12px; }
QPushButton#primaryButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 #8b5cf6, stop:1 #6d4aff); color: white; border: 0; border-radius: 16px;
    padding: 8px 18px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #8f74ff; }
QPushButton#primaryButton:disabled { background: #3a3260; color: #8d86aa; }
QPushButton#ghostButton { background: transparent; color: #c8c1e2;
    border: 1px solid #3a3260; border-radius: 16px; padding: 7px 16px; }
QPushButton#ghostButton:hover { border-color: #7c5cff; color: #ffffff; }
QPushButton#chip { background: #171330; color: #d5d0e8; border: 1px solid #2f2856;
    border-radius: 17px; padding: 9px 18px; font-size: 12px; }
QPushButton#chip:hover { border-color: #7c5cff; color: #ffffff; background: #1c1740; }

/* ---------- Conversa ---------- */
QTextBrowser#chat { background: transparent; border: 0; padding: 6px 10px;
    selection-background-color: #574673; }
QLabel#progress { color: #b9b2d6; font-size: 11px; }
QLabel#typing { color: #a49dc4; font-size: 12px; }

/* ---------- Compositor ---------- */
QFrame#composer { background: #191430; border: 1px solid #352c5e; border-radius: 22px; }
QLabel#composerProject { color: #c8c1e2; font-weight: 600; font-size: 11px; }
QPlainTextEdit#input { background: transparent; border: 0; padding: 10px 4px;
    font-size: 14px; color: #ece9fb; selection-background-color: #574673; }
QPushButton#sendButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #8b5cf6, stop:1 #6d4aff); color: white; border: 0;
    border-radius: 22px; font-size: 20px; font-weight: 600; }
QPushButton#sendButton:hover { background: #8f74ff; }
QPushButton#sendButton:disabled { background: #3a3260; color: #8d86aa; }
QPushButton#cancelButton { background: #2a1631; color: #f0a5b8; border: 1px solid #6b2f45;
    border-radius: 16px; padding: 9px 16px; font-weight: 600; }
QPushButton#cancelButton:hover { background: #3a1d42; }
QPushButton:disabled { background: #221d3a; color: #6b6588; }
QLabel#footerHint, QLabel#brandFooter { font-size: 10px; color: #8d86aa; padding-left: 4px; }

/* ---------- Painel de contexto ---------- */
QWidget#contextActivityPanel { background: #161228; border-left: 1px solid #262048; }
QLabel#contextPanelTitle { color: #f2eefc; font-size: 15px; font-weight: 650; }
QLabel#contextModel, QLabel#contextProject { color: #d9d1ec; padding: 7px 0; }
QLabel#emptyActivity { color: #8d86aa; font-size: 12px; padding: 5px 0; }
QLabel#activityDetails { background: #1e1838; border-radius: 9px; padding: 10px; color: #bfb7d8; }
QLabel#contextPanelHint, QLabel#paletteHint, QLabel#paletteFooter, QLabel#muted { color: #8d86aa; }

/* ---------- Diálogos (paleta, MCP, configurações) ---------- */
QDialog { background: #161228; color: #ece9fb; }
QScrollArea { border: 0; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox {
    background: #12102a; border: 1px solid #332c5c; border-radius: 10px;
    padding: 8px 12px; color: #ece9fb; selection-background-color: #574673; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus { border-color: #7c5cff; }
QListWidget { background: #12102a; border: 1px solid #332c5c; border-radius: 10px;
    outline: 0; color: #d5d0e8; }
QListWidget::item { padding: 9px 12px; border-radius: 8px; }
QListWidget::item:selected { background: #2b2354; color: #ffffff; }
QListWidget::item:hover { background: #221b44; }
QComboBox { background: #12102a; border: 1px solid #332c5c; border-radius: 10px;
    padding: 7px 12px; color: #e9e3f0; }
QComboBox QAbstractItemView { background: #1a1630; color: #ece9fb;
    selection-background-color: #2b2354; }
QPushButton { background: #241d44; color: #e6e1f5; border: 1px solid #352c5e;
    border-radius: 10px; padding: 8px 16px; }
QPushButton:hover { border-color: #7c5cff; }
QDialogButtonBox QPushButton { min-width: 84px; }
QToolTip { background: #241d44; color: #ece9fb; border: 1px solid #352c5c; padding: 5px; }
QMenu { background: #1a1630; color: #ece9fb; border: 1px solid #332c5c; }
QMenu::item:selected { background: #2b2354; }

/* ---------- Dock de projeto ---------- */
QDockWidget { color: #d5d0e8; }
QDockWidget::title { background: #161228; padding: 8px 12px; border-bottom: 1px solid #262048; }
QDockWidget QTreeView, QDockWidget QTabWidget, QDockWidget QLineEdit,
QDockWidget QListWidget { background: #12102a; }

/* ---------- Barras de rolagem ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2c2552; border-radius: 5px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #443a78; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2c2552; border-radius: 5px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: #443a78; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


LIGHT_THEME = DARK_THEME
for _dark, _light in {
    "#0f0d1e": "#f4f2fa",
    "#12102a": "#fffefe",
    "#121024": "#fbfaff",
    "#100e1e": "#eeebf5",
    "#302858": "#dcd7e9",
    "#282344": "#e4def5",
    "#0d0b1c": "#f0edf8",
    "#161228": "#eeebf5",
    "#262048": "#dcd7e9",
    "#ece9fb": "#29253b",
    "#f2eefc": "#29253b",
    "#b9b2d6": "#5e5873",
    "#221b44": "#e4def5",
    "#2a2154": "#d9cef4",
    "#cbc6e2": "#514b66",
    "#6b6588": "#858098",
    "#8d85b0": "#756f89",
    "#b4acce": "#5b5570",
    "#d5d0e8": "#38344a",
    "#2b2354": "#ded5f3",
    "#191430": "#f8f6fc",
    "#2b2350": "#ded9e9",
    "#a49dc4": "#746e87",
    "#c8c1e2": "#514b66",
    "#35295e": "#d5cdea",
    "#e9e3f0": "#302b41",
    "#1a1630": "#f4f1fa",
    "#574673": "#ddd3f4",
    "#241d3f": "#f1edfa",
    "#4c3a7d": "#c9b9ec",
    "#e3ddf5": "#39334c",
    "#171330": "#fffefe",
    "#2f2856": "#d8d1e8",
    "#1c1740": "#e8e1f7",
    "#241d44": "#eee9f7",
    "#241d47": "#e8e2f3",
    "#2a1631": "#f8eaf0",
    "#352c5e": "#d2cbe3",
    "#352c5c": "#d2cbe3",
    "#332c5c": "#d2cbe3",
    "#1e1838": "#e9e4f2",
    "#bfb7d8": "#514b66",
    "#2c2552": "#d5cdea",
    "#443a78": "#b9a9e1",
    "#221d3a": "#e5e0ed",
    "#3a1d42": "#f2e5ed",
    "#3a3260": "#d9d3e6",
    "#6b2f45": "#d7aebc",
    "#d9d1ec": "#433e55",
    "#e6e1f5": "#39344c",
    "#8d86aa": "#716b83",
}.items():
    LIGHT_THEME = LIGHT_THEME.replace(_dark, _light)

