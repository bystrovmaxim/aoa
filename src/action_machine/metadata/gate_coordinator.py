# src/action_machine/metadata/gate_coordinator.py
"""
GateCoordinator — transactional facet graph and typed facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Registry for **static** metadata: registered **inspectors** (subclasses of
``BaseGateHostInspector``) discover gate-host markers on classes, emit
``FacetPayload`` nodes, and may attach typed per-class snapshots via
``facet_snapshot_for_class()`` / ``facet_snapshot_storage_key()``.

After a successful ``register(...).build()``:

1. **Facet graph** (``rx.PyDiGraph``) — committed nodes and edges from payloads.
   Used for traversal, MCP ``system://graph``, and structural cycle checks.

2. **Facet snapshot map** (``_facet_snapshots``) — optional typed views keyed by
   ``(owner class, facet storage key)``. Read via ``get_snapshot(cls, facet_key)``.

**Public API (domain-agnostic):** ``register``, ``build``, ``is_built``,
``graph_node_count``, ``graph_edge_count``, ``get_graph``, ``get_node``,
``get_nodes_by_type``, ``get_nodes_for_class``, ``get_snapshot``.

Dependency ``DependencyFactory`` instances may be cached on this object under
``dependency_factory.DEPENDENCY_FACTORY_CACHE_KEY``; clearing that cache does
not rebuild or invalidate the facet graph.

Applications may import from ``action_machine.core.gate_coordinator`` (thin
re-export); the canonical implementation is **this** module. Typical apps use
``CoreActionMachine.create_coordinator()`` for a pre-built coordinator.

═══════════════════════════════════════════════════════════════════════════════
EXPLICIT ``build()``
═══════════════════════════════════════════════════════════════════════════════

- Inspectors are registered with ``register(InspectorClass)`` **before**
  ``build()``; after ``build()``, further ``register()`` calls raise
  ``RuntimeError``.
- ``build()`` runs once; a second ``build()`` raises ``RuntimeError``.
- Until ``build()`` completes, graph accessors and ``get_snapshot`` call
  ``_require_built()`` and raise ``RuntimeError`` (there is no implicit lazy
  build from read APIs).

If the inspector list is empty at ``build()``, validation still runs with no
payloads (caller's responsibility to register a useful set).

═══════════════════════════════════════════════════════════════════════════════
TRANSACTIONAL ``build()`` — THREE PHASES
═══════════════════════════════════════════════════════════════════════════════

The graph is either built completely and consistently, or not committed at all.

    PHASE 1 — COLLECT
        For each inspector: walk ``_subclasses_recursive()`` over gate-host
        markers; ``inspect()`` → ``FacetPayload | None``.
        ``DependencyGateHostInspector`` and ``ConnectionGateHostInspector`` may
        emit the same node key ``action:<full name>`` for one action class;
        those payloads are **merged** into one node (edges concatenated) so
        keys stay unique without a combined "structure" inspector.

    PHASE 1b — MATERIALIZE
        ``_materialize_edge_targets`` adds missing nodes for edges that carry
        ``target_class_ref`` (stub ``dependency`` / ``connection`` /
        ``domain``), iterating to a fixed point until all targets exist.

    PHASE 2 — VALIDATE
        Payload fields, uniqueness of ``node_type:node_name`` keys, referential
        integrity, acyclicity of **structural** edges; @depends cycles surface
        as ``CyclicDependencyError``.

    PHASE 3 — COMMIT
        Nodes and edges into ``rx.PyDiGraph``; ``_node_index`` /
        ``_class_index`` populated; ``_built = True``. The graph is read-only
        afterward.

═══════════════════════════════════════════════════════════════════════════════
WHERE VALIDATION LIVES
═══════════════════════════════════════════════════════════════════════════════

Decorators validate arguments at import time. Coordinator phase 2 validates
global graph shape. Per-class invariants are enforced in gate hosts / inspectors.

═══════════════════════════════════════════════════════════════════════════════
NODE AND KEY FORMAT
═══════════════════════════════════════════════════════════════════════════════

Node key: ``f"{node_type}:{node_name}"``. One Python class may have several
nodes (``meta``, ``role``, ``aspect``, ``compensator``, …) — see
``get_nodes_for_class``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE (EXPLICIT INSPECTOR REGISTRATION)
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.metadata.gate_coordinator import GateCoordinator
    from action_machine.auth.role_gate_host_inspector import RoleGateHostInspector

    coordinator = (
        GateCoordinator()
        .register(RoleGateHostInspector)
        # ... other inspectors
        .build()
    )

In a typical app, use ``CoreActionMachine.create_coordinator()`` to obtain a
pre-registered and built coordinator.
"""

