# packages/maxitor/tools/graph_builder/tests/test_schemas.py
"""The graph schema by version: what passes, what is refused and why, and that a published version never changes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from maxitor.graph_builder.schemas import SCHEMA_VERSIONS, GraphRefused, check_graph, graph_schema

FIXTURES = Path(__file__).parent / "fixtures"
PROTOCOL_1_3 = Path(__file__).parents[4] / "open-gnomon-protocol" / "graph" / "1.3.json"


def _sample(version: str) -> dict[str, Any]:
    """A small graph of that version: one edge of every type in the demo's graph, and their nodes."""
    document: dict[str, Any] = json.loads((FIXTURES / f"graph-{version}.json").read_text(encoding="utf-8"))
    return document


@pytest.mark.parametrize("version", SCHEMA_VERSIONS)
def test_a_graph_of_each_version_passes(version: str) -> None:
    """The sample of every known version is a graph of that version."""
    check_graph(_sample(version))


def test_an_edge_without_an_id_is_refused_by_1_1() -> None:
    """Since 1.1 every edge has an ``id``; the refusal names the edge."""
    document = _sample("1.1")
    del document["edges"][3]["id"]
    with pytest.raises(GraphRefused) as refused:
        check_graph(document)
    assert (refused.value.version, refused.value.path) == ("1.1", "edges/3")
    assert "'id'" in refused.value.reason


def test_a_1_0_graph_claiming_1_1_is_refused() -> None:
    """A document is checked against the version it claims, not the one it would fit."""
    document = _sample("1.0")
    document["schema_version"] = "1.1"
    with pytest.raises(GraphRefused, match="'id' is a required property"):
        check_graph(document)


def test_an_unknown_version_is_refused_by_name() -> None:
    """``9.9`` is no version; both entry points say so and list the known ones."""
    document = _sample("1.1")
    document["schema_version"] = "9.9"
    with pytest.raises(GraphRefused, match=r"unknown schema version '9\.9'; known: 1\.0, 1\.1"):
        check_graph(document)
    with pytest.raises(GraphRefused, match=r"'9\.9'"):
        graph_schema("9.9")


def test_a_document_without_a_version_is_refused() -> None:
    """Without ``schema_version`` no schema applies."""
    document = _sample("1.1")
    del document["schema_version"]
    with pytest.raises(GraphRefused, match="no schema_version"):
        check_graph(document)


def test_an_edge_of_no_known_shape_is_refused_briefly() -> None:
    """When no branch of a union was meant, the refusal names the place, not the whole value."""
    document = _sample("1.1")
    document["edges"][3]["relationship"] = "Nonsense"
    with pytest.raises(GraphRefused) as refused:
        check_graph(document)
    assert (refused.value.path, refused.value.reason) == ("edges/3", "matches none of the shapes allowed here")


def test_a_wrong_value_inside_the_meant_shape_is_named_by_its_path() -> None:
    """Inside the branch an edge was meant for, the refusal reaches the field itself."""
    document = _sample("1.1")
    document["edges"][3]["source_id"] = 5
    with pytest.raises(GraphRefused) as refused:
        check_graph(document)
    assert (refused.value.path, refused.value.reason) == ("edges/3/source_id", "5 is not of type 'string'")


@pytest.mark.parametrize("document", [[], "graph", None])
def test_something_that_is_not_an_object_is_refused(document: object) -> None:
    """A graph document is a JSON object."""
    with pytest.raises(GraphRefused, match="JSON object"):
        check_graph(document)


@pytest.mark.parametrize("version", SCHEMA_VERSIONS)
def test_each_version_is_the_protocols(version: str) -> None:
    """Every known version is the protocol's own, named by its raw ``$id`` (its bytes are proved by ``tests/scripts``)."""
    assert graph_schema(version)["$id"].endswith(f"/packages/open-gnomon-protocol/graph/{version}.json")


def test_a_large_graph_is_checked_in_moments() -> None:
    """A graph the size of the demo's is checked in well under a second, not the tens a pure-Python check takes."""
    sample = _sample("1.1")
    copies = range(100)
    document = {
        "schema_version": "1.1",
        "nodes": [{**node, "id": f"{node['id']}#{n}"} for n in copies for node in sample["nodes"]],
        "edges": [{**edge, "id": f"{edge['id']}#{n}"} for n in copies for edge in sample["edges"]],
    }
    started = time.monotonic()
    check_graph(document)
    assert time.monotonic() - started < 2


def test_a_repeated_node_is_refused_without_its_whole_value() -> None:
    """The same node twice: the refusal names the array, not every node in it."""
    document = _sample("1.1")
    document["nodes"].append(document["nodes"][0])
    with pytest.raises(GraphRefused) as refused:
        check_graph(document)
    assert (refused.value.path, refused.value.reason) == ("nodes", "holds the same element twice")


def _events_document() -> dict[str, Any]:
    """A minimal 1.3 document: a domain, an aspect, an event and both new edges."""
    return {
        "schema_version": "1.3",
        "nodes": [
            {"id": "shop.Domain", "type": "Domain", "label": "Domain", "properties": {"name": "shop", "description": "Shop", "typed_events": True}},
            {"id": "shop.Place:finish", "type": "RegularAspect", "label": "finish", "properties": {"description": "Finish"}},
            {"id": "shop.PlacedEvent", "type": "Event", "label": "PlacedEvent", "properties": {}},
        ],
        "edges": [
            {"id": "e1", "source_id": "shop.Domain", "target_id": "shop.PlacedEvent", "type": "domain_event", "relationship": "Aggregation", "is_dag": False, "properties": {}},
            {"id": "e2", "source_id": "shop.Place:finish", "target_id": "shop.PlacedEvent", "type": "@emits", "relationship": "Association", "is_dag": False, "properties": {}},
        ],
    }


def _events_errors(document: dict[str, Any]) -> list[Any]:
    """Check ``document`` against the protocol's own 1.3 file."""
    schema = json.loads(PROTOCOL_1_3.read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(document))


def test_the_words_of_1_3_pass() -> None:
    """A document with an event, its two edges and ``typed_events`` is a 1.3 graph."""
    assert _events_errors(_events_document()) == []


def test_an_event_carries_no_properties() -> None:
    """An ``Event`` node's facts are its fields; its own properties stay empty."""
    document = _events_document()
    document["nodes"][2]["properties"] = {"description": "Placed"}
    assert _events_errors(document)


def test_a_domain_must_say_typed_events() -> None:
    """A reader never guesses whether a domain has a vocabulary."""
    document = _events_document()
    del document["nodes"][0]["properties"]["typed_events"]
    assert _events_errors(document)


def test_typed_events_is_a_boolean() -> None:
    """``typed_events`` answers yes or no."""
    document = _events_document()
    document["nodes"][0]["properties"]["typed_events"] = "yes"
    assert _events_errors(document)


@pytest.mark.parametrize(
    ("index", "member", "value"),
    [
        (0, "relationship", "Association"),
        (1, "relationship", "Aggregation"),
        (0, "is_dag", True),
        (1, "is_dag", True),
        (0, "properties", {"a": 1}),
        (1, "properties", {"a": 1}),
    ],
)
def test_the_new_edges_have_a_fixed_shape(index: int, member: str, value: Any) -> None:
    """``domain_event`` is an Aggregation, ``@emits`` an Association; neither is in the acyclic slice or has properties."""
    document = _events_document()
    document["edges"][index][member] = value
    assert _events_errors(document)
