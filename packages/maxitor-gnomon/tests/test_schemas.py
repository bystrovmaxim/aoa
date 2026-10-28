# packages/maxitor-gnomon/tests/test_schemas.py
"""The graph schema by version: what passes, what is refused and why, and that a published version never changes."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pytest
from maxitor_gnomon.schemas import SCHEMA_VERSIONS, GraphRefused, check_graph, graph_schema

FIXTURES = Path(__file__).parent / "fixtures"

# SHA-256 of each published schema without its ``$id``, as ``json.dumps(..., sort_keys=True)``.
# A published version never changes: a new shape of the graph is a new version, not an edit.
PUBLISHED = {
    "1.0": "77f1a7960a09dcb63b31d75e9d08467dd34c28e563281f959beb087c615b9bb4",
    "1.1": "4d5e7bbe4efadbbba63a03a598a8784c240db5d81322cd0fd794d726c2b5adde",
}


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
def test_a_published_version_never_changes(version: str) -> None:
    """Every known version is published, its ``$id`` names it, and its content has the hash it was published with."""
    schema = dict(graph_schema(version))
    assert schema.pop("$id").endswith(f"/schemas/graph/{version}.json")
    assert hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest() == PUBLISHED[version]
    assert set(PUBLISHED) == set(SCHEMA_VERSIONS)


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