from __future__ import annotations

from typing import Any

import rustworkx as rx

from action_machine.core.exceptions import CyclicDependencyError
from action_machine.dependencies.dependency_factory import DEPENDENCY_FACTORY_CACHE_KEY
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.exceptions import (
    DuplicateNodeError,
    InvalidGraphError,
    PayloadValidationError,
)
from action_machine.metadata.payload import FacetPayload


class GateCoordinator:
    """
    Transactional facet graph plus typed facet snapshots.

    See the module docstring for ``build()`` phases and the public read API.
    Safe to share across the execution engine and adapters after ``build()``.

    Attributes:
        _inspectors : list[type[BaseGateHostInspector]]
            Registered inspectors, in registration order.

        _registered : set[type[BaseGateHostInspector]]
            Set of registered inspectors (duplicate registration guard).

        _graph : rx.PyDiGraph
            Directed system graph. Filled at commit (phase 3). Read-only after
            ``build()``.

        _node_index : dict[str, int]
            Node key → graph index. Populated at commit.

        _class_index : dict[type, list[str]]
            Class → list of node keys emitted for that class. Populated at
            commit.

        _built : bool
            After True, ``register()`` and a second ``build()`` are forbidden.

        _facet_snapshots : dict[tuple[type, str], BaseFacetSnapshot]
            Typed facet snapshots keyed by ``(owner class, facet_key)`` where
            ``facet_key`` comes from ``facet_snapshot_storage_key()`` (e.g.
            ``"role"``, ``"depends"``), filled when
            ``inspector.facet_snapshot_for_class()`` is non-``None``.
    """

    def __init__(self) -> None:
        """Create a coordinator with an empty graph."""
        self._inspectors: list[type[BaseGateHostInspector]] = []
        self._registered: set[type[BaseGateHostInspector]] = set()
        self._graph: rx.PyDiGraph = rx.PyDiGraph()
        self._node_index: dict[str, int] = {}
        self._class_index: dict[type, list[str]] = {}
        self._built: bool = False
        self._facet_snapshots: dict[tuple[type, str], BaseFacetSnapshot] = {}

    def _require_built(self) -> None:
        """Fail-fast guard: coordinator must be explicitly built before reads."""
        if not self._built:
            raise RuntimeError(
                "GateCoordinator is not built. Register inspectors and call build() first.",
            )

    # ═══════════════════════════════════════════════════════════════════
    # Fluent inspector registration
    # ═══════════════════════════════════════════════════════════════════

    def register(self, target: type) -> GateCoordinator:
        """Register a gate-host inspector before ``build()``."""
        if not isinstance(target, type):
            raise TypeError(f"register() expects a type, got {type(target)!r}")
        if not issubclass(target, BaseGateHostInspector):
            raise TypeError(
                f"register() accepts only BaseGateHostInspector subclasses, got {target!r}",
            )
        return self._register_inspector(target)

    def _register_inspector(
        self,
        inspector_cls: type[BaseGateHostInspector],
    ) -> GateCoordinator:
        """
        Register a gate-host inspector before ``build()``.

        Supports fluent chaining::

            GateCoordinator().register(RoleGateHostInspector).build()
        """
        if self._built:
            raise RuntimeError(
                f"Cannot register {inspector_cls.__name__} after build(). "
                f"All inspectors must be registered before build()."
            )
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

    def build(self) -> GateCoordinator:
        """
        Transactionally build the facet graph and facet snapshot map.

        Invoked **explicitly** in a fluent chain (or via
        ``CoreActionMachine.create_coordinator()``). A second call after
        ``_built is True`` raises ``RuntimeError``.

        Three phases: collect payloads → validate → commit into ``rx.PyDiGraph``.
        Any phase-2 failure means nothing from this build is committed.

        Returns:
            ``self`` (fluent).

        Raises:
            RuntimeError: second ``build()``.
            PayloadValidationError, DuplicateNodeError, InvalidGraphError,
            CyclicDependencyError — see phase 2 and the @depends cycle wrapper.
        """
        if self._built:
            raise RuntimeError(
                "build() already completed. The coordinator builds the graph once."
            )

        self._facet_snapshots.clear()
        all_payloads, payload_sources = self._phase1_collect()
        all_payloads = self._materialize_edge_targets(all_payloads, payload_sources)
        self._phase2_check_payloads(all_payloads)
        self._phase2_check_key_uniqueness(all_payloads, payload_sources)
        self._phase2_check_referential_integrity(all_payloads)
        try:
            self._phase2_check_acyclicity(all_payloads)
        except InvalidGraphError as exc:
            raise CyclicDependencyError(str(exc)) from exc
        self._phase3_commit(all_payloads)

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
                payload = inspector_cls.inspect(target_cls)
                if payload is None:
                    continue

                snap = inspector_cls.facet_snapshot_for_class(target_cls)
                if snap is not None:
                    sk = inspector_cls.facet_snapshot_storage_key(target_cls, payload)
                    self._facet_snapshots[(target_cls, sk)] = snap

                key = self._make_key(payload.node_type, payload.node_name)

                if key not in by_key:
                    by_key[key] = payload
                    payload_sources[key] = inspector_name
                    continue

                merged = self._merge_facets_same_action_node(by_key[key], payload)
                if merged is None:
                    raise DuplicateNodeError(
                        key=key,
                        first_gate_host=payload_sources[key],
                        second_gate_host=inspector_name,
                    )
                by_key[key] = merged
                payload_sources[key] = f"{payload_sources[key]}+{inspector_name}"

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
        """
        keys = {self._make_key(p.node_type, p.node_name) for p in payloads}
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
                    extra.append(
                        FacetPayload(
                            node_type=edge.target_node_type,
                            node_name=edge.target_name,
                            node_class=edge.target_class_ref,
                            node_meta=(),
                            edges=(),
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
                    first_gate_host=payload_sources.get(key, "unknown"),
                    second_gate_host="unknown",
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
            idx = self._graph.add_node({
                "node_type": p.node_type,
                "name": p.node_name,
                "class_ref": p.node_class,
                "meta": dict(p.node_meta),
            })
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
                self._graph.add_edge(source_idx, target_idx, {
                    "edge_type": edge.edge_type,
                    "meta": dict(edge.edge_meta),
                })

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _merge_facets_same_action_node(
        first: FacetPayload,
        second: FacetPayload,
    ) -> FacetPayload | None:
        """
        Merge two payloads with the same ``action:<name>`` key when both describe
        the same action class and carry identical ``node_meta``.

        Used for ``DependencyGateHostInspector`` + ``ConnectionGateHostInspector``.
        Any other key collision must remain a ``DuplicateNodeError``.
        """
        if first.node_type != "action" or second.node_type != "action":
            return None
        if first.node_name != second.node_name or first.node_class is not second.node_class:
            return None
        if first.node_meta != second.node_meta:
            return None
        return FacetPayload(
            node_type=first.node_type,
            node_name=first.node_name,
            node_class=first.node_class,
            node_meta=first.node_meta,
            edges=first.edges + second.edges,
        )

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

    @property
    def graph_node_count(self) -> int:
        """Number of nodes (0 before the first build / lazy build)."""
        if not self._built:
            return 0
        return self._graph.num_nodes()

    @property
    def graph_edge_count(self) -> int:
        """Number of edges (0 before the first build / lazy build)."""
        if not self._built:
            return 0
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
        return dict(self._graph[idx])

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
            dict(self._graph[idx])
            for idx in self._graph.node_indices()
            if self._graph[idx].get("node_type") == node_type
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
                result.append(dict(self._graph[idx]))
        return result

    def get_graph(self) -> rx.PyDiGraph:
        """
        Return a copy of the graph.

        Copying prevents external code from mutating the coordinator's graph.

        Returns:
            ``rx.PyDiGraph`` clone.
        """
        self._require_built()
        return self._graph.copy()

    # ═══════════════════════════════════════════════════════════════════
    # Facet snapshots (storage key is inspector-defined, e.g. "role", "depends")
    # ═══════════════════════════════════════════════════════════════════

    def get_snapshot(self, cls: type, facet_key: str) -> BaseFacetSnapshot | None:
        """
        Typed facet snapshot for owner class ``cls`` and storage key ``facet_key``.

        Populated during ``build()`` when the inspector returns a snapshot from
        ``facet_snapshot_for_class()``. The key may differ from graph
        ``node_type`` (e.g. ``depends`` / ``connections`` on merged ``action`` nodes).
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
        nodes = self._graph.num_nodes() if self._built else 0
        edges = self._graph.num_edges() if self._built else 0
        fc = self.__dict__.get(DEPENDENCY_FACTORY_CACHE_KEY)
        n_factories = len(fc) if isinstance(fc, dict) else 0
        return (
            f"GateCoordinator("
            f"state={state}, factories={n_factories}, "
            f"inspectors=[{inspector_names}], nodes={nodes}, edges={edges}"
            f")"
        )
