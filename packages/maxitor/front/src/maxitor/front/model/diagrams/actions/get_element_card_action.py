# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/get_element_card_action.py
"""
GetElementCardAction — what a card says about one element of a version.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A diagram holds an element's name and little else. When a card opens (spec 043,
FR-013) this read gives the rest for that one node: its kind, its description where
the graph has one, and its lifecycle where it is one.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/element-card?id=<node id>
        ──► DuckDB ``nodes`` view ──► {id, type, label, description, lifecycle_id}
                 └─ absent ──► ElementNotInGraphError (404)
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

_NODE_SQL = """
SELECT id, type, label, json_extract_string(payload, '$.description') AS description
FROM nodes
WHERE id = ?
LIMIT 1
"""


class ElementNotInGraphError(LookupError):
    """This version holds no such node; answered as "not found"."""


class GetElementCardParams(BaseParams):
    """Which node of the version."""

    id: str = Field(min_length=1, max_length=2000, description="The node's id")


class GetElementCardResult(BaseResult):
    """What a card says about the node."""

    id: str = Field(description="The node's id")
    type: str = Field(description="The kind of element it is")
    label: str = Field(description="Its name")
    description: str | None = Field(description="Its description, when the graph has one")
    lifecycle_id: str | None = Field(description="Its own id when it is a lifecycle, else nothing")


@meta(description="Read what a card says about one node of a version", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB (nodes view)")
class GetElementCardAction(BaseAction[GetElementCardParams, GetElementCardResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer what a card shows beyond what a diagram holds, for one node.
    CONTRACT: The node's type, label and description, and ``lifecycle_id`` on a lifecycle; an id the version does not hold raises ``ElementNotInGraphError``.
    INVARIANTS: Read-only; an empty description reads as none.
    AI-CORE-END
    """

    @summary_aspect("Give one node's card")
    async def card_summary(
        self,
        params: GetElementCardParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GetElementCardResult:
        """Look the node up in the version's graph."""
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        rows = duck.execute_fetch_dicts(_NODE_SQL, [params.id])
        if not rows:
            raise ElementNotInGraphError("not found")
        row = rows[0]
        return GetElementCardResult(
            id=str(row["id"]),
            type=str(row["type"]),
            label=str(row["label"]),
            description=str(row["description"]) if row["description"] else None,
            lifecycle_id=str(row["id"]) if row["type"] == "lifecycle" else None,
        )
