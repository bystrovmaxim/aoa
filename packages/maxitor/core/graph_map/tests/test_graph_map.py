# packages/maxitor/core/graph_map/tests/test_graph_map.py
"""A graph document cut into areas, laid out, placed and assembled (spec 040)."""

from __future__ import annotations

import json
from typing import Any

from maxitor.graph_map import OUTSIDE, AreaLayout, Place, area_dot, assemble, read_layout, settle_places, split_areas


def node(identifier: str, kind: str = "Entity") -> dict[str, Any]:
    """A node of the graph file."""
    return {"id": identifier, "label": identifier.upper(), "type": kind, "properties": {}}


def edge(source: str, kind: str, target: str, relationship: str = "Association") -> dict[str, Any]:
    """A link of the graph file."""
    return {"id": f"{source}|{kind}|{target}", "source_id": source, "target_id": target, "type": kind, "relationship": relationship, "properties": {}}


def document() -> dict[str, Any]:
    """Two domains; a field held by an entity; a node in both domains; one in none; a generalization."""
    return {
        "nodes": [node("d1", "Domain"), node("d2", "Domain"), node("a"), node("a:f", "EntityField"), node("b"), node("shared"), node("free", "Role"), node("c")],
        "edges": [
            edge("a", "domain", "d1", "Aggregation"),
            edge("b", "domain", "d2", "Aggregation"),
            edge("shared", "domain", "d1", "Aggregation"),
            edge("shared", "domain", "d2", "Aggregation"),
            edge("c", "domain", "d2", "Aggregation"),
            edge("a", "entity_field", "a:f", "Composition"),
            edge("a", "entity_relation", "b"),
            edge("a", "entity_relation_2", "c"),
            edge("b", "parent_entity", "c", "Generalization"),
        ],
    }


def by_id(document_: dict[str, Any]) -> dict[str, Any]:
    """The areas of a document by id."""
    return {area.id: area for area in split_areas(document_).areas}


def test_every_node_stands_in_one_area() -> None:
    areas = by_id(document())
    assert [item.id for item in areas["d1"].nodes] == ["a", "a:f", "d1", "shared"]
    assert [item.id for item in areas["d2"].nodes] == ["b", "c", "d2"]
    assert [item.id for item in areas[OUTSIDE].nodes] == ["free"]


def test_what_something_contains_stands_with_it() -> None:
    assert "a:f" in [item.id for item in by_id(document())["d1"].nodes]


def test_a_node_in_several_domains_lists_them_all() -> None:
    assert split_areas(document()).memberships == {"shared": ("d1", "d2")}


def test_levels() -> None:
    levels = {item.id: item.level for item in by_id(document())["d1"].nodes}
    assert levels == {"a": 2, "a:f": 3, "d1": 2, "shared": 2}


def test_a_generalization_is_not_drawn() -> None:
    assert not any(item.type == "parent_entity" for area in split_areas(document()).areas for item in (*area.inner, *area.across))


def test_links_between_areas_are_counted_by_the_types_of_their_ends() -> None:
    assert split_areas(document()).links == {("d1", "d2"): {"Entity|Entity": 2, "Entity|Domain": 1}}


def test_the_content_hash_ignores_labels_and_follows_structure() -> None:
    relabelled = document()
    relabelled["nodes"][2]["label"] = "another name"
    assert by_id(relabelled)["d1"].content_hash == by_id(document())["d1"].content_hash
    grown = document()
    grown["nodes"].append(node("a:g", "EntityField"))
    grown["edges"].append(edge("a", "entity_field", "a:g", "Composition"))
    changed, same = by_id(grown), by_id(document())
    assert changed["d1"].content_hash != same["d1"].content_hash
    assert changed["d2"].content_hash == same["d2"].content_hash


def test_the_dot_does_not_depend_on_the_documents_order() -> None:
    shuffled = document()
    shuffled["nodes"].reverse()
    shuffled["edges"].reverse()
    assert area_dot(by_id(shuffled)["d1"]) == area_dot(by_id(document())["d1"])


