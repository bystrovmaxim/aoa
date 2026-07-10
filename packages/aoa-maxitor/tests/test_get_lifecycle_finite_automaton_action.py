"""Tests for GetLifecycleFiniteAutomatonAction: aspect pipeline over a DuckDB graph."""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.model import BaseState
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
)
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

_ACTION = GetLifecycleFiniteAutomatonAction()

_HOST = "my.domain.MyEntity"
_LC_ID = f"{_HOST}:lifecycle:status"
_STATE_DRAFT = f"{_LC_ID}:draft"
_STATE_PUBLISHED = f"{_LC_ID}:published"
_STATE_ARCHIVED = f"{_LC_ID}:archived"

_GRAPH_JSON: dict[str, Any] = {
    "nodes": [
        {"id": _LC_ID, "type": "Lifecycle", "label": "status", "properties": {"field_name": "status"}},
        {
            "id": _STATE_DRAFT,
            "type": "StateInitial",
            "label": "draft",
            "properties": {"lifecycle_class_id": "my.domain.StatusLifecycle", "state_key": "draft"},
        },
        {
            "id": _STATE_PUBLISHED,
            "type": "StateIntermediate",
            "label": "published",
            "properties": {"lifecycle_class_id": "my.domain.StatusLifecycle", "state_key": "published"},
        },
        {
            "id": _STATE_ARCHIVED,
            "type": "StateFinal",
            "label": "archived",
            "properties": {"lifecycle_class_id": "my.domain.StatusLifecycle", "state_key": "archived"},
        },
    ],
    "edges": [
        {
            "source_id": _LC_ID, "target_id": _STATE_DRAFT,
            "type": "lifecycle_contains_state", "relationship": "COMPOSITION", "is_dag": False,
            "properties": {"state_key": "draft"},
        },
        {
            "source_id": _LC_ID, "target_id": _STATE_PUBLISHED,
            "type": "lifecycle_contains_state", "relationship": "COMPOSITION", "is_dag": False,
            "properties": {"state_key": "published"},
        },
        {
            "source_id": _LC_ID, "target_id": _STATE_ARCHIVED,
            "type": "lifecycle_contains_state", "relationship": "COMPOSITION", "is_dag": False,
            "properties": {"state_key": "archived"},
        },
        {
            "source_id": _STATE_DRAFT, "target_id": _STATE_PUBLISHED,
            "type": "lifecycle_transition", "relationship": "COMPOSITION", "is_dag": False,
            "properties": {"from_state": "draft", "to_state": "published"},
        },
        {
            "source_id": _STATE_PUBLISHED, "target_id": _STATE_ARCHIVED,
            "type": "lifecycle_transition", "relationship": "COMPOSITION", "is_dag": False,
            "properties": {"from_state": "published", "to_state": "archived"},
        },
    ],
}


def _state(**kwargs: Any) -> BaseState:
    return BaseState(**kwargs)


def _params(node_id: str) -> GetLifecycleFiniteAutomatonAction.Params:
    return GetLifecycleFiniteAutomatonAction.Params(lifecycle_graph_node_id=node_id)


@pytest.fixture(scope="module")
def connections() -> dict[str, DuckDBGraphResource]:
    return {DUCKDB_GRAPH_CONNECTION_KEY: DuckDBGraphResource.build_from_json(_GRAPH_JSON)}


# ─── parse_interchange_id_aspect ─────────────────────────────────────────────


async def test_parse_rejects_non_interchange_id() -> None:
    with pytest.raises(ValueError, match=":lifecycle:"):
        await _ACTION.parse_interchange_id_aspect(_params("not-a-lifecycle-id"), _state(), None, {})  # type: ignore[arg-type]


async def test_parse_rejects_empty_host() -> None:
    with pytest.raises(ValueError, match="Invalid lifecycle interchange id"):
        await _ACTION.parse_interchange_id_aspect(_params(":lifecycle:status"), _state(), None, {})  # type: ignore[arg-type]


async def test_parse_rejects_empty_field() -> None:
    with pytest.raises(ValueError, match="Invalid lifecycle interchange id"):
        await _ACTION.parse_interchange_id_aspect(_params("my.Entity:lifecycle: "), _state(), None, {})  # type: ignore[arg-type]


