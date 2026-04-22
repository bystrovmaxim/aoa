# src/graph/node_graph_coordinator.py
"""
NodeGraphCoordinator — transactional assembly of interchange ``*Node`` graphs in ``rustworkx``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collects :class:`~graph.base_graph_node.BaseGraphNode` instances from
registered :class:`~graph.base_graph_node_inspector.BaseGraphNodeInspector`
**instances** (each implements :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`),
validates **unique**
:attr:`~graph.base_graph_node.BaseGraphNode.node_id` keys, **referential
integrity** of :class:`~graph.base_graph_edge.BaseGraphEdge.target_node_id`,
and **acyclicity** of edges marked ``is_dag=True``, then materializes and **retains**
a ``rustworkx.PyDiGraph`` whose node weights are :class:`~graph.base_graph_node.BaseGraphNode`
instances and edge weights are :class:`~graph.base_graph_edge.BaseGraphEdge` instances.
Read it via :attr:`NodeGraphCoordinator.rx_graph` after a successful :meth:`build`,
or list interchange nodes without touching rustworkx via :meth:`get_all_nodes`.

This coordinator is **domain-agnostic**: it does not interpret ``node_type`` or
``edge_name`` beyond validation and DAG checks. It does **not** recurse into
:attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes`; each inspector's
:meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes` must already
include every ``node_id`` referenced by emitted edges (flatten companions there).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors: Sequence[BaseGraphNodeInspector[Any]]  (instances)
              │
              v
    for each: inspector.get_graph_nodes()  ->  flat list of (node, inspector_label)
              │
              v
    dict[node_id -> BaseGraphNode] with unique ids
              │
              ├─ duplicate id  -> DuplicateNodeError
              ├─ missing target_node_id  -> InvalidGraphError
              ├─ is_dag cycle  -> InvalidGraphError
              v
    build rustworkx ``PyDiGraph``  ->  :attr:`NodeGraphCoordinator.rx_graph` / :meth:`get_all_nodes`

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    coord = NodeGraphCoordinator()
    coord.build([adapter])

Edge case: empty inspector list completes without error.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import rustworkx as rx

from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.exceptions import DuplicateNodeError, InvalidGraphError


class NodeGraphCoordinator:
    """
    AI-CORE-BEGIN
    ROLE: Build rustworkx graph from ``BaseGraphNode`` contributions.
    CONTRACT: ``build`` with :class:`~graph.base_graph_node_inspector.BaseGraphNodeInspector` instances; each ``get_graph_nodes()``;
        then expose the assembled ``PyDiGraph`` as :attr:`rx_graph` and interchange nodes via :meth:`get_all_nodes`.
    INVARIANTS: Duplicate id / missing target / DAG cycle raise during build; :attr:`rx_graph` / :meth:`get_all_nodes` unavailable until ``build`` succeeds.
    AI-CORE-END
    """

    __slots__ = ("_built", "_rx_graph")

    def __init__(self) -> None:
        self._built: bool = False
        self._rx_graph: rx.PyDiGraph | None = None

    def build(self, inspectors: Sequence[BaseGraphNodeInspector[Any]]) -> None:
        """
        Collect nodes from each inspector instance via :meth:`BaseGraphNodeInspector.get_graph_nodes`,
        validate, construct the ``rustworkx`` graph, and store it on :attr:`rx_graph`.

        Raises:
            DuplicateNodeError: two sources contributed the same ``node.node_id``.
            InvalidGraphError: missing ``target_node_id`` or a cycle among ``is_dag`` edges.
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

    @property
    def rx_graph(self) -> rx.PyDiGraph:
        """
        The interchange graph built by the last successful :meth:`build`.

        Node weights are :class:`~graph.base_graph_node.BaseGraphNode` payloads (same order as sorted ``node_id``).
        Edge weights are :class:`~graph.base_graph_edge.BaseGraphEdge` instances.

        Raises:
            RuntimeError: :meth:`build` has not completed successfully on this coordinator.
        """
        if not self._built or self._rx_graph is None:
            msg = "NodeGraphCoordinator.rx_graph is only available after a successful build()."
            raise RuntimeError(msg)
        return self._rx_graph

    def get_all_nodes(self) -> tuple[BaseGraphNode[Any], ...]:
        """
        Return every :class:`~graph.base_graph_node.BaseGraphNode` in graph vertex order.

        Vertex weights are the same instances contributed during :meth:`build` (no copies).
        Order follows ``rustworkx`` node index order, which matches ascending ``node_id`` from
        :meth:`_materialize_rustworkx_graph` (sorted keys at construction).

        Raises:
            RuntimeError: :meth:`build` has not completed successfully on this coordinator.
        """
        return tuple(self.rx_graph.nodes())

    def _inspector_label(self, inspector: BaseGraphNodeInspector[Any]) -> str:
        return type(inspector).__qualname__

    def _gather_all_nodes(
        self,
        inspectors: Sequence[BaseGraphNodeInspector[Any]],
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
        Build ``node_id -> node`` and ensure each :attr:`~graph.base_graph_node.BaseGraphNode.node_id`
        appears at most once.
        """
        nodes: dict[str, BaseGraphNode[Any]] = {}
        owners: dict[str, str] = {}
        for node, label in flat:
            nid = node.node_id
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
                if edge.target_node_id not in ids:
                    raise InvalidGraphError(
                        f"Edge {edge.edge_name!r} from {source_id!r} references "
                        f"missing target_node_id {edge.target_node_id!r}.",
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
                g.add_edge(idx[source_id], idx[edge.target_node_id], edge.edge_name)
        if has_dag and not rx.is_directed_acyclic_graph(g):
            raise InvalidGraphError(
                "Edges with is_dag=True form a directed cycle. "
                "Review interchange link wiring.",
            )

    def _materialize_rustworkx_graph(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        """Build ``PyDiGraph`` with ``BaseGraphNode`` / ``BaseGraphEdge`` weights; assign :attr:`_rx_graph`."""
        g = rx.PyDiGraph()
        id_to_idx: dict[str, int] = {}
        for nid in sorted(nodes.keys()):
            id_to_idx[nid] = g.add_node(nodes[nid])
        for source_id, node in nodes.items():
            sidx = id_to_idx[source_id]
            for edge in node.edges:
                tidx = id_to_idx[edge.target_node_id]
                g.add_edge(sidx, tidx, edge)
        self._rx_graph = g
