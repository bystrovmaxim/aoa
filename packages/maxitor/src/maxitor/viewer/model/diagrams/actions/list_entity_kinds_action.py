# packages/maxitor/src/maxitor/viewer/model/diagrams/actions/list_entity_kinds_action.py
"""
ListEntityKindsAction — the entity kinds present in the loaded graph, each with its display name.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The ERD filters tables by kind, and the set of kinds is the graph's, not Maxitor's:
AOA ships six, another producer states its own, an old export states none. This
action reads the distinct ``entity_kind`` words from the DuckDB ``entity`` table and
names each with the display name the graph carries (``entity_kind_label``) or, when
the graph names none, with the word itself, first letter capitalised. Maxitor holds no
table of kinds or names; the icon dictionary of the client is presentation only.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ``connections["DuckDBGraph"]`` (``entity`` table)
          |
          v
    @summary_aspect — ``Result(list_entity_kinds=[{entity_kind, label}, ...])``
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.viewer.model.diagrams.actions.list_entity_kinds_action_schema import ListEntityKindsJson
from maxitor.viewer.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


def _capitalised(word: str) -> str:
    """The fallback name of a kind the graph does not name: its word with the first letter upper-cased."""
    return word[:1].upper() + word[1:]


@meta(
    description="List the entity kinds of the loaded graph with their display names (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (entity rows for the ERD kind filter)",
)
class ListEntityKindsAction(BaseAction[ParamsStub, "ListEntityKindsAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``list_entity_kinds`` rows (word + display name) for the ERD kind filter.
    CONTRACT: Rows are the distinct ``entity_kind`` words of the ``entity`` table ordered by ``lower(word)``; a row's label is the smallest non-blank ``entity_kind_label`` of that kind or the capitalised word; test and ``<locals>`` ids are excluded like the domain listing.
    INVARIANTS: No colour, no count, no table of kinds or names in Maxitor — the graph decides which kinds exist and what they are called.
    AI-CORE-END
    """

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single key ``list_entity_kinds``)."""

        # [
        #   {"entity_kind": "assoc", "label": "Association"},
        #   {"entity_kind": "core", "label": "Core"}
        # ]
        list_entity_kinds: ListEntityKindsJson = Field(
            description="Entity kinds present in the loaded graph, ordered by word, each with its display name.",
        )

    @staticmethod
    def entity_kind_rows(duck: DuckDBGraphResource) -> list[dict[str, Any]]:
        """Return ``list_entity_kinds`` rows read from the DuckDB ``entity`` table."""
        sql = """
        SELECT entity_kind, MIN(NULLIF(trim(entity_kind_label), '')) AS label
        FROM entity
        WHERE id NOT LIKE 'tests.%'
          AND strpos(id, '<locals>') = 0
        GROUP BY entity_kind
        ORDER BY lower(entity_kind), entity_kind
        """
        return [
            {"entity_kind": str(row["entity_kind"]), "label": str(row["label"] or _capitalised(str(row["entity_kind"])))}
            for row in duck.execute_fetch_dicts(sql)
        ]

    @summary_aspect("Resolve entity kind list from DuckDB graph")
    async def build_list_entity_kinds_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ListEntityKindsAction.Result:
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        return ListEntityKindsAction.Result(list_entity_kinds=ListEntityKindsAction.entity_kind_rows(duck))
