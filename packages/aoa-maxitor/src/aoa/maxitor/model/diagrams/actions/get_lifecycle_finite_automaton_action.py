# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action.py
"""
GetLifecycleFiniteAutomatonAction — FSM snapshot for one Lifecycle interchange vertex from DuckDB.

Reads states and transitions from the already-loaded DuckDB graph; no local class import needed,
so the action works in standalone deployments where the target service's packages are absent.

Aspect sequence:
  1. parse_interchange_id — validate ``<entity_qualname>:lifecycle:<field_name>`` shape, extract host qualname
  2. validate_lifecycle_node — verify the Lifecycle vertex exists in DuckDB, read its field_name
  3. load_states — read state rows attached via ``lifecycle_contains_state_edges``
  4. load_transitions — read directed transition arcs via ``lifecycle_transition_edges``
  5. build_fsm (summary) — assemble the wire payload (metadata, per-state rows, explicit edges)

State flows strictly aspect-to-aspect: each aspect re-returns every key the downstream
aspects still need and drops the rest.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action_schema import LifecycleFiniteAutomatonJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

_LIFECYCLE_SEGMENT = ":lifecycle:"

_KIND_TO_SLUG: dict[str, str] = {
    "StateInitial": "initial",
    "StateIntermediate": "intermediate",
    "StateFinal": "final",
}


@meta(
    description="Return lifecycle FSM states and transitions for one interchange Lifecycle vertex id",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Shared DuckDB graph connection — queried for lifecycle/state/transition rows",
)
class GetLifecycleFiniteAutomatonAction(
    BaseAction["GetLifecycleFiniteAutomatonAction.Params", "GetLifecycleFiniteAutomatonAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Five-aspect pipeline — parse interchange id, validate Lifecycle vertex in DuckDB, load states, load transitions, assemble FSM payload.
    CONTRACT: ``lifecycle_graph_node_id`` must match a Lifecycle node id in the loaded graph; raises ``ValueError`` on shape mismatch or when the vertex is absent.
    INVARIANTS: Read-only DuckDB queries only; no dynamic imports — works in standalone deployments where entity classes are not locally installed. Each aspect re-returns exactly the state keys the downstream aspects consume.
    AI-CORE-END
    """

    class Params(BaseParams):
        lifecycle_graph_node_id: str = Field(
            min_length=1,
            description="Interchange Lifecycle vertex id (<entity_qualname>:lifecycle:<field_name>)",
        )

    class Result(BaseResult):
        lifecycle_finite_automaton: LifecycleFiniteAutomatonJson = Field(
            description="FSM snapshot (metadata, per-state rows, explicit directed edges).",
        )

    # ─── Aspect 1 ────────────────────────────────────────────────────────────

    @result_string("lifecycle_graph_node_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("host_entity_type_qualname", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Validate interchange id shape (<entity_qualname>:lifecycle:<field_name>) and extract host qualname.")
    async def parse_interchange_id_aspect(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (state, box, connections)
        node_id = params.lifecycle_graph_node_id.strip()
        if _LIFECYCLE_SEGMENT not in node_id:
            msg = f"Expected interchange lifecycle id containing {_LIFECYCLE_SEGMENT!r}, got {node_id!r}"
            raise ValueError(msg)
        host, field = node_id.split(_LIFECYCLE_SEGMENT, 1)
        host = host.strip()
        field = field.strip()
        if not host or not field:
            msg = f"Invalid lifecycle interchange id: {node_id!r}"
            raise ValueError(msg)
        return {
            "lifecycle_graph_node_id": node_id,
            "host_entity_type_qualname": host,
        }

    # ─── Aspect 2 ────────────────────────────────────────────────────────────

    @result_string("lifecycle_graph_node_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("host_entity_type_qualname", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("field_name", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Validate the Lifecycle vertex exists in the loaded DuckDB graph and read its field_name.")
    async def validate_lifecycle_node_aspect(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box)
        graph = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        node_id = cast(str, state["lifecycle_graph_node_id"])

        rows = graph.execute_fetch_dicts("SELECT field_name FROM lifecycle WHERE id = ?", [node_id])
        if not rows:
            msg = (
                f"Lifecycle node {node_id!r} not found in the loaded graph. "
                "Ensure the AOA service graph is loaded via POST /api/load."
            )
            raise ValueError(msg)
        return {
            "lifecycle_graph_node_id": node_id,
            "host_entity_type_qualname": state["host_entity_type_qualname"],
            "field_name": str(rows[0]["field_name"]),
        }

    # ─── Aspect 3 ────────────────────────────────────────────────────────────

    @result_string("lifecycle_graph_node_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("host_entity_type_qualname", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("field_name", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("state_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Load state rows attached to the Lifecycle vertex via lifecycle_contains_state_edges.")
    async def load_states_aspect(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box)
        graph = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        node_id = cast(str, state["lifecycle_graph_node_id"])

        state_rows = graph.execute_fetch_dicts(
            """
            SELECT s.state_key, s.kind, s.label, s.lifecycle_class_id
            FROM lifecycle_contains_state_edges lcs
            JOIN state s ON s.id = lcs.target_id
            WHERE lcs.source_id = ?
            ORDER BY s.state_key
            """,
            [node_id],
        )
        return {
            "lifecycle_graph_node_id": node_id,
            "host_entity_type_qualname": state["host_entity_type_qualname"],
            "field_name": state["field_name"],
            "state_rows": state_rows,
        }

    # ─── Aspect 4 ────────────────────────────────────────────────────────────

    @result_string("lifecycle_graph_node_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("host_entity_type_qualname", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_string("field_name", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("state_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("transition_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Load directed transition arcs between the Lifecycle vertex's states via lifecycle_transition_edges.")
    async def load_transitions_aspect(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (params, box)
        graph = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        node_id = cast(str, state["lifecycle_graph_node_id"])

        transition_rows = graph.execute_fetch_dicts(
            """
            SELECT lte.from_state, lte.to_state
            FROM lifecycle_transition_edges lte
            JOIN lifecycle_contains_state_edges lcs ON lte.source_id = lcs.target_id
            WHERE lcs.source_id = ?
            ORDER BY lte.from_state, lte.to_state
            """,
            [node_id],
        )
        return {
            "lifecycle_graph_node_id": node_id,
            "host_entity_type_qualname": state["host_entity_type_qualname"],
            "field_name": state["field_name"],
            "state_rows": state["state_rows"],
            "transition_rows": transition_rows,
        }

    # ─── Aspect 5 (summary) ──────────────────────────────────────────────────

    @summary_aspect("Assemble the FSM wire payload from loaded state and transition rows.")
    async def build_fsm_summary(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetLifecycleFiniteAutomatonAction.Result:
        _ = (params, box, connections)
        node_id = cast(str, state["lifecycle_graph_node_id"])
        host_q = cast(str, state["host_entity_type_qualname"])
        field_name = cast(str, state["field_name"])
        state_rows = cast(list[dict[str, Any]], state["state_rows"])
        transition_rows = cast(list[dict[str, Any]], state["transition_rows"])

        transitions_by_state: dict[str, list[str]] = {}
        for tr in transition_rows:
            transitions_by_state.setdefault(str(tr["from_state"]), []).append(str(tr["to_state"]))

        lifecycle_class_qualname = ""
        initials: list[str] = []
        states_json: list[dict[str, Any]] = []

        for sr in state_rows:
            st_slug = _KIND_TO_SLUG.get(str(sr["kind"]), "intermediate")
            key = str(sr["state_key"])
            if st_slug == "initial":
                initials.append(key)
            if not lifecycle_class_qualname:
                lifecycle_class_qualname = str(sr["lifecycle_class_id"])
            states_json.append(
                {
                    "key": key,
                    "display_name": str(sr["label"]),
                    "state_type": st_slug,
                    "transitions": sorted(transitions_by_state.get(key, [])),
                },
            )

        states_json.sort(key=lambda s: (s["state_type"] != "initial", s["key"]))
        edges_json = [
            {"source": str(tr["from_state"]), "target": str(tr["to_state"])}
            for tr in transition_rows
        ]

        payload: dict[str, Any] = {
            "lifecycle_graph_node_id": node_id,
            "host_entity_type_qualname": host_q,
            "field_name": field_name,
            "lifecycle_class_qualname": lifecycle_class_qualname,
            "initial_state_keys": sorted(set(initials)),
            "states": states_json,
            "transitions": edges_json,
        }

        return GetLifecycleFiniteAutomatonAction.Result(lifecycle_finite_automaton=payload)
