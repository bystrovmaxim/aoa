# packages/maxitor/front/src/maxitor/front/model/diagrams/resources/map_store.py
"""
MapStore — the map of a version, laid out once, kept on disk and shared by every reader.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The full graph is read as a map (spec 040). This resource makes a version's map the first
time anyone asks, with ``maxitor.graph_map`` and native Graphviz, and keeps it: it survives
a restart, and every later reader only reads files. An area's layout is kept under the hash
of its content, so a version changing one domain lays out one area, and the places of the
areas are kept per history, so that change moves no other area.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action ──overview()──► map on disk? ──yes──► the overview
                               │
                               └─no──► one task per version, in a thread ──► {"state": "laying-out"}
                                          split_areas ──► layouts/<content hash>.json, or sfdp
                                                      ──► places/<scope>.json
                                                      ──► maps/<version>/, overview written last

    action ──area(id)──► maps/<version>/areas/<hash of id>.json

    middleware ──stored(source)──► index/<hash of source>.json ──► read with no graph built

A version's map is written with its overview last, so an overview on disk means the whole
map is there. An area ``sfdp`` fails on is listed as failed, and the rest of the map reads.

A read that names two versions (``a``) gets their pair's map, made the same way: the union
of both, each node where B has it, what only A has beside that, every area where the
version's map has it, and the comparison's marks. It is kept under the two versions' hashes.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.graph_compare import GraphNotComparableError, Status, compare
from maxitor.graph_compare.edge_ids import edge_id
from maxitor.graph_map import (
    Area,
    AreaLayout,
    GraphAreas,
    Marks,
    Place,
    VersionMap,
    area_dot,
    assemble,
    read_layout,
    settle_places,
    split_areas,
    union_document,
    union_layouts,
)

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_controller import BaseController

#: Connection key under which the map actions receive the store.
MAP_STORE_CONNECTION_KEY = "Maps"

#: The longest one area may take; ``sfdp`` needs a fraction of a second.
SFDP_TIMEOUT_SECONDS = 120

LAYING_OUT: dict[str, Any] = {"state": "laying-out", "types": [], "areas": [], "bundles": [], "shared": []}
"""What a read of a version not laid out yet answers."""


class MappedGraph(Protocol):
    """What a held graph offers the map: where it came from, what it was built from, and its text."""

    @property
    def source(self) -> str:
        """Where the graph came from."""

    @property
    def content_sha256(self) -> str:
        """The hash of what the graph was built from."""

    @property
    def document(self) -> str:
        """The graph's text."""


@dataclasses.dataclass(frozen=True, slots=True)
class StoredVersion:
    """A version whose map is on disk: enough to read it, with no graph built."""

    source: str
    content_sha256: str
    document: str = ""


class MapRefusedError(ValueError):
    """The map cannot be made; the message says why, for the user."""


class NoGraphError(LookupError):
    """The read is bound to no graph."""


def run_sfdp(dot: str) -> str:
    """Run native Graphviz on one area and return its answer."""
    try:
        return subprocess.run(["sfdp", "-Tjson0"], input=dot, capture_output=True, text=True, check=True, timeout=SFDP_TIMEOUT_SECONDS).stdout
    except FileNotFoundError as exc:
        raise MapRefusedError("Graphviz is not installed: `sfdp` was not found.") from exc


def _digest(text: str) -> str:
    """The SHA-256 of ``text``, as a file name."""
    return hashlib.sha256(text.encode()).hexdigest()


def _write(path: Path, content: Any) -> None:
    """Write ``content`` as JSON, whole or not at all."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        json.dump(content, file, separators=(",", ":"))
    os.replace(temporary, path)


def _read(path: Path) -> Any:
    """Read one JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _with_edge_ids(document: dict[str, Any]) -> dict[str, Any]:
    """``document`` with every edge carrying its id: an older graph's are computed, as the comparison does."""
    try:
        for edge in document.get("edges", []):
            edge.setdefault("id", edge_id(edge))
    except GraphNotComparableError as exc:
        raise MapRefusedError(str(exc)) from exc
    return document


