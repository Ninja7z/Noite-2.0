from __future__ import annotations

import json
from pathlib import Path

_THEME_PATH = Path(__file__).resolve().parent / "theme.json"
with _THEME_PATH.open(encoding="utf-8") as _theme_file:
    _THEME_DOCUMENT = json.load(_theme_file)

_THEMES = _THEME_DOCUMENT["qss"]
UI_TOKENS = {
    key: dict(_THEME_DOCUMENT[key]) for key in ("layout", "motion", "scrollbar")
}


def theme_colors(mode: str) -> dict[str, str]:
    return dict(_THEME_DOCUMENT["colors"][mode])


def _reference_styles(mode: str) -> str:
    colors = _THEME_DOCUMENT["colors"][mode]
    background = colors["background"]
    surface = colors["surface"]
    border = colors["border"]
    text = colors["text"]
    secondary = colors["secondary"]
    accent = colors["accent"]
    success = colors["success"]
    highlight_title_size = _THEME_DOCUMENT["typography"]["highlight_title"]
    scrollbar = UI_TOKENS["scrollbar"]
    rgb = tuple(int(accent[index : index + 2], 16) for index in (1, 3, 5))
    accent_tint = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.14)"
    wave = (_THEME_PATH.parent / "assets" / "waves" / f"{mode}.svg").as_posix()
    return "\n".join(
        (
            f"QWidget#mainPane {{ background-color: transparent; "
            f"border-image: url('{wave}') 0 0 0 0 stretch stretch; }}",
            "QFrame#welcome { background: transparent; border: 0; }",
            f"QWidget#sidebar, QWidget#iconRail {{ background: {surface}; }}",
            "QPushButton#navButton { text-align: left; padding-left: 14px; "
            "border-radius: 15px; }",
            f"QPushButton#navButton:checked {{ color: {text}; "
            f"background: {accent}; }}",
            f"QPushButton#navButton:focus, QPushButton#chip:focus, QToolButton:focus "
            f"{{ border: 2px solid {accent}; }}",
            f"QLabel#modePill {{ color: {text}; background: {surface}; "
            f"border: 1px solid {border}; border-radius: 18px; "
            "padding: 8px 14px; font-weight: 600; }",
            f"QLabel#userAvatar {{ color: {text}; background: {accent}; "
            "border-radius: 22px; min-width: 42px; max-width: 42px; "
            "min-height: 42px; max-height: 42px; font-size: 18px; font-weight: 700; }",
            f"QLabel#userName {{ color: {text}; font-weight: 600; }}",
            f"QLabel#footerDot {{ background: {accent}; border-radius: 4px; }}",
            f"QLabel#statusDot[severity='ok'] {{ background: {success}; border-radius: 5px; }}",
            f"QLabel#statusDot[severity='warn'] {{ background: {accent}; border-radius: 5px; }}",
            f"QLabel#statusDot[severity='error'] {{ background: {accent}; "
            "border-radius: 5px; }",
            f"QFrame#contextActivityPanel {{ background: {surface}; "
            f"border-left: 1px solid {border}; }}",
            "QFrame#highlightCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {surface},stop:1 {background}); border: 1px solid {border}; "
            "border-radius: 18px; }",
            f"QLabel#highlightTitle {{ color: {text}; "
            f"font-size: {highlight_title_size}px; font-weight: 700; }}",
            f"QLabel#highlightCopy {{ color: {secondary}; }}",
            f"QPushButton#highlightAction {{ color: white; background: {accent}; "
            "border: 0; border-radius: 13px; padding: 8px 13px; font-weight: 600; }",
            f"QPushButton#highlightAction:hover {{ background: {accent}; "
            f"border: 1px solid {text}; }}",
            f"QFrame#referenceContextCard, QFrame#referenceToolsCard "
            f"{{ background: {background}; border: 1px solid {border}; "
            "border-radius: 16px; }",
            f"QLabel#referenceContextValue {{ color: {text}; padding: 2px 0; }}",
            f"QPushButton#contextDetailsButton {{ color: {text}; background: transparent; "
            f"border: 1px solid {border}; border-radius: 12px; padding: 7px 10px; }}",
            f"QPushButton#contextDetailsButton:hover {{ border-color: {accent}; }}",
            f"QToolButton#referenceToolButton {{ color: {text}; text-align: left; "
            "background: transparent; border: 0; border-radius: 8px; padding: 4px; }",
            f"QToolButton#referenceToolButton:hover {{ background: {accent_tint}; }}",
            f"QToolButton#referenceToolButton:pressed {{ background: {accent}; }}",
            f"QToolButton#referenceToolButton:disabled {{ color: {secondary}; }}",
            f"QLabel#referenceContextCaption {{ color: {secondary}; font-size: 11px; }}",
            f"QFrame#thinkingPanel {{ background: {surface}; border: 1px solid {border}; "
            "border-radius: 12px; }",
            f"QFrame#composer[focused='true'] {{ border-color: {accent}; }}",
            f"QLabel#thinkingTitle {{ color: {secondary}; font-weight: 600; }}",
            f"QLabel#thinkingText {{ color: {secondary}; padding: 4px 0; }}",
            f"QToolButton#thinkingToggle {{ color: {secondary}; background: transparent; "
            "border: 0; padding: 2px; }",
            f"QTextBrowser#chat {{ color: {text}; }}",
            f"QPlainTextEdit#input:focus {{ border: 1px solid {accent}; "
            f"border-radius: 8px; }}",
            f"QPushButton#chip:pressed {{ color: {text}; background: {accent}; }}",
            "QScrollBar:vertical, QScrollBar:horizontal { background: transparent; "
            f"width: {scrollbar['width']}px; height: {scrollbar['width']}px; margin: 1px; }}",
            f"QScrollBar:vertical:hover {{ width: {scrollbar['hover_width']}px; }}",
            f"QScrollBar:horizontal:hover {{ height: {scrollbar['hover_width']}px; }}",
            f"QScrollBar::handle:vertical, QScrollBar::handle:horizontal "
            f"{{ background: {accent_tint}; border-radius: 5px; min-height: 26px; "
            "min-width: 26px; }}",
            f"QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover "
            f"{{ background: {accent}; }}",
            "QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, "
            "QScrollBar::sub-page { background: transparent; border: 0; width: 0; height: 0; }",
            "QLabel#status { border: 0; background: transparent; }",
            "QListWidget#conversationList::item { padding-left: 8px; }",
            "QPushButton#sendButton { border-radius: 23px; }",
        )
    )


