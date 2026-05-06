# src/maxitor/visualizer/erd_visualizer/__init__.py
"""
ERD viewer — reusable G6 shell (canvas, zoom, detail panel) with **data-only** graph assembly.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:class:`ErdGraphPayload` (:mod:`.erd_graph_data`) owns entity/relationship records and
serialization to interchange-style ``nodes`` / ``edges`` dictionaries.
:mod:`.erd_html` injects payloads into ``template.html`` and writes ``erd.html`` under
``archive/logs`` by default (:data:`DEFAULT_ERD_HTML_PATH`).
"""

from __future__ import annotations

from .erd_graph_data import (
    ErdEdgeSpec,
    ErdEntitySpec,
    ErdGraphPayload,
    build_demo_erd_payload,
    erd_payload_to_g6_records,
)
from .erd_html import (
    DEFAULT_ERD_HTML_PATH,
    G6_CDN_URL,
    write_erd_html,
)

__all__ = [
    "DEFAULT_ERD_HTML_PATH",
    "ErdEdgeSpec",
    "ErdEntitySpec",
    "ErdGraphPayload",
    "G6_CDN_URL",
    "build_demo_erd_payload",
    "erd_payload_to_g6_records",
    "write_erd_html",
]
