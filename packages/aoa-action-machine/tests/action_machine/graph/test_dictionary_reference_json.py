# tests/action_machine/graph/test_dictionary_reference_json.py
"""
Tests for a dictionary value's reference form inside the interchange graph.

The graph publishes each declared value as ``properties.values``. Those entries
travel to a JSON document, so every leaf must be JSON-compatible: a date becomes
its JSON string, and a field with its own serializer carries that serializer's
text. The old implementation read fields with ``getattr``, so the document could
hold a Python object that ``json.dumps`` refused.
"""

from __future__ import annotations

import json
from datetime import date

from pydantic import Field, field_serializer

from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class DatedShopDomain(BaseDomain):
    """The domain this fixture belongs to."""

    name = "dated-shop"
    description = "Dated shop"


@exclude_graph_model
@entity(description="Dated reference value", domain=DatedShopDomain)
class DatedEnumEntity(BaseEnumEntity):
    """A dictionary value whose date is formatted by its own serializer."""

    since: date = Field(description="Start date")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        """Format the date for consumers of the graph."""
        return moment.strftime("%d/%m/%Y")


@exclude_graph_model
@entity(description="Plain dated reference value", domain=DatedShopDomain)
class PlainDatedEnumEntity(BaseEnumEntity):
    """A dictionary value whose date has no serializer."""

    since: date = Field(description="Start date")

    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))


def _values(declaration: type[BaseEnumEntity]) -> list[dict]:
    """Return the graph node's published values."""
    return EntityGraphNode(declaration).properties["values"]


def test_the_graph_document_carries_the_serializer_text() -> None:
    """The node's value carries what the model's serializer produces, not a Python date."""
    values = _values(DatedEnumEntity)

    assert values[0]["properties"]["since"] == "02/01/2020"


def test_the_graph_document_survives_json_dumps() -> None:
    """A standard non-primitive type reaches the document as JSON, or the export is broken."""
    document = json.dumps(_values(PlainDatedEnumEntity))

    assert json.loads(document)[0]["properties"]["since"] == "2020-01-02"


def test_the_published_reference_keeps_its_three_members() -> None:
    """The reference shape is unchanged: code, label, and the extra fields under properties."""
    values = _values(DatedEnumEntity)

    assert set(values[0]) == {"code", "display_name", "properties"}