def chat_document_styles(mode: str) -> str:
    colors = theme_colors(mode)
    return (
        f"body {{ color: {colors['text']}; "
        f"font-family: '{_THEME_DOCUMENT['typography']['family']}'; }}"
        "p { margin: 0 0 12px; }"
        f".message-name {{ color: {colors['accent']}; font-size: 12px; font-weight: 600; }}"
        f".message-user-name {{ color: {colors['secondary']}; }}"
        f".message-body {{ color: {colors['text']}; font-size: 14px; line-height: 1.5; }}"
        f".message-user {{ border-left: 2px solid {colors['accent']}; padding-left: 12px; }}"
        f"pre {{ background: {colors['surface']}; border: 1px solid {colors['border']}; "
        "border-radius: 8px; padding: 10px; white-space: pre-wrap; }"
        f"blockquote {{ color: {colors['secondary']}; border-left: 2px solid {colors['border']}; "
        "margin-left: 0; padding-left: 12px; }"
        f"code {{ background: {colors['surface']}; border-radius: 4px; padding: 1px 3px; }}"
        f"a {{ color: {colors['accent']}; }}"
    )

DARK_THEME = _THEMES["dark"] + _reference_styles("dark")
LIGHT_THEME = _THEMES["light"] + _reference_styles("light")
