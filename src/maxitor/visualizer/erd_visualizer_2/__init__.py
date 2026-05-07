# src/maxitor/visualizer/erd_visualizer_2/__init__.py
"""
ERD viewer — graph-backed ERD export with Graphviz SVG, Cytoscape, and Mermaid
renderers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:func:`.erd_document_from_coordinator_graph` reads the current coordinator
graph and returns a graph document (cells) for one domain.
:mod:`.erd_html` injects CSS + an ES-module bootstrap and
:func:`.write_erd_html_from_coordinator` takes a production
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator` and an optional
:class:`~action_machine.domain.base_domain.BaseDomain`, reads graph vertices
at call time, and writes a standalone HTML file.

Renderers available in the generated HTML
──────────────────────────────────────────
- **Graphviz SVG** ✦ — DOT rendered directly through ``@hpcc-js/wasm-graphviz``.
- **Cytoscape.js** — graph renderer with dagre layout and interactive selection.
- **Mermaid** — ``erDiagram`` via Mermaid v11.
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
    DEFAULT_ERD_HTML_PATH,
    GRAPHVIZ_MODULE_URL,
    MERMAID_MODULE_URL,
    write_erd_html,
    write_erd_html_from_coordinator,
)

__all__ = [
    "DEFAULT_ERD_HTML_PATH",
    "GRAPHVIZ_MODULE_URL",
    "MERMAID_MODULE_URL",
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
