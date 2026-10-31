# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/compare_element_action.py
"""
CompareElementAction — what changed in one element from A to B, property by property.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The second comparison read (spec 038, FR-019): one node or edge of the two versions a
read names, with its status and, when it changed, every difference by its property path
— the value in A and in B. A changed element's card is drawn from it (FR-028).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/compare-element?source=<B>&a=<A>&kind=node|edge&id=<id>
        ──► ComparisonStore.current() ──► nodes|edges[id] ──► {status, differences}
                                               └─ absent ──► ElementNotComparedError (404)
"""

from __future__ import annotations

from typing import Any, Literal, cast

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.comparison_store import COMPARISON_STORE_CONNECTION_KEY, ComparisonStore
from maxitor.graph_compare import Change, Difference
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class ElementNotComparedError(LookupError):
    """The element is in neither version; answered as "not found"."""


class CompareElementParams(BaseParams):
    """Which element of the two versions."""

    kind: Literal["node", "edge"] = Field(description="Whether ``id`` names a node or an edge")
    id: str = Field(min_length=1, max_length=2000, description="The element's id, as the protocol gives it (an edge of a 1.0 graph by #285's rule)")


class CompareElementResult(BaseResult):
    """One element's status and its differences."""

    status: str = Field(description="'added', 'removed', 'changed' or 'unchanged'")
    differences: list[dict[str, Any]] = Field(
        description="Each changed property: its path from the element's top, 'added', 'removed' or 'changed', and its value before and after"
    )


@meta(description="Compare one element of two versions of a history, property by property", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(ComparisonStore, key=COMPARISON_STORE_CONNECTION_KEY, description="The comparisons of held versions")
class CompareElementAction(BaseAction[CompareElementParams, CompareElementResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer how one element changed between the two versions the read names.
    CONTRACT: Its status and every difference by path, with ``before`` absent for an added property and ``after`` absent for a removed one; an id in neither version raises ``ElementNotComparedError``.
    INVARIANTS: Reads the comparison ``ComparisonStore`` holds for the pair; computes nothing of its own.
    AI-CORE-END
    """

    @summary_aspect("Give one element's status and differences")
    async def element_summary(
        self,
        params: CompareElementParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> CompareElementResult:
        """Look the element up in the pair's comparison."""
        _ = (state, box)
        comparison = await cast(ComparisonStore, connections[COMPARISON_STORE_CONNECTION_KEY]).current()
        item = (comparison.nodes if params.kind == "node" else comparison.edges).get(params.id)
        if item is None:
            raise ElementNotComparedError("not found")
        return CompareElementResult(status=item.status.value, differences=[written_difference(difference) for difference in item.differences])


def written_difference(difference: Difference) -> dict[str, Any]:
    """One difference as the read writes it: no ``before`` for an addition, no ``after`` for a removal."""
    written: dict[str, Any] = {"path": list(difference.path), "change": difference.change.value}
    if difference.change is not Change.ADDED:
        written["before"] = difference.before
    if difference.change is not Change.REMOVED:
        written["after"] = difference.after
    return written
