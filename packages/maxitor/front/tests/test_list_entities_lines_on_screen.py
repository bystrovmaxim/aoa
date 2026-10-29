# tests/maxitor/test_list_entities_lines_on_screen.py
"""
Tests that the ERD draws every line between two tables on screen, whatever brought each table there.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Reproduced on the admingameoffer graph (frozen as the reference graph of spec 025):
a relation between two 1-hop neighbours was dropped, a generalization between two
neighbours was dropped, a specialization head had no line to its axis dictionary,
and in the merged view a line whose ends came from two slices existed in none.
These tests pin each case on that graph, then sweep every slice and every set of
domains for a line that is missing or that ends off screen.
"""

from __future__ import annotations

import gzip
import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_REFERENCE_GRAPH = Path(__file__).resolve().parents[4] / "specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz"
_LINE_EDGES = ("entity_relation", "entity_reference", "parent_entity")


def _short(identifier: str) -> str:
    """The class name at the end of a dotted id."""
    return identifier.rsplit(".", 1)[-1]


@pytest.fixture(scope="module")
def graph() -> dict[str, Any]:
    """The frozen reference graph."""
    data = json.loads(gzip.decompress(_REFERENCE_GRAPH.read_bytes()))
    data = data.get("coordinator_json", data)
    return json.loads(data) if isinstance(data, str) else data


@pytest.fixture(scope="module")
def duck(graph: dict[str, Any]) -> DuckDBGraphResource:
    """The reference graph loaded into the store."""
    return DuckDBGraphResource.build_from_json(graph)


@pytest.fixture(scope="module")
def domains(graph: dict[str, Any]) -> dict[str, str]:
    """Domain ids by class name."""
    return {_short(node["id"]): node["id"] for node in graph["nodes"] if node["type"] == "Domain"}


def _pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """Unordered table pairs joined by ``rows``, as sorted short names."""
    return {tuple(sorted((_short(r["source"]), _short(r["target"])))) for r in rows}


def _slice(duck: DuckDBGraphResource, qual: str) -> dict[str, Any]:
    """One domain slice with its 1-hop neighbours."""
    return ListEntitiesAction._slice_payload(duck, qual, include_neighbors=True)


def test_two_neighbours_of_a_domain_are_joined(duck: DuckDBGraphResource, domains: dict[str, str]) -> None:
    """On ``EventsDomain`` the neighbours ``PlayerCore`` and ``ShowcaseCore`` are both drawn, so their line is."""
    pairs = _pairs(_slice(duck, domains["EventsDomain"])["relations"])

    assert ("PlayerCoreEntity", "ShowcaseCoreEntity") in pairs
    assert ("GenderEnumEntity", "PlayerCoreEntity") in pairs
    assert ("EnergyResourceCoreEntity", "GameCoreEntity") in pairs


def test_a_generalization_between_neighbours_is_drawn(duck: DuckDBGraphResource, domains: dict[str, str]) -> None:
    """On ``PlayersDomain`` the extensions of ``UserEventCore`` on screen keep their line to it."""
    rows = [r for r in _slice(duck, domains["PlayersDomain"])["relations"] if r["relationship_kind"] == "generalization"]

    assert {(_short(r["source"]), _short(r["target"])) for r in rows} >= {
        ("UserEventLoginSpecEntity", "UserEventCoreEntity"),
        ("UserEventNewProfileSpecEntity", "UserEventCoreEntity"),
        ("UserEventChangeProfileSpecEntity", "UserEventCoreEntity"),
    }


def test_a_specialization_head_is_joined_to_its_axis_dictionary(duck: DuckDBGraphResource, domains: dict[str, str]) -> None:
    """``UserEventCore`` specializes by ``kind`` from ``EventKindEnum``: one reference line joins them."""
    events = _slice(duck, domains["EventsDomain"])
    rows = [r for r in events["relations"] if _short(r["target"]) == "EventKindEnumEntity"]

    assert [(_short(r["source"]), r["label"], r["relationship_kind"]) for r in rows] == [
        ("UserEventCoreEntity", "kind", "reference"),
    ]
    players = _slice(duck, domains["PlayersDomain"])
    assert "EventKindEnumEntity" not in {_short(e["id"]) for e in players["entities"]}
    assert not [r for r in players["relations"] if _short(r["target"]) == "EventKindEnumEntity"]


def test_a_line_whose_ends_come_from_two_slices_is_in_the_request_list(
    duck: DuckDBGraphResource, domains: dict[str, str]
) -> None:
    """``OfferCore`` comes with the Players slice, ``IndustryEnum`` with the Showcases slice."""
    quals = [domains["PlayersDomain"], domains["ShowcasesDomain"]]
    in_slices = set().union(*(_pairs(_slice(duck, q)["relations"]) for q in quals))
    in_request = _pairs(ListEntitiesAction.request_relations(duck, quals, include_neighbors=True))

    assert ("IndustryEnumEntity", "OfferCoreEntity") not in in_slices
    assert ("IndustryEnumEntity", "OfferCoreEntity") in in_request


def test_no_line_is_missing_or_off_screen_for_any_view(
    graph: dict[str, Any], duck: DuckDBGraphResource, domains: dict[str, str]
) -> None:
    """Every slice and every set of domains: each graph line between two tables on screen is drawn, and only those."""
    lines = [(e["source_id"], e["target_id"]) for e in graph["edges"] if e["type"] in _LINE_EDGES]
    lines += [
        (e["source_id"], e["properties"]["dictionary_qualname"])
        for e in graph["edges"]
        if e["type"] == "entity_specialization" and e["properties"].get("dictionary_qualname")
    ]
    entity_ids = {q: {e["id"] for e in _slice(duck, q)["entities"]} for q in domains.values()}
    views: list[tuple[list[str], list[dict[str, Any]]]] = [
        ([q], [r for r in _slice(duck, q)["relations"] if r["relationship_kind"] != "specialization"]) for q in domains.values()
    ]
    for size in range(1, len(domains) + 1):
        for quals in itertools.combinations(domains.values(), size):
            views.append((list(quals), ListEntitiesAction.request_relations(duck, list(quals), include_neighbors=True)))

    problems = []
    for quals, rows in views:
        on_screen = set().union(*(entity_ids[q] for q in quals))
        drawn = {frozenset((r["source"], r["target"])) for r in rows}
        missing = {(_short(a), _short(b)) for a, b in lines if a in on_screen and b in on_screen and a != b and frozenset((a, b)) not in drawn}
        stray = [r for r in rows if r["source"] not in on_screen or r["target"] not in on_screen]
        if missing or stray:
            problems.append(([_short(q) for q in quals], sorted(missing), len(stray)))

    assert problems == []
