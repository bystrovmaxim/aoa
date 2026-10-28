# packages/maxitor/tools/gnomon/tests/test_differences.py
"""Differences between two graph documents: elements matched by ``id``, one line per change."""

from __future__ import annotations

from typing import Any

from maxitor.gnomon.differences import differences


def _graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], version: str = "1.1") -> dict[str, Any]:
    """A minimal document: a version, nodes and edges."""
    return {"schema_version": version, "nodes": nodes, "edges": edges}


A = {"id": "pkg.A", "label": "A", "properties": {"kind": "entity"}}
B = {"id": "pkg.B", "label": "B", "properties": {}}
AB = {"id": "pkg.A|uses|pkg.B", "source_id": "pkg.A", "target_id": "pkg.B"}


def test_equal_documents_have_no_differences() -> None:
    """Nothing changed, nothing to say."""
    assert differences(_graph([A, B], [AB]), _graph([A, B], [AB])) == []


def test_elements_are_matched_by_id_not_by_position() -> None:
    """Reordering nodes is no change; a node gone and a node come are named by id."""
    c = {"id": "pkg.C", "label": "C", "properties": {}}
    assert differences(_graph([A, B], [AB]), _graph([c, A], [AB])) == [
        "nodes[id=pkg.B]: removed",
        "nodes[id=pkg.C]: added",
    ]


def test_a_changed_field_is_named_by_its_path() -> None:
    """A field inside an element, at any depth, is named from the top."""
    moved = {**AB, "target_id": "pkg.C"}
    renamed = {**A, "properties": {"kind": "value"}}
    assert differences(_graph([A, B], [AB]), _graph([renamed, B], [moved])) == [
        "edges[id=pkg.A|uses|pkg.B].target_id: pkg.B → pkg.C",
        "nodes[id=pkg.A].properties.kind: entity → value",
    ]


def test_fields_added_and_removed_and_the_version() -> None:
    """A new key, a dropped key and a new version each get their line."""
    old = _graph([A], [], "1.0")
    new = _graph([{"id": "pkg.A", "label": "A", "properties": {"kind": "entity"}, "note": "x"}], [])
    del new["nodes"][0]["label"]
    assert differences(old, new) == [
        "nodes[id=pkg.A].label: removed",
        "nodes[id=pkg.A].note: added",
        "schema_version: 1.0 → 1.1",
    ]


def test_an_array_without_ids_is_compared_as_a_value() -> None:
    """A list of plain values is one value: it changed or it did not."""
    old = _graph([{**A, "properties": {"tags": ["a", "b"]}}], [])
    new = _graph([{**A, "properties": {"tags": ["b", "a"]}}], [])
    assert differences(old, new) == ['nodes[id=pkg.A].properties.tags: ["a", "b"] → ["b", "a"]']


def test_long_values_are_shortened() -> None:
    """A value longer than one short line ends with an ellipsis."""
    old = _graph([{**A, "label": "x" * 100}], [])
    (line,) = differences(old, _graph([A], []))
    assert line == f"nodes[id=pkg.A].label: {'x' * 59}… → A"


def test_past_the_limit_the_rest_is_counted() -> None:
    """At most ``limit`` lines, then how many more."""
    new = _graph([{"id": f"n{i}", "label": "", "properties": {}} for i in range(25)], [])
    lines = differences(_graph([], []), new, limit=20)
    assert len(lines) == 21
    assert lines[-1] == "… and 5 more"
