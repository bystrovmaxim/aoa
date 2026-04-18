# src/action_machine/graph/graph_coordinator.py
"""
GraphCoordinator — transactional interchange graph, internal facet skeleton, and typed facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Registry for **static** metadata: registered **inspectors** (subclasses of
``BaseIntentInspector``) discover intent markers on classes, emit
``FacetPayload`` nodes, and may attach typed per-class snapshots via
``facet_snapshot_for_class()`` / ``facet_snapshot_storage_key()``.

After a successful ``register(...).build()``:

1. **Facet skeleton** (internal ``_facet_graph`` ``rx.PyDiGraph``) — committed nodes
   and edges from payloads for hydration APIs. Each node stores ``node_type``,
   ``name``, and ``class_ref``; when a payload carried ``node_meta`` at commit time,
   a ``committed_meta`` dict is stored on the node so per-vertex metadata (e.g. one
   checker row) can hydrate without merging a class-wide snapshot. Otherwise facet
   body is resolved via ``hydrate_graph_node()`` using snapshots.

2. **Facet snapshot map** (``_facet_snapshots``) — optional typed views keyed by
   ``(owner class, facet storage key)``. Read via ``get_snapshot(cls, facet_key)``.

3. **Interchange graph** — the committed ``rx.PyDiGraph`` in ``_graph`` holds the
   canonical public topology (``vertex_type``, ``id``, …). Vertex ``id`` matches the
   facet key ``node_type:node_name``; edges are projected from payload ``edges`` via
   :mod:`action_machine.graph.graph_builder`. Read it with :meth:`get_graph`.

   A separate **internal** facet skeleton ``rx.PyDiGraph`` (``_facet_graph``) stores
   ``node_type`` / ``name`` / ``class_ref`` for snapshot hydration, ``get_node``, and
   integrations that need facet-shaped topology; use :meth:`facet_topology_copy` for
   a read-only copy (e.g. MCP graph JSON). It is not the interchange returned by
   :meth:`get_graph`.

**Public API (domain-agnostic):** ``register``, ``build``, ``is_built``,
``build_status``, ``graph_node_count``, ``graph_edge_count``, ``get_graph``,
``get_graph_for_visualization``, ``facet_topology_copy``,
``hydrate_graph_node``, ``get_node``, ``get_nodes_by_type``, ``get_nodes_for_class``,
``get_snapshot``.

**Raw graph vs hydrated reads:** :meth:`get_graph` returns the **interchange**
copy (no ``meta``). Prefer ``get_node`` / ``get_nodes_by_type`` / ``get_nodes_for_class``
for facet ``meta``. To hydrate raw dicts yourself, pass **facet** payloads from
:meth:`facet_topology_copy` (node index matches ``_node_index`` facet ordering), not
interchange :meth:`get_graph` payloads. Snapshot storage keys for
hydration are recorded during phase 1 from each inspector's
``facet_snapshot_storage_key()``; if several snapshot storage keys hydrate the same merged node, ``meta`` is the
union of their ``to_facet_payload().node_meta`` maps. Nodes without a registration (stubs) fall
back to ``get_snapshot(cls, node_type)`` unless ``node_type`` is ``action``.

Dependency ``DependencyFactory`` instances may be cached on this object under
``dependency_factory.DEPENDENCY_FACTORY_CACHE_KEY``; clearing that cache does
not rebuild or invalidate the facet graph.

The canonical implementation is **this** module. Typical apps use
``CoreActionMachine.create_coordinator()`` for a pre-built coordinator.

═══════════════════════════════════════════════════════════════════════════════
EXPLICIT ``build()``
═══════════════════════════════════════════════════════════════════════════════

- Inspectors are registered with ``register(InspectorClass)`` **before**
  ``build()``; after ``build()``, further ``register()`` calls raise
  ``RuntimeError``.
- ``build()`` runs once; a second ``build()`` raises ``RuntimeError``.
- Until ``build()`` completes, graph accessors, counts, and ``get_snapshot``
  call ``_require_built()`` and raise ``RuntimeError`` (there is no implicit
  lazy build from read APIs). Use ``build_status()`` or ``is_built`` to branch
  without triggering those errors.

If the inspector list is empty at ``build()``, validation still runs with no
payloads (caller's responsibility to register a useful set).

Discovery source parity:
    ``build()`` consumes candidates from inspectors, and inspectors discover
    candidates from marker ``__subclasses__()`` trees. Tests and production use
    the same mechanism by design (no test-only isolation layer inside the
    coordinator).

═══════════════════════════════════════════════════════════════════════════════
TRANSACTIONAL ``build()`` — THREE PHASES
═══════════════════════════════════════════════════════════════════════════════

The graph is either built completely and consistently, or not committed at all.

    PHASE 1 — COLLECT
        For each inspector: walk ``_subclasses_recursive()`` over intent
        markers; ``inspect()`` → ``FacetPayload | None``.
        Inspectors that emit the same logical ``action:<full name>`` host (structural
        ``@depends`` / ``@connection`` rows, or a ``@meta`` facet on the same
        ``BaseAction`` class) are **merged** in phase 1: edges and ``node_meta`` are
        concatenated so the coordinator keeps a single facet node per graph.md host
        without cross-inspector coupling.

    PHASE 1b — MATERIALIZE
        ``_materialize_edge_targets`` adds missing nodes for edges that carry
        ``target_class_ref`` (stub ``dependency`` / ``connection`` /
        ``domain``), iterating to a fixed point until all targets exist.

    PHASE 2 — VALIDATE
        Payload fields, uniqueness of ``node_type:node_name`` keys, referential
        integrity, acyclicity of **structural** edges; @depends cycles surface
        as ``CyclicDependencyError``.

    PHASE 2b — DAG slice (before commit)
        :mod:`action_machine.graph.graph_builder` on facet payloads; acyclicity
        of the DAG slice (``DEPENDS_ON`` / ``CONNECTS_TO`` with ``is_dag=True``).
        Entity–entity edges (``COMPOSITION_*``, ``ASSOCIATION_*``, …) are outside
        this slice and may cycle; they do not trigger ``CyclicDependencyError``.
        Cycles in the slice raise ``CyclicDependencyError`` (same surface as structural cycles).

    PHASE 3 — COMMIT
        Facet skeleton nodes and edges into internal ``_facet_graph`` (payload:
        ``node_type``, ``name``, ``class_ref``); ``_node_index`` / ``_class_index``
        populated. The interchange ``PyDiGraph`` ``_graph`` is filled from the builder
        output computed in phase 2b. After ``_built = True``, both graphs are read-only.

═══════════════════════════════════════════════════════════════════════════════
WHERE VALIDATION LIVES
═══════════════════════════════════════════════════════════════════════════════

Decorators validate arguments at import time. Coordinator phase 2 validates
global graph shape. Per-class invariants are enforced in intent modules / inspectors.

═══════════════════════════════════════════════════════════════════════════════
NODE AND KEY FORMAT
═══════════════════════════════════════════════════════════════════════════════

Node key: ``f"{node_type}:{node_name}"``. One Python class may have several
nodes (``meta``, ``resource_manager`` (``@meta`` on ``BaseResourceManager``), ``role_class``
(includes ``@role_mode`` ``mode`` via merge), ``aspect``,
``described_fields`` on schema classes, ``compensator``, …)
— see ``get_nodes_for_class``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE (EXPLICIT INSPECTOR REGISTRATION)
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.graph.graph_coordinator import GraphCoordinator
    from action_machine.intents.auth.role_class_inspector import RoleClassInspector
    from action_machine.intents.auth.role_intent_inspector import RoleIntentInspector
    from action_machine.intents.auth.role_mode_intent_inspector import (
        RoleModeIntentInspector,
    )

    coordinator = (
        GraphCoordinator()
        .register(RoleClassInspector)
        .register(RoleIntentInspector)
        .register(RoleModeIntentInspector)
        # ... other inspectors
        .build()
    )

In a typical app, use ``CoreActionMachine.create_coordinator()`` to obtain a
pre-registered and built coordinator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Build failures are surfaced as typed exceptions (payload, duplicate, graph shape, cycles).
- Graph payloads stored in ``rx.PyDiGraph`` are skeletal by design; rich facet metadata is reconstructed from snapshots.
- Coordinator build is single-shot and immutable after commit.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Transactional coordinator for facet graph assembly and typed snapshot cache.
CONTRACT: Register inspectors, execute explicit one-time build, and provide safe read APIs over committed metadata.
INVARIANTS: Build is atomic and immutable after commit; payload validation and graph integrity checks run before commit.
FLOW: register inspectors -> phase 1 collect/materialize -> phase 2 validate -> phase 3 commit -> read/hydrate APIs.
FAILURES: Raises typed graph/build exceptions and lifecycle guards for invalid state transitions.
EXTENSION POINTS: New inspectors can plug into build phases without changing coordinator public read contract.
AI-CORE-END
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import rustworkx as rx

from action_machine.dependencies.dependency_factory import DEPENDENCY_FACTORY_CACHE_KEY
from action_machine.dependencies.dependency_intent_inspector import DependencyIntentInspector
from action_machine.domain.application_context import ApplicationContext
from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.exceptions import (
    DuplicateNodeError,
    InvalidGraphError,
    PayloadValidationError,
)
from action_machine.graph.graph_builder import build_interchange_from_facet_payloads
from action_machine.graph.dag import assert_dag_edges_acyclic
from action_machine.graph.model import GraphEdge, GraphVertex
from action_machine.graph.payload import FacetPayload
from action_machine.model.base_action import BaseAction
from action_machine.model.exceptions import CyclicDependencyError


class GraphCoordinator:
    """
    Transactional interchange graph plus internal facet skeleton and typed facet snapshots.

    See the module docstring for ``build()`` phases and the public read API.
    Safe to share across the execution engine and adapters after ``build()``.

    AI-CORE-BEGIN
    ROLE: Runtime-safe metadata graph coordinator.
    CONTRACT: Own inspector registry, transactional build, snapshot cache, and hydrated read surface.
    INVARIANTS: No registration/build mutations after commit; all read APIs require built state.
    AI-CORE-END

    Attributes:
        _inspectors : list[type[BaseIntentInspector]]
            Registered inspectors, in registration order.

        _registered : set[type[BaseIntentInspector]]
            Set of registered inspectors (duplicate registration guard).

        _graph : rx.PyDiGraph
            Directed interchange graph (vertex ``id`` / ``vertex_type`` /
            ``stereotype``, edge ``edge_type`` / ``category`` / …). Filled at the end of
            ``build()``; read-only afterward via :meth:`get_graph`.

        _facet_graph : rx.PyDiGraph
            Internal **facet** skeleton (``node_type``, ``name``, ``class_ref``) used for
            ``get_node``, ``hydrate_graph_node``, and tools that need facet topology.
            Not returned by :meth:`get_graph`; copy via :meth:`facet_topology_copy`.

        _node_index : dict[str, int]
            Node key → **facet** graph index. Populated at commit.

        _class_index : dict[type, list[str]]
            Class → list of node keys emitted for that class. Populated at
            commit.

        _built : bool
            After True, ``register()`` and a second ``build()`` are forbidden.

        _facet_snapshots : dict[tuple[type, str], BaseFacetSnapshot]
            Typed facet snapshots keyed by ``(owner class, facet_key)`` where
            ``facet_key`` comes from ``facet_snapshot_storage_key()`` (e.g.
            ``"role"``, ``"role_class"``, ``"depends"``, …), filled
            when ``inspector.facet_snapshot_for_class()`` is non-``None``.

        _hydration_snapshot_key_by_graph_key : dict[str, str | tuple[str, ...]]
            Graph key ``node_type:node_name`` → snapshot storage key (or sorted tuple of
            distinct keys when several facets hydrate the same merged node). Filled during
            phase 1; cleared at each ``build()`` start.
    """

    def __init__(self) -> None:
        """Create a coordinator with empty interchange and internal facet graphs."""
        self._inspectors: list[type[BaseIntentInspector]] = []
        self._registered: set[type[BaseIntentInspector]] = set()
        self._graph: rx.PyDiGraph = rx.PyDiGraph()
        self._facet_graph: rx.PyDiGraph = rx.PyDiGraph()
        self._node_index: dict[str, int] = {}
        self._class_index: dict[type, list[str]] = {}
        self._built: bool = False
        self._facet_snapshots: dict[tuple[type, str], BaseFacetSnapshot] = {}
        self._hydration_snapshot_key_by_graph_key: dict[str, str | tuple[str, ...]] = {}

    def _require_built(self) -> None:
        """Fail-fast guard: coordinator must be explicitly built before reads."""
        if not self._built:
            raise RuntimeError(
                "GraphCoordinator is not built. Register inspectors and call build() first.",
            )

    def _require_not_built(self, operation: str) -> None:
        """Fail-fast guard: mutation APIs that are invalid after ``build()``."""
        if self._built:
            raise RuntimeError(
                f"Cannot {operation} after build(). "
                "The facet graph and snapshots are immutable once committed.",
            )

    # ═══════════════════════════════════════════════════════════════════
    # Fluent inspector registration
    # ═══════════════════════════════════════════════════════════════════

    def register(self, target: type) -> GraphCoordinator:
        """Register an intent inspector before ``build()``."""
        if not isinstance(target, type):
            raise TypeError(f"register() expects a type, got {type(target)!r}")
        if not issubclass(target, BaseIntentInspector):
            raise TypeError(
                f"register() accepts only BaseIntentInspector subclasses, got {target!r}",
            )
        return self._register_inspector(target)

    def _register_inspector(
        self,
        inspector_cls: type[BaseIntentInspector],
    ) -> GraphCoordinator:
        """
        Register an intent inspector before ``build()``.

        Supports fluent chaining::

            GraphCoordinator().register(RoleIntentInspector).build()
        """
        self._require_not_built(f"register {inspector_cls.__name__}")
        if inspector_cls in self._registered:
            raise ValueError(
                f"Inspector {inspector_cls.__name__} is already registered."
            )
        self._inspectors.append(inspector_cls)
        self._registered.add(inspector_cls)
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Graph build
    # ═══════════════════════════════════════════════════════════════════

    def build(self) -> GraphCoordinator:
        """
        Transactionally build the interchange graph, internal facet skeleton, and facet snapshot map.

        Invoked **explicitly** in a fluent chain (or via
        ``CoreActionMachine.create_coordinator()``). A second call after
        ``_built is True`` raises ``RuntimeError``.

        Three phases: collect payloads → validate → commit into internal facet
        ``rx.PyDiGraph`` plus interchange ``rx.PyDiGraph``.
        Any phase-2 failure means nothing from this build is committed. After facet
        validation succeeds, the interchange graph is built from facet payloads
        via :func:`~action_machine.graph.graph_builder.build_interchange_from_facet_payloads`;
        if its DAG slice (``DEPENDS_ON`` / ``CONNECTS_TO`` with ``is_dag=True``;
        entity relation interchange edges are excluded) is cyclic, ``build()`` raises
        ``CyclicDependencyError`` and
        nothing is committed.

        Returns:
            ``self`` (fluent).

        Raises:
            RuntimeError: second ``build()``.
            PayloadValidationError: Invalid facet payloads in phase 2.
            DuplicateNodeError: Duplicate graph keys in phase 2.
            InvalidGraphError: Structural graph validation failed in phase 2.
            CyclicDependencyError: Dependency cycle detected (wrapped from
                ``InvalidGraphError`` in ``_phase2_check_acyclicity``).
        """
        if self._built:
            raise RuntimeError(
                "build() already completed. The coordinator builds the graph once.",
            )

        self._facet_snapshots.clear()
        self._hydration_snapshot_key_by_graph_key.clear()
        self._facet_graph = rx.PyDiGraph()
        self._node_index.clear()
        self._class_index.clear()
        all_payloads, payload_sources = self._phase1_collect()
        all_payloads = self._materialize_edge_targets(all_payloads, payload_sources)
        self._phase2_check_payloads(all_payloads)
        self._phase2_check_key_uniqueness(all_payloads, payload_sources)
        self._phase2_check_referential_integrity(all_payloads)
        try:
            self._phase2_check_acyclicity(all_payloads)
        except InvalidGraphError as exc:
            raise CyclicDependencyError(str(exc)) from exc

        interchange_vertices, interchange_edges = build_interchange_from_facet_payloads(all_payloads)
        try:
            assert_dag_edges_acyclic(interchange_vertices, interchange_edges)
        except InvalidGraphError as exc:
            raise CyclicDependencyError(str(exc)) from exc

        self._phase3_commit(all_payloads)
        self._commit_interchange_graph(interchange_vertices, interchange_edges)

        self._built = True
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Phase 1 — Collect
    # ═══════════════════════════════════════════════════════════════════

    def _phase1_collect(
        self,
    ) -> tuple[list[FacetPayload], dict[str, str]]:
        """
        Run every inspector and collect ``FacetPayload`` instances.

        For each inspector: ``_subclasses_recursive()``, then ``inspect()`` per
        discovered class. Payloads that are ``None`` are skipped.

        Also records which inspector produced each payload for clearer phase-2
        error messages.

        Returns:
            A tuple of:
            - ``list[FacetPayload]`` — all collected payloads (after merge).
            - ``dict[str, str]`` — node key → inspector name(s), for
              ``DuplicateNodeError`` diagnostics.
        """
        by_key: dict[str, FacetPayload] = {}
        payload_sources: dict[str, str] = {}

        for inspector_cls in self._inspectors:
            inspector_name = inspector_cls.__name__
            subclasses = inspector_cls._subclasses_recursive()

            for target_cls in subclasses:
                produced = inspector_cls.inspect(target_cls)
                if produced is None:
                    continue
                if isinstance(produced, FacetPayload):
                    payloads_from_inspect: list[FacetPayload] = [produced]
                elif isinstance(produced, (list, tuple)):
                    payloads_from_inspect = [
                        p for p in produced if isinstance(p, FacetPayload)
                    ]
                    if not payloads_from_inspect:
                        continue
                else:
                    msg = (
                        f"{inspector_name}.inspect({target_cls!r}) must return "
                        f"FacetPayload | list[FacetPayload] | tuple[FacetPayload, ...] | None, "
                        f"got {type(produced)!r}"
                    )
                    raise TypeError(msg)

                snap = inspector_cls.facet_snapshot_for_class(target_cls)
                sk: str | None = None
                if snap is not None:
                    sk = inspector_cls.facet_snapshot_storage_key(
                        target_cls, payloads_from_inspect[0],
                    )
                    self._facet_snapshots[(target_cls, sk)] = snap

                for payload in payloads_from_inspect:
                    collect_key = self._facet_collect_key(payload)
                    if (
                        snap is not None
                        and sk is not None
                        and inspector_cls.should_register_facet_snapshot_for_payload(
                            target_cls, payload,
                        )
                    ):
                        self._register_hydration_snapshot_key(collect_key, sk)

                    incoming = self._normalize_payload_for_collect_key(payload, collect_key)

                    if collect_key not in by_key:
                        by_key[collect_key] = incoming
                        payload_sources[collect_key] = inspector_name
                        continue

                    merged = self._merge_facets_under_collect_key(
                        by_key[collect_key], incoming,
                    )
                    if merged is None:
                        raise DuplicateNodeError(
                            key=collect_key,
                            first_inspector=payload_sources[collect_key],
                            second_inspector=inspector_name,
                        )
                    by_key[collect_key] = merged
                    payload_sources[collect_key] = (
                        f"{payload_sources[collect_key]}+{inspector_name}"
                    )

        return list(by_key.values()), payload_sources

    def _materialize_edge_targets(
        self,
        payloads: list[FacetPayload],
        payload_sources: dict[str, str],
    ) -> list[FacetPayload]:
        """
        Ensure every edge target key exists when the edge carries ``target_class_ref``.

        Covers structural depends/connection stubs and informational belongs_to
        (domain classes are not otherwise visited by inspectors).

        Class dependency stubs (``@depends`` on a non-``BaseAction`` type) get
        informational ``belongs_to`` → ``application`` when the application
        vertex is present (see
        :meth:`DependencyIntentInspector.stub_outgoing_edges_for_class_dependency`).
        """
        keys = {self._make_key(p.node_type, p.node_name) for p in payloads}
        app_key = self._make_key(
            "application",
            BaseIntentInspector._make_node_name(ApplicationContext),
        )
        synthetic_source = "__edge_target__"
        result = list(payloads)
        changed = True
        while changed:
            changed = False
            extra: list[FacetPayload] = []
            for p in result:
                for edge in p.edges:
                    if edge.target_class_ref is None:
                        continue
                    tkey = self._make_key(edge.target_node_type, edge.target_name)
                    if tkey in keys:
                        continue
                    keys.add(tkey)
                    stub_edges: tuple = ()
                    if (
                        edge.edge_type == "depends"
                        and not issubclass(edge.target_class_ref, BaseAction)
                        and app_key in keys
                    ):
                        stub_edges = (
                            DependencyIntentInspector.stub_outgoing_edges_for_class_dependency()
                        )
                    extra.append(
                        FacetPayload(
                            node_type=edge.target_node_type,
                            node_name=edge.target_name,
                            node_class=edge.target_class_ref,
                            node_meta=(),
                            edges=stub_edges,
                        ),
                    )
                    if tkey not in payload_sources:
                        payload_sources[tkey] = synthetic_source
                    changed = True
            result.extend(extra)
        return result

    # ═══════════════════════════════════════════════════════════════════
    # Phase 2 — Validate
    # ═══════════════════════════════════════════════════════════════════

    def _phase2_check_payloads(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Validation 2a: required payload fields are non-empty.

        Each payload must have:
        - ``node_type`` — non-empty string.
        - ``node_name`` — non-empty string.
        - ``node_class`` — a ``type`` instance.

        Args:
            payloads: Payloads to validate.

        Raises:
            PayloadValidationError: if any required field is invalid.
        """
        for p in payloads:
            if not p.node_type:
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_type",
                    detail="empty string",
                )
            if not p.node_name:
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_name",
                    detail="empty string",
                )
            if not isinstance(p.node_class, type):
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_class",
                    detail=f"expected type, got {type(p.node_class).__name__}",
                )

    def _phase2_check_key_uniqueness(
        self,
        payloads: list[FacetPayload],
        payload_sources: dict[str, str],
    ) -> None:
        """
        Validation 2b: node-key uniqueness.

        Duplicates are normally resolved in ``_phase1_collect`` (merge or
        error). This method is a safety net when phase 2 is invoked directly in
        tests without going through the same bookkeeping.

        Args:
            payloads: Payloads to validate.
            payload_sources: Key → inspector name map.

        Raises:
            DuplicateNodeError: if a duplicate key remains.
        """
        seen: set[str] = set()
        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            if key in seen:
                raise DuplicateNodeError(
                    key=key,
                    first_inspector=payload_sources.get(key, "unknown"),
                    second_inspector="unknown",
                )
            seen.add(key)

    def _phase2_check_referential_integrity(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Validation 2c: referential integrity of edges.

        Every edge names its target via ``target_node_type:target_name``. That
        key must exist among collected payloads; otherwise the edge is broken.

        Args:
            payloads: Payloads to validate.

        Raises:
            InvalidGraphError: if an edge points at a missing node.
        """
        all_keys: set[str] = {
            self._make_key(p.node_type, p.node_name)
            for p in payloads
        }

        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            for edge in p.edges:
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                if target_key not in all_keys:
                    raise InvalidGraphError(
                        f"Edge '{edge.edge_type}' from '{source_key}' "
                        f"references missing node '{target_key}'. "
                        f"No inspector materialized the target class."
                    )

    def _phase2_check_acyclicity(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Validation 2d: acyclicity of structural edges.

        Builds a scratch graph with only structural edges (``is_structural is
        True``) and checks acyclicity via ``rustworkx.is_directed_acyclic_graph``.

        Informational edges (``is_structural is False``) are ignored — cyclic
        informational links are allowed.

        Args:
            payloads: Payloads to validate.

        Raises:
            InvalidGraphError: if structural edges form a cycle.
        """
        test_graph: rx.PyDiGraph = rx.PyDiGraph()
        test_index: dict[str, int] = {}

        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            idx = test_graph.add_node(key)
            test_index[key] = idx

        has_structural_edges = False
        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            source_idx = test_index[source_key]
            for edge in p.edges:
                if not edge.is_structural:
                    continue
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                target_idx = test_index[target_key]
                test_graph.add_edge(source_idx, target_idx, edge.edge_type)
                has_structural_edges = True

        if has_structural_edges and not rx.is_directed_acyclic_graph(test_graph):
            raise InvalidGraphError(
                "Structural edges (depends, connection) form a cycle. "
                "Review dependencies between classes."
            )

    # ═══════════════════════════════════════════════════════════════════
    # Phase 3 — Commit
    # ═══════════════════════════════════════════════════════════════════

    def _phase3_commit(self, payloads: list[FacetPayload]) -> None:
        """
        Commit all payloads into the graph.

        Runs only after phase 2 succeeds. Converts tuple-of-tuples metadata to
        dicts for graph storage. Populates ``_node_index`` and ``_class_index``.

        Args:
            payloads: Validated payloads.
        """
        # Add all nodes
        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            node_payload: dict[str, Any] = {
                "node_type": p.node_type,
                "name": p.node_name,
                "class_ref": p.node_class,
            }
            if p.node_meta:
                node_payload["committed_meta"] = dict(p.node_meta)
            idx = self._facet_graph.add_node(node_payload)
            self._node_index[key] = idx

            # Populate class_index
            if p.node_class not in self._class_index:
                self._class_index[p.node_class] = []
            self._class_index[p.node_class].append(key)

        # Add all edges
        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            source_idx = self._node_index[source_key]
            for edge in p.edges:
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                target_idx = self._node_index[target_key]
                self._facet_graph.add_edge(source_idx, target_idx, {
                    "edge_type": edge.edge_type,
                    "meta": dict(edge.edge_meta),
                })

    def _commit_interchange_graph(
        self,
        vertices: list[GraphVertex],
        edges: list[GraphEdge],
    ) -> None:
        """
        Populate ``_graph`` from interchange vertices and edges.

        Node payloads mirror :class:`~action_machine.graph.model.GraphVertex`
        fields; edge payloads mirror :class:`~action_machine.graph.model.GraphEdge`.
        """
        lg = rx.PyDiGraph()
        id_to_idx: dict[str, int] = {}
        for v in vertices:
            id_to_idx[v.id] = lg.add_node(
                {
                    "vertex_type": v.vertex_type,
                    "id": v.id,
                    "stereotype": v.stereotype,
                    "display_name": v.display_name,
                    "class_ref": v.class_ref,
                    "properties": v.properties,
                },
            )
        for e in edges:
            source_idx = id_to_idx[e.source_id]
            target_idx = id_to_idx[e.target_id]
            lg.add_edge(
                source_idx,
                target_idx,
                {
                    "edge_type": e.edge_type,
                    "stereotype": e.stereotype,
                    "category": e.category,
                    "is_dag": e.is_dag,
                    "attributes": e.attributes,
                },
            )
        self._graph = lg

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _action_collect_key_for_meta_on_primary_action(payload: FacetPayload) -> str | None:
        """
        When ``@meta`` targets the primary ``BaseAction`` host (same name as the
        structural action node), fold into ``action:<name>`` for collect/merge.
        """
        if payload.node_type != "meta":
            return None
        if not issubclass(payload.node_class, BaseAction):
            return None
        canonical = BaseIntentInspector._make_node_name(payload.node_class)
        primary_meta = BaseIntentInspector._make_host_dependent_node_name(
            payload.node_class, "meta",
        )
        if payload.node_name not in (canonical, primary_meta):
            return None
        return GraphCoordinator._make_key("action", canonical)

    def _facet_collect_key(self, payload: FacetPayload) -> str:
        folded = self._action_collect_key_for_meta_on_primary_action(payload)
        if folded is not None:
            return folded
        return self._make_key(payload.node_type, payload.node_name)

    @staticmethod
    def _normalize_payload_for_collect_key(
        payload: FacetPayload,
        collect_key: str,
    ) -> FacetPayload:
        fold = GraphCoordinator._action_collect_key_for_meta_on_primary_action(payload)
        if fold is not None and collect_key == fold:
            canonical = BaseIntentInspector._make_node_name(payload.node_class)
            return FacetPayload(
                node_type="action",
                node_name=canonical,
                node_class=payload.node_class,
                node_meta=payload.node_meta,
                edges=payload.edges,
            )
        return payload

    @staticmethod
    def _merge_facets_under_collect_key(
        first: FacetPayload,
        second: FacetPayload,
    ) -> FacetPayload | None:
        """
        Merge two payloads sharing the same collect key.

        Structural ``action`` rows (``@depends`` / ``@connection``) and a folded
        primary-host ``@meta`` facet normalize to ``node_type=\"action\"`` and merge
        here. Two ``role_class`` rows for the same role class (``RoleClassInspector``
        + ``RoleModeIntentInspector``) merge the same way. Two ``resource_manager``
        rows for the same manager class (``@meta`` + materialized stub from
        ``@connection``) merge here.
        Repeated ``application`` payloads from ``ApplicationContextInspector`` merge.
        ``domain`` stubs from edge materialization merge with full ``domain`` rows.

        Duplicate non-mergeable facets with the same collect key remain an error.
        """
        if first.node_class is not second.node_class or first.node_name != second.node_name:
            return None
        if first.node_type == "action" and second.node_type == "action":
            return FacetPayload(
                node_type="action",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "role_class" and second.node_type == "role_class":
            return FacetPayload(
                node_type="role_class",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "resource_manager" and second.node_type == "resource_manager":
            return FacetPayload(
                node_type="resource_manager",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "described_fields" and second.node_type == "described_fields":
            return FacetPayload(
                node_type="described_fields",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "params_schema" and second.node_type == "params_schema":
            return FacetPayload(
                node_type="params_schema",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "result_schema" and second.node_type == "result_schema":
            return FacetPayload(
                node_type="result_schema",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "sensitive_field" and second.node_type == "sensitive_field":
            return FacetPayload(
                node_type="sensitive_field",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "entity" and second.node_type == "entity":
            return FacetPayload(
                node_type="entity",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "application" and second.node_type == "application":
            return FacetPayload(
                node_type="application",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        if first.node_type == "domain" and second.node_type == "domain":
            return FacetPayload(
                node_type="domain",
                node_name=first.node_name,
                node_class=first.node_class,
                node_meta=first.node_meta + second.node_meta,
                edges=first.edges + second.edges,
            )
        return None

    def _register_hydration_snapshot_key(
        self,
        graph_key: str,
        storage_key: str,
    ) -> None:
        """
        Record which snapshot storage key(s) hydrate a graph node.

        Several inspectors may target the same merged node (e.g. ``depends``,
        ``connections``, ``meta`` on one ``action:<name>``); keys accumulate as a
        sorted tuple of distinct strings.
        """
        d = self._hydration_snapshot_key_by_graph_key
        existing = d.get(graph_key)
        if existing is None:
            d[graph_key] = storage_key
            return
        if existing == storage_key:
            return
        keys: set[str] = {storage_key}
        if isinstance(existing, str):
            keys.add(existing)
        else:
            keys.update(existing)
        if len(keys) == 1:
            d[graph_key] = next(iter(keys))
        else:
            d[graph_key] = tuple(sorted(keys))

    def hydrate_graph_node(self, node: Mapping[str, Any]) -> dict[str, Any]:
        """
        Return a node dict with ``meta`` filled from facet snapshots.

        Pass **facet** skeleton dicts (``node_type``, ``name``, ``class_ref``), e.g. from
        :meth:`facet_topology_copy` node payloads — not interchange :meth:`get_graph` payloads
        (those use ``vertex_type`` / ``id``).

        Resolves the snapshot storage key from phase-1 registration (or falls back to
        ``node_type`` for nodes that never registered a snapshot, except ``action``) and
        fills ``meta`` via ``to_facet_payload().node_meta``.

        Args:
            node: Raw payload from ``rx.PyDiGraph`` (or compatible mapping).

        Returns:
            Shallow copy of ``node`` plus ``meta`` (possibly empty).
        """
        self._require_built()
        raw = dict(node)
        nt = raw.get("node_type", "")
        nm = raw.get("name", "")
        cr = raw.get("class_ref")
        gk = self._make_key(nt, nm)
        meta: dict[str, Any] = {}
        committed = raw.pop("committed_meta", None)
        if isinstance(committed, dict):
            meta.update(committed)

        mapped = self._hydration_snapshot_key_by_graph_key.get(gk)
        storage_keys: tuple[str, ...] = ()
        if isinstance(mapped, str):
            storage_keys = (mapped,)
        elif isinstance(mapped, tuple):
            storage_keys = mapped

        if storage_keys and isinstance(cr, type):
            for sk in storage_keys:
                snap = self.get_snapshot(cr, sk)
                if snap is not None:
                    meta.update(dict(snap.to_facet_payload().node_meta))
        elif not storage_keys and nt != "action" and not meta:
            # Per-facet vertices (e.g. ``compensator:{host}:{method}``) carry row meta in
            # ``committed_meta``; do not replace with the class-level aggregate snapshot.
            sk_fallback = nt
            if isinstance(cr, type):
                snap = self.get_snapshot(cr, sk_fallback)
                if snap is not None:
                    meta = dict(snap.to_facet_payload().node_meta)
        raw["meta"] = meta
        return raw

    @staticmethod
    def _make_key(node_type: str, name: str) -> str:
        """
        Build the unique node key ``node_type:name``.

        Args:
            node_type: Facet type (``"role"``, ``"action"``, ``"entity"``, …).
            name: Node name (``"module.ClassName"``).

        Returns:
            Key string such as ``"role:module.CreateOrderAction"``.
        """
        return f"{node_type}:{name}"

    # ═══════════════════════════════════════════════════════════════════
    # Public properties
    # ═══════════════════════════════════════════════════════════════════

    @property
    def is_built(self) -> bool:
        """True after ``build()`` has completed."""
        return self._built

    def build_status(self) -> Literal["not_built", "built"]:
        """
        Explicit lifecycle label for logging and guards.

        Safe to call at any time; does not raise. Prefer this or ``is_built``
        when you need to branch before calling graph or snapshot APIs (those
        require a completed ``build()``).
        """
        return "built" if self._built else "not_built"

    @property
    def graph_node_count(self) -> int:
        """Number of nodes in the graph returned by :meth:`get_graph`. Requires ``build()``."""
        self._require_built()
        return self._graph.num_nodes()

    @property
    def graph_edge_count(self) -> int:
        """Number of edges in the graph returned by :meth:`get_graph`. Requires ``build()``."""
        self._require_built()
        return self._graph.num_edges()

    # ═══════════════════════════════════════════════════════════════════
    # Graph access — public API (domain-agnostic)
    # ═══════════════════════════════════════════════════════════════════

    def get_node(
        self,
        node_type_or_full_key: str,
        name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Return the node record.

        Call ``get_node("action", "pkg.MyAction")`` or pass the full key
        ``get_node("action:pkg.MyAction")`` — ``type:name``.
        """
        self._require_built()
        if name is not None:
            key = self._make_key(node_type_or_full_key, name)
        else:
            key = node_type_or_full_key
        idx = self._node_index.get(key)
        if idx is None:
            return None
        return self.hydrate_graph_node(self._facet_graph[idx])

    def get_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """
        Return every node of the given facet type.

        Args:
            node_type: Facet type to filter by.

        Returns:
            List of node dicts.
        """
        self._require_built()
        return [
            self.hydrate_graph_node(self._facet_graph[idx])
            for idx in self._facet_graph.node_indices()
            if self._facet_graph[idx].get("node_type") == node_type
        ]

    def get_nodes_for_class(self, cls: type) -> list[dict[str, Any]]:
        """
        Return all graph nodes emitted for ``cls``.

        One class may spawn multiple nodes from different inspectors (e.g.
        ``"role:..."``, ``"action:..."``, ``"aspect:..."``).

        Args:
            cls: Python class.

        Returns:
            List of node dicts; empty if the class produced no nodes.
        """
        self._require_built()
        keys = self._class_index.get(cls, [])
        result: list[dict[str, Any]] = []
        for key in keys:
            idx = self._node_index.get(key)
            if idx is not None:
                result.append(self.hydrate_graph_node(self._facet_graph[idx]))
        return result

    def get_graph(self) -> rx.PyDiGraph:
        """
        Return a **low-level** copy of the interchange graph (topology + payloads).

        Node payloads use ``vertex_type``, ``id``, ``stereotype``, ``display_name``,
        ``class_ref``, ``properties`` (no ``meta``). For facet skeleton dicts
        (``node_type``, ``name``, ``class_ref``), use :meth:`facet_topology_copy`.

        Returns:
            ``rx.PyDiGraph`` clone.
        """
        self._require_built()
        return self._graph.copy()

    def facet_topology_copy(self) -> rx.PyDiGraph:
        """Return a copy of the internal facet skeleton graph (``node_type``, ``name``, ``class_ref``)."""
        self._require_built()
        return self._facet_graph.copy()

    def get_graph_for_visualization(self) -> rx.PyDiGraph:
        """Return graph for diagram and file export tools (same interchange view as :meth:`get_graph`)."""
        return self.get_graph()

    # ═══════════════════════════════════════════════════════════════════
    # Facet snapshots (storage key is inspector-defined, e.g. "role", "depends")
    # ═══════════════════════════════════════════════════════════════════

    def get_snapshot(self, cls: type, facet_key: str) -> BaseFacetSnapshot | None:
        """
        Typed facet snapshot for owner class ``cls`` and storage key ``facet_key``.

        Populated during ``build()`` when the inspector returns a snapshot from
        ``facet_snapshot_for_class()``. The key may differ from graph
        ``node_type`` (e.g. ``depends`` / ``connections`` on merged ``action`` nodes).

        Args:
            cls: action, plugin, entity, or other registered class that owns the facet.
            facet_key: inspector storage key (e.g. ``"role"``, ``"aspect"``, ``"depends"``).

        Returns:
            Frozen snapshot dataclass for that facet, or ``None`` if no inspector
            produced a snapshot for this pair (optional facets, or class not in
            the inspector’s candidate set).

        Raises:
            RuntimeError: if ``build()`` has not completed (``_require_built``).
        """
        self._require_built()
        return self._facet_snapshots.get((cls, facet_key))

    # ═══════════════════════════════════════════════════════════════════
    # String representation
    # ═══════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """Compact debug representation."""
        state = "built" if self._built else "not built"
        inspector_names = ", ".join(i.__name__ for i in self._inspectors)
        if self._built:
            nodes = self._graph.num_nodes()
            edges = self._graph.num_edges()
        else:
            nodes = 0
            edges = 0
        fc = self.__dict__.get(DEPENDENCY_FACTORY_CACHE_KEY)
        n_factories = len(fc) if isinstance(fc, dict) else 0
        return (
            f"GraphCoordinator("
            f"state={state}, factories={n_factories}, "
            f"inspectors=[{inspector_names}], nodes={nodes}, edges={edges}"
            f")"
        )
