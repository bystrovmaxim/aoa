# packages/aoa-maxitor/src/aoa/maxitor/api/resources/maxitor_interchange_nx_resource.py
"""
MaxitorInterchangeNxResource — ActionMachine connection for the live interchange nx graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Wrap the single ``networkx.DiGraph`` produced by ``LoadGraphAction`` so diagram
actions declare ``@connection(..., key="interchange_nx")`` instead of carrying
``nx_graph`` on every ``Params`` model.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service.external_service_resource import ExternalServiceResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@meta(
    description="Interchange NetworkX graph view (LoadGraphAction nx_graph)",
    domain=DiagramsDomain,
)
class MaxitorInterchangeNxResource(ExternalServiceResource[Any]):
    """Holds one ``DiGraph`` reference; aspects read ``nx_graph``."""

    @property
    def nx_graph(self) -> Any:
        """Same graph object stored on ``MaxitorApiSession.nx_graph``."""
        return self.service
