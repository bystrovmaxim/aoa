# src/maxitor/visualizer/erd_visualizer/__init__.py
"""
ERD viewer — AntV **X6** ER-style nodes (see X6 practices ER example) with a G6-like shell
(zoom toolbar, properties panel, LOD on scale).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:class:`ErdGraphPayload` (:mod:`.erd_graph_data`) holds entity/relationship specs;
:func:`.erd_payload_to_x6_document` serializes them to X6 ``fromJSON`` shape.
:mod:`.erd_html` injects CSS + an ES-module bootstrap (dynamic ``import`` of X6) and
:func:`.write_erd_html_from_coordinator`, which takes a production
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator` and a
:class:`~action_machine.domain.base_domain.BaseDomain`, builds the ER payload from interchange
vertices, and writes HTML.
"""

from __future__ import annotations

from .erd_graph_data import (
    ErdEdgeSpec,
    ErdEntitySpec,
    ErdGraphPayload,
    build_demo_erd_payload,
    erd_payload_from_coordinator_for_domain,
    erd_payload_to_x6_document,
)
from .erd_html import (
    DEFAULT_ERD_HTML_PATH,
    ELK_MODULE_URL,
    X6_MODULE_URL,
    write_erd_html,
    write_erd_html_from_coordinator,
)

__all__ = [
    "DEFAULT_ERD_HTML_PATH",
    "ELK_MODULE_URL",
    "X6_MODULE_URL",
    "ErdEdgeSpec",
    "ErdEntitySpec",
    "ErdGraphPayload",
    "build_demo_erd_payload",
    "erd_payload_from_coordinator_for_domain",
    "erd_payload_to_x6_document",
    "write_erd_html",
    "write_erd_html_from_coordinator",
]
