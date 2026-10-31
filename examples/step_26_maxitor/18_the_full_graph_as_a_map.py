"""
18_the_full_graph_as_a_map.py — Maxitor's full graph is a map

The full graph is read as a map: named domains far away, what they hold closer. A version is laid out once on the
server, domain by domain, and the browser reads an overview first and the detail of what it looks at. This example
runs the store Maxitor runs, over a small service in three versions, and reads what the page reads.

The cases, with the real output at the bottom:

  1. the graph cut into areas: where a node stands, at which level, and what stands above it;
  2. the overview and one domain's detail, by level;
  3. a new version changing one domain: one area laid out, and no other moves;
  4. two versions compared: each change, nodes and links, in the order the map steps through them;
  5. a filter: a type switched off takes everything below it, and `n of m left` comes from the overview alone;
  6. a domain removed: it keeps its place, so an older version still has somewhere to stand.

Everything runs in a temporary folder; Graphviz required (`brew install graphviz`).

Output:

    1. The graph cut into areas
       billing: billing, invoice, pay
       orders: order, order.lifecycle, order.state, order.total, orders, place
       order.state: level 3, above Domain, Entity, Lifecycle
    2. The overview and one domain's detail
       2 areas, 9 nodes, 1 bundle
       orders at level 2: 3 nodes · at level 3: 6 nodes
    3. A new version changing one domain
       areas laid out: 1
       billing stands where it stood: True
    4. Two versions compared
       + billing/refund (Entity)
       + billing/refund → billing (domain)
       ~ orders/order (Entity)
       ~ orders/place → order (order_of)
       counts: +2 −0 ~2
    5. A filter
       Entity off, orders: 2 of 6 left
       Entity off, billing: 2 of 4 left
    6. A domain removed
       billing keeps its place: True
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maxitor.front.model.diagrams.resources.map_store import MapStore
from maxitor.graph_map import split_areas

STATUSES = ("unchanged", "added", "removed", "changed")
SIGNS = {"added": "+", "removed": "−", "changed": "~"}


@dataclass
class Held:
    """A held graph as the store sees it: where it came from, what it was built from, and its text."""

    source: str
    content_sha256: str
    document: str


def node(identifier: str, kind: str, description: str = "") -> dict[str, Any]:
    """A node of the graph file."""
    return {"id": identifier, "label": identifier, "type": kind, "properties": {"description": description}}


def link(source: str, kind: str, target: str, relationship: str = "Aggregation") -> dict[str, Any]:
    """A link of the graph file."""
    return {"id": f"{source}|{kind}|{target}", "source_id": source, "target_id": target, "type": kind, "relationship": relationship, "properties": {}}


def shop() -> dict[str, Any]:
    """Two domains: orders, with an entity that has a field and a lifecycle, and billing, with an entity and an action."""
    return {
        "schema_version": "1.1",
        "nodes": [
            node("orders", "Domain"),
            node("billing", "Domain"),
            node("order", "Entity"),
            node("order.total", "EntityField"),
            node("order.lifecycle", "Lifecycle"),
            node("order.state", "StateInitial"),
            node("place", "Action"),
            node("invoice", "Entity"),
            node("pay", "Action"),
        ],
        "edges": [
            link("order", "domain", "orders"),
            link("place", "domain", "orders"),
            link("invoice", "domain", "billing"),
            link("pay", "domain", "billing"),
            link("order", "entity_field", "order.total", "Composition"),
            link("order", "lifecycle", "order.lifecycle", "Composition"),
            link("order.lifecycle", "lifecycle_contains_state", "order.state", "Composition"),
            link("place", "order_of", "order", "Association"),
            link("pay", "order_of", "order", "Association"),
        ],
    }


def held(document: dict[str, Any], version: str) -> Held:
    """A version of the graph."""
    return Held(f"https://port/history/shop/{version}", version, json.dumps(document))


class Maps:
    """The store the app runs, with the graph a read is bound to held here instead of in a request."""

    def __init__(self, root: Path) -> None:
        self.graph: Held | None = None
        self.pair: tuple[Held, Held] | None = None
        self.store = MapStore(root, lambda: self.graph, lambda _source: "shop", ("#3b82f6", "#ef4444"), pair=lambda: self.pair)

    def overview(self, graph: Held, older: Held | None = None) -> dict[str, Any]:
        """Read a map's overview as the page does: it says it is laying out until the map is made."""
        self.graph = graph
        self.pair = (older, graph) if older else None

        async def ready() -> dict[str, Any]:
            first = await self.store.overview()
            await self.store.wait()
            return first if first["state"] == "ready" else await self.store.overview()

        return asyncio.run(ready())


