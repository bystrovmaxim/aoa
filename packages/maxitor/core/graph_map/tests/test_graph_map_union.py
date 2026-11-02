# packages/maxitor/core/graph_map/tests/test_graph_map_union.py
"""Two versions joined into one document, each node standing where its version has it (spec 040)."""

from __future__ import annotations

from maxitor.graph_map import AreaLayout, split_areas, union_document, union_layouts

from .graph_documents import by_id, document, edge, node


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


def test_an_area_only_in_a_takes_a_layout_from_a() -> None:
    older, newer = document(), document()
    newer["nodes"] = [item for item in newer["nodes"] if item["id"] != "d2"]
    joined, _ = union_document(older, newer)
    union = split_areas(joined)
    layouts = union_layouts(union, {"d2": AreaLayout({"d2": (5.0, 6.0)}, 200.0)}, {})
    assert layouts["d2"].positions["d2"] == (5.0, 6.0)
