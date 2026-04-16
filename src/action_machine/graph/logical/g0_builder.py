# src/action_machine/graph/logical/g0_builder.py
"""
Build a **minimal logical graph** from the G0 synthetic bundle (golden ``logical_minimal.json``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Seed implementation for **PR2 / G0**: translate a tiny declarative JSON ``input``
into ``LogicalVertex`` / ``LogicalEdge`` lists with **BELONGS_TO / CONTAINS** and
**ASSIGNED_TO / REQUIRES_ROLE** pairs, matching ``graph.md`` v4.1 §5.3.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    logical_minimal.json["input"]
              │
              ▼
    build_from_g0_input()
              │
              ▼
    (vertices, edges)  →  canonical JSON  →  pytest vs fixture["expected"]

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every ``ASSIGNED_TO`` (role → action) has a matching ``REQUIRES_ROLE`` (action → role).
- Every ``BELONGS_TO`` (action → domain) has a matching ``CONTAINS`` (domain → action).
- DAG flags: only structural DAG edge types would set ``is_dag=True``; this bundle uses ``False``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- See ``tests/fixtures/golden_graph/logical_minimal.json``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Validates only presence/shape of required keys, unique vertex ids, and referential
  integrity; not a general coordinator builder.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from action_machine.graph.logical.model import LogicalEdge, LogicalVertex
from action_machine.graph.logical.reverse_edge import reverse_direct_edge


def _assert_unique_g0_vertex_ids(
    domains: list[Any],
    actions: list[Any],
    roles: list[Any],
) -> None:
    """Reject duplicate ``id`` strings across domain / action / role rows."""
    seen: set[str] = set()
    for kind, rows in (
        ("domain", domains),
        ("action", actions),
        ("role", roles),
    ):
        for row in rows:
            vid = str(row["id"])
            if vid in seen:
                msg = f"duplicate vertex id {vid!r} (second occurrence in {kind} list)"
                raise ValueError(msg)
            seen.add(vid)


def build_from_g0_input(inp: Mapping[str, Any]) -> tuple[list[LogicalVertex], list[LogicalEdge]]:
    """
    Build vertices and edges from the ``input`` object inside ``logical_minimal.json``.

    Raises:
        KeyError: missing required section.
        ValueError: duplicate vertex ``id``, or inconsistent references between
            actions, domains, and roles.
        RuntimeError: internal inconsistency if a §5.3 forward edge does not reverse.
    """
    domains = inp["domains"]
    actions = inp["actions"]
    roles = inp["roles"]

    _assert_unique_g0_vertex_ids(domains, actions, roles)

    vertices: list[LogicalVertex] = []
    edges: list[LogicalEdge] = []

    domain_ids = {str(d["id"]) for d in domains}
    action_ids = {str(a["id"]) for a in actions}

    for d in domains:
        did = str(d["id"])
        vertices.append(
            LogicalVertex(
                id=did,
                vertex_type="domain",
                stereotype="Business Object",
                display_name=str(d["display_name"]),
                class_ref=None,
                properties={},
            ),
        )

    for a in actions:
        aid = str(a["id"])
        dom_id = str(a["domain_id"])
        if dom_id not in domain_ids:
            msg = f"action {aid!r} references unknown domain_id {dom_id!r}"
            raise ValueError(msg)
        vertices.append(
            LogicalVertex(
                id=aid,
                vertex_type="action",
                stereotype="Business Process",
                display_name=str(a["display_name"]),
                class_ref=None,
                properties={},
            ),
        )

    for r in roles:
        rid = str(r["id"])
        act_id = str(r["assigned_action_id"])
        if act_id not in action_ids:
            msg = f"role {rid!r} references unknown assigned_action_id {act_id!r}"
            raise ValueError(msg)
        vertices.append(
            LogicalVertex(
                id=rid,
                vertex_type="role",
                stereotype="Business Role",
                display_name=str(r["display_name"]),
                class_ref=None,
                properties={},
            ),
        )

    for a in actions:
        aid = str(a["id"])
        dom_id = str(a["domain_id"])
        belongs = LogicalEdge(
            source_id=aid,
            target_id=dom_id,
            edge_type="BELONGS_TO",
            stereotype="Aggregation",
            category="direct",
            is_dag=False,
            attributes={},
        )
        contains = reverse_direct_edge(belongs)
        if contains is None:
            msg = "internal error: BELONGS_TO must reverse via REVERSE_EDGE_MAP"
            raise RuntimeError(msg)
        edges.append(belongs)
        edges.append(contains)

    for r in roles:
        rid = str(r["id"])
        act_id = str(r["assigned_action_id"])
        assigned = LogicalEdge(
            source_id=rid,
            target_id=act_id,
            edge_type="ASSIGNED_TO",
            stereotype="Assignment",
            category="direct",
            is_dag=False,
            attributes={},
        )
        requires = reverse_direct_edge(assigned)
        if requires is None:
            msg = "internal error: ASSIGNED_TO must reverse via REVERSE_EDGE_MAP"
            raise RuntimeError(msg)
        edges.append(assigned)
        edges.append(requires)

    return vertices, edges