async def test_parse_extracts_host_and_normalizes_id() -> None:
    result = await _ACTION.parse_interchange_id_aspect(_params(f"  {_LC_ID}  "), _state(), None, {})  # type: ignore[arg-type]
    assert result == {
        "lifecycle_graph_node_id": _LC_ID,
        "host_entity_type_qualname": _HOST,
    }


# ─── validate_lifecycle_node_aspect ──────────────────────────────────────────


async def test_validate_raises_when_node_absent(connections: dict[str, DuckDBGraphResource]) -> None:
    state = _state(lifecycle_graph_node_id="ghost:lifecycle:status", host_entity_type_qualname="ghost")
    with pytest.raises(ValueError, match="not found in the loaded graph"):
        await _ACTION.validate_lifecycle_node_aspect(None, state, None, connections)  # type: ignore[arg-type]


async def test_validate_threads_state_and_adds_field_name(connections: dict[str, DuckDBGraphResource]) -> None:
    state = _state(lifecycle_graph_node_id=_LC_ID, host_entity_type_qualname=_HOST)
    result = await _ACTION.validate_lifecycle_node_aspect(None, state, None, connections)  # type: ignore[arg-type]
    assert result == {
        "lifecycle_graph_node_id": _LC_ID,
        "host_entity_type_qualname": _HOST,
        "field_name": "status",
    }


# ─── load_states_aspect ──────────────────────────────────────────────────────


async def test_load_states_threads_state_and_adds_rows(connections: dict[str, DuckDBGraphResource]) -> None:
    state = _state(lifecycle_graph_node_id=_LC_ID, host_entity_type_qualname=_HOST, field_name="status")
    result = await _ACTION.load_states_aspect(None, state, None, connections)  # type: ignore[arg-type]
    assert result["lifecycle_graph_node_id"] == _LC_ID
    assert result["host_entity_type_qualname"] == _HOST
    assert result["field_name"] == "status"
    by_key = {r["state_key"]: r["kind"] for r in result["state_rows"]}
    assert by_key == {
        "draft": "StateInitial",
        "published": "StateIntermediate",
        "archived": "StateFinal",
    }


async def test_load_states_empty_for_unknown_node(connections: dict[str, DuckDBGraphResource]) -> None:
    state = _state(lifecycle_graph_node_id="ghost:lifecycle:status", host_entity_type_qualname="ghost", field_name="status")
    result = await _ACTION.load_states_aspect(None, state, None, connections)  # type: ignore[arg-type]
    assert result["state_rows"] == []


# ─── load_transitions_aspect ─────────────────────────────────────────────────


async def test_load_transitions_threads_state_and_adds_rows(connections: dict[str, DuckDBGraphResource]) -> None:
    state = _state(
        lifecycle_graph_node_id=_LC_ID,
        host_entity_type_qualname=_HOST,
        field_name="status",
        state_rows=[],
    )
    result = await _ACTION.load_transitions_aspect(None, state, None, connections)  # type: ignore[arg-type]
    assert result["state_rows"] == []
    assert result["transition_rows"] == [
        {"from_state": "draft", "to_state": "published"},
        {"from_state": "published", "to_state": "archived"},
    ]


# ─── build_fsm_summary ───────────────────────────────────────────────────────


async def test_full_pipeline_payload(connections: dict[str, DuckDBGraphResource]) -> None:
    params = _params(_LC_ID)
    state = _state()
    for aspect in (
        _ACTION.parse_interchange_id_aspect,
        _ACTION.validate_lifecycle_node_aspect,
        _ACTION.load_states_aspect,
        _ACTION.load_transitions_aspect,
    ):
        state = _state(**await aspect(params, state, None, connections))  # type: ignore[arg-type]

    result = await _ACTION.build_fsm_summary(params, state, None, connections)  # type: ignore[arg-type]
    fsm = result.lifecycle_finite_automaton

    assert fsm["lifecycle_graph_node_id"] == _LC_ID
    assert fsm["host_entity_type_qualname"] == _HOST
    assert fsm["field_name"] == "status"
    assert fsm["lifecycle_class_qualname"] == "my.domain.StatusLifecycle"
    assert fsm["initial_state_keys"] == ["draft"]
    assert [s["key"] for s in fsm["states"]] == ["draft", "archived", "published"]
    assert fsm["states"][0] == {
        "key": "draft",
        "display_name": "draft",
        "state_type": "initial",
        "transitions": ["published"],
    }
    assert fsm["transitions"] == [
        {"source": "draft", "target": "published"},
        {"source": "published", "target": "archived"},
    ]
