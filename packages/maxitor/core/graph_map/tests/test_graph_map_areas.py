# packages/maxitor/core/graph_map/tests/test_graph_map_areas.py
"""A graph document cut into areas, and each area read to and from a layout (spec 040)."""

from __future__ import annotations

import json

from maxitor.graph_map import OUTSIDE, area_dot, read_layout, split_areas

from .graph_documents import by_id, document, edge, node


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
    assert not any(
        item.type == "parent_entity" for area in split_areas(document()).areas for item in (*area.inner, *area.across)
    )


def test_links_between_areas_are_counted_by_the_types_of_their_ends() -> None:
    assert split_areas(document()).links == {
        ("d1", "d2"): {"Entity>Domain|Entity>Domain": 2, "Entity>Domain|Domain": 1}
    }


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
    answer = {
        "bb": "0,0,200,100",
        "objects": [{"name": "n0", "pos": "0,0"}, {"name": "n1", "pos": "200,100"}, {"name": "n2", "pos": "100,50"}],
    }
    layout = read_layout(area, json.dumps(answer))
    assert layout.positions == {"b": (-100.0, -50.0), "c": (100.0, 50.0), "d2": (0.0, 0.0)}
    assert layout.radius > 111


def test_homes_name_where_a_node_stands_whatever_its_domains() -> None:
    areas = {area.id: area for area in split_areas(document(), {"a": "d2"}).areas}
    assert "a" in {item.id for item in areas["d2"].nodes} and "a" not in {item.id for item in areas["d1"].nodes}


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
    held["edges"] += [
        edge("first", "lifecycle_transition", "next", "Composition"),
        edge("f", "entity_schema", "schema", "Aggregation"),
    ]
    nodes = {item.id: item for area in split_areas(held).areas for item in area.nodes}
    assert "StateInitial" not in nodes["next"].above
    assert "Field" not in nodes["schema"].above
