# tests/maxitor/test_duckdb_entity_kind_tolerance.py
"""
Tests for loading entity kinds from any producer: absent, blank, foreign or named.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A graph whose ``Entity`` rows state no kind — an old export, another producer —
must load and stay visible: the kind is stored as ``unknown``, never guessed. A
display name is stored when the graph sends one. A value that is not a string is
an error that names the node. Both paths that write ``entity`` rows agree.
"""

from __future__ import annotations

import re
from typing import Any

import duckdb
import pytest
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource, _fill_table_entity


def _entity(identifier: str, **properties: Any) -> dict[str, Any]:
    """Return an ``Entity`` node whose properties hold a description plus ``properties``."""
    return {"id": identifier, "label": identifier.rsplit(".", 1)[-1], "type": "Entity", "properties": {"description": "", **properties}}


ROWS = [
    _entity("shop.MissingEntity"),
    _entity("shop.BlankEntity", entity_kind=""),
    _entity("shop.OrderEntity", entity_kind="aggregate", entity_kind_label="Aggregate root"),
    _entity("shop.PlacedEntity", entity_kind="event"),
    _entity("shop.CurrencyEntity", entity_kind="enum", entity_kind_label="  ", values=[]),
]

EXPECTED = [
    ("shop.BlankEntity", "unknown", None, False),
    ("shop.CurrencyEntity", "enum", None, True),
    ("shop.MissingEntity", "unknown", None, False),
    ("shop.OrderEntity", "aggregate", "Aggregate root", False),
    ("shop.PlacedEntity", "event", None, False),
]

_SELECT = "SELECT id, entity_kind, entity_kind_label, declares_values FROM entity ORDER BY id"


def _graph(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a coordinator payload holding only ``nodes``."""
    return {"schema_version": "1.0", "nodes": nodes, "edges": []}


def test_a_graph_without_kinds_loads_and_its_rows_are_unknown() -> None:
    """The graph build stores what the producer sent and ``unknown`` where it sent nothing."""
    store = DuckDBGraphResource.build_from_json(_graph(ROWS))

    rows = [tuple(row.values()) for row in store.execute_fetch_dicts(_SELECT)]

    assert rows == EXPECTED


def test_the_per_row_fill_writes_the_same_rows() -> None:
    """The second path that writes ``entity`` rows goes through the same rule."""
    con = duckdb.connect(database=":memory:")
    DuckDBGraphResource._install_database(object.__new__(DuckDBGraphResource), con)

    _fill_table_entity(con, ROWS)

    assert [tuple(row) for row in con.execute(_SELECT).fetchall()] == EXPECTED


@pytest.mark.parametrize("bad", [{"entity_kind": 5}, {"entity_kind": "core", "entity_kind_label": 5}])
def test_a_non_string_kind_or_name_names_the_node(bad: dict[str, Any]) -> None:
    """A malformed value is the producer's error, and the message points at the row."""
    with pytest.raises(ValueError, match=re.escape("shop.BrokenEntity")):
        DuckDBGraphResource.build_from_json(_graph([_entity("shop.BrokenEntity", **bad)]))


def test_the_reconstructed_node_carries_its_display_name() -> None:
    """A node read back from the store keeps the name the graph sent."""
    store = DuckDBGraphResource.build_from_json(_graph(ROWS))

    rows = store.execute_fetch_dicts(
        "SELECT payload->>'entity_kind_label' AS label FROM nodes WHERE id = 'shop.OrderEntity'"
    )

    assert rows == [{"label": "Aggregate root"}]
