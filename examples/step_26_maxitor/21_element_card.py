"""
21_element_card.py — what a card reads about one element, and where a description comes from

A card in Maxitor shows what the diagram holds at once and reads the rest when it opens. This example builds a small graph
of protocol 1.2 and asks the read a card asks. The cases, with the real output at the bottom:

  1. a table: its kind and description;
  2. a field: its description, which needs protocol 1.2;
  3. a lifecycle: it names itself, which is how a card knows to draw a miniature;
  4. a field the model left undescribed: no description, and the card leaves the line out;
  5. an element this version does not hold: refused, and in Diff the card asks the older version.

Output:

    1. A table
       entity: One order line
    2. A field
       entity_field: How many units
    3. A lifecycle
       lifecycle: Where the line stands (lifecycle shop.Line:lifecycle:status)
    4. A field with no description
       entity_field: None
    5. Not in this version
       refused: not found
"""

from __future__ import annotations

import asyncio
from typing import Any

from maxitor.front.model.diagrams.actions.get_element_card_action import (
    ElementNotInGraphError,
    GetElementCardAction,
    GetElementCardParams,
)
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

from aoa.action_machine.model import BaseState

LINE = "shop.Line"
GRAPH: dict[str, Any] = {
    "schema_version": "1.2",
    "nodes": [
        {"id": LINE, "type": "Entity", "label": "Line", "properties": {"description": "One order line", "entity_kind": "core", "entity_kind_label": "Core"}},
        {"id": f"{LINE}:quantity", "type": "EntityField", "label": "quantity", "properties": {"field_type": "int", "primary_key_hint": False, "description": "How many units"}},
        {"id": f"{LINE}:id", "type": "EntityField", "label": "id", "properties": {"field_type": "str", "primary_key_hint": True}},
        {"id": f"{LINE}:lifecycle:status", "type": "Lifecycle", "label": "status", "properties": {"field_name": "status", "description": "Where the line stands"}},
    ],
    "edges": [],
}


async def card(node_id: str) -> str:
    """What a card reads for one node, in one line."""
    connections: Any = {DUCKDB_GRAPH_CONNECTION_KEY: DuckDBGraphResource.build_from_json(GRAPH)}
    action = GetElementCardAction()
    try:
        read = await action.card_summary(GetElementCardParams(id=node_id), BaseState(), None, connections)  # type: ignore[arg-type]
    except ElementNotInGraphError as refused:
        return f"refused: {refused}"
    lifecycle = f" (lifecycle {read.lifecycle_id})" if read.lifecycle_id else ""
    return f"{read.type}: {read.description}{lifecycle}"


async def main() -> None:
    """Walk the five cases."""
    cases = [
        ("1. A table", LINE),
        ("2. A field", f"{LINE}:quantity"),
        ("3. A lifecycle", f"{LINE}:lifecycle:status"),
        ("4. A field with no description", f"{LINE}:id"),
        ("5. Not in this version", "shop.Gone"),
    ]
    for title, node_id in cases:
        print(title)
        print(f"   {await card(node_id)}")


if __name__ == "__main__":
    asyncio.run(main())
