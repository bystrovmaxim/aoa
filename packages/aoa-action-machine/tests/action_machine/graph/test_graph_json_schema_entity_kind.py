# tests/action_machine/graph/test_graph_json_schema_entity_kind.py
"""
Tests for the entity kind on the interchange graph: an open word and an optional name.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The schema requires every ``Entity`` row to state its kind as a lowercase word but
no longer lists which words exist, so a graph from any producer — or an AOA model
with a kind of its own — is valid. The display name travels next to the word and is
optional on the wire. AOA's export writes both for every kind it ships and for a
kind a user model declares.
"""

from __future__ import annotations

from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseDomain,
    BaseEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity

_VALIDATOR = Draft202012Validator(GRAPH_JSON_SCHEMA)


class KindShopDomain(BaseDomain):
    """The domain the exported fixtures belong to."""

    name = "kind-shop"
    description = "Kind shop"


def _document(properties: dict[str, Any]) -> dict[str, Any]:
    """Return a one-node graph document for the given entity properties."""
    return {
        "schema_version": "1.1",
        "nodes": [{"id": "shop.model.OrderEntity", "type": "Entity", "label": "OrderEntity", "properties": properties}],
        "edges": [],
    }


@pytest.mark.parametrize("properties", [
    {"description": "Order", "entity_kind": "aggregate"},
    {"description": "Order", "entity_kind": "aggregate", "entity_kind_label": "Aggregate"},
    {"description": "Order", "entity_kind": "in_flight"},
])
def test_a_kind_word_this_engine_does_not_know_is_valid(properties: dict[str, Any]) -> None:
    """The word is open: any lowercase word is a kind, with or without a name."""
    _VALIDATOR.validate(_document(properties))


@pytest.mark.parametrize("kind", [None, "", "Core", "core entity", 1])
def test_a_missing_or_malformed_kind_word_is_rejected(kind: Any) -> None:
    """The word stays required and stays one lowercase word."""
    properties: dict[str, Any] = {"description": "Order"}
    if kind is not None:
        properties["entity_kind"] = kind
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(_document(properties))


@pytest.mark.parametrize("label", ["", 1])
def test_an_empty_or_non_string_display_name_is_rejected(label: Any) -> None:
    """The name is optional, but when present it names something."""
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(_document({"description": "Order", "entity_kind": "core", "entity_kind_label": label}))


def test_an_enum_row_without_values_is_still_rejected() -> None:
    """The dictionary branch of the schema is untouched by opening the word."""
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(_document({"description": "Currency", "entity_kind": "enum"}))


@exclude_graph_model
@entity(description="Customer", domain=KindShopDomain)
class KindCustomerCoreEntity(BaseCoreEntity):
    """A core row."""


@exclude_graph_model
@entity(description="Customer link", domain=KindShopDomain)
class KindLinkAssocEntity(BaseAssocEntity):
    """An association row."""


@exclude_graph_model
@entity(description="Order line", domain=KindShopDomain)
class KindLineDetailEntity(BaseDetailEntity):
    """A detail row."""


@exclude_graph_model
@entity(description="Card payment", domain=KindShopDomain)
class KindCardSpecEntity(BaseSpecEntity):
    """A specialization row."""


@exclude_graph_model
@entity(description="Currency", domain=KindShopDomain)
class KindCurrencyEnumEntity(BaseEnumEntity):
    """A dictionary row."""

    USD = value(code="usd", display_name="US dollar")


EXPORTED = (
    (KindCustomerCoreEntity, "core", "Core"),
    (KindLinkAssocEntity, "assoc", "Association"),
    (KindLineDetailEntity, "detail", "Detail"),
    (KindCardSpecEntity, "spec", "Specialization"),
    (KindCurrencyEnumEntity, "enum", "Enumeration"),
)


@pytest.mark.parametrize(("entity_cls", "word", "label"), EXPORTED)
def test_each_aoa_kind_exports_its_word_and_name(entity_cls: type, word: str, label: str) -> None:
    """Every Entity row carries the kind word and the name its kind base declares, and validates."""
    row = EntityGraphNode(entity_cls).to_dict()
    assert row["properties"]["entity_kind"] == word
    assert row["properties"]["entity_kind_label"] == label
    _VALIDATOR.validate({"schema_version": "1.1", "nodes": [row], "edges": []})


def test_a_user_kind_exports_its_own_word_and_name() -> None:
    """A model with a kind AOA does not ship exports it and stays valid."""
    aggregate = exclude_graph_model(type(
        "BaseAggregateEntity",
        (BaseEntity,),
        {
            "__init_subclass__": classmethod(lambda cls, **kwargs: None),
            "__module__": __name__,
            "KIND_LABEL": "Aggregate",
        },
    ))
    order = exclude_graph_model(
        entity(description="Order", domain=KindShopDomain)(type("OrderAggregateEntity", (aggregate,), {"__module__": __name__}))
    )
    row = EntityGraphNode(order).to_dict()
    assert row["properties"]["entity_kind"] == "aggregate"
    assert row["properties"]["entity_kind_label"] == "Aggregate"
    _VALIDATOR.validate({"schema_version": "1.1", "nodes": [row], "edges": []})
