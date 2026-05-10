# packages/aoa-maxitor/src/aoa/maxitor/diagrams/erd/__init__.py
"""
ERD viewer — graph-backed ERD export with Graphviz SVG, Cytoscape, and Mermaid
renderers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:class:`~aoa.maxitor.model.app_view.actions.build_erd_graph_data_action.BuildErdGraphDataAction`
and related helpers prepare ``erd_data``; :mod:`.html_page` injects CSS + an ES-module bootstrap;
:func:`~.html_page.erd_html_string` returns standalone HTML consumed by the FastAPI backend.

Renderers available in the generated HTML
──────────────────────────────────────────

- **Graphviz SVG** — DOT rendered directly through ``@hpcc-js/wasm-graphviz``.
- **Cytoscape.js** — graph renderer with dagre layout and interactive selection.
- **Mermaid** — ``erDiagram`` via Mermaid v11.
"""

from __future__ import annotations

from aoa.maxitor.model.app_view.actions.build_erd_graph_data_action import (
    BuildErdGraphDataAction,
    ErdEdgeSpec,
    ErdEntitySpec,
    ErdGraphPayload,
    build_demo_erd_payload,
    domain_classes_from_coordinator,
    domain_qualnames_from_interchange_nx,
    erd_document_from_coordinator_graph,
    erd_payload_from_coordinator_for_domain,
    erd_payload_to_x6_document,
    node_graph_coordinator_from_interchange_nx,
)

from .html_page import GRAPHVIZ_MODULE_URL, MERMAID_MODULE_URL, erd_html_string

__all__ = [
    "GRAPHVIZ_MODULE_URL",
    "MERMAID_MODULE_URL",
    "BuildErdGraphDataAction",
    "ErdEdgeSpec",
    "ErdEntitySpec",
    "ErdGraphPayload",
    "build_demo_erd_payload",
    "domain_classes_from_coordinator",
    "domain_qualnames_from_interchange_nx",
    "erd_document_from_coordinator_graph",
    "erd_html_string",
    "erd_payload_from_coordinator_for_domain",
    "erd_payload_to_x6_document",
    "node_graph_coordinator_from_interchange_nx",
]
