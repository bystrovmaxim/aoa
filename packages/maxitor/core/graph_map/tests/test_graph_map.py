# packages/maxitor/core/graph_map/tests/test_graph_map.py
"""A graph document cut into areas, laid out, placed and assembled (spec 040)."""

from __future__ import annotations

import json
from typing import Any

from maxitor.graph_map import (
    OUTSIDE,
    AreaLayout,
    Marks,
    Place,
    area_dot,
    assemble,
    read_layout,
    settle_places,
    split_areas,
    union_document,
    union_layouts,
)


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
    assert split_areas(document()).links == {("d1", "d2"): {"Entity>Domain|Entity>Domain": 2, "Entity>Domain|Domain": 1}}


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
    assert overview["bundles"] == [["d1", "d2", 3, {"Entity>Domain|Domain": 1, "Entity>Domain|Entity>Domain": 2}]]
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


def test_a_union_keeps_b_and_remembers_where_a_relation_pointed() -> None:
    older, newer = document(), document()
    newer["nodes"] = [item for item in newer["nodes"] if item["id"] != "free"]
    newer["edges"][6]["target_id"] = "c"
    joined, was = union_document(older, newer)
    assert "free" in {item["id"] for item in joined["nodes"]}
    assert was == {"a|entity_relation|b": "b"}


def test_a_node_in_b_stands_where_b_has_it_and_a_node_only_in_a_beside_it() -> None:
    older, newer = document(), document()
    older["nodes"].append(node("gone"))
    older["edges"].append(edge("gone", "domain", "d1", "Aggregation"))
    joined, _ = union_document(older, newer)
    union = split_areas(joined)
    positions = {item.id: (float(index * 100), 0.0) for index, item in enumerate(by_id(newer)["d1"].nodes)}
    b = {"d1": AreaLayout(positions, 300.0)}
    a = {"d1": AreaLayout({**positions, "gone": positions["a"]}, 300.0)}
    merged = union_layouts(union, a, b)["d1"]
    assert all(merged.positions[key] == value for key, value in positions.items())
    x, y = merged.positions["gone"]
    assert min(((x - px) ** 2 + (y - py) ** 2) ** 0.5 for px, py in positions.values()) >= 45


def test_homes_name_where_a_node_stands_whatever_its_domains() -> None:
    areas = {area.id: area for area in split_areas(document(), {"a": "d2"}).areas}
    assert "a" in {item.id for item in areas["d2"].nodes} and "a" not in {item.id for item in areas["d1"].nodes}


def test_a_changed_domain_is_said_by_its_count_and_not_as_a_whole() -> None:
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    made = assemble(graph, layouts, places, ("#111111",), Marks({"d2": "changed"}, {}, {}))
    assert "status" not in next(item for item in made.overview["areas"] if item["id"] == "d2")


def test_an_area_only_in_a_takes_a_layout_from_a() -> None:
    older, newer = document(), document()
    newer["nodes"] = [item for item in newer["nodes"] if item["id"] != "d2"]
    joined, _ = union_document(older, newer)
    union = split_areas(joined)
    layouts = union_layouts(union, {"d2": AreaLayout({"d2": (5.0, 6.0)}, 200.0)}, {})
    assert layouts["d2"].positions["d2"] == (5.0, 6.0)


def test_marks_reach_the_overview_the_detail_and_the_changes() -> None:
    graph = split_areas(document())
    layouts = {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    marks = Marks({"a": "changed", "b": "added", "d2": "added"}, {"a|entity_relation|b": "changed"}, {"a|entity_relation|b": "c"})
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


def test_a_contained_node_knows_the_types_above_it() -> None:
    held = document()
    held["nodes"].append(node("a:f:s", "State"))
    held["edges"].append(edge("a:f", "state", "a:f:s", "Composition"))
    nodes = {item.id: item for area in split_areas(held).areas for item in area.nodes}
    assert nodes["a:f"].above == ("Domain", "Entity")
    assert nodes["a:f:s"].above == ("Domain", "Entity", "EntityField")
    assert nodes["a"].above == ("Domain",)
    assert nodes["c"].above == ("Domain",)


def test_an_application_stands_above_its_domains_and_all_they_hold() -> None:
    held = document()
    held["nodes"].append(node("app", "Application"))
    held["edges"].append(edge("d1", "application", "app", "Aggregation"))
    nodes = {item.id: item for area in split_areas(held).areas for item in area.nodes}
    assert nodes["d1"].above == ("Application",)
    assert nodes["a:f"].above == ("Application", "Domain", "Entity")


def test_a_transition_and_a_schema_hold_nothing() -> None:
    held = document()
    held["nodes"] += [node("first", "StateInitial"), node("next", "StateFinal"), node("f", "Field"), node("schema")]
    held["edges"] += [edge("first", "lifecycle_transition", "next", "Composition"), edge("f", "entity_schema", "schema", "Aggregation")]
    nodes = {item.id: item for area in split_areas(held).areas for item in area.nodes}
    assert "StateInitial" not in nodes["next"].above
    assert "Field" not in nodes["schema"].above


def laid_out(graph: Any) -> tuple[dict[str, AreaLayout], dict[str, Place]]:
    """Every node at the middle of its area."""
    return {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}, {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}


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
    made = assemble(graph, *laid_out(graph), ("#111111",), Marks({"a:f": "added"}, {"a|entity_relation|b": "changed"}, {}))
    field_change = next(item for item in made.changes if item["id"] == "a:f")
    link = next(item for item in made.changes if item["id"] == "a|entity_relation|b")
    chain = made.overview["chains"].index(["Domain", "Entity"])
    assert field_change["ends"] == [["a:f", "d1", "EntityField", chain, "added"]]
    assert [end[0] for end in link["ends"]] == ["a", "b"]


def test_types_carry_their_colours() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), type_colour=lambda name: f"#{len(name):06d}")
    assert made.overview["type_colours"]["Entity"] == "#000006"