def area_of(overview: dict[str, Any], area_id: str) -> dict[str, Any]:
    """One area of an overview."""
    return next(area for area in overview["areas"] if area["id"] == area_id)


def left_of(overview: dict[str, Any], area_id: str, off: str) -> str:
    """How much of an area is left with one type off, from its sketch alone: a type takes everything below it."""
    types, chains = overview["types"], overview["chains"]
    cells = area_of(overview, area_id)["sketch"]["cells"]
    total = sum(cell[3] for cell in cells)
    left = sum(cell[3] for cell in cells if types[cell[2]] != off and off not in chains[cell[4]])
    return f"{left} of {total} left"


print("1. The graph cut into areas")
areas = split_areas(shop())
for area in areas.areas:
    print(f"   {area.id}: {', '.join(item.id for item in area.nodes)}")
state = next(item for area in areas.areas for item in area.nodes if item.id == "order.state")
print(f"   {state.id}: level {state.level}, above {', '.join(state.above)}")

with tempfile.TemporaryDirectory() as folder:
    maps = Maps(Path(folder))
    first = held(shop(), "v1")
    overview = maps.overview(first)

    print("2. The overview and one domain's detail")
    count = sum(sum(area["counts"].values()) for area in overview["areas"])
    print(f"   {len(overview['areas'])} areas, {count} nodes, {len(overview['bundles'])} bundle")
    detail = asyncio.run(maps.store.area("orders"))
    assert detail is not None
    second_level = [item for item in detail["nodes"] if item["level"] == 2]
    print(f"   orders at level 2: {len(second_level)} nodes · at level 3: {len(detail['nodes'])} nodes")

    print("3. A new version changing one domain")
    changed = shop()
    changed["nodes"].append(node("refund", "Entity"))
    changed["edges"].append(link("refund", "domain", "billing"))
    next(item for item in changed["nodes"] if item["id"] == "order")["properties"]["description"] = "An order a customer places"
    next(item for item in changed["edges"] if item["source_id"] == "place" and item["type"] == "order_of")["properties"]["note"] = "placed once"
    second = held(changed, "v2")
    before = maps.store.laid_out
    moved = maps.overview(second)
    print(f"   areas laid out: {maps.store.laid_out - before}")
    print(f"   billing stands where it stood: {(area_of(moved, 'billing')['x'], area_of(moved, 'billing')['y']) == (area_of(overview, 'billing')['x'], area_of(overview, 'billing')['y'])}")

    print("4. Two versions compared")
    pair = maps.overview(second, first)
    listed = asyncio.run(maps.store.changes())
    for change in sorted(listed, key=lambda each: (each["area"], each["label"])):
        kind = change["type"]
        print(f"   {SIGNS[change['status']]} {change['area']}/{change['label']} ({kind})")
    counted = {status: sum(1 for change in listed if change["status"] == status) for status in SIGNS}
    print(f"   counts: +{counted['added']} −{counted['removed']} ~{counted['changed']}")

    print("5. A filter")
    print(f"   Entity off, orders: {left_of(moved, 'orders', 'Entity')}")
    print(f"   Entity off, billing: {left_of(moved, 'billing', 'Entity')}")

    print("6. A domain removed")
    without = shop()
    without["nodes"] = [item for item in without["nodes"] if item["id"] not in ("billing", "invoice", "pay")]
    without["edges"] = [item for item in without["edges"] if not {item["source_id"], item["target_id"]} & {"billing", "invoice", "pay"}]
    maps.overview(held(without, "v3"))
    back = maps.overview(first)
    print(f"   billing keeps its place: {(area_of(back, 'billing')['x'], area_of(back, 'billing')['y']) == (area_of(overview, 'billing')['x'], area_of(overview, 'billing')['y'])}")
