# packages/maxitor/front/tests/test_map_store.py
"""A version's map is laid out once, kept on disk, and shared (spec 040, FR-015 – FR-019)."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from maxitor.front.model.diagrams.resources.map_store import MapRefusedError, MapStore, run_sfdp
from maxitor.graph_compare import KNOWN_VERSIONS


@dataclass
class Held:
    """A held graph as the store sees it."""

    source: str
    content_sha256: str
    document: str


def node(identifier: str, kind: str = "Entity") -> dict[str, Any]:
    """A node of the graph file."""
    return {"id": identifier, "label": identifier, "type": kind, "properties": {}}


def link(source: str, target: str) -> dict[str, Any]:
    """A node's link to its domain."""
    return {"id": f"{source}|domain|{target}", "source_id": source, "target_id": target, "type": "domain", "relationship": "Aggregation", "properties": {}}


def graph(extra: str | None = None, name: str = "v1") -> Held:
    """Two domains of two entities each; ``extra`` adds an entity to the first."""
    nodes = [node("d1", "Domain"), node("d2", "Domain"), node("a"), node("b"), node("c"), node("e")]
    edges = [link("a", "d1"), link("b", "d1"), link("c", "d2"), link("e", "d2")]
    if extra:
        nodes.append(node(extra))
        edges.append(link(extra, "d1"))
    return Held(f"https://port/history/{name}", name, json.dumps({"nodes": nodes, "edges": edges}))


class Sfdp:
    """A stand-in for ``sfdp``: nodes on a line, every call counted."""

    def __init__(self) -> None:
        self.calls = 0
        self.fail_on: str | None = None

    def __call__(self, dot: str) -> str:
        self.calls += 1
        if self.fail_on and self.fail_on in dot:
            raise ValueError("no layout")
        names = re.findall(r"^(n\d+);$", dot, re.MULTILINE)
        objects = [{"name": name, "pos": f"{index * 50},0"} for index, name in enumerate(names)]
        return json.dumps({"bb": f"0,0,{max(len(names) * 50, 1)},10", "objects": objects})


def store(root: Path, held: list[Held], run: Any) -> MapStore:
    """A store over the graph in ``held``, every source of one history."""
    return MapStore(root, lambda: held[0], lambda _source: "history", ("#111111", "#222222"), run=run)


def overview(maps: MapStore) -> dict[str, Any]:
    """Ask for the overview until it is ready."""

    async def ready() -> dict[str, Any]:
        first = await maps.overview()
        await maps.wait()
        return first if first["state"] == "ready" else await maps.overview()

    return asyncio.run(ready())


def test_the_first_read_says_laying_out_and_a_later_one_is_ready(tmp_path: Path) -> None:
    async def run() -> None:
        maps = store(tmp_path, [graph()], Sfdp())
        assert (await maps.overview())["state"] == "laying-out"
        await maps.wait()
        assert (await maps.overview())["state"] == "ready"

    asyncio.run(run())


def test_two_readers_share_one_layout(tmp_path: Path) -> None:
    async def run() -> int:
        sfdp = Sfdp()
        maps = store(tmp_path, [graph()], sfdp)
        await asyncio.gather(maps.overview(), maps.overview(), maps.overview())
        await maps.wait()
        return sfdp.calls

    assert asyncio.run(run()) == 2


def test_what_is_on_disk_survives_a_restart(tmp_path: Path) -> None:
    held = [graph()]
    overview(store(tmp_path, held, Sfdp()))
    sfdp = Sfdp()
    assert overview(store(tmp_path, held, sfdp))["state"] == "ready"
    assert sfdp.calls == 0


def test_a_new_version_lays_out_only_the_area_that_changed(tmp_path: Path) -> None:
    held = [graph()]
    sfdp = Sfdp()
    maps = store(tmp_path, held, sfdp)
    first = overview(maps)
    held[0] = graph("added", "v2")
    second = overview(maps)
    assert sfdp.calls == 3
    assert [area for area in first["areas"] if area["id"] == "d2"] == [area for area in second["areas"] if area["id"] == "d2"]


