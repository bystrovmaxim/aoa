# packages/aoa-maxitor/src/aoa/maxitor/diagrams/erd/__init__.py
"""
ERD data — serializers for interchange coordinator domains.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose graph-shaped payloads for the Maxitor React ERD viewer. The SPA loads JSON from
``GET /api/v1/erd/*`` and renders with bundled assets under ``client/src/.../diagram-viewer/erd/shell``.
This package does **not** emit HTML; that lives in the frontend.
"""

from __future__ import annotations

from aoa.maxitor.model.app_view.actions.build_erd_graph_data_action import (
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

__all__ = [
    "ErdEdgeSpec",
    "ErdEntitySpec",
    "ErdGraphPayload",
    "build_demo_erd_payload",
    "domain_classes_from_coordinator",
    "domain_qualnames_from_interchange_nx",
    "erd_document_from_coordinator_graph",
    "erd_payload_from_coordinator_for_domain",
    "erd_payload_to_x6_document",
    "node_graph_coordinator_from_interchange_nx",
]
