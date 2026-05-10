# packages/aoa-maxitor/src/aoa/maxitor/app/diagrams/shared/chrome.py
"""
Interchange viewer chrome — CSS injection for HTML exports.
"""

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_INTERCHANGE_CHROME_CSS = _PACKAGE_DIR / "interchange_chrome.css"


def read_interchange_chrome_css() -> str:
    """Return shared viewer chrome CSS (legend + bottom toolbar)."""

    return _INTERCHANGE_CHROME_CSS.read_text(encoding="utf-8")
