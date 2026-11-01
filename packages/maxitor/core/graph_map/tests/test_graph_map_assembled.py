# packages/maxitor/core/graph_map/tests/test_graph_map_assembled.py
"""Areas, layouts and places assembled into a version's map (spec 040)."""

from __future__ import annotations

from typing import Any

from maxitor.graph_map import AreaLayout, Place, assemble, split_areas

from .graph_documents import document


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
    assert {each["id"]: each["level"] for each in detail["edges"]} == {
        "a|domain|d1": 2,
        "shared|domain|d1": 2,
        "a|entity_field|a:f": 3,
    }


def test_an_area_with_no_layout_leaves_the_rest_readable() -> None:
    graph = split_areas(document())
    layouts = {
        area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0)
        for area in graph.areas
        if area.id != "d2"
    }
    places = {area.id: Place(0.0, 0.0, 230.0) for area in graph.areas}
    result = assemble(graph, layouts, places, ("#111111",))
    assert next(item for item in result.overview["areas"] if item["id"] == "d2")["failed"] is True
    assert "d2" not in result.details and "d1" in result.details


def laid_out(graph: Any) -> tuple[dict[str, AreaLayout], dict[str, Place]]:
    """Every node at the middle of its area."""
    return {area.id: AreaLayout({item.id: (0.0, 0.0) for item in area.nodes}, 200.0) for area in graph.areas}, {
        area.id: Place(0.0, 0.0, 230.0) for area in graph.areas
    }


def test_types_carry_their_colours() -> None:
    graph = split_areas(document())
    made = assemble(graph, *laid_out(graph), ("#111111",), type_colour=lambda name: f"#{len(name):06d}")
    assert made.overview["type_colours"]["Entity"] == "#000006"