def test_a_layout_is_read_around_the_areas_centre() -> None:
    area = by_id(document())["d2"]
    answer = {"bb": "0,0,200,100", "objects": [{"name": "n0", "pos": "0,0"}, {"name": "n1", "pos": "200,100"}, {"name": "n2", "pos": "100,50"}]}
    layout = read_layout(area, json.dumps(answer))
    assert layout.positions == {"b": (-100.0, -50.0), "c": (100.0, 50.0), "d2": (0.0, 0.0)}
    assert layout.radius > 111


def test_no_two_rooms_overlap() -> None:
    places = settle_places({f"a{i}": 100.0 + i * 10 for i in range(40)}, {}, {})
    items = list(places.values())
    for index, one in enumerate(items):
        for other in items[index + 1 :]:
            assert ((one.x - other.x) ** 2 + (one.y - other.y) ** 2) ** 0.5 >= one.room + other.room


def test_an_area_that_fits_keeps_its_place_to_the_digit() -> None:
    known = settle_places({"a": 100.0, "b": 100.0}, {}, {})
    assert settle_places({"a": 110.0, "b": 100.0}, {}, known) == known


def test_a_new_area_stands_beside_what_it_links_to_and_moves_nothing() -> None:
    known = settle_places({"a": 100.0, "b": 100.0, "c": 100.0, "d": 100.0}, {}, {})
    after = settle_places({"a": 100.0, "b": 100.0, "c": 100.0, "d": 100.0, "e": 100.0}, {("a", "e"): 5}, known)
    assert {area: after[area] for area in known} == known
    nearest = min(known, key=lambda area: (known[area].x - after["e"].x) ** 2 + (known[area].y - after["e"].y) ** 2)
    assert nearest == "a"


def test_an_area_that_outgrows_its_room_moves_alone() -> None:
    known = settle_places({"a": 100.0, "b": 100.0, "c": 100.0}, {}, {})
    after = settle_places({"a": 100.0, "b": 100.0, "c": 400.0}, {}, known)
    assert after["a"] == known["a"] and after["b"] == known["b"]
    assert after["c"].room > known["c"].room


def test_a_removed_area_keeps_its_place() -> None:
    known = settle_places({"a": 100.0, "b": 100.0}, {}, {})
    assert settle_places({"a": 100.0}, {}, known)["b"] == known["b"]


def assembled() -> Any:
    """The test document's map, every node at the centre but one."""
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (10.0, 20.0) for item in area.nodes}, 200.0) for area in graph.areas}
    places = {area.id: Place(1000.0 * index, 0.0, 230.0) for index, area in enumerate(graph.areas)}
    return assemble(graph, layouts, places, ("#111111", "#222222"))


def test_the_overview_says_what_a_filter_needs() -> None:
    overview = assembled().overview
    area = next(item for item in overview["areas"] if item["id"] == "d2")
    assert area["counts"] == {"Domain": 1, "Entity": 2}
    assert overview["bundles"] == [["d1", "d2", 3, {"Entity|Domain": 1, "Entity|Entity": 2}]]
    assert overview["shared"] == [{"id": "shared", "domains": ["d1", "d2"]}]


def test_a_sketch_counts_every_node_once() -> None:
    for area in assembled().overview["areas"]:
        assert sum(cell[3] for cell in area["sketch"]["cells"]) == sum(area["counts"].values())


def test_a_detail_stands_at_the_areas_place() -> None:
    detail = assembled().details["d1"]
    place = next(item for item in assembled().overview["areas"] if item["id"] == "d1")
    item = next(each for each in detail["nodes"] if each["id"] == "a")
    assert (item["x"], item["y"]) == (place["x"] + 10.0, place["y"] + 20.0)
    assert {each["id"]: each["level"] for each in detail["edges"]} == {"a|domain|d1": 2, "shared|domain|d1": 2, "a|entity_field|a:f": 3}


def test_an_area_with_no_layout_leaves_the_rest_readable() -> None:
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas if area.id != "d2"}
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    result = assemble(graph, layouts, places, ("#111111",))
    assert next(item for item in result.overview["areas"] if item["id"] == "d2")["failed"] is True
    assert "d2" not in result.details and "d1" in result.details