@meta(description="The map of a version, laid out once and kept on disk", domain=DiagramsDomain)
class MapStore(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: Make each version's map once, keep it on disk, and read it back in parts.
    CONTRACT: ``overview()`` answers a ready map, or starts one and answers ``state: laying-out``; ``area(id)`` answers one area's detail, or ``None``; a map that cannot be made raises ``MapRefusedError``.
    INVARIANTS: A version is laid out by one task however many read it; an unchanged area's layout is reused across versions; places are kept per scope; what is on disk survives a restart.
    AI-CORE-END
    """

    def __init__(
        self,
        root: Path,
        graph: Callable[[], MappedGraph | None],
        scope: Callable[[str], str],
        colours: Sequence[str],
        immutable: Callable[[str], bool] = lambda _source: False,
        pair: Callable[[], tuple[MappedGraph, MappedGraph] | None] = lambda: None,
        run: Callable[[str], str] = run_sfdp,
        workers: int | None = None,
    ) -> None:
        self._root = root
        self._graph = graph
        self._scope = scope
        self._colours = colours
        self._immutable = immutable
        self._pair = pair
        self._run = run
        self._workers = workers or os.cpu_count() or 1
        self._running: dict[str, asyncio.Task[None]] = {}
        self._refused: dict[str, str] = {}
        self.laid_out = 0
        """How many areas were laid out, not found under their content hash."""

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same store."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the store is not a rollup target."""
        return False

    def _bound(self) -> MappedGraph:
        """The graph the current read is bound to."""
        graph = self._graph()
        if graph is None:
            raise NoGraphError("This read names no graph.")
        return graph

    def stored(self, source: str, older: str = "") -> StoredVersion | None:
        """The map of ``source``, or of its pair with ``older``, when it is on disk and cannot change, so no graph need be built."""
        path = self._root / "index" / f"{_digest(f'{older}|{source}' if older else source)}.json"
        if not path.exists():
            return None
        return StoredVersion(source, _read(path))

    def _key(self, graph: MappedGraph) -> str:
        """What the current read's map is kept under: the version, or the pair the read names."""
        pair = self._pair()
        return f"{pair[0].content_sha256}-{pair[1].content_sha256}" if pair else graph.content_sha256

    def _folder(self, key: str) -> Path:
        """Where a map stands."""
        return self._root / "maps" / key

    async def overview(self) -> dict[str, Any]:
        """The bound version's overview, or ``state: laying-out`` while it is made."""
        graph = self._bound()
        key = self._key(graph)
        ready = self._folder(key) / "overview.json"
        if ready.exists():
            return await asyncio.to_thread(_read, ready)
        if key in self._refused:
            raise MapRefusedError(self._refused[key])
        if key not in self._running:
            self._running[key] = asyncio.create_task(self._make(key, graph, self._pair()))
        return dict(LAYING_OUT)

    async def wait(self) -> None:
        """Wait for every map being made."""
        await asyncio.gather(*self._running.values(), return_exceptions=True)

    async def area(self, area_id: str) -> dict[str, Any] | None:
        """One area's detail in the bound version, or ``None`` when there is no such area."""
        path = self._folder(self._key(self._bound())) / "areas" / f"{_digest(area_id)}.json"
        if not path.exists():
            return None
        return await asyncio.to_thread(_read, path)

    async def changes(self) -> list[dict[str, Any]]:
        """The bound pair's changed nodes in the stepping order; empty until its map is made."""
        path = self._folder(self._key(self._bound())) / "changes.json"
        return await asyncio.to_thread(_read, path) if path.exists() else []

    async def _make(self, key: str, graph: MappedGraph, pair: tuple[MappedGraph, MappedGraph] | None) -> None:
        """Make one map in a thread, remembering a refusal for it."""
        try:
            await asyncio.to_thread(self._build, key, graph, pair)
        except (MapRefusedError, ValueError, KeyError, OSError) as exc:
            self._refused[key] = str(exc)
        finally:
            self._running.pop(key, None)

    def _build(self, key: str, graph: MappedGraph, pair: tuple[MappedGraph, MappedGraph] | None) -> None:
        """Make a version's map or a pair's, and write it, overview last."""
        made = self._pair_map(*pair) if pair else self._version_map(graph)
        folder = self._folder(key)
        for area_id, detail in made.details.items():
            _write(folder / "areas" / f"{_digest(area_id)}.json", detail)
        if pair:
            _write(folder / "changes.json", made.changes)
        _write(folder / "overview.json", made.overview)
        if all(self._immutable(each.source) for each in pair or (graph,)):
            name = f"{pair[0].source}|{pair[1].source}" if pair else graph.source
            _write(self._root / "index" / f"{_digest(name)}.json", key)

    def _version_map(self, graph: MappedGraph) -> VersionMap:
        """One version: lay out what has no layout yet, and settle the places."""
        areas = split_areas(json.loads(graph.document))
        layouts = self._layouts(areas)
        return assemble(areas, layouts, self._places(graph, areas, layouts), self._colours)

    def _pair_map(self, older: MappedGraph, newer: MappedGraph) -> VersionMap:
        """Two versions as one map: B's positions, every area where it stands, and what the comparison says."""
        before, after = (_with_edge_ids(json.loads(each.document)) for each in (older, newer))
        try:
            comparison = compare(before, after)
        except GraphNotComparableError as exc:
            raise MapRefusedError(str(exc)) from exc
        joined, was = union_document(before, after)
        areas_a, areas_b = split_areas(before), split_areas(after)
        union = split_areas(joined, {node.id: area.id for area in areas_b.areas for node in area.nodes})
        layouts = union_layouts(union, self._layouts(areas_a), self._layouts(areas_b))
        marks = Marks(
            {key: item.status.value for key, item in comparison.nodes.items() if item.status is not Status.UNCHANGED},
            {key: item.status.value for key, item in comparison.edges.items() if item.status is not Status.UNCHANGED},
            was,
        )
        return assemble(union, layouts, self._places(newer, union, layouts, stay=True), self._colours, marks)

    def _layouts(self, areas: GraphAreas) -> dict[str, AreaLayout]:
        """Every area's layout: kept under its content hash, or laid out now."""
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            answers = pool.map(self._layout, areas.areas)
            return {area.id: layout for area, layout in zip(areas.areas, answers, strict=True) if layout is not None}

    def _layout(self, area: Area) -> AreaLayout | None:
        """One area's layout, or ``None`` when ``sfdp`` fails on it."""
        path = self._root / "layouts" / f"{area.content_hash}.json"
        if path.exists():
            kept = _read(path)
            return AreaLayout({key: (x, y) for key, (x, y) in kept["positions"].items()}, kept["radius"])
        try:
            layout = read_layout(area, self._run(area_dot(area)))
        except MapRefusedError:
            raise
        except (subprocess.SubprocessError, ValueError, KeyError):
            return None
        self.laid_out += 1
        _write(path, {"positions": layout.positions, "radius": layout.radius})
        return layout

    def _places(self, graph: MappedGraph, areas: GraphAreas, layouts: dict[str, AreaLayout], stay: bool = False) -> dict[str, Place]:
        """Settle the areas' places in this scope, keeping what is kept there; with ``stay``, no known area moves."""
        path = self._root / "places" / f"{_digest(self._scope(graph.source))}.json"
        known = {key: Place(**value) for key, value in _read(path).items()} if path.exists() else {}
        radii = {area.id: layouts[area.id].radius if area.id in layouts else 150.0 for area in areas.areas}
        if stay:
            radii = {area: min(radius, known[area].room) if area in known else radius for area, radius in radii.items()}
        links = {pair: sum(ends.values()) for pair, ends in areas.links.items()}
        places = settle_places(radii, links, known)
        _write(path, {key: dataclasses.asdict(place) for key, place in places.items()})
        return places
