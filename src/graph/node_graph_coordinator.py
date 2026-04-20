# src/graph/node_graph_coordinator.py
"""
NodeGraphCoordinator — transactional assembly of interchange ``*Node`` graphs in ``rustworkx``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collects :class:`~graph.base_graph_node.BaseGraphNode` instances from
registered :class:`~graph.base_intent_inspector.BaseIntentInspector`
**instances** (each must implement :meth:`~graph.base_intent_inspector.BaseIntentInspector.get_graph_nodes`),
validates **unique**
:attr:`~graph.base_graph_node.BaseGraphNode.id` keys, **referential
integrity** of :class:`~graph.base_graph_edge.BaseGraphEdge.target_id`,
and **acyclicity** of edges marked ``is_dag=True``, then materializes a
``rustworkx.PyDiGraph`` in memory for the duration of the build step (no retained
read API — construction only).

This coordinator is **domain-agnostic**: it does not interpret ``node_type`` or
``link_name`` beyond validation and DAG checks.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors: Sequence[BaseIntentInspector]  (instances)
              │
              v
    for each: inspector.get_graph_nodes()  ->  flat list of (node, inspector_label)
              │
              v
    dict[id -> BaseGraphNode] with unique ids
              │
              ├─ duplicate id  -> DuplicateNodeError
              ├─ missing target_id  -> InvalidGraphError
              ├─ is_dag cycle  -> InvalidGraphError
              v
    build rustworkx PyDiGraph (local), then discard

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    coord = NodeGraphCoordinator()
    coord.build([adapter])

Edge case: empty inspector list completes without error.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Interchange-node graph coordinator (parallel to facet ``GraphCoordinator``).
CONTRACT: ``build(inspectors)`` with ``BaseIntentInspector`` instances; graph construction only.
INVARIANTS: Built-once; DAG slice uses ``is_dag``; no graph read surface.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import rustworkx as rx

from graph.base_graph_node import BaseGraphNode
from graph.base_inspector import BaseInspector
from graph.exceptions import DuplicateNodeError, InvalidGraphError


class NodeGraphCoordinator:
    """
    AI-CORE-BEGIN
    ROLE: Build rustworkx graph from ``BaseGraphNode`` contributions.
    CONTRACT: ``build`` with ``BaseIntentInspector`` instances; each ``get_graph_nodes()``;
        construction-only, no graph accessors.
    INVARIANTS: Duplicate id / missing target / DAG cycle raise during build.
    AI-CORE-END
    """

    __slots__ = ("_built",)

    def __init__(self) -> None:
        self._built: bool = False

    def build(self, inspectors: Sequence[BaseInspector]) -> None:
        """
        Collect nodes from each inspector instance via :meth:`BaseIntentInspector.get_graph_nodes`,
        validate, and construct the ``rustworkx`` graph (not exposed).

        Raises:
            DuplicateNodeError: two sources contributed the same ``node.id``.
            InvalidGraphError: missing ``target_id`` or a cycle among ``is_dag`` edges.
            NotImplementedError: an inspector inherits the default ``get_graph_nodes`` stub.
            RuntimeError: if :meth:`build` was already called on this instance.
        """
        if self._built:
            msg = "NodeGraphCoordinator.build() was already called on this instance."
            raise RuntimeError(msg)
        flat = self._gather_all_nodes(inspectors)
        nodes = self._map_unique_node_ids(flat)
        self._validate_referential_integrity(nodes)
        self._validate_dag_acyclicity(nodes)
        self._materialize_rustworkx_graph(nodes)
        self._built = True

    def _inspector_label(self, inspector: BaseInspector) -> str:
        return type(inspector).__qualname__

    def _gather_all_nodes(
        self,
        inspectors: Sequence[BaseInspector],
    ) -> list[tuple[BaseGraphNode[Any], str]]:
        """
        Concatenate ``get_graph_nodes()`` from every inspector in order.

        Each entry is ``(node, inspector_qualname)`` so a later merge step can report
        :class:`~graph.exceptions.DuplicateNodeError` with both sources.
        """
        out: list[tuple[BaseGraphNode[Any], str]] = []
        for insp in inspectors:
            label = self._inspector_label(insp)
            for node in insp.get_graph_nodes():
                out.append((node, label))
        return out

    def _map_unique_node_ids(
        self,
        flat: list[tuple[BaseGraphNode[Any], str]],
    ) -> dict[str, BaseGraphNode[Any]]:
        """
        Build ``id -> node`` and ensure each :attr:`~graph.base_graph_node.BaseGraphNode.id`
        appears at most once.
        """
        nodes: dict[str, BaseGraphNode[Any]] = {}
        owners: dict[str, str] = {}
        for node, label in flat:
            nid = node.id
            if nid in nodes:
                raise DuplicateNodeError(
                    key=nid,
                    first_inspector=owners[nid],
                    second_inspector=label,
                )
            nodes[nid] = node
            owners[nid] = label
        return nodes

    def _validate_referential_integrity(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        ids = set(nodes.keys())
        for source_id, node in nodes.items():
            for edge in node.edges:
                if edge.target_id not in ids:
                    raise InvalidGraphError(
                        f"Link {edge.link_name!r} from {source_id!r} references "
                        f"missing target_id {edge.target_id!r}.",
                    )

    def _validate_dag_acyclicity(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        ids = sorted(nodes.keys())
        if not ids:
            return
        g = rx.PyDiGraph()
        idx = {nid: g.add_node(nid) for nid in ids}
        has_dag = False
        for source_id, node in nodes.items():
            for edge in node.edges:
                if not edge.is_dag:
                    continue
                has_dag = True
                g.add_edge(idx[source_id], idx[edge.target_id], edge.link_name)
        if has_dag and not rx.is_directed_acyclic_graph(g):
            raise InvalidGraphError(
                "Edges with is_dag=True form a directed cycle. "
                "Review interchange link wiring.",
            )

    def _materialize_rustworkx_graph(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        """Build ``PyDiGraph`` to ensure rustworkx accepts the topology; graph is not stored."""
        g = rx.PyDiGraph()
        id_to_idx: dict[str, int] = {}
        for nid in sorted(nodes.keys()):
            id_to_idx[nid] = g.add_node(nodes[nid])
        for source_id, node in nodes.items():
            sidx = id_to_idx[source_id]
            for edge in node.edges:
                tidx = id_to_idx[edge.target_id]
                g.add_edge(sidx, tidx, edge)
