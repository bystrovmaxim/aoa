# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_lifecycle_finite_automaton_action.py
"""
GetLifecycleFiniteAutomatonAction — template FSM for one ``Lifecycle`` interchange vertex.

Interchange lifecycle rows use ids shaped like
``<entity_type_qualname>:lifecycle:<field_name>`` (see
:class:`~aoa.action_machine.graph.nodes.lifecycle_graph_node.LifeCycleGraphNode`).
The action resolves the host entity class, loads the lifecycle template, and returns
states plus explicit directed edges for diagramming clients.
"""

from __future__ import annotations

import importlib
from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.lifecycle import StateType
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.entity.lifecycle_intent_resolver import LifeCycleIntentResolver
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action_schema import LifecycleFiniteAutomatonJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

_LIFECYCLE_SEGMENT = ":lifecycle:"


def _import_type_from_full_qualname(full_qualname: str) -> type[Any]:
    """Resolve ``module.nested.Class`` (including nested classes) to a type object."""
    parts = full_qualname.split(".")
    if len(parts) < 2:
        msg = f"Not a dotted type path: {full_qualname!r}"
        raise ValueError(msg)

    for mod_end in range(len(parts) - 1, 0, -1):
        mod_name = ".".join(parts[:mod_end])
        tail = parts[mod_end:]
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        obj: Any = mod
        try:
            for attr in tail:
                obj = getattr(obj, attr)
        except AttributeError:
            continue
        if isinstance(obj, type):
            return obj

    msg = f"Could not import type {full_qualname!r}"
    raise ValueError(msg)


def _parse_lifecycle_interchange_id(lifecycle_graph_node_id: str) -> tuple[str, str]:
    raw = lifecycle_graph_node_id.strip()
    if _LIFECYCLE_SEGMENT not in raw:
        msg = f"Expected interchange lifecycle id containing {_LIFECYCLE_SEGMENT!r}, got {raw!r}"
        raise ValueError(msg)
    host, field = raw.split(_LIFECYCLE_SEGMENT, 1)
    host = host.strip()
    field = field.strip()
    if not host or not field:
        msg = f"Invalid lifecycle interchange id: {raw!r}"
        raise ValueError(msg)
    return host, field


@meta(
    description="Return lifecycle template states and transitions for one interchange Lifecycle vertex id",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Shared DuckDB graph connection (required by FastAPI adapter; unused by this action)",
)
class GetLifecycleFiniteAutomatonAction(
    BaseAction["GetLifecycleFiniteAutomatonAction.Params", "GetLifecycleFiniteAutomatonAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Serialize one lifecycle field's declarative FSM template for UI builders.
    CONTRACT: ``lifecycle_graph_node_id`` matches ``LifeCycleGraphNode`` ids; raises ``ValueError`` on parse/import mismatch.
    INVARIANTS: Read-only; no DuckDB reads despite declared connection.
    AI-CORE-END
    """

    class Params(BaseParams):
        lifecycle_graph_node_id: str = Field(
            min_length=1,
            description="Interchange Lifecycle vertex id (<entity_qualname>:lifecycle:<field_name>)",
        )

    class Result(BaseResult):
        # {
        #   "lifecycle_graph_node_id": "aoa.examples...Entity:lifecycle:lifecycle",
        #   "host_entity_type_qualname": "aoa.examples...Entity",
        #   "field_name": "lifecycle",
        #   "lifecycle_class_qualname": "aoa.examples...BillingDenseLifecycle",
        #   "initial_state_keys": ["open"],
        #   "states": [
        #     {"key": "open", "display_name": "Open", "state_type": "initial", "transitions": ["finalized"]}
        #   ],
        #   "transitions": [{"source": "open", "target": "finalized"}]
        # }
        lifecycle_finite_automaton: LifecycleFiniteAutomatonJson = Field(
            description="Template FSM snapshot (metadata, per-state rows, explicit directed edges).",
        )

    @summary_aspect("Resolve lifecycle template FSM from interchange Lifecycle vertex id")
    async def build_fsm_summary(
        self,
        params: GetLifecycleFiniteAutomatonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetLifecycleFiniteAutomatonAction.Result:
        _ = (state, box)
        _ = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])

        host_q, field_name = _parse_lifecycle_interchange_id(params.lifecycle_graph_node_id)
        entity_cls = _import_type_from_full_qualname(host_q)
        if not isinstance(entity_cls, type) or not issubclass(entity_cls, BaseEntity):
            msg = f"Resolved host {host_q!r} is not a BaseEntity subclass"
            raise ValueError(msg)

        fsm = LifeCycleIntentResolver.resolve_finite_state_machine(entity_cls, field_name)
        lifecycle_cls = fsm.lifecycle_class
        lifecycle_q = TypeIntrospection.full_qualname(lifecycle_cls)

        states_json: list[dict[str, Any]] = []
        edges_json: list[dict[str, str]] = []
        initials: list[str] = []

        for key, info in fsm.states.items():
            st = info.state_type
            if st == StateType.INITIAL:
                initials.append(key)
            st_slug = st.value
            targets = sorted(info.transitions)
            states_json.append(
                {
                    "key": key,
                    "display_name": info.display_name,
                    "state_type": st_slug,
                    "transitions": targets,
                },
            )
            for tgt in targets:
                edges_json.append({"source": key, "target": tgt})

        states_json.sort(key=lambda s: (s["state_type"] != "initial", s["key"]))
        edges_json.sort(key=lambda e: (e["source"], e["target"]))
        initials_sorted = sorted(set(initials))

        payload: dict[str, Any] = {
            "lifecycle_graph_node_id": params.lifecycle_graph_node_id.strip(),
            "host_entity_type_qualname": host_q,
            "field_name": field_name,
            "lifecycle_class_qualname": lifecycle_q,
            "initial_state_keys": initials_sorted,
            "states": states_json,
            "transitions": edges_json,
        }

        return GetLifecycleFiniteAutomatonAction.Result(lifecycle_finite_automaton=payload)
