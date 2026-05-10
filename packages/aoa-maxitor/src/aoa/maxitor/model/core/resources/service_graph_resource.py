# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/service_graph_resource.py
"""
ServiceGraphResource — ActionMachine connection for a NetworkX interchange graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Wrap the single ``networkx.DiGraph`` produced by ``LoadGraphAction`` so diagram
actions declare ``@connection(..., key=SERVICE_GRAPH_CONNECTION_KEY)`` instead of carrying
the graph on every ``Params`` model. Callers read the graph via ``.service``
(:class:`~aoa.action_machine.resources.external_service.external_service_resource.ExternalServiceResource`).
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service.external_service_resource import ExternalServiceResource
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

SERVICE_GRAPH_CONNECTION_KEY = "ServiceGraph"


@meta(
    description="Interchange NetworkX graph view (LoadGraphAction nx_graph)",
    domain=DiagramsDomain,
)
class ServiceGraphResource(ExternalServiceResource[Any]):
    """
    AI-CORE-BEGIN
    ROLE: Expose one interchange ``DiGraph`` as ``ExternalServiceResource.service`` for ``@connection`` wiring.
    CONTRACT: ``service`` is the live graph from ``LoadGraphAction``; connection key is :data:`SERVICE_GRAPH_CONNECTION_KEY`.
    AI-CORE-END
    """
