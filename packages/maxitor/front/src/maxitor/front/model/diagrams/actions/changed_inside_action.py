# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/changed_inside_action.py
"""
ChangedInsideAction — what changed inside each action of two versions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A use-case diagram does not draw an action's parts (spec 041, FR-008), so an action
whose parts changed reads unchanged in the comparison. This read gives those parts:
the diagram's marks, its counts, its card and its stepper all read this one answer
(FR-024).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/compare/changed-inside?source=<B>&a=<A>
        ──► ComparisonStore.changed_inside() ──► {actions: {id: [part, ...]}}
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.front.model.diagrams.actions.compare_element_action import written_difference
from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.comparison_store import COMPARISON_STORE_CONNECTION_KEY, ComparisonStore
from maxitor.graph_compare import ChangedPart
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class ChangedInsideResult(BaseResult):
    """Each action's changed parts."""

    actions: dict[str, list[dict[str, Any]]] = Field(description="By action id, each changed part: kind, id, label, type, group, status and differences")


@meta(description="List what changed inside each action of two versions of a history", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(ComparisonStore, key=COMPARISON_STORE_CONNECTION_KEY, description="The comparisons of held versions")
class ChangedInsideAction(BaseAction[ParamsStub, ChangedInsideResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer which parts of each action changed between the two versions the read names.
    CONTRACT: Actions found in both versions with at least one changed part; an action with none is left out.
    INVARIANTS: Reads what ``ComparisonStore`` holds for the pair; computes nothing of its own.
    AI-CORE-END
    """

    @summary_aspect("Give each action's changed parts")
    async def changed_inside_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ChangedInsideResult:
        """Read the pair's answer as the read writes it."""
        _ = (params, state, box)
        inside = await cast(ComparisonStore, connections[COMPARISON_STORE_CONNECTION_KEY]).changed_inside()
        return ChangedInsideResult(actions={action: [_written(part) for part in parts] for action, parts in inside.items()})


def _written(part: ChangedPart) -> dict[str, Any]:
    """One part as the read writes it."""
    return {
        "kind": part.kind,
        "id": part.id,
        "label": part.label,
        "type": part.type,
        "group": part.group,
        "status": part.status.value,
        "differences": [written_difference(difference) for difference in part.differences],
    }
