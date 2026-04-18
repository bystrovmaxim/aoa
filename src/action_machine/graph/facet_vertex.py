# src/action_machine/graph/facet_vertex.py
"""
Facet-layer node + outgoing edges (:class:`FacetVertex`), collected before interchange.

Pairs with :class:`~action_machine.graph.graph_vertex.GraphVertex` after commit.
Outgoing edges use :class:`~action_machine.graph.facet_edge.FacetEdge`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from action_machine.graph.facet_edge import FacetEdge


@dataclass(frozen=True)
class FacetVertex:
    """
    One graph node with all of its outgoing edges.

    Built by an inspector in ``_build_payload()`` (or ``inspect()``). One call
    → one ``FacetVertex`` (or ``None`` if the class does not match). The
    coordinator collects everything in phase 1, validates in phase 2, commits in
    phase 3.

    A single class may emit several vertices from different inspectors. For
    example, ``CreateOrderAction`` may yield:
    - ``FacetVertex(node_type="Action", ...)`` with ``requires_role`` edges from ``RoleIntentInspector``
    - ``FacetVertex(node_type="role_class", ...)`` from ``RoleClassInspector`` (name, description, …)
    - Another ``FacetVertex(node_type="role_class", ...)`` from ``RoleModeIntentInspector``
      (canonical class name; ``node_meta`` carries ``mode``) merged with the row above
    - One merged ``FacetVertex(node_type="Action", ...)`` with depends and/or
      connection edges (two inspectors → merged in ``GraphCoordinator._phase1_collect``)
    - ``FacetVertex(node_type="RegularAspect", ...)`` / ``"SummaryAspect"`` from ``AspectIntentInspector``
      (per method)

    After merging structural ``Action`` facets, uniqueness is still
    ``node_type`` + ``node_name``.

    Attributes:
        node_type : str
            Facet type: ``"Action"``, ``"role_class"``, ``"RegularAspect"``, ``"SummaryAspect"``, ``"Checker"``,
            ``"Entity"``, ``"Domain"``,
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

        edges : tuple[FacetEdge, ...]
            Outgoing edges. Facets without graph edges (e.g. bare role nodes) use
            an empty tuple. Defaults to empty tuple.

        merge_group_key : str | None
            If set, the full collect key ``"type:name"`` used to bucket this vertex
            with others for merge (inspectors own the string; the coordinator does
            not interpret facet kinds).

        merge_node_type / merge_node_name : str | None
            When ``merge_group_key`` matches the active collect key, the coordinator
            normalizes the vertex to this ``node_type`` / ``node_name`` before merge.

        skip_node_type_snapshot_fallback : bool
            When true, :meth:`GraphCoordinator.hydrate_graph_node` will not use the
            node's ``node_type`` string as a snapshot storage key fallback.

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
    edges: tuple[FacetEdge, ...] = field(default_factory=tuple)
    merge_group_key: str | None = None
    merge_node_type: str | None = None
    merge_node_name: str | None = None
    skip_node_type_snapshot_fallback: bool = False
