# src/action_machine/graph/base_intent_inspector.py
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
3. Registers with ``GateCoordinator``.

During ``build()`` the coordinator walks registered inspectors, calls
``inspect()`` on each candidate, and commits ``FacetPayload`` nodes into
``rx.PyDiGraph``. Inspectors do not assemble runtime metadata — only graph
nodes/edges plus optional node ``meta`` for tooling.

Optionally, ``facet_snapshot_for_class()`` returns a :class:`BaseFacetSnapshot`
(usually a nested ``Snapshot`` on the inspector); the coordinator caches it
next to the graph so ``to_facet_payload()`` stays the single projection path.

═══════════════════════════════════════════════════════════════════════════════
MARKER VS INSPECTOR
═══════════════════════════════════════════════════════════════════════════════

Each intent is represented twice:

    Marker mixin (``RoleIntent``, ``AspectIntent``, ``DependencyIntent[T]``, …)
        Lives in the MRO of ``BaseAction`` (or ``BaseEntity``, ``BaseResourceManager``).
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
TWO REQUIRED METHODS
═══════════════════════════════════════════════════════════════════════════════

Every inspector implements two abstract ``classmethod`` hooks:

    inspect(target_cls) → FacetPayload | None
        Entry point. Decides whether the class belongs to this inspector.
        Either returns a ``FacetPayload`` or ``None`` when the class is irrelevant.

    _build_payload(target_cls) → FacetPayload
        Builds the node/edge bundle. Reads class scratch attributes
        (``_role_info``, ``_depends_info``, ``_meta_info``, …) and uses base
        helpers to assemble ``FacetPayload``.

═══════════════════════════════════════════════════════════════════════════════
WHERE VALIDATION LIVES
═══════════════════════════════════════════════════════════════════════════════

Validation is layered:

    Decorators (``@check_roles``, ``@regular_aspect``, ``@depends``, …)
        Validate arguments at import time: types, emptiness, ``issubclass``,
        duplicates. Fail fast when the class body executes.

    Coordinator (``GateCoordinator.build()``)
        Global checks after every payload is collected: key uniqueness, edge
        integrity, structural acyclicity.

Inspectors do **not** implement ``_validate()`` — responsibility stays in
decorators plus coordinator.

═══════════════════════════════════════════════════════════════════════════════
RESPONSIBILITY SPLIT
═══════════════════════════════════════════════════════════════════════════════

    inspect()        — cheap presence checks only (e.g. ``_role_info``?)
    _build_payload() — reads data, materializes ``FacetPayload``

This keeps ``inspect()`` fast (``hasattr`` / ``getattr`` only) and
``_build_payload()`` free of side effects beyond constructing payloads.

═══════════════════════════════════════════════════════════════════════════════
HELPERS
═══════════════════════════════════════════════════════════════════════════════

The base class exposes five helpers shared by inspectors:

    _make_node_name(target_cls, suffix="") → str
        Builds ``"module.ClassName"`` or ``"module.ClassName.suffix"``.
        Does **not** add facet prefixes — the coordinator prepends ``node_type:``.

    _make_edge(target_node_type, target_cls, edge_type,
               is_structural, edge_meta=()) → EdgeInfo
        Builds ``EdgeInfo`` with ``_make_node_name(target_cls)`` for the target.

    _make_edge_by_name(target_node_type, target_name, edge_type,
                       is_structural, edge_meta=()) → EdgeInfo
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
        _target_intent = RoleIntent

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
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This base class does not perform payload semantic validation; decorators and
  coordinator build phases own that responsibility.
- Subclass discovery relies on Python runtime class registry
  (``__subclasses__()``), so process-level import history affects candidate sets.
- Inspectors that skip ``facet_snapshot_for_class`` do not participate in typed
  snapshot cache.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE — INSPECTOR WITHOUT EDGES
═══════════════════════════════════════════════════════════════════════════════

    class RoleIntentInspector(BaseIntentInspector):
        _target_intent = RoleIntent

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_intent)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetPayload | None:
            role_info = getattr(target_cls, "_role_info", None)
            if role_info is None:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetPayload:
            return FacetPayload(
                node_type="role",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                node_meta=cls._make_meta(spec=target_cls._role_info["spec"]),
            )

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE — INSPECTOR WITH EDGES
═══════════════════════════════════════════════════════════════════════════════

    class DependencyIntentInspector(BaseIntentInspector):
        _target_intent = DependencyIntent

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_intent)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetPayload | None:
            depends_info = getattr(target_cls, "_depends_info", None)
            if not depends_info:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetPayload:
            edges = tuple(
                cls._make_edge(
                    target_node_type="dependency",
                    target_cls=dep_info.cls,
                    edge_type="depends",
                    is_structural=True,
                )
                for dep_info in target_cls._depends_info
            )
            return FacetPayload(
                node_type="action",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                edges=edges,
            )

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract inspector base for all intent-driven graph facets.
CONTRACT: ``inspect`` / ``_build_payload`` + shared payload and traversal helpers.
INVARIANTS: Stateless classmethods; markers never import inspectors.
FLOW: coordinator → ``_subclasses_recursive`` → ``inspect`` → ``FacetPayload``.
FAILURES: abstract until concrete inspector implements hooks.
EXTENSION POINTS: concrete inspectors override traversal and payload shape.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.payload import EdgeInfo, FacetPayload


