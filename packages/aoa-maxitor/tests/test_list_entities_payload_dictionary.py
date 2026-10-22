# tests/maxitor/test_list_entities_payload_dictionary.py
"""The ERD payload carries a dictionary's values and the fields that reference it."""

from __future__ import annotations

import json
from typing import Any

from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_DICTIONARIES = "aoa.demo.model.dictionaries.domain.DictionariesDomain"
_BILLING = "aoa.demo.model.billing.domain.BillingDomain"


def _slice(domain: str = _DICTIONARIES) -> dict[str, Any]:
    """Build the demo graph, then read one domain's slice."""
    from aoa.demo.model.interchange_demo_coordinator import (
        build_registered_interchange_coordinator,
    )

    graph = json.loads(build_registered_interchange_coordinator().to_json())
    duck = DuckDBGraphResource.build_from_json(graph)
    payload = ListEntitiesAction._slice_payload(duck, domain, include_neighbors=False)
    assert isinstance(payload, dict)
    return payload


def test_the_dictionary_row_carries_its_values() -> None:
    """The card has the rows a reader needs, and nothing else."""
    currency = next(entity for entity in _slice()["entities"] if entity["label"] == "CurrencyEnumEntity")

    assert currency["entity_kind"] == "enum"
    assert currency["values"] == [
        {"code": "usd", "display_name": "US dollar"},
        {"code": "eur", "display_name": "Euro"},
        {"code": "rub", "display_name": "Ruble"},
    ]


def test_a_plain_entity_carries_no_values() -> None:
    """Only a dictionary declares values; the key is present and empty elsewhere."""
    for entity in _slice()["entities"]:
        if entity["label"] != "CurrencyEnumEntity":
            assert entity["values"] == []


def test_a_field_that_references_the_dictionary_names_it() -> None:
    """A reference is readable in the payload, so the client can draw it as a reference."""
    payload = _slice(_BILLING)
    references = [
        field
        for entity in payload["entities"]
        for field in entity["fields"]
        if (field.get("reference_qualname") or "").endswith("CurrencyEnumEntity")
    ]

    assert references, "a currency field in the dictionaries domain must reference the dictionary"
