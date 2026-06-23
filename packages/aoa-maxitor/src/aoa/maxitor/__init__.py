# packages/aoa-maxitor/src/aoa/maxitor/__init__.py
"""
Maxitor — sample graph helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide helpers for the graph visualizer HTML export path built on ``NodeGraphCoordinator``
and the FastAPI-backed React SPA (see :mod:`aoa.maxitor.api.app`).

═══════════════════════════════════════════════════════════════════════════════
REACT SPA + FASTAPI
═══════════════════════════════════════════════════════════════════════════════

Run the backend with ``uv run task maxitor-api`` and the frontend with ``npm run dev``
from ``packages/aoa-maxitor/client``. Interchange and ERD viewers render in the SPA
from JSON under ``/api/v1`` (see ``aoa.maxitor.api.app``).
"""

from __future__ import annotations

from aoa.maxitor.node_build import build_sample_node_graph_coordinator, export_samples_graph_html

__all__ = [
    "build_sample_node_graph_coordinator",
    "export_samples_graph_html",
]
