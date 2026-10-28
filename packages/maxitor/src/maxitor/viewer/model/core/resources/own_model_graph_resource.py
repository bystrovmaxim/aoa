# packages/maxitor/src/maxitor/viewer/model/core/resources/own_model_graph_resource.py
"""
OwnModelGraphResource — Maxitor's own model, as the graph-json every AOA service serves.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor is an AOA service too: every room operation and every diagram read is an AOA
action on its machine. Its own model is the coordinator the machine was built with, and
Maxitor serves it like any service (spec 029, FR-060), so typing Maxitor's own address
into the service field opens Maxitor's diagram. The interchange JSON is rendered once:
a process's model does not change while it runs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine.graph_coordinator ──► OwnModelGraphResource
                                                  └─ graph_json() ──► to_json(), kept after the first call
"""

from __future__ import annotations

from maxitor.viewer.model.core.core_domain import CoreDomain

from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage

#: Connection key under which actions receive Maxitor's own model.
OWN_MODEL_GRAPH_CONNECTION_KEY = "OwnModelGraph"


@meta(description="Maxitor's own model as interchange graph JSON", domain=CoreDomain)
class OwnModelGraphResource(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: The resource through which an action reads Maxitor's own model as interchange JSON.
    CONTRACT: ``graph_json`` returns ``to_json()`` of the coordinator Maxitor's machine was built with.
    INVARIANTS: Rendered once per process and read only.
    AI-CORE-END
    """

    def __init__(self, coordinator: NodeGraphCoordinator) -> None:
        self._coordinator = coordinator
        self._json: str | None = None

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same resource."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the model is not a rollup target."""
        return False

    def graph_json(self) -> str:
        """Maxitor's own model as interchange JSON, rendered on the first call."""
        if self._json is None:
            self._json = self._coordinator.to_json()
        return self._json
