# src/maxitor/visualizer/shared/chrome.py

"""
Interchange viewer chrome — CSS injection for HTML exports.

**PURPOSE**

Load ``interchange_chrome.css`` (left legend + right detail drawer) so graph and ERD
standalone pages share one stylesheet fragment.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_INTERCHANGE_CHROME_CSS = _PACKAGE_DIR / "interchange_chrome.css"


def read_interchange_chrome_css() -> str:
    """Return shared viewer chrome (left legend + right detail drawer) as CSS text."""
    return _INTERCHANGE_CHROME_CSS.read_text(encoding="utf-8")
