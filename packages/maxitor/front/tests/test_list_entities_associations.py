# tests/maxitor/test_list_entities_associations.py
"""
Tests that a relation field and its declared inverse come out as one association.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PlayerCoreEntity.showcase`` and its inverse ``ShowcaseCoreEntity.players`` are one
association seen from both sides: one row, with the field on each side named, and the
cardinality of each end. A relation without an inverse — ``chosen_offer`` next to the
pair ``offers`` / ``offer_request`` — is an association of its own. The same
association always comes out in the same direction.
"""

from __future__ import annotations

import collections
import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_REFERENCE_GRAPH = Path(__file__).resolve().parents[4] / "specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz"
_PAIRED = ("association", "composition", "aggregation")


def _short(identifier: str) -> str:
    """The class name at the end of a dotted id."""
    return identifier.rsplit(".", 1)[-1]


@pytest.fixture(scope="module")
def reference() -> tuple[DuckDBGraphResource, list[str]]:
    """The frozen reference graph in the store, and its domain ids."""
    data = json.loads(gzip.decompress(_REFERENCE_GRAPH.read_bytes()))
    data = data.get("coordinator_json", data)
    graph = json.loads(data) if isinstance(data, str) else data
    return DuckDBGraphResource.build_from_json(graph), [n["id"] for n in graph["nodes"] if n["type"] == "Domain"]


def _associations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The relation rows that are associations (not references, generalizations or containers)."""
    return [r for r in rows if r["relationship_kind"] not in ("reference", "generalization", "specialization")]


def test_a_field_and_its_inverse_are_one_row(reference: tuple[DuckDBGraphResource, list[str]]) -> None:
    """``showcase`` / ``players`` give one row from the table that holds the ``one`` side."""
    duck, domains = reference
    rows = [r for r in _associations(ListEntitiesAction.request_relations(duck, domains, True))
            if {_short(r["source"]), _short(r["target"])} == {"PlayerCoreEntity", "ShowcaseCoreEntity"}]

    assert [(_short(r["source"]), r["source_field"], r["target_field"], r["source_cardinality"], r["target_cardinality"]) for r in rows] == [
        ("PlayerCoreEntity", "showcase", "players", "zero_many", "one"),
    ]


def test_a_relation_without_an_inverse_is_its_own_row(reference: tuple[DuckDBGraphResource, list[str]]) -> None:
    """``chosen_offer`` has no inverse, so it is a second association beside ``offers`` / ``offer_request``."""
    duck, domains = reference
    rows = [r for r in _associations(ListEntitiesAction.request_relations(duck, domains, True))
            if {_short(r["source"]), _short(r["target"])} == {"OfferRequestCoreEntity", "OfferRequestItemDetailEntity"}]

    assert sorted((r["source_field"], r["target_field"]) for r in rows) == [
        ("chosen_offer", None),
        ("offer_request", "offers"),
    ]


def test_the_reference_graph_has_34_associations(reference: tuple[DuckDBGraphResource, list[str]]) -> None:
    """46 relation fields, 34 associations, and only one pair of tables keeps two."""
    duck, domains = reference
    rows = _associations(ListEntitiesAction.request_relations(duck, domains, True))
    pairs = collections.Counter(frozenset((r["source"], r["target"])) for r in rows)

    assert len(rows) == 34
    assert [sorted(_short(t) for t in pair) for pair, count in pairs.items() if count > 1] == [
        ["OfferRequestCoreEntity", "OfferRequestItemDetailEntity"],
    ]


def test_a_slice_pairs_the_same_way(reference: tuple[DuckDBGraphResource, list[str]]) -> None:
    """Each domain slice draws one line for the pair too."""
    duck, domains = reference
    events = next(d for d in domains if d.endswith("EventsDomain"))
    rows = [r for r in _associations(ListEntitiesAction._slice_payload(duck, events, True)["relations"])
            if {_short(r["source"]), _short(r["target"])} == {"PlayerCoreEntity", "ShowcaseCoreEntity"}]

    assert len(rows) == 1


def _one_to_one(first: str, second: str) -> dict[str, Any]:
    """A graph with two tables joined one-to-one by ``partner`` / ``partner_of``, ids as given."""
    domain = "shop.ShopDomain"

    def entity(identifier: str) -> dict[str, Any]:
        return {"id": identifier, "type": "Entity", "label": _short(identifier), "properties": {"description": "", "entity_kind": "core"}}

    def relation(source: str, target: str, field: str, inverse: str) -> dict[str, Any]:
        return {
            "source_id": source, "target_id": target, "type": "entity_relation", "relationship": "Association", "is_dag": False,
            "properties": {"field_name": field, "cardinality": "one", "relation_type": "association", "description": "",
                           "has_inverse": True, "deprecated": False, "inverse_entity_id": target, "inverse_field": inverse},
        }

    return {
        "schema_version": "1.0",
        "nodes": [{"id": domain, "type": "Domain", "label": "ShopDomain", "properties": {"name": "shop", "description": ""}},
                  entity(first), entity(second)],
        "edges": [
            *({"source_id": e, "target_id": domain, "type": "domain", "relationship": "Composition", "is_dag": False} for e in (first, second)),
            relation(first, second, "partner", "partner_of"),
            relation(second, first, "partner_of", "partner"),
        ],
    }


@pytest.mark.parametrize(("first", "second"), [("shop.AEntity", "shop.BEntity"), ("shop.BEntity", "shop.AEntity")])
def test_a_one_to_one_pair_always_comes_out_from_the_smaller_id(first: str, second: str) -> None:
    """With both sides ``one``, the table with the smaller id is the source, whatever order the graph lists them in."""
    duck = DuckDBGraphResource.build_from_json(_one_to_one(first, second))
    rows = _associations(ListEntitiesAction.request_relations(duck, ["shop.ShopDomain"], False))

    assert [(r["source"], r["source_field"], r["target_field"], r["source_cardinality"], r["target_cardinality"]) for r in rows] == [
        ("shop.AEntity", "partner" if first == "shop.AEntity" else "partner_of",
         "partner_of" if first == "shop.AEntity" else "partner", "one", "one"),
    ]


def test_generalizations_are_never_paired(reference: tuple[DuckDBGraphResource, list[str]]) -> None:
    """An extension's line to its head stays a generalization of its own."""
    duck, domains = reference
    rows = [r for r in ListEntitiesAction.request_relations(duck, domains, True) if r["relationship_kind"] == "generalization"]

    assert len(rows) == 5
    assert all(_short(r["target"]) == "UserEventCoreEntity" for r in rows)


