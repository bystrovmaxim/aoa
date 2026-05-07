# src/maxitor/visualizer/erd_visualizer_2/__init__.py
"""
ERD viewer — graph-backed ERD export with X6, Graphviz SVG, Cytoscape,
Mermaid, and D2 renderers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:func:`.erd_document_from_coordinator_graph` reads the current coordinator
graph and serializes an X6 ``fromJSON`` shape for one domain.
:mod:`.erd_html` injects CSS + an ES-module bootstrap and
:func:`.write_erd_html_from_coordinator` takes a production
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator` and an optional
:class:`~action_machine.domain.base_domain.BaseDomain`, reads graph vertices
at call time, and writes a standalone HTML file.

Renderers available in the generated HTML
──────────────────────────────────────────
- **X6 + Dagre** — AntV X6 canvas, Dagre LR/TB layout.
- **Graphviz SVG** ✦ — DOT rendered directly through ``@hpcc-js/wasm-graphviz``.
- **Cytoscape.js** — graph renderer with dagre layout and interactive selection.
- **Mermaid** — ``erDiagram`` via Mermaid v11.
- **D2** — ``sql_table`` shapes via ``@terrastruct/d2`` WASM.
- **D2 source** — raw D2 text.
"""

from __future__ import annotations

from .erd_graph_data import (
    ErdEdgeSpec,
    ErdEntitySpec,
    ErdGraphPayload,
    build_demo_erd_payload,
    domain_classes_from_coordinator,
    erd_document_from_coordinator_graph,
    erd_payload_from_coordinator_for_domain,
    erd_payload_to_x6_document,
)
from .erd_html import (
    D2_MODULE_URL,
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
    "D2_MODULE_URL",
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
    "domain_classes_from_coordinator",
    "erd_document_from_coordinator_graph",
    "erd_payload_from_coordinator_for_domain",
    "erd_payload_to_x6_document",
    "write_erd_html",
    "write_erd_html_from_coordinator",
]
