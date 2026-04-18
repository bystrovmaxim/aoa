# src/action_machine/graph/edge_info.py
"""
One directed edge from a facet node (:class:`EdgeInfo`).

See :mod:`action_machine.graph.payload` for package-level documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Hashable facet ``node_meta`` row: string keys, opaque values (see inspector hydrators).
FacetMetaRow = tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class EdgeInfo:
    """
    One directed edge leaving a graph node.

    Produced via inspector helpers (see ``BaseIntentInspector._make_edge()``).
    Lives inside ``FacetPayload.edges``. The coordinator uses ``EdgeInfo`` for
    referential integrity (target exists) and, for structural edges, acyclicity.

    Attributes:
        target_node_type : str
            Target facet type (``"Action"``, ``"Entity"``, ``"Domain"``, …).
            Used to build the full target key ``target_node_type:target_name``.

        target_name : str
            Target node name (``"module.ClassName"`` or ``"module.ClassName.suffix"``),
            from ``_make_node_name()``.

        edge_type : str
            Edge kind: ``"depends"``, ``"connection"``, ``"has_aspect"``,
            ``"belongs_to"``, ``"requires_context"``, ``"has_checker"``,
            ``"subscribes"``, ``"has_error_handler"``, ``"has_compensator"``,
            ``"has_sensitive"``, ``"has_role"``, ``"has_field"``,
            ``"has_relation"``, ``"has_lifecycle"``,
            ``"requires_role"``.

        is_structural : bool
            True — structural edge; cycles forbidden.
            False — informational edge; cycles allowed.

        edge_meta : tuple[tuple[str, Any], ...]
            Extra metadata as tuple-of-tuples; converted to dict at commit.
            Defaults to empty tuple.

        target_class_ref : type | None
            When the target is a concrete class (dependency or connection
            manager), the coordinator may synthesize a facet node if no
            inspector emitted one. ``None`` for name-only targets.

        synthetic_stub_edges : tuple[EdgeInfo, ...]
            When the coordinator materializes a missing target for this edge,
            these edges are attached to the synthesized target node. Empty by
            default; inspectors populate when the stub needs outgoing edges.

    AI-CORE-BEGIN
    ROLE: Immutable edge transport row.
    CONTRACT: Describe one outgoing graph edge with target identity and structural semantics.
    INVARIANTS: Structural flag drives cycle checks; metadata remains tuple-encoded until commit.
    AI-CORE-END
    """

    target_node_type: str
    target_name: str
    edge_type: str
    is_structural: bool
    edge_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    target_class_ref: type | None = None
    synthetic_stub_edges: tuple[EdgeInfo, ...] = field(default_factory=tuple)
