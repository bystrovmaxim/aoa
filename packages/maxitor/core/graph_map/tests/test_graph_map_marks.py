# packages/maxitor/core/graph_map/tests/test_graph_map_marks.py
"""What changed between two versions, as a map shows it (spec 040)."""

from __future__ import annotations

from typing import Any

from maxitor.graph_map import AreaLayout, Marks, Place, assemble, split_areas

from .graph_documents import document


def laid_out(graph: Any) -> tuple[dict[str, AreaLayout], dict[str, Place]]:
    """Every node at the middle of its area."""
    return {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}, {
        area.id: Place(0.0, 0.0, 230.0) for area in graph.areas
    }


def test_a_changed_domain_is_said_by_its_count_and_not_as_a_whole() -> None:
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    made = assemble(graph, layouts, places, ("#111111",), Marks({"d2": "changed"}, {}, {}))
    assert "status" not in next(item for item in made.overview["areas"] if item["id"] == "d2")


def test_marks_reach_the_overview_the_detail_and_the_changes() -> None:
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    marks = Marks(
        {"a": "changed", "b": "added", "d2": "added"}, {"a|entity_relation|b": "changed"}, {"a|entity_relation|b": "c"}
    )
    made = assemble(graph, layouts, places, ("#111111",), marks)
    area = next(item for item in made.overview["areas"] if item["id"] == "d2")
    assert area["status"] == "added" and area["changes"] == {"Domain": {"added": 1}, "Entity": {"added": 1}}
    assert made.overview["links_changed"] == 1 and made.overview["bundles"][0][4] == {"changed": 1}
    assert next(item for item in made.details["d1"]["across"] if item["id"] == "a|entity_relation|b")["was"] == "c"
    assert [item["id"] for item in made.changes] == ["a", "a|entity_relation|b", "b", "d2"]
    d1_nodes = {item["id"]: item for item in made.details["d1"]["nodes"]}
    assert d1_nodes["a"]["diff"] == "changed" and "diff" not in d1_nodes["shared"]
    link = made.changes[1]
    assert link["span"] == 0.0 and link["label"] == "A → B" and link["status"] == "changed"


def test_a_sketch_counts_by_type_chain_and_status() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), Marks({"a:f": "added"}, {}, {}))
    area = next(item for item in made.overview["areas"] if item["id"] == "d1")
    types, chains = made.overview["types"], made.overview["chains"]
    cells = {(types[cell[2]], tuple(chains[cell[4]]), cell[5]): cell[3] for cell in area["sketch"]["cells"]}
    assert cells[("EntityField", ("Domain", "Entity"), 1)] == 1
    assert cells[("Entity", ("Domain",), 3)] == 1


def test_what_holds_a_change_reads_as_changed_and_keeps_no_mark() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), Marks({"a:f": "added"}, {}, {}))
    held = next(item for item in made.details["d1"]["nodes"] if item["id"] == "a")
    assert held["glance"] == "changed" and "diff" not in held


def test_the_ends_of_a_changed_link_read_as_changed() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), Marks({}, {"a|entity_relation|b": "changed"}, {}))
    held = {item["id"]: item for detail in made.details.values() for item in detail["nodes"]}
    assert held["a"]["glance"] == "changed" and held["b"]["glance"] == "changed"


def test_a_domain_holding_a_change_reads_as_changed() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), Marks({"a:f": "added"}, {}, {}))
    assert next(item for item in made.details["d1"]["nodes"] if item["id"] == "d1")["glance"] == "changed"


def test_a_change_says_what_a_filter_asks_of_its_ends() -> None:
    graph = split_areas(document())
    made = assemble(
        graph, *laid_out(graph), ("#111111",), Marks({"a:f": "added"}, {"a|entity_relation|b": "changed"}, {})
    )
    field_change = next(item for item in made.changes if item["id"] == "a:f")
    link = next(item for item in made.changes if item["id"] == "a|entity_relation|b")
    chain = made.overview["chains"].index(["Domain", "Entity"])
    assert field_change["ends"] == [["a:f", "d1", "EntityField", chain, "added"]]
    assert [end[0] for end in link["ends"]] == ["a", "b"]
