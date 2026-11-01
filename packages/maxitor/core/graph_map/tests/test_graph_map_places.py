# packages/maxitor/core/graph_map/tests/test_graph_map_places.py
"""Areas placed so that no two rooms overlap and a stable area keeps its place (spec 040)."""

from __future__ import annotations

from maxitor.graph_map import settle_places


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
