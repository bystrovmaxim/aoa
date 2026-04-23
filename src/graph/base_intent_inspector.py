# src/graph/base_intent_inspector.py
"""
BaseIntentInspector — abstract base for every ActionMachine intent inspector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseIntentInspector`` defines the contract every concrete inspector must
follow.

An inspector:
1. Knows which marker mixin subtree to walk (``_target_intent``).
2. Can inspect each candidate class and emit graph data.
3. Registers with ``GraphCoordinator``.

During ``build()`` the coordinator walks registered inspectors, calls
``inspect()`` on each candidate, and commits graph topology. Inspectors emit
either legacy :class:`FacetVertex` rows or, **once migrated**, pure interchange
data (see **Interchange return shape** below).

Optionally, ``facet_snapshot_for_class()`` returns a :class:`BaseFacetSnapshot`
(usually a nested ``Snapshot`` on the inspector); the coordinator caches it
next to the graph so ``to_facet_vertex()`` stays the single projection path.

═══════════════════════════════════════════════════════════════════════════════
MARKER VS INSPECTOR
═══════════════════════════════════════════════════════════════════════════════

Each intent is represented twice:

    Marker mixin (``CheckRolesIntent``, ``AspectIntent``, ``DependencyIntent[T]``, …)
        Lives in the MRO of ``BaseAction`` (or ``BaseEntity``, ``BaseResource``).
        Declares intent for the matching decorator grammar via ``issubclass`` checks.
        Contains no inspection logic. Does not inherit ``BaseIntentInspector``.
        Stays stable across refactors.

    Inspector (``RoleIntentInspector``, ``AspectIntentInspector``, …)
        Inherits ``BaseIntentInspector``. Implements ``inspect()`` and
        ``_build_payload()``. Walks marker subclasses via ``_target_intent``.
        Registers with the coordinator.

The link is the inspector's ``_target_intent`` (single marker) or, rarely, the
``_target_intents`` tuple / custom ``_subclasses_recursive()`` used by
``MetaIntentInspector`` to union action and resource markers without duplicate
nodes. The marker never references the inspector.

═══════════════════════════════════════════════════════════════════════════════
INTERCHANGE RETURN SHAPE (TARGET — NO EXTRA TYPES)
═══════════════════════════════════════════════════════════════════════════════

The preferred contract uses **only** :class:`~graph.graph_vertex.GraphVertex`
and :class:`~graph.graph_edge.GraphEdge` — no wrapper dataclass.

``inspect()`` **may** return (see :data:`InspectGraphPair`)::

    (vertices, edges)

where:

- ``vertices`` is a ``list`` of :class:`~graph.graph_vertex.GraphVertex`.
  Each vertex ``id`` is the global interchange id (same string the coordinator
  uses as ``node_name`` today).
- ``edges`` is a ``list`` of :class:`~graph.graph_edge.GraphEdge`.
  Every ``source_id`` / ``target_id`` must match some ``GraphVertex.id`` in the
  same contribution (possibly across lists from other classes after merge).

Coordinator-specific metadata (owner class, facet meta, merge keys) until the
collector is migrated may live in reserved ``properties`` entries on those
dataclasses; interchange-only consumers ignore unknown keys.

If the candidate class is irrelevant, return ``None``.

Until all inspectors migrate, :class:`~graph.facet_vertex.FacetVertex`
returns remain valid (see :data:`FacetInspectResult`).

═══════════════════════════════════════════════════════════════════════════════
TWO REQUIRED METHODS
═══════════════════════════════════════════════════════════════════════════════

Every inspector implements two abstract ``classmethod`` hooks:

    inspect(target_cls) → FacetInspectResult
        Entry point. Prefer ``tuple[list[GraphVertex], list[GraphEdge]]`` (see
        :data:`InspectGraphPair`); legacy facet payloads remain supported during migration.

    _build_payload(target_cls) → FacetBuildResult
        Builds the node/edge bundle (or several facets). Reads class scratch attributes
        (``_role_info``, ``_depends_info``, ``_meta_info``, …) and uses base
        helpers to assemble ``FacetVertex`` (until interchange-only migration).

═══════════════════════════════════════════════════════════════════════════════
WHERE VALIDATION LIVES
═══════════════════════════════════════════════════════════════════════════════

Validation is layered:

    Decorators (``@check_roles``, ``@regular_aspect``, ``@depends``, …)
        Validate arguments at import time: types, emptiness, ``issubclass``,
        duplicates. Fail fast when the class body executes.

    Coordinator (``GraphCoordinator.build()``)
        Global checks after every payload is collected: key uniqueness, edge
        integrity, structural acyclicity.

Inspectors do **not** implement ``_validate()`` — responsibility stays in
decorators plus coordinator.

═══════════════════════════════════════════════════════════════════════════════
RESPONSIBILITY SPLIT
═══════════════════════════════════════════════════════════════════════════════

    inspect()        — cheap presence checks only (e.g. ``_role_info``?)
    _build_payload() — reads data, materializes ``FacetVertex``

This keeps ``inspect()`` fast (``hasattr`` / ``getattr`` only) and
``_build_payload()`` free of side effects beyond constructing payloads.

═══════════════════════════════════════════════════════════════════════════════
HELPERS
═══════════════════════════════════════════════════════════════════════════════

The base class exposes five helpers shared by inspectors:

    _make_node_name(target_cls, suffix="") → str
        Builds ``"module.ClassName"`` or ``"module.ClassName:suffix"`` for dependent facets.
        Does **not** add ``node_type:`` — interchange vertex ``id`` is this string alone.

    _make_edge(target_node_type, target_cls, edge_type,
               is_structural, edge_meta=()) → FacetEdge
        Builds ``FacetEdge`` with ``_make_node_name(target_cls)`` for the target.

    _make_edge_by_name(target_node_type, target_name, edge_type,
                       is_structural, edge_meta=()) → FacetEdge
        Like ``_make_edge`` when the target is a string
        (e.g. ``"context_field:user.user_id"``).

    _make_meta(**kwargs) → tuple[tuple[str, Any], ...]
        Friendly kwargs → immutable tuple-of-tuples for frozen dataclasses.

    _unwrap_declaring_class_member(attr) → Any
        For ``vars(cls)`` iteration: return ``property.fget`` when ``attr`` is a
        property with a getter, otherwise return ``attr`` (used to read decorator
        scratch on methods).

    _collect_subclasses(mixin) → list[type]
        Depth-first walk of every subclass registered on the marker mixin.

═══════════════════════════════════════════════════════════════════════════════
SUBCLASS WALK
═══════════════════════════════════════════════════════════════════════════════

Default ``_subclasses_recursive()`` walks subclasses of the inspector class
itself. Concrete inspectors override it to traverse ``_target_intent`` instead::

    class RoleIntentInspector(BaseIntentInspector):
        _target_intent = CheckRolesIntent

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_intent)

The coordinator calls ``_subclasses_recursive()`` for each registered inspector.

═══════════════════════════════════════════════════════════════════════════════
RUNTIME PARITY (TESTS == APPLICATION)
═══════════════════════════════════════════════════════════════════════════════

ActionMachine intentionally uses the same subclass discovery path in tests and
in production: ``__subclasses__()`` recursion over marker mixins.

This means there is no dedicated "test-only discovery sandbox". Any class that
is imported and registered in the current Python process can be discovered by
inspectors, including module-level test classes.

This is a deliberate design trade-off for parity: tests exercise the same
registration/discovery semantics as real application code, rather than a mocked
or synthetic discovery layer.

Practical implication: when tests define long-lived module-level classes, later
tests in the same process can observe them via subclass traversal.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE — INSPECTOR WITH INFORMATIONAL EDGES (``@check_roles``)
═══════════════════════════════════════════════════════════════════════════════

    class RoleIntentInspector(BaseIntentInspector):
        _target_intent = CheckRolesIntent

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_intent)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetInspectResult:
            role_info = getattr(target_cls, "_role_info", None)
            if role_info is None:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetBuildResult:
            # Real implementation: merged ``node_type="action"`` row plus
            # ``requires_role`` edges to canonical ``role_class`` vertices.
            ...

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE — INSPECTOR WITH EDGES
═══════════════════════════════════════════════════════════════════════════════

    class DependencyIntentInspector(BaseIntentInspector):
        _target_intent = DependencyIntent

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_intent)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetInspectResult:
            depends_info = getattr(target_cls, "_depends_info", None)
            if not depends_info:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetBuildResult:
            edges = tuple(
                cls._make_edge(
                    target_node_type="dependency",
                    target_cls=dep_info.cls,
                    edge_type="depends",
                    is_structural=True,
                )
                for dep_info in target_cls._depends_info
            )
            return FacetVertex(
                node_type="PrimaryHost",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                edges=edges,
            )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_inspector import BaseInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex
from graph.graph_edge import GraphEdge
from graph.graph_vertex import GraphVertex

# Target: ``(vertices, edges)`` only — no envelope type (see module docstring).
type InspectGraphPair = tuple[list[GraphVertex], list[GraphEdge]]

# Legacy facet payloads **or** ``InspectGraphPair`` **or** ``None`` when irrelevant.
type FacetInspectResult = (
    FacetVertex
    | list[FacetVertex]
    | tuple[FacetVertex, ...]
    | InspectGraphPair
    | None
)
type FacetBuildResult = FacetVertex | list[FacetVertex]


class BaseIntentInspector(ABC, BaseInspector):
    """
