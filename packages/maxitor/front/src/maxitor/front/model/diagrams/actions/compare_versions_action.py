# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/compare_versions_action.py
"""
CompareVersionsAction — what changed from A to B: every element that is not unchanged, and the counts.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The first of the two comparison reads (spec 038, FR-019): for the two versions a read
names — B as ``source``, A as ``a`` — the status of every node and edge of their union
and the counts. Unchanged elements are left out, since they are everything else in the
union: a release changes tens of elements of thousands, and the read stays small. The
diagrams draw the union from their own reads of A and B and mark it with these statuses.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/compare?source=<B>&a=<A> ──► GraphSourceMiddleware (both guarded, both bound)
        ──► ComparisonStore.current() ──► {counts, nodes: {id: status}, edges: {id: status}}
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.comparison_store import COMPARISON_STORE_CONNECTION_KEY, ComparisonStore
from maxitor.graph_compare import Counts, ElementComparison, Status
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class CompareVersionsResult(BaseResult):
    """The statuses of the elements that changed from A to B, and the counts."""

    counts: dict[str, dict[str, int]] = Field(description="Per kind ('nodes', 'edges'): how many were added, removed and changed")
    nodes: dict[str, str] = Field(description="Node id → 'added', 'removed' or 'changed'; a node left out is unchanged")
    edges: dict[str, str] = Field(description="Edge id → 'added', 'removed' or 'changed'; an edge left out is unchanged")


@meta(description="Compare two versions of a history: the elements that changed and the counts", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(ComparisonStore, key=COMPARISON_STORE_CONNECTION_KEY, description="The comparisons of held versions")
class CompareVersionsAction(BaseAction[ParamsStub, CompareVersionsResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer what changed between the two versions the read names.
    CONTRACT: Every node and edge that is added, removed or changed, with its status, and the counts per kind; unchanged elements are left out.
    INVARIANTS: Computed once per pair by ``ComparisonStore``; names no address and no key in its log.
    AI-CORE-END
    """

    @summary_aspect("Give the changed elements and the counts")
    async def compare_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CompareVersionsResult:
        """Read the pair's comparison and keep what is not unchanged."""
        _ = (params, state)
        store = cast(ComparisonStore, connections[COMPARISON_STORE_CONNECTION_KEY])
        before = store.computed
        comparison = await store.current()
        if store.computed != before:
            await box.info(
                Channel.debug,
                "Comparison computed in {%var.ms} ms: nodes {%var.nodes}, edges {%var.edges}",
                ms=round(store.last_milliseconds),
                nodes=_said(comparison.node_counts),
                edges=_said(comparison.edge_counts),
            )
        return CompareVersionsResult(
            counts={"nodes": _counts(comparison.node_counts), "edges": _counts(comparison.edge_counts)},
            nodes=_changed(comparison.nodes),
            edges=_changed(comparison.edges),
        )


def _counts(counts: Counts) -> dict[str, int]:
    """The counts as the read writes them."""
    return {"added": counts.added, "removed": counts.removed, "changed": counts.changed}


def _said(counts: Counts) -> str:
    """The counts in one short phrase for the log."""
    return f"+{counts.added} −{counts.removed} ~{counts.changed}"


def _changed(elements: Mapping[str, ElementComparison]) -> dict[str, str]:
    """Every element that is not unchanged, with its status."""
    return {element_id: item.status.value for element_id, item in elements.items() if item.status is not Status.UNCHANGED}
