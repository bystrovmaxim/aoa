# packages/maxitor/core/graph_map/src/maxitor/graph_map/areas.py
"""
Areas — a graph document cut into one area per domain, and one for what is outside domains.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An area is what the map folds and unfolds. A node belongs to the domains it is linked to
and to those of whatever contains it; it stands in one of them, its home, the first in the
domains' order. Generalization links are not drawn, as on the full graph. An area's
content hash covers what its layout depends on, so a layout can be reused across versions.
A node also knows the types of everything above it, from the application down: a filter
that hides one of those takes it along, and with no node in the browser the map still knows
what that leaves.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    document ──► drawn links ──► domains' members ──► homes ──► areas, links inside and across
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

OUTSIDE = "(outside)"
"""The id of the area that holds what belongs to no domain."""

DOMAIN = "Domain"
APPLICATION = "Application"
GENERALIZATION = "Generalization"
CONTAINMENT = frozenset({"Composition", "Aggregation"})
DOMAIN_LINK = "domain"
APPLICATION_LINK = "application"

NOT_HOLDING = frozenset({"lifecycle_transition", "entity_schema"})
"""Containment links that hold nothing: a transition moves between states, and a schema points at an entity."""

LEVEL_TWO = frozenset({"Entity", "Action", "Role", "Resource", DOMAIN, APPLICATION})
"""What shows once a domain unfolds; everything else waits for the closest level."""


@dataclass(frozen=True, slots=True)
class MapNode:
    """One node as the map needs it."""

    id: str
    label: str
    type: str
    level: int
    above: tuple[str, ...] = ()
    """The types of everything above this node, at any depth, sorted."""


@dataclass(frozen=True, slots=True)
class MapEdge:
    """One drawn link as the map needs it."""

    id: str
    source: str
    target: str
    type: str


@dataclass(frozen=True, slots=True)
class Area:
    """
    One folding place of the map.

    AI-CORE-BEGIN
    ROLE: A domain, or everything outside domains, with what stands in it.
    CONTRACT: ``nodes`` are sorted by id; ``inner`` links both ends here; ``across`` starts here and ends elsewhere.
    INVARIANTS: ``content_hash`` depends only on what the area's layout depends on: node ids and inner links.
    AI-CORE-END
    """

    id: str
    name: str
    nodes: tuple[MapNode, ...]
    inner: tuple[MapEdge, ...]
    across: tuple[MapEdge, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class GraphAreas:
    """A graph cut into areas, in the areas' id order."""

    areas: tuple[Area, ...]
    links: Mapping[tuple[str, str], Mapping[str, int]]
    """Each pair of areas, ids sorted → its links, counted by their ends: ``Type>Above>Above|Type``."""
    memberships: Mapping[str, tuple[str, ...]]
    """A node in more than one domain → all of them."""
    types: tuple[str, ...]
    containers: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    """A node → what stands directly above it."""


def _text(value: Any) -> str:
    """Return ``value`` as text, empty when it is missing."""
    return value if isinstance(value, str) else ""


def _drawn_edges(document: Mapping[str, Any], nodes: Mapping[str, Any]) -> list[MapEdge]:
    """The links the map draws: both ends known, and no generalization."""
    edges: list[MapEdge] = []
    for index, edge in enumerate(document.get("edges", [])):
        source, target = _text(edge.get("source_id")), _text(edge.get("target_id"))
        if edge.get("relationship") != GENERALIZATION and source in nodes and target in nodes:
            edges.append(MapEdge(_text(edge.get("id")) or f"e-{index}", source, target, _text(edge.get("type"))))
    return edges


def _contained(document: Mapping[str, Any], types: Mapping[str, str]) -> dict[str, list[str]]:
    """What each node contains directly; a link to a domain is membership, and a domain or an application is never held."""
    children: dict[str, list[str]] = {}
    for edge in document.get("edges", []):
        source, target = _text(edge.get("source_id")), _text(edge.get("target_id"))
        linked_to_domain = edge.get("type") == DOMAIN_LINK and types.get(target) == DOMAIN
        if not linked_to_domain and edge.get("relationship") in CONTAINMENT and source in types and types.get(target, DOMAIN) not in (DOMAIN, APPLICATION):
            children.setdefault(source, []).append(target)
    return children


def _held(document: Mapping[str, Any], types: Mapping[str, str]) -> dict[str, list[str]]:
    """What stands directly below each node: a domain's and an application's members, and what containment holds."""
    held: dict[str, list[str]] = {}
    for edge in document.get("edges", []):
        source, target, kind = _text(edge.get("source_id")), _text(edge.get("target_id")), edge.get("type")
        if source not in types or target not in types:
            continue
        if types[target] in (DOMAIN, APPLICATION):
            if kind in (DOMAIN_LINK, APPLICATION_LINK):
                held.setdefault(target, []).append(source)
        elif edge.get("relationship") in CONTAINMENT and kind not in NOT_HOLDING:
            held.setdefault(source, []).append(target)
    return held