def test_a_field_is_paired_only_with_its_declared_inverse() -> None:
    """``A.b`` ↔ ``B.a_list`` is one association; ``B.owner`` → ``A`` has no inverse and must not be taken for one."""
    domain = "shop.ShopDomain"

    def entity(identifier: str) -> dict[str, Any]:
        return {"id": identifier, "type": "Entity", "label": _short(identifier), "properties": {"description": "", "entity_kind": "core"}}

    def relation(source: str, target: str, field: str, cardinality: str, inverse: str | None) -> dict[str, Any]:
        properties = {"field_name": field, "cardinality": cardinality, "relation_type": "association", "description": "",
                      "has_inverse": inverse is not None, "deprecated": False}
        if inverse:
            properties.update(inverse_entity_id=target, inverse_field=inverse)
        return {"source_id": source, "target_id": target, "type": "entity_relation", "relationship": "Association",
                "is_dag": False, "properties": properties}

    graph = {
        "schema_version": "1.0",
        "nodes": [{"id": domain, "type": "Domain", "label": "ShopDomain", "properties": {"name": "shop", "description": ""}},
                  entity("shop.AEntity"), entity("shop.BEntity")],
        "edges": [
            *({"source_id": e, "target_id": domain, "type": "domain", "relationship": "Composition", "is_dag": False}
              for e in ("shop.AEntity", "shop.BEntity")),
            relation("shop.AEntity", "shop.BEntity", "b", "one", "a_list"),
            relation("shop.BEntity", "shop.AEntity", "a_list", "many", "b"),
            relation("shop.BEntity", "shop.AEntity", "owner", "one", None),
        ],
    }
    rows = _associations(ListEntitiesAction.request_relations(DuckDBGraphResource.build_from_json(graph), [domain], False))

    assert sorted((r["source_field"], r["target_field"]) for r in rows) == [("b", "a_list"), ("owner", None)]
