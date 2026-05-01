# src/action_machine/legacy/role_intent_inspector.py
"""
Role intent inspector for role facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walk subclasses of ``CheckRolesIntent``, read ``@check_roles`` (``_role_info``), and
emit **outgoing informational edges** from the canonical **action** vertex to
required **``role_class``** taxonomy anchor (``ApplicationRole`` only). Concrete
types from ``@check_roles`` map to that anchor via
``role_class_topology_anchor``; when the anchor differs from the declared type or
several concretes collapse to one anchor, ``edge_meta`` carries
``check_roles_roles`` (dotted class names). The decorator is not a graph node:
only the action class and anchor role vertices exist as graph nodes;
``@check_roles`` is modeled by those edges plus the cached ``role`` facet snapshot
on the action class (``spec`` still lists the declared types).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(AdminRole)
          │
          ▼
    cls._role_info = {"spec": <BaseRole subtype> | tuple[...] | NoneRole | AnyRole }
          │
          ▼
    RoleIntentInspector.inspect()
          │
          ▼
    Snapshot.from_target() → FacetVertex(node_type="action", … ``requires_role`` → anchor ``role_class``)

The inspector uses ``_target_intent = CheckRolesIntent`` to discover candidate
classes. For each class with ``_role_info``, it builds an **action** payload
(same collect key as structural ``@depends`` / folded ``@meta``) carrying
``node_meta`` with ``spec`` and **edges** toward existing ``role_class`` nodes
(``RoleClassInspector``). Sentinels and concretes use the same ``role_class`` anchor (see topology helper).

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE
from action_machine.legacy.role_graph_roots import role_class_topology_anchor
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex


class RoleIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete role facet inspector.
    CONTRACT: ``_role_info`` → ``action`` payload + ``requires_role`` to taxonomy anchors.
    INVARIANTS: Marker is ``CheckRolesIntent``; snapshot storage key ``"role"``.
    AI-CORE-END
"""

    _target_intent: type = CheckRolesIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed role facet for a target class."""

        class_ref: type
        spec: Any

        def to_facet_vertex(self) -> FacetVertex:
            return RoleIntentInspector._facet_vertex_for_action_and_spec(
                self.class_ref, self.spec,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> RoleIntentInspector.Snapshot:
            info = getattr(target_cls, "_role_info", None)
            if not isinstance(info, dict):
                raise TypeError(
                    f"{target_cls.__name__} does not contain valid _role_info.",
                )
            return cls(class_ref=target_cls, spec=info["spec"])

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """Return all subclasses of ``CheckRolesIntent``."""
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        """Build payload if ``@check_roles`` is present."""
        role_info = getattr(target_cls, "_role_info", None)
        if role_info is None:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> RoleIntentInspector.Snapshot | None:
        if getattr(target_cls, "_role_info", None) is None:
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        """Stable cache key; payload ``node_type`` is ``action`` after projection."""
        return "role"

    @classmethod
    def _edges_requires_role_to_role_classes(
        cls, spec: object,
    ) -> tuple[FacetEdge, ...]:
        concretes = spec if isinstance(spec, tuple) else (spec,)
        buckets: dict[type, list[type[BaseRole]]] = {}
        for role_cls in concretes:
            anchor = role_class_topology_anchor(role_cls)
            bucket = buckets.setdefault(anchor, [])
            if role_cls not in bucket:
                bucket.append(role_cls)
        edges: list[FacetEdge] = []
        for anchor in sorted(buckets, key=lambda t: t.__name__):
            uniq = tuple(buckets[anchor])
            edge_meta: tuple[tuple[str, Any], ...] = ()
            if len(uniq) > 1 or (len(uniq) == 1 and uniq[0] is not anchor):
                names = tuple(f"{r.__module__}.{r.__qualname__}" for r in uniq)
                edge_meta = (("check_roles_roles", names),)
            edges.append(
                cls._make_edge(
                    target_node_type="role_class",
                    target_cls=anchor,
                    edge_type="requires_role",
                    is_structural=False,
                    edge_meta=edge_meta,
                ),
            )
        return tuple(edges)

    @classmethod
    def _facet_vertex_for_action_and_spec(
        cls, action_cls: type, spec: Any,
    ) -> FacetVertex:
        return FacetVertex(
            node_type=ACTION_VERTEX_TYPE,
            node_name=cls._make_node_name(action_cls),
            node_class=action_cls,
            node_meta=cls._make_meta(spec=spec),
            edges=cls._edges_requires_role_to_role_classes(spec),
        )

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """Build merged ``action`` facet rows + ``requires_role`` edges from ``_role_info``."""
        snap = cls.Snapshot.from_target(target_cls)
        return cls._facet_vertex_for_action_and_spec(snap.class_ref, snap.spec)
