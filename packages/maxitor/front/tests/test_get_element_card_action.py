"""Tests for GetElementCardAction: one node's card over a DuckDB graph."""

from __future__ import annotations

from typing import Any

import pytest
from maxitor.front.model.diagrams.actions.get_element_card_action import (
    ElementNotInGraphError,
    GetElementCardAction,
    GetElementCardParams,
)
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.model import BaseState

_LIFECYCLE = "my.Entity:lifecycle:status"
_GRAPH: dict[str, Any] = {
    "nodes": [
        {"id": "my.Entity", "type": "Entity", "label": "Entity", "properties": {"description": "One row", "entity_kind": "core", "entity_kind_label": "Core"}},
        {"id": "my.Entity:name", "type": "EntityField", "label": "name", "properties": {"field_type": "str", "primary_key_hint": False, "description": "What it is called"}},
        {"id": _LIFECYCLE, "type": "Lifecycle", "label": "status", "properties": {"field_name": "status"}},
    ],
    "edges": [],
}


async def _card(node_id: str) -> Any:
    connections: Any = {DUCKDB_GRAPH_CONNECTION_KEY: DuckDBGraphResource.build_from_json(_GRAPH)}
    return await GetElementCardAction().card_summary(GetElementCardParams(id=node_id), BaseState(), None, connections)  # type: ignore[arg-type]


async def test_an_entity_has_its_description() -> None:
    card = await _card("my.Entity")
    assert (card.type, card.label, card.description, card.lifecycle_id) == ("entity", "Entity", "One row", None)


async def test_a_field_has_its_description() -> None:
    assert (await _card("my.Entity:name")).description == "What it is called"


async def test_a_node_with_no_description_has_none() -> None:
    assert (await _card(_LIFECYCLE)).description is None


async def test_a_lifecycle_names_itself() -> None:
    assert (await _card(_LIFECYCLE)).lifecycle_id == _LIFECYCLE


async def test_an_unknown_id_is_refused() -> None:
    with pytest.raises(ElementNotInGraphError):
        await _card("my.Other")