def _above(below: Mapping[str, list[str]], types: Mapping[str, str]) -> dict[str, set[str]]:
    """The types above each node, at any depth."""
    above: dict[str, set[str]] = {}
    queue = list(below)
    while queue:
        parent = queue.pop()
        passed = above.get(parent, set()) | {types[parent]}
        for child in below.get(parent, ()):
            known = above.setdefault(child, set())
            if not passed <= known:
                known |= passed
                queue.append(child)
    return above


def _members(document: Mapping[str, Any], types: Mapping[str, str], domains: list[str], children: Mapping[str, list[str]]) -> dict[str, set[str]]:
    """Each domain's members: what is linked to it and, through containment, what those hold."""
    members = {domain: {domain} for domain in domains}
    for edge in document.get("edges", []):
        source, target = _text(edge.get("source_id")), _text(edge.get("target_id"))
        if edge.get("type") == DOMAIN_LINK and types.get(target) == DOMAIN and source in types:
            members[target].add(source)
    for member_set in members.values():
        queue = sorted(member_set)
        while queue:
            for child in children.get(queue.pop(), ()):
                if child not in member_set:
                    member_set.add(child)
                    queue.append(child)
    return members


def _hash(nodes: list[MapNode], inner: list[MapEdge]) -> str:
    """The hash of what an area's layout depends on."""
    content = {"nodes": [node.id for node in nodes], "edges": [[edge.source, edge.target] for edge in inner]}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def split_areas(document: Mapping[str, Any], homes: Mapping[str, str] | None = None) -> GraphAreas:
    """
    AI-CORE-BEGIN
    ROLE: Cut a graph document into the areas of its map.
    CONTRACT: Every node stands in exactly one area; a node in several domains stands in the first in id order, unless ``homes`` names its area.
    INVARIANTS: Pure; the same document gives the same areas, in the same order.
    AI-CORE-END
    """
    nodes = {_text(node.get("id")): node for node in document.get("nodes", [])}
    types = {node_id: _text(node.get("type")) for node_id, node in nodes.items()}
    domains = sorted(node_id for node_id, node_type in types.items() if node_type == DOMAIN)
    held = _held(document, types)
    above = {node_id: tuple(sorted(parents)) for node_id, parents in _above(held, types).items()}
    members = _members(document, types, domains, _contained(document, types))
    memberships: dict[str, list[str]] = {}
    for domain in domains:
        for node_id in members[domain]:
            memberships.setdefault(node_id, []).append(domain)
    home = {node_id: held[0] for node_id, held in memberships.items()} | dict(homes or {})
    standing: dict[str, list[MapNode]] = {}
    for node_id in sorted(nodes):
        node = MapNode(node_id, _text(nodes[node_id].get("label")) or node_id, types[node_id], 2 if types[node_id] in LEVEL_TWO else 3, above.get(node_id, ()))
        standing.setdefault(home.get(node_id, OUTSIDE), []).append(node)
    inner: dict[str, list[MapEdge]] = {}
    across: dict[str, list[MapEdge]] = {}
    links: dict[tuple[str, str], dict[str, int]] = {}
    for edge in sorted(_drawn_edges(document, nodes), key=lambda each: each.id):
        start, end = home.get(edge.source, OUTSIDE), home.get(edge.target, OUTSIDE)
        if start == end:
            inner.setdefault(start, []).append(edge)
            continue
        across.setdefault(start, []).append(edge)
        ends = "|".join(">".join((types[each], *above.get(each, ()))) for each in (edge.source, edge.target))
        pair = links.setdefault((min(start, end), max(start, end)), {})
        pair[ends] = pair.get(ends, 0) + 1
    areas = tuple(
        Area(
            area_id,
            _text(nodes.get(area_id, {}).get("label")) or area_id,
            tuple(standing[area_id]),
            tuple(inner.get(area_id, ())),
            tuple(across.get(area_id, ())),
            _hash(standing[area_id], inner.get(area_id, [])),
        )
        for area_id in sorted(standing)
    )
    shared = {node_id: tuple(held) for node_id, held in memberships.items() if len(held) > 1}
    containers: dict[str, list[str]] = {}
    for parent, below in held.items():
        for child in below:
            containers.setdefault(child, []).append(parent)
    return GraphAreas(areas, links, shared, tuple(sorted(set(types.values()))), {node_id: tuple(sorted(parents)) for node_id, parents in containers.items()})