class BaseIntentInspector(ABC):
    """
    Abstract base for all intent inspectors.

    Defines two abstract ``classmethod`` hooks (``inspect``, ``_build_payload``)
    and shared helpers that build ``FacetPayload`` / ``EdgeInfo`` and traverse
    marker subclasses without duplicating boilerplate.

    Everything is a ``classmethod`` or ``staticmethod`` — inspectors are
    stateless and need no instances. The class exists for namespacing, shared
    helpers, and ABC enforcement.

    ``GateCoordinator.build()`` does:
    1. ``inspector._subclasses_recursive()`` — marker subclass list.
    2. ``inspector.inspect(target_cls)`` — per-class inspection.

    AI-CORE-BEGIN
    ROLE: Abstract contract for all graph intent inspectors.
    CONTRACT: Provide class traversal + payload projection hooks with shared helper primitives.
    INVARIANTS: Stateless classmethod design; concrete subclasses implement ``inspect`` and ``_build_payload``.
    AI-CORE-END
    """

    # ═══════════════════════════════════════════════════════════════════
    # Required contract (two abstract methods)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    @abstractmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """
        Decide whether ``target_cls`` matches this inspector and build data.

        Called for every class discovered via ``_subclasses_recursive()``. A
        typical ``inspect()``:

            1. Check decorator scratch (``hasattr`` / ``getattr``).
            2. If missing → ``return None``.
            3. Call ``_build_payload()`` → ``FacetPayload``.
            4. Return the payload.

        Args:
            target_cls: Candidate class (subclass of the marker mixin).
        """
        pass

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> BaseFacetSnapshot | None:
        """
        Optional typed snapshot for ``target_cls`` when this inspector owns it.

        When non-``None``, ``GateCoordinator`` stores it during graph ``build()``
        (phase 1) under ``(target_cls, facet_snapshot_storage_key(...))``.
        Default: no snapshot.

        Override in inspectors that define a nested ``Snapshot`` with
        ``to_facet_payload()``.
        """
        return None

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetPayload,
    ) -> str:
        """
        Cache key for ``_facet_snapshots`` (may differ from ``payload.node_type``).

        Several inspectors merge into one graph node (e.g. ``node_type=\"action\"``);
        each facet that exposes a snapshot should return a **distinct** key here.
        """
        return payload.node_type

    @classmethod
    @abstractmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """
        Construct ``FacetPayload`` from class scratch attributes.

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
        Derive a stable node name from ``__module__`` and ``__qualname__``.

        Format: ``"module.ClassName"`` or ``"module.ClassName.suffix"``.
        Falls back to ``__qualname__`` when ``__module__`` is missing or
        ``"__main__"``.

        Facet prefixes such as ``"action:"`` are **not** included — the
        coordinator forms ``"node_type:node_name"``.

        Args:
            target_cls: Class being named.
            suffix: Optional dot suffix for child facets (aspects, entity fields).

        Returns:
            Node name string.

        Examples::

            _make_node_name(CreateOrderAction)
            → "myapp.orders.CreateOrderAction"

            _make_node_name(CreateOrderAction, "validate_aspect")
            → "myapp.orders.CreateOrderAction.validate_aspect"
        """
        module = getattr(target_cls, "__module__", None)
        if module and module != "__main__":
            name = f"{module}.{target_cls.__qualname__}"
        else:
            name = target_cls.__qualname__
        if suffix:
            return f"{name}.{suffix}"
        return name

    @classmethod
    def _make_edge(
        cls,
        target_node_type: str,
        target_cls: type,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
    ) -> EdgeInfo:
        """
        Build ``EdgeInfo`` when the target is a concrete class.

        Target name comes from ``_make_node_name(target_cls)``.

        Args:
            target_node_type: Target facet (``"dependency"``, ``"domain"``, …).
            target_cls: Python class at the arrow head.
            edge_type: Edge label (``"depends"``, ``"connection"``, …).
            is_structural: Structural vs informational edge.
            edge_meta: Optional tuple metadata (defaults to empty).

        Returns:
            Populated ``EdgeInfo`` with ``target_class_ref=target_cls``.
        """
        return EdgeInfo(
            target_node_type=target_node_type,
            target_name=cls._make_node_name(target_cls),
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
            target_class_ref=target_cls,
        )

    @classmethod
    def _make_edge_by_name(
        cls,
        target_node_type: str,
        target_name: str,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
    ) -> EdgeInfo:
        """
        Build ``EdgeInfo`` when the target is a string identifier.

        Useful for context-field nodes (``"user.user_id"``) or synthetic domains.

        Args:
            target_node_type: Target facet type.
            target_name: Target node name string.
            edge_type: Edge label.
            is_structural: Structural vs informational edge.
            edge_meta: Optional edge metadata tuple.

        Returns:
            ``EdgeInfo`` with ``target_class_ref=None``.
        """
        return EdgeInfo(
            target_node_type=target_node_type,
            target_name=target_name,
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
            target_class_ref=None,
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

            BaseIntentInspector._collect_subclasses(RoleIntent)
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

        ``GateCoordinator.build()`` invokes this for every registered inspector.

        Returns:
            Sequence of classes that should be passed to ``inspect()``.
        """
        result: list[type] = []
        for subclass in cls.__subclasses__():
            result.append(subclass)
            if hasattr(subclass, "_subclasses_recursive"):
                result.extend(subclass._subclasses_recursive())
        return result
