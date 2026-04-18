# src/action_machine/intents/auth/role_intent_inspector.py
"""
Role intent inspector for role facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walk subclasses of ``RoleIntent``, read ``@check_roles`` (``_role_info``), and
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
    Snapshot.from_target() → FacetPayload(node_type="action", … ``requires_role`` → anchor ``role_class``)

The inspector uses ``_target_intent = RoleIntent`` to discover candidate
classes. For each class with ``_role_info``, it builds an **action** payload
(same collect key as structural ``@depends`` / folded ``@meta``) carrying
``node_meta`` with ``spec`` and **edges** toward existing ``role_class`` nodes
(``RoleClassInspector``). ``NoneRole`` / ``AnyRole`` yield no role-class edges.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only classes inheriting ``RoleIntent`` are inspected.
- A class may inherit ``RoleIntent`` without ``@check_roles``; such classes
  produce ``None`` from ``inspect()``.
- The ``spec`` value is taken directly from ``_role_info["spec"]`` (``BaseRole``
  type, tuple of types, ``NoneRole``, or ``AnyRole``); graph edges target anchors
  derived from that spec.
- The facet snapshot storage key is ``"role"`` (see ``facet_snapshot_storage_key``);
  the emitted payload uses ``node_type=\"action\"`` for merge with other action facets.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AdminRole)
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    # inspect(AdminAction) → FacetPayload(
    #     node_type="action",
    #     node_name == module.AdminAction,
    #     edges: requires_role → role_class:…ApplicationRole (anchor),
    #     node_meta includes spec == AdminRole,
    # )

    @check_roles(NoneRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    # inspect(PingAction) → spec is NoneRole

    class BaseAction(ABC, RoleIntent, ...):
        ...

    # inspect(BaseAction) → None (no _role_info)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The inspector does not validate the role spec; validation is performed by
  ``@check_roles`` at import time and by the machine at runtime.
- Global graph checks (key uniqueness, acyclicity, role topology) are performed
  by ``GraphCoordinator.build()`` together with ``RoleClassInspector`` /
  ``RoleModeIntentInspector``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role facet inspector.
CONTRACT: ``_role_info`` → merged ``action`` facet + ``requires_role`` edges to anchor ``role_class`` nodes.
INVARIANTS: Target mixin is RoleIntent; snapshot key ``"role"``; edge targets are ``ApplicationRole``.
FLOW: _role_info present → Snapshot → FacetPayload → coordinator graph.
FAILURES: Returns None when ``_role_info`` is missing.
EXTENSION POINTS: Payload consumed by coordinator and role-checking runtime.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import EdgeInfo, FacetPayload
from action_machine.intents.auth.any_role import AnyRole
from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.auth.role_graph_roots import role_class_topology_anchor
from action_machine.intents.auth.role_intent import RoleIntent


class RoleIntentInspector(BaseIntentInspector):
    """
    Role intent inspector.

    Walks ``RoleIntent`` subclasses, detects ``@check_roles``, and builds merged
    ``action`` facet payloads with ``requires_role`` edges to ``role_class`` vertices.

    AI-CORE-BEGIN
    ROLE: Concrete role facet inspector.
    CONTRACT: ``_role_info`` → ``action`` payload + ``requires_role`` to taxonomy anchors.
    INVARIANTS: Marker is ``RoleIntent``; snapshot storage key ``\"role\"``.
    AI-CORE-END
    """

    _target_intent: type = RoleIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed role facet for a target class."""

        class_ref: type
        spec: Any

        def to_facet_payload(self) -> FacetPayload:
            return RoleIntentInspector._facet_payload_for_action_and_spec(
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
        """Return all subclasses of ``RoleIntent``."""
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
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
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        """Stable cache key; payload ``node_type`` is ``action`` after projection."""
        return "role"

    @staticmethod
    def _required_role_types_from_spec(spec: object) -> tuple[type[BaseRole], ...]:
        if spec in (NoneRole, AnyRole):
            return ()
        if isinstance(spec, type) and issubclass(spec, BaseRole):
            return (spec,)
        if isinstance(spec, tuple):
            return tuple(r for r in spec if isinstance(r, type) and issubclass(r, BaseRole))
        return ()

    @classmethod
    def _edges_requires_role_to_role_classes(
        cls, spec: object,
    ) -> tuple[EdgeInfo, ...]:
        concretes = cls._required_role_types_from_spec(spec)
        if not concretes:
            return ()
        buckets: dict[type, list[type[BaseRole]]] = {}
        for role_cls in concretes:
            anchor = role_class_topology_anchor(role_cls)
            bucket = buckets.setdefault(anchor, [])
            if role_cls not in bucket:
                bucket.append(role_cls)
        edges: list[EdgeInfo] = []
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
    def _facet_payload_for_action_and_spec(
        cls, action_cls: type, spec: Any,
    ) -> FacetPayload:
        return FacetPayload(
            node_type="action",
            node_name=cls._make_node_name(action_cls),
            node_class=action_cls,
            node_meta=cls._make_meta(spec=spec),
            edges=cls._edges_requires_role_to_role_classes(spec),
        )

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Build merged ``action`` facet rows + ``requires_role`` edges from ``_role_info``."""
        snap = cls.Snapshot.from_target(target_cls)
        return cls._facet_payload_for_action_and_spec(snap.class_ref, snap.spec)