AI-CORE-BEGIN
    ROLE: Abstract contract for all graph intent inspectors.
    CONTRACT: Provide class traversal + payload projection hooks with shared helper primitives.
    INVARIANTS: Classmethod facet API; concrete subclasses implement ``inspect`` and ``_build_payload``.
    AI-CORE-END
"""

    # ═══════════════════════════════════════════════════════════════════
    # Required contract (two abstract methods)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    @abstractmethod
    def inspect(cls, target_cls: type) -> FacetInspectResult:
        """
        Decide whether ``target_cls`` matches this inspector and build data.

        Called for every class discovered via ``_subclasses_recursive()``. A
        typical ``inspect()``:

            1. Check decorator scratch (``hasattr`` / ``getattr``).
            2. If missing → ``return None``.
            3. Call ``_build_payload()`` → legacy ``FacetVertex`` / list, **or**
               return ``(vertices, edges)`` as two lists of interchange types
               (:data:`InspectGraphPair`).

        Args:
            target_cls: Candidate class (subclass of the marker mixin).
        """
        pass

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> BaseFacetSnapshot | None:
        """
        Optional typed snapshot for ``target_cls`` when this inspector owns it.

        When non-``None``, ``GraphCoordinator`` stores it during graph ``build()``
        (phase 1) under ``(target_cls, facet_snapshot_storage_key(...))``.
        Default: no snapshot.

        Override in inspectors that define a nested ``Snapshot`` with
        ``to_facet_vertex()``.
        """
        return None

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetVertex,
    ) -> str:
        """
        Cache key for ``_facet_snapshots`` (may differ from ``payload.node_type``).

        Several inspectors merge into one graph node (e.g. ``node_type=\"action\"``);
        each facet that exposes a snapshot should return a **distinct** key here.
        """
        return payload.node_type

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls,
        _target_cls: type,
        payload: FacetVertex,
    ) -> bool:
        """
        If ``False``, :class:`~graph.graph_coordinator.GraphCoordinator`
        skips :meth:`~graph.graph_coordinator.GraphCoordinator._register_hydration_snapshot_key`
        for this payload.

        Use when an inspector emits an extra merged node (e.g. ``node_type=\"action\"``)
        only to attach informational edges; the typed facet snapshot must hydrate
        the primary facet nodes, not that shell.
        """
        return True

    @classmethod
    @abstractmethod
    def _build_payload(cls, target_cls: type) -> FacetBuildResult:
        """
        Construct ``FacetVertex`` (or several) from class scratch attributes.

        Reads ``_role_info``, ``_depends_info``, etc., and uses
        ``_make_node_name``, ``_make_edge``, ``_make_edge_by_name``, ``_make_meta``.

        Args:
            target_cls: Class that already passed ``inspect()``.
        """
        pass

    # ═══════════════════════════════════════════════════════════════════
    # Helpers for _build_payload
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def _make_node_name(cls, target_cls: type, suffix: str = "") -> str:
        """
        Derive a stable **facet node name** (interchange vertex ``id``) from ``__module__``
        and ``__qualname__``.

        Standalone hosts use the full dotted class path only. Dependent facets on the
        same host (aspect method, ``@meta`` facet row, ``role``, …) use
        ``"{host_path}:{suffix}"`` with a single ASCII colon (never ``node_type:`` here).

        Falls back to ``__qualname__`` when ``__module__`` is missing or ``"__main__"``.

        Args:
            target_cls: Class being named.
            suffix: Optional logical child segment (aspect method name, ``"meta"``, …).

        Returns:
            Node name string (global facet key body; uniqueness is this string alone).

        Examples::

            _make_node_name(CreateOrderAction)
            → "myapp.orders.CreateOrderAction"

            _make_node_name(CreateOrderAction, "validate_aspect")
            → "myapp.orders.CreateOrderAction:validate_aspect"
        """
        module = getattr(target_cls, "__module__", None)
        if module and module != "__main__":
            name = f"{module}.{target_cls.__qualname__}"
        else:
            name = target_cls.__qualname__
        if suffix:
            return f"{name}:{suffix}"
        return name

    @classmethod
    def _make_host_dependent_node_name(cls, host_cls: type, facet_tag: str) -> str:
        """
        Node name for a facet that hangs off ``host_cls`` but is not the host identity itself.

        ``facet_tag`` is a short stable label (``"meta"``, ``"role"``, method name, …).
        """
        return cls._make_node_name(host_cls, facet_tag)

    @classmethod
    def _make_edge(
        cls,
        target_node_type: str,
        target_cls: type,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
        *,
        synthetic_stub_edges: tuple[FacetEdge, ...] = (),
    ) -> FacetEdge:
        """
        Build ``FacetEdge`` when the target is a concrete class.

        Target name comes from ``_make_node_name(target_cls)``.

        Args:
            target_node_type: Target facet (``"dependency"``, ``"Domain"``, …).
            target_cls: Python class at the arrow head.
            edge_type: Edge label (``"depends"``, ``"connection"``, …).
            is_structural: Structural vs informational edge.
            edge_meta: Optional tuple metadata (defaults to empty).

        Returns:
            Populated ``FacetEdge`` with ``target_class_ref=target_cls``.

            synthetic_stub_edges:
                Outgoing edges on a coordinator-synthesized target node when this
                edge's target was materialized from ``target_class_ref``.
        """
        return FacetEdge(
            target_node_type=target_node_type,
            target_name=cls._make_node_name(target_cls),
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
            target_class_ref=target_cls,
            synthetic_stub_edges=synthetic_stub_edges,
        )

    @classmethod
    def _make_edge_by_name(
        cls,
        target_node_type: str,
        target_name: str,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
        *,
        target_class_ref: type | None = None,
    ) -> FacetEdge:
        """
        Build ``FacetEdge`` when the target is a string identifier.

        Useful for context-field nodes (``"user.user_id"``) or synthetic domains.
        When ``target_class_ref`` is set, :meth:`GraphCoordinator._materialize_edge_targets`
        can synthesize a stub facet node for that class.

        Args:
            target_node_type: Target facet type.
            target_name: Target node name string.
            edge_type: Edge label.
            is_structural: Structural vs informational edge.
            edge_meta: Optional edge metadata tuple.
            target_class_ref: Optional concrete class for materialized stubs.

        Returns:
            ``FacetEdge`` (``target_class_ref`` defaults to ``None``).
        """
        return FacetEdge(
            target_node_type=target_node_type,
            target_name=target_name,
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
            target_class_ref=target_class_ref,
        )

    @classmethod
    def _make_meta(cls, **kwargs: Any) -> tuple[tuple[str, Any], ...]:
        """
        Convert kwargs into an immutable metadata tuple.

        Frozen payloads must stay hashable; this replaces dict literals.

        Args:
            **kwargs: Arbitrary key/value metadata.

        Returns:
            ``tuple[tuple[str, Any], ...]`` suitable for ``node_meta`` / ``edge_meta``.

        Example::

            cls._make_meta(spec=AdminRole, description="Administrator")
            → (("spec", AdminRole), ("description", "Administrator"))

        The same shape can be reused for **each row** inside a larger metadata
        value (tuple of rows): every row is ``tuple[tuple[str, Any], ...]``,
        hashable and readable via ``dict(row)``.
        """
        return tuple(kwargs.items())

    @staticmethod
    def _unwrap_declaring_class_member(attr: Any) -> Any:
        """
        Normalize a class dict entry so decorator scratch can be read.

        Properties store metadata on ``fget``; bare callables use the value as-is.

        Args:
            attr: Value from ``vars(target_cls).items()``.

        Returns:
            Unwrapped callable target for ``getattr(..., "_…_meta")`` probes.
        """
        if isinstance(attr, property) and attr.fget is not None:
            return attr.fget
        return attr

    # ═══════════════════════════════════════════════════════════════════
    # Subclass traversal
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _collect_subclasses(mixin: type) -> list[type]:
        """
        Recursively list every subclass of ``mixin``.

        Uses Python's automatic ``__subclasses__()`` registration — no manual
        bookkeeping.

        Inspectors call this from ``_subclasses_recursive()`` to follow marker
        mixins instead of inspector subclasses.

        Traversal order: depth-first; direct subclasses precede deeper ones.

        Args:
            mixin: Marker whose inheritance tree should be scanned.

        Returns:
            All direct and transitive subclasses; empty when none exist.

        Example::

            BaseIntentInspector._collect_subclasses(CheckRolesIntent)
            → [BaseAction, CreateOrderAction, ...]
        """
        result: list[type] = []
        for sub in mixin.__subclasses__():
            result.append(sub)
            result.extend(BaseIntentInspector._collect_subclasses(sub))
        return result

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """
        Default traversal walks subclasses of **this inspector class**.

        Concrete inspectors override it to scan ``_target_intent`` instead::

            @classmethod
            def _subclasses_recursive(cls) -> list[type]:
                return cls._collect_subclasses(cls._target_intent)

        ``GraphCoordinator.build()`` invokes this for every registered inspector.

        Returns:
            Sequence of classes that should be passed to ``inspect()``.
        """
        result: list[type] = []
        for subclass in cls.__subclasses__():
            result.append(subclass)
            if hasattr(subclass, "_subclasses_recursive"):
                result.extend(subclass._subclasses_recursive())
        return result
