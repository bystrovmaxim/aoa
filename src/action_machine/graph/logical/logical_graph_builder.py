# src/action_machine/graph/logical/logical_graph_builder.py
"""
``LogicalGraphBuilder`` — pure construction of ``LogicalVertex`` / ``LogicalEdge`` lists.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Turn either the **G0 synthetic JSON bundle** (same contract as ``build_from_g0_input``)
or a **sequence of ``FacetPayload``** rows (coordinator-phase-1 shape) into canonical
logical graph lists **without** ``rustworkx``. The facet projection sets ``class_ref``
to ``None`` on every ``LogicalVertex`` so the interchange matches the G0 golden
fixture shape (types are still read from payloads for ids and validation).

The facet path is intentionally **narrow** (PR2): ``domain``, ``action``, ``meta`` with
informational ``belongs_to`` → domain, and ``role`` facets whose ``spec`` metadata is a
``type`` (logical role vertex id = ``module.qualname`` of that type). Other facet kinds
are ignored until later PRs widen the projection. Optional ``display_name`` in domain ``node_meta`` overrides the default tail label;
after all payloads are scanned, overrides apply even if ``meta`` created the domain
vertex first (order-independent vs golden G0).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Mapping (G0 input)  →  build_from_g0_input  →  vertices + edges
    Sequence[FacetPayload]  →  _from_facet_payloads  →  vertices + edges

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Deterministic ordering: vertices sorted by ``id``; edges by
  ``(source_id, target_id, edge_type, category)`` before return (callers may re-sort).
- ``belongs_to`` / ``ASSIGNED_TO`` logical pairs are **deduplicated** while preserving first-seen order.
- Duplicate logical vertex ids across emitted vertices raise ``ValueError``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from action_machine.graph.logical.g0_builder import build_from_g0_input
from action_machine.graph.logical.model import LogicalEdge, LogicalVertex
from action_machine.graph.logical.reverse_edge import reverse_direct_edge
from action_machine.graph.payload import FacetPayload


def _tail_name(qualname: str) -> str:
    return qualname.rsplit(".", maxsplit=1)[-1]


def _meta_map(meta: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return dict(meta)


class LogicalGraphBuilder:
    """
    Build logical graph interchange lists from G0 JSON or facet payload snapshots.
    """

    @classmethod
    def build(
        cls,
        *,
        synthetic_g0: Mapping[str, Any] | None = None,
        facet_payloads: Sequence[FacetPayload] | None = None,
    ) -> tuple[list[LogicalVertex], list[LogicalEdge]]:
        """
        Return ``(vertices, edges)`` from exactly one input source.

        Raises:
            ValueError: neither or both sources supplied, invalid facet projection, or
                duplicate logical vertex ids across facet rows.
            RuntimeError: forward edges that must reverse fail to map (constant drift).
        """
        if (synthetic_g0 is None) == (facet_payloads is None):
            msg = "pass exactly one of synthetic_g0=... or facet_payloads=..."
            raise ValueError(msg)
        if synthetic_g0 is not None:
            return build_from_g0_input(synthetic_g0)
        assert facet_payloads is not None
        return cls._from_facet_payloads(tuple(facet_payloads))

    @classmethod
    def _from_facet_payloads(  # pylint: disable=too-many-branches,too-many-statements
        cls,
        payloads: tuple[FacetPayload, ...],
    ) -> tuple[list[LogicalVertex], list[LogicalEdge]]:
        vertices_by_id: dict[str, LogicalVertex] = {}
        belongs_pairs: list[tuple[str, str]] = []
        assigned_pairs: list[tuple[str, str]] = []

        domain_display_override: dict[str, str] = {}
        for p in payloads:
            if p.node_type != "domain":
                continue
            dmeta = _meta_map(p.node_meta)
            dlabel = dmeta.get("display_name")
            if isinstance(dlabel, str) and dlabel.strip():
                domain_display_override[p.node_name] = dlabel

        def ensure_domain_vertex(domain_id: str, display_name: str, _owner_cls: type | None) -> None:
            existing = vertices_by_id.get(domain_id)
            if existing is not None:
                if existing.vertex_type != "domain":
                    msg = f"duplicate vertex id {domain_id!r} (already a {existing.vertex_type})"
                    raise ValueError(msg)
                return
            vertices_by_id[domain_id] = LogicalVertex(
                id=domain_id,
                vertex_type="domain",
                stereotype="Business Object",
                display_name=display_name,
                class_ref=None,
                properties={},
            )

        def ensure_action_vertex(action_id: str, _owner_cls: type) -> None:
            existing = vertices_by_id.get(action_id)
            if existing is not None:
                if existing.vertex_type != "action":
                    msg = f"duplicate vertex id {action_id!r} (already a {existing.vertex_type})"
                    raise ValueError(msg)
                return
            vertices_by_id[action_id] = LogicalVertex(
                id=action_id,
                vertex_type="action",
                stereotype="Business Process",
                display_name=_tail_name(action_id),
                class_ref=None,
                properties={},
            )

        def ensure_role_vertex(role_id: str, _role_cls: type) -> None:
            existing = vertices_by_id.get(role_id)
            if existing is not None:
                if existing.vertex_type != "role":
                    msg = f"duplicate vertex id {role_id!r} (already a {existing.vertex_type})"
                    raise ValueError(msg)
                return
            vertices_by_id[role_id] = LogicalVertex(
                id=role_id,
                vertex_type="role",
                stereotype="Business Role",
                display_name=_tail_name(role_id),
                class_ref=None,
                properties={},
            )

        for p in payloads:
            if p.node_type == "domain":
                dmeta = _meta_map(p.node_meta)
                dlabel = dmeta.get("display_name")
                ddisplay = dlabel if isinstance(dlabel, str) and dlabel.strip() else _tail_name(p.node_name)
                ensure_domain_vertex(p.node_name, ddisplay, p.node_class)
            elif p.node_type == "action":
                ensure_action_vertex(p.node_name, p.node_class)
            elif p.node_type == "meta":
                ensure_action_vertex(p.node_name, p.node_class)
                for e in p.edges:
                    if e.edge_type == "belongs_to" and e.target_node_type == "domain":
                        domain_id = e.target_name
                        if not domain_id:
                            msg = "belongs_to edge missing domain target_name"
                            raise ValueError(msg)
                        ensure_domain_vertex(domain_id, _tail_name(domain_id), e.target_class_ref)
                        belongs_pairs.append((p.node_name, domain_id))
            elif p.node_type == "role":
                ensure_action_vertex(p.node_name, p.node_class)
                meta = _meta_map(p.node_meta)
                spec = meta.get("spec")
                if isinstance(spec, type):
                    role_id = f"{spec.__module__}.{spec.__qualname__}"
                    ensure_role_vertex(role_id, spec)
                    assigned_pairs.append((role_id, p.node_name))

        # Stable dedupe: same (action, domain) or (role, action) may appear from merged facets.
        belongs_pairs = list(dict.fromkeys(belongs_pairs))
        assigned_pairs = list(dict.fromkeys(assigned_pairs))

        for did, label in domain_display_override.items():
            cur = vertices_by_id.get(did)
            if cur is None or cur.vertex_type != "domain":
                continue
            if cur.display_name == label:
                continue
            vertices_by_id[did] = LogicalVertex(
                id=cur.id,
                vertex_type=cur.vertex_type,
                stereotype=cur.stereotype,
                display_name=label,
                class_ref=cur.class_ref,
                properties=cur.properties,
            )

        edges: list[LogicalEdge] = []

        for action_id, domain_id in belongs_pairs:
            if action_id not in vertices_by_id:
                msg = f"belongs_to references unknown action id {action_id!r}"
                raise ValueError(msg)
            if domain_id not in vertices_by_id:
                msg = f"belongs_to references unknown domain id {domain_id!r}"
                raise ValueError(msg)
            forward = LogicalEdge(
                source_id=action_id,
                target_id=domain_id,
                edge_type="BELONGS_TO",
                stereotype="Aggregation",
                category="direct",
                is_dag=False,
                attributes={},
            )
            rev = reverse_direct_edge(forward)
            if rev is None:
                msg = "internal error: BELONGS_TO must reverse via REVERSE_EDGE_MAP"
                raise RuntimeError(msg)
            edges.append(forward)
            edges.append(rev)

        for role_id, action_id in assigned_pairs:
            if role_id not in vertices_by_id or action_id not in vertices_by_id:
                msg = f"ASSIGNED_TO references unknown vertex {role_id!r} -> {action_id!r}"
                raise ValueError(msg)
            forward = LogicalEdge(
                source_id=role_id,
                target_id=action_id,
                edge_type="ASSIGNED_TO",
                stereotype="Assignment",
                category="direct",
                is_dag=False,
                attributes={},
            )
            rev = reverse_direct_edge(forward)
            if rev is None:
                msg = "internal error: ASSIGNED_TO must reverse via REVERSE_EDGE_MAP"
                raise RuntimeError(msg)
            edges.append(forward)
            edges.append(rev)

        vertices = sorted(vertices_by_id.values(), key=lambda v: v.id)
        edges.sort(key=lambda e: (e.source_id, e.target_id, e.edge_type, e.category))
        return vertices, edges