def test_an_area_reads_its_nodes_and_an_unknown_one_reads_nothing(tmp_path: Path) -> None:
    async def run() -> None:
        maps = store(tmp_path, [graph()], Sfdp())
        await maps.overview()
        await maps.wait()
        detail = await maps.area("d1")
        assert detail is not None and {item["id"] for item in detail["nodes"]} == {"a", "b", "d1"}
        assert await maps.area("nowhere") is None

    asyncio.run(run())


def test_an_area_sfdp_fails_on_leaves_the_rest(tmp_path: Path) -> None:
    sfdp = Sfdp()
    sfdp.fail_on = "n3;"
    items = {area["id"]: area for area in overview(store(tmp_path, [graph("added")], sfdp))["areas"]}
    assert items["d1"].get("failed") is True
    assert "sketch" in items["d2"]


def test_a_missing_graphviz_says_so(tmp_path: Path) -> None:
    def missing(_dot: str) -> str:
        raise MapRefusedError("Graphviz is not installed: `sfdp` was not found.")

    async def run() -> None:
        maps = store(tmp_path, [graph()], missing)
        await maps.overview()
        await maps.wait()
        with pytest.raises(MapRefusedError, match="Graphviz"):
            await maps.overview()

    asyncio.run(run())


@pytest.mark.skipif(shutil.which("sfdp") is None, reason="native Graphviz is not installed")
def test_native_graphviz_gives_the_same_positions_twice(tmp_path: Path) -> None:
    first = overview(store(tmp_path / "one", [graph()], run_sfdp))
    second = overview(store(tmp_path / "two", [graph()], run_sfdp))
    assert first == second
    assert all("sketch" in area for area in first["areas"])


def versioned(document: dict[str, Any], name: str) -> Held:
    """A graph the comparison reads."""
    return Held(f"https://port/history/{name}", name, json.dumps({**document, "schema_version": max(KNOWN_VERSIONS)}))


def pair_store(root: Path, older: Held, newer: Held) -> tuple[MapStore, list[tuple[Held, Held]]]:
    """A store over ``newer``, and the list that binds the read to the pair once it holds it."""
    bound: list[tuple[Held, Held]] = []
    return MapStore(root, lambda: newer, lambda _source: "history", ("#111111", "#222222"), pair=lambda: (older, newer) if bound else None, run=Sfdp()), bound


def test_a_pair_moves_no_area_however_much_only_a_held(tmp_path: Path) -> None:
    crowded = json.loads(graph().document)
    crowded["nodes"] += [node(f"old{index}") for index in range(40)]
    crowded["edges"] += [link(f"old{index}", "d1") for index in range(40)]
    maps, bound = pair_store(tmp_path, versioned(crowded, "a"), versioned(json.loads(graph().document), "b"))
    alone = {area["id"]: (area["x"], area["y"]) for area in overview(maps)["areas"]}
    bound.append(("older", "newer"))  # type: ignore[arg-type]
    both = {area["id"]: (area["x"], area["y"]) for area in overview(maps)["areas"]}
    assert all(both[area] == place for area, place in alone.items())


def test_a_node_stands_in_the_domain_b_gives_it_whatever_a_said(tmp_path: Path) -> None:
    moved = json.loads(graph().document)
    moved["edges"] = [link("a", "d2") if edge["source_id"] == "a" else edge for edge in moved["edges"]]
    maps, bound = pair_store(tmp_path, versioned(json.loads(graph().document), "a"), versioned(moved, "b"))
    overview(maps)
    where = {item["id"]: (item["x"], item["y"]) for item in asyncio.run(maps.area("d2"))["nodes"]}  # type: ignore[index]
    bound.append(("older", "newer"))  # type: ignore[arg-type]
    overview(maps)
    both = {item["id"]: (item["x"], item["y"]) for item in asyncio.run(maps.area("d2"))["nodes"]}  # type: ignore[index]
    assert both["a"] == where["a"]
    assert "a" not in {item["id"] for item in asyncio.run(maps.area("d1"))["nodes"]}  # type: ignore[index]
