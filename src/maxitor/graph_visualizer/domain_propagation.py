# src/maxitor/graph_visualizer/domain_propagation.py
"""
InterchangeGraphDomainPropagation — domain bubble membership for G6 payloads.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Compute ``node_domains`` and ``bubble-sets`` plugin payloads used by
:mod:`~maxitor.graph_visualizer.visualizer` so the large HTML exporter stays within
maintainability limits (line count). Logic is deterministic dict graph only.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode

_INTERNAL_INTERCHANGE_EDGES: frozenset[str] = frozenset({"CHECKS_ASPECT", "COMPENSATES_ASPECT"})

# Seeds ``node_domains`` membership: interchange slot from host row → ``Domain`` vertex.
_DOMAIN_EDGE_SLOTS: frozenset[str] = frozenset({"BELONGS_TO", "domain"})

# Host→child interchange slots that are **Composition** or **Aggregation** in the typed
# graph model, used only when G6 edge ``data`` omits ``relationshipName`` (tests / skinny
# payloads). **Association-only** interchange slots (e.g. ``@check_roles``, entity
# ``relations`` navigations, ``@depends`` targets) stay out of this table.
SLOT_ONLY_CONTAINMENT_CHILDREN: frozenset[str] = frozenset(
    {
        "@regular_aspect",
        "@summary_aspect",
        "@result_checker",
        "@compensate",
        "@on_error",
        "@required_context",
        "lifecycle",
        "lifecycle_contains_state",
        "lifecycle_transition",
        "generic:params",
        "generic:result",
        "field",
        "property",
    },
)


def canonical_g6_edge_slot(edge_data: dict[str, Any]) -> str:
    """Normalize viz edge ``label`` so ``belongs_to`` aliases match archived ``BELONGS_TO``."""
    lab = str(edge_data.get("label", "") or "").strip()
    if lab.lower() == "belongs_to":
        return "BELONGS_TO"
    return lab


def g6_edge_propagates_domain_from_host_to_child(e: dict[str, Any]) -> bool:
    """
    Whether host→child edges carry **domain bubble** membership downward.

    Rule: only **whole–part containment** (**Aggregation**, **Composition**) — direct and,
    via the fixpoint in :func:`propagate_node_domains`, indirect. **Association**, **Flow**,
    and other ArchiMate relationship names do **not** extend the bubble, even when the child
    is structurally ``near`` the host (roles, entity lifecycle hubs, peers, …).
    """
    ed = e.get("data") or {}
    rel = str(ed.get("relationshipName", "") or "").strip()
    if rel in ("Composition", "Aggregation"):
        return True
    if not rel and canonical_g6_edge_slot(ed) in SLOT_ONLY_CONTAINMENT_CHILDREN:
        return True
    return False


# Hull colors for domain bubbles (one per domain vertex); distinct from typical node fills.
_BUBBLE_SETS_PALETTE: tuple[str, ...] = (
    "#1783FF",
    "#00C9C9",
    "#F08F56",
    "#D580FF",
    "#5B8FF9",
    "#5AD8A6",
    "#F6BD16",
    "#6F5EF9",
    "#E8684A",
    "#269A99",
    "#B371E3",
    "#5D7092",
)


def domain_sort_key_for_id(g6_nodes: list[dict[str, Any]], nid: str) -> tuple[str, str]:
    node = next(x for x in g6_nodes if str(x["id"]) == nid)
    d = node.get("data") or {}
    return (str(d.get("label", "")), str(d.get("graph_key", nid)))


def propagate_node_domains(  # pylint: disable=too-many-branches
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
) -> tuple[dict[str, str], list[str], defaultdict[str, set[str]]]:
    """
    Domain bubble membership mirrors coordinator ``domain`` seeding plus **containment** only:

    1. Seed from any interchange slot toward a ``Domain`` row
       (``domain`` edge from typed graph model or legacy ``belongs_to`` / ``BELONGS_TO``).
    2. Propagate along host→child edges whose ``relationshipName`` is ``Composition`` or
       ``Aggregation`` (and the slot-only subset in :data:`SLOT_ONLY_CONTAINMENT_CHILDREN`
       when ``relationshipName`` is absent). Transitive closure pulls in nested parts the
       same way: only along those relationship kinds.
    3. Merge domains along checker/compensator bridges
       ``CHECKS_ASPECT`` / ``COMPENSATES_ASPECT``.
    """
    id_to_type: dict[str, str] = {}
    for n in g6_nodes:
        nid = str(n["id"])
        id_to_type[nid] = str((n.get("data") or {}).get("node_type", "unknown"))

    domain_ids = [nid for nid, t in id_to_type.items() if t == DomainGraphNode.NODE_TYPE]

    node_domains: defaultdict[str, set[str]] = defaultdict(set)

    for e in g6_edges:
        ed_raw = e.get("data") or {}
        ed = ed_raw if isinstance(ed_raw, dict) else {}
        slot = canonical_g6_edge_slot(ed)
        if slot not in _DOMAIN_EDGE_SLOTS:
            continue
        src, tgt = str(e["source"]), str(e["target"])
        if id_to_type.get(tgt) != DomainGraphNode.NODE_TYPE:
            continue
        if id_to_type.get(src) == ApplicationGraphNode.NODE_TYPE:
            continue
        node_domains[src].add(tgt)

    changed = True
    while changed:
        changed = False
        for e in g6_edges:
            ed_raw = e.get("data") or {}
            ed = ed_raw if isinstance(ed_raw, dict) else {}
            label = str(ed.get("label", "") or "")
            src, tgt = str(e["source"]), str(e["target"])
            if label in _INTERNAL_INTERCHANGE_EDGES:
                merged = node_domains[src] | node_domains[tgt]
                if not merged:
                    continue
                if merged != node_domains[src] or merged != node_domains[tgt]:
                    node_domains[src] = merged
                    node_domains[tgt] = merged
                    changed = True
            elif g6_edge_propagates_domain_from_host_to_child(e):
                if not node_domains[src]:
                    continue
                before = len(node_domains[tgt])
                node_domains[tgt] |= node_domains[src]
                if len(node_domains[tgt]) > before:
                    changed = True

    return id_to_type, domain_ids, node_domains


def bubble_sets_plugins_for_domains(
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
    *,
    propagation: tuple[dict[str, str], list[str], defaultdict[str, set[str]]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build G6 ``bubble-sets`` plugins: one hull per ``domain`` vertex.

    Members: the domain vertex, interchange rows seeded with ``domain`` / ``belongs_to``
    toward that domain (``Action``, ``Resource``, ``Entity``, …), and every row reached by
    repeated host→child steps along **Composition** / **Aggregation** only (see
    :func:`g6_edge_propagates_domain_from_host_to_child`), plus checker/compensator bridge
    merges from :func:`propagate_node_domains`.

    The ``application`` vertex is never added to a domain bubble.
    """
    if propagation is None:
        propagation = propagate_node_domains(g6_nodes, g6_edges)
    id_to_type, domain_ids, node_domains = propagation

    members_by_domain: dict[str, set[str]] = {}
    for d in domain_ids:
        mem = {d}
        for nid, doms in node_domains.items():
            if d in doms and id_to_type.get(nid) != ApplicationGraphNode.NODE_TYPE:
                mem.add(nid)
        members_by_domain[d] = mem

    palette = _BUBBLE_SETS_PALETTE

    plugins: list[dict[str, Any]] = []
    if domain_ids:
        for i, dom_id in enumerate(sorted(domain_ids, key=lambda did: domain_sort_key_for_id(g6_nodes, did))):
            raw_members = members_by_domain.get(dom_id, {dom_id})
            members = sorted(
                [m for m in raw_members if id_to_type.get(m) != ApplicationGraphNode.NODE_TYPE],
            )
            dom_node = next(n for n in g6_nodes if str(n["id"]) == dom_id)
            ddata = dom_node.get("data") or {}
            label_text = str(ddata.get("label") or ddata.get("graph_key") or dom_id)
            base = palette[i % len(palette)]
            plugins.append(
                {
                    "key": f"bubble-domain-{i}",
                    "type": "bubble-sets",
                    "members": members,
                    "labelText": label_text,
                    "fill": base,
                    "stroke": base,
                    "labelFill": "#fff",
                    "labelPadding": 2,
                    "labelBackgroundFill": base,
                    "labelBackgroundRadius": 5,
                },
            )

    return plugins
