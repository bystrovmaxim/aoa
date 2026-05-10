# packages/aoa-maxitor/src/aoa/maxitor/api/main.py
"""
CLI entry for running the Maxitor FastAPI backend locally.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a small development convenience around ``uvicorn``. Production ASGI
hosting should import :mod:`aoa.maxitor.api.app`.
"""

from __future__ import annotations

import os

import uvicorn


def run() -> None:
    """
    Run the Maxitor API with uvicorn for local development.

    AI-CORE-BEGIN
    ROLE: Console-script entry point for developers who want ``uv run maxitor-api``.
    SIDE EFFECTS: Starts an HTTP server and blocks until interrupted.
    AI-CORE-END
    """
    host = os.environ.get("MAXITOR_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_raw = os.environ.get("MAXITOR_API_PORT", "8000").strip()
    port = int(port_raw) if port_raw else 8000
    uvicorn.run("aoa.maxitor.api.app:app", host=host, port=port)
