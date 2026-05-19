"""Tests for :class:`~aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action.GetLifecycleFiniteAutomatonAction`."""

from __future__ import annotations

import pytest

from aoa.action_machine.graph_model.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.examples.model.billing.entities.billing_sat_acquirer_integrity import AcquirerIntegrityCheckEntity
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
    _parse_lifecycle_interchange_id,
)
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)


def test_parse_lifecycle_interchange_id() -> None:
    host = TypeIntrospection.full_qualname(AcquirerIntegrityCheckEntity)
    raw = f"{host}:lifecycle:lifecycle"
    assert _parse_lifecycle_interchange_id(raw) == (host, "lifecycle")


@pytest.mark.asyncio
async def test_get_lifecycle_finite_automaton_acquirer_integrity_lifecycle() -> None:
    from aoa.action_machine.context.context import Context

    host = TypeIntrospection.full_qualname(AcquirerIntegrityCheckEntity)
    node_id = f"{host}:lifecycle:lifecycle"
    duck = DuckDBGraphResource.build_from_json({"schema_version": "1.0", "nodes": [], "edges": []})
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    result = await machine.run(
        Context(),
        GetLifecycleFiniteAutomatonAction(),
        GetLifecycleFiniteAutomatonAction.Params(lifecycle_graph_node_id=node_id),
        {DUCKDB_GRAPH_CONNECTION_KEY: duck},
    )
    j = result.model_dump(mode="json")["lifecycle_finite_automaton"]
    assert isinstance(j, dict)
    assert j["lifecycle_graph_node_id"] == node_id
    assert j["host_entity_type_qualname"] == host
    assert j["field_name"] == "lifecycle"
    states = j["states"]
    assert isinstance(states, list) and states
    keys = {s["key"] for s in states}
    assert "open" in keys and "finalized" in keys
    trans = j["transitions"]
    assert isinstance(trans, list) and trans
    assert any(t["source"] == "open" and t["target"] == "finalized" for t in trans)
    assert j["initial_state_keys"] == ["open"]


def test_parse_rejects_non_interchange_id() -> None:
    with pytest.raises(ValueError, match=":lifecycle:"):
        _parse_lifecycle_interchange_id("not-a-lifecycle-id")
