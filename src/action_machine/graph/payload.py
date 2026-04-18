# src/action_machine/graph/payload.py
"""
Transport objects between inspectors and ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module defines two frozen dataclasses — the contract between
**inspectors** (``BaseIntentInspector``) and ``GraphCoordinator``:

1. ``EdgeInfo`` — one outgoing edge from a node.
2. ``FacetPayload`` — one graph node plus all of its outgoing edges.

Both are transport-only: an inspector builds them in ``_build_payload()`` /
``inspect()``, the coordinator consumes them in phase 1 of ``build()``, and
they are discarded after commit. Facet node skeletons land in the coordinator’s
internal facet ``rx.PyDiGraph``; the public interchange graph is a separate commit.
Tuple → dict conversion for facet ``meta`` is applied when projecting from
typed snapshots (see ``GraphCoordinator.hydrate_graph_node``).

═══════════════════════════════════════════════════════════════════════════════
IMMUTABILITY
═══════════════════════════════════════════════════════════════════════════════

Both dataclasses are ``frozen=True``. That prevents accidental mutation of data
collected by an inspector between coordinator phases (collect → validate →
commit).

``node_meta`` and ``edge_meta`` use ``tuple[tuple[str, Any], ...]`` instead of
``dict[str, Any]`` because a frozen dataclass should be hashable and dicts are
not. Tuple-of-tuples is immutable and hashable; the coordinator turns it into a
dict once during commit.

═══════════════════════════════════════════════════════════════════════════════
TWO EDGE CLASSES
═══════════════════════════════════════════════════════════════════════════════

Edges are split by ``is_structural``:

    is_structural=True  — structural edges (depends, connection).
        Define the system skeleton. Cycles are forbidden. The coordinator
        checks acyclicity in phase 2 using a scratch graph. A cycle raises
        ``InvalidGraphError``.

    is_structural=False — informational edges (e.g. ``belongs_to`` a domain,
        ``has_aspect`` in some scenarios, etc., depending on the inspector).
        They carry visualization semantics. Cycles are not forbidden as they
        are for structural edges. Each inspector chooses ``edge_type`` values;
        some details (context keys, compensator internals) deliberately stay
        in runtime metadata rather than in edges.

═══════════════════════════════════════════════════════════════════════════════
NODE KEY FORMAT
═══════════════════════════════════════════════════════════════════════════════

Every graph node has a string key ``"type:name"``. The inspector supplies only
the name (``node_name``) via ``_make_node_name()``; the coordinator builds the
full ``node_type:node_name`` key.

    node_type = "Action",  node_name = "module.CreateOrderAction"
    → graph key: "Action:module.CreateOrderAction"

    node_type = "role_class", node_name = "module.AdminRole"
    → graph key: "role_class:module.AdminRole"

One class may emit several nodes with different ``node_type`` values from
different inspectors (``meta``, ``aspect``, ``role_class``, …; structural ``Action``
appears when ``@depends`` and/or ``@connection`` is present — two inspectors,
merged by the coordinator into one node with the same key). Uniqueness follows
from the pair ``node_type`` + ``node_name``.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    # Illustrative: AdminRole is a BaseRole subtype; CreateOrderAction is any action class.

    # 1. Inspector creates a payload in _build_payload():
    # ``edges`` carry informational ``requires_role`` targets (``role_class`` rows).
    payload = FacetPayload(
        node_type="Action",
        node_name="module.CreateOrderAction",
        node_class=CreateOrderAction,
        node_meta=(("spec", AdminRole),),
        edges=(),
    )

    # 2. Coordinator gathers every payload in phase 1 (collect).

    # 3. Coordinator validates payloads in phase 2:
    #    - node_type and node_name non-empty
    #    - node_class is a type
    #    - keys unique
    #    - edge targets exist
    #    - structural edges acyclic

    # 4. Coordinator commits in phase 3: facet skeleton into internal ``_facet_graph``,
    #    then interchange projection into ``_graph``. Node payload is skeleton only
    #    (``node_type``, ``name``, ``class_ref`` on the facet graph).
    #    Facet body is in ``GraphCoordinator`` facet snapshots; ``get_node`` /
    #    ``hydrate_graph_node`` attach ``meta`` from the matching snapshot.

    # 5. Payload objects are discarded. Committed graphs are the source of truth.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``EdgeInfo`` and ``FacetPayload`` are frozen transport objects.
- ``node_meta`` / ``edge_meta`` use tuple-of-tuples for immutable/hashable transport shape.
- Payload validation and graph integrity are enforced by coordinator build phases.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module defines data contracts only; it does not validate graph integrity directly.
- Metadata values may contain runtime classes/callables and are not guaranteed to be JSON-serializable as-is.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Transport contract between inspectors and coordinator.
CONTRACT: Carry immutable node/edge payloads through collect/validate/commit build phases.
INVARIANTS: Frozen dataclasses, deterministic key shape, structural-edge flag for acyclicity policy.
FLOW: inspector emits payload -> coordinator validates -> coordinator commits facet skeleton + interchange graph + cached snapshots.
FAILURES: Invalid payload shape/integrity errors are raised by coordinator validators.
EXTENSION POINTS: New facet/edge kinds can be added by extending node_type/edge_type conventions.
AI-CORE-END
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
            Target facet type (``"Action"``, ``"entity"``, ``"domain"``, …).
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


@dataclass(frozen=True)
class FacetPayload:
    """
    One graph node with all of its outgoing edges.

    Built by an inspector in ``_build_payload()`` (or ``inspect()``). One call
    → one ``FacetPayload`` (or ``None`` if the class does not match). The
    coordinator collects everything in phase 1, validates in phase 2, commits in
    phase 3.

    A single class may emit several payloads from different inspectors. For
    example, ``CreateOrderAction`` may yield:
    - ``FacetPayload(node_type="Action", ...)`` with ``requires_role`` edges from ``RoleIntentInspector``
    - ``FacetPayload(node_type="role_class", ...)`` from ``RoleClassInspector`` (name, description, …)
    - Another ``FacetPayload(node_type="role_class", ...)`` from ``RoleModeIntentInspector``
      (canonical class name; ``node_meta`` carries ``mode``) merged with the row above
    - One merged ``FacetPayload(node_type="Action", ...)`` with depends and/or
      connection edges (two inspectors → merged in ``GraphCoordinator._phase1_collect``)
    - ``FacetPayload(node_type="RegularAspect", ...)`` / ``"SummaryAspect"`` from ``AspectIntentInspector``
      (per method)

    After merging structural ``Action`` facets, uniqueness is still
    ``node_type`` + ``node_name``.

    Attributes:
        node_type : str
            Facet type: ``"Action"``, ``"role_class"``, ``"RegularAspect"``, ``"SummaryAspect"``, ``"Checker"``,
            ``"entity"``, ``"domain"``,
            ``"dependency"``, ``"connection"``, ``"error_handler"``,
            ``"Compensator"``, ``"subscription"``, ``"sensitive_field"``,
            ``"context_field"``, ``"entity_field"``, ``"entity_relation"``,
            ``"entity_lifecycle"``.

        node_name : str
            Name without the type prefix. Format ``"module.ClassName"`` or
            ``"module.ClassName.suffix"``, from ``_make_node_name()``; the
            coordinator forms ``"node_type:node_name"``.

        node_class : type
            Python class that owns this node; stored in the graph and used for
            runtime lookups.

        node_meta : tuple[tuple[str, Any], ...]
            Node-specific metadata as ``(key, value)`` pairs; becomes a dict at
            commit. Examples:
            - Role: ``(("spec", AdminRole),)`` (``AdminRole`` — подкласс ``BaseRole``)
            - Repeated rows: e.g. ``("items", (row, ...))`` where each ``row`` is
              ``tuple[tuple[str, Any], ...]`` (same shape as ``_make_meta``), so
              consumers use keys instead of positional unpacking.
            - Entity: ``(("description", "Order"), ("domain", "shop"), ...)``
            Defaults to empty tuple.

        edges : tuple[EdgeInfo, ...]
            Outgoing edges. Facets without graph edges (e.g. bare role nodes) use
            an empty tuple. Defaults to empty tuple.

    AI-CORE-BEGIN
    ROLE: Immutable node+edges transport envelope.
    CONTRACT: Represent one facet node emitted by an inspector for coordinator build phases.
    INVARIANTS: Node identity is ``node_type`` + ``node_name``; edges are attached as immutable tuples.
    AI-CORE-END
    """

    node_type: str
    node_name: str
    node_class: type
    node_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    edges: tuple[EdgeInfo, ...] = field(default_factory=tuple)
