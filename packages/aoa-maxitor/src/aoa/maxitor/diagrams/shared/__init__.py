# packages/aoa-maxitor/src/aoa/maxitor/diagrams/shared/__init__.py

"""
Shared interchange viewer assets (injected CSS for graph + ERD HTML shells).
"""

from __future__ import annotations

from pathlib import Path

_CHROME_CSS_PATH = Path(__file__).resolve().parent / "interchange_chrome.css"


def read_interchange_chrome_css() -> str:
    """Return shared viewer chrome CSS (legend + bottom toolbar)."""
    return _CHROME_CSS_PATH.read_text(encoding="utf-8")


__all__ = ["read_interchange_chrome_css"]
