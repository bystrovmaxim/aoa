# src/maxitor/visualizer/shared/chrome.py

"""
Interchange viewer chrome — CSS / JS injection for HTML exports.

**PURPOSE**

Load shared viewer assets so graph and ERD standalone pages use the same chrome.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_INTERCHANGE_CHROME_CSS = _PACKAGE_DIR / "interchange_chrome.css"
_DETAIL_PANEL_JS = _PACKAGE_DIR / "detail_panel.js"


def read_interchange_chrome_css() -> str:
    """Return shared viewer chrome (left legend + right detail drawer) as CSS text."""
    return _INTERCHANGE_CHROME_CSS.read_text(encoding="utf-8")


def read_detail_panel_js() -> str:
    """
    Return shared right-side detail panel runtime as JS text.

    AI-CORE-BEGIN
    ROLE: Inline asset loader for standalone HTML exporters that cannot import external local files.
    OUTPUT: JavaScript defining ``window.InterchangeDetailPanel``.
    AI-CORE-END
    """
    return _DETAIL_PANEL_JS.read_text(encoding="utf-8")
