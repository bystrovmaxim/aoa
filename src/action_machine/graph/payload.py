# src/action_machine/graph/payload.py
"""
Transport objects between inspectors and ``GraphCoordinator``.

``EdgeInfo`` and ``FacetPayload`` live in dedicated modules; this module re-exports
them so existing ``from action_machine.graph.payload import ...`` imports stay stable.
"""

from __future__ import annotations

from action_machine.graph.edge_info import EdgeInfo, FacetMetaRow
from action_machine.graph.facet_payload import FacetPayload

__all__ = ("EdgeInfo", "FacetMetaRow", "FacetPayload")
