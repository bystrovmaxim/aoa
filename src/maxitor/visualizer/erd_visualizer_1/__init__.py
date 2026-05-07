# src/maxitor/visualizer/erd_visualizer_1/__init__.py
"""
ERD viewer — graph-backed ERD export with X6, Mermaid, Graphviz, and Dagre renderers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:func:`.erd_document_from_coordinator_graph` reads the current coordinator graph and
serializes an X6 ``fromJSON`` shape for one domain. :mod:`.erd_html` injects CSS +
an ES-module bootstrap (dynamic imports of X6, ELK, Dagre, Mermaid, and Graphviz)
and :func:`.write_erd_html_from_coordinator`, which takes a production
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator` and a
:class:`~action_machine.domain.base_domain.BaseDomain`, reads graph vertices at call
time, and writes a standalone HTML file.

Renderers available in the generated HTML
──────────────────────────────────────────
- **X6 (interactive)** — AntV X6 canvas with port-based ER-table nodes.
- **Mermaid** — ``erDiagram`` via Mermaid v11.
- **Graphviz SVG** — full HTML-label DOT rendered via ``@hpcc-js/wasm-graphviz``.

Layout engines available for the X6 renderer
─────────────────────────────────────────────
- ELK Right / Down / Tree / Stress / Force  (``elkjs``)
- Dagre LR / TB  (``@dagrejs/dagre``, pure JS, recommended ✦)
- Grid  (built-in BFS component layout)
- Graphviz-backed X6: Dot LR/TB, Neato, FDP, SFDP, Circo, Twopi
"""

from __future__ import annotations

from .erd_graph_data import (
    ErdEdgeSpec,
    ErdEntitySpec,
    ErdGraphPayload,
    build_demo_erd_payload,
    erd_document_from_coordinator_graph,
    erd_payload_from_coordinator_for_domain,
    erd_payload_to_x6_document,
)
from .erd_html import (
    DAGRE_MODULE_URL,
    DEFAULT_ERD_HTML_PATH,
    ELK_MODULE_URL,
    GRAPHVIZ_MODULE_URL,
    MERMAID_MODULE_URL,
    X6_MODULE_URL,
    write_erd_html,
    write_erd_html_from_coordinator,
)

__all__ = [
    "DAGRE_MODULE_URL",
    "DEFAULT_ERD_HTML_PATH",
    "ELK_MODULE_URL",
    "GRAPHVIZ_MODULE_URL",
    "MERMAID_MODULE_URL",
    "X6_MODULE_URL",
    "ErdEdgeSpec",
    "ErdEntitySpec",
    "ErdGraphPayload",
    "build_demo_erd_payload",
    "erd_document_from_coordinator_graph",
    "erd_payload_from_coordinator_for_domain",
    "erd_payload_to_x6_document",
    "write_erd_html",
    "write_erd_html_from_coordinator",
]
