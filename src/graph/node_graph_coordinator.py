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
``edge_name`` beyond validation and DAG checks. It recursively expands inspector rows
with each node's :meth:`~graph.base_graph_node.BaseGraphNode.get_companion_nodes` result
before validating and materializing the graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors: Sequence[BaseGraphNodeInspector[Any]]  (instances)
              │
              v
    for each: inspector.get_graph_nodes()  ->  flat list of (node + recursive companions, inspector_label)
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
from typing import Any, cast

import rustworkx as rx

from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.exceptions import DuplicateNodeError, InvalidGraphError
from graph.protocol_node_graph_coordinator import ProtocolNodeGraphCoordinator


class NodeGraphCoordinator(ProtocolNodeGraphCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Build rustworkx graph from ``BaseGraphNode`` contributions.
    CONTRACT: ``build`` with :class:`~graph.base_graph_node_inspector.BaseGraphNodeInspector` instances; each ``get_graph_nodes()``;
        then expose the assembled ``PyDiGraph`` as :attr:`rx_graph` and interchange nodes via :meth:`get_all_nodes`.
    INVARIANTS: Duplicate id / missing target / DAG cycle raise during build; :attr:`rx_graph` / :meth:`get_all_nodes` unavailable until ``build`` succeeds.
    AI-CORE-END
    """

    __slots__ = ("_built", "_node_index", "_rx_graph")

    def __init__(self) -> None:
        self._built: bool = False
        self._node_index: dict[str, int] = {}
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
        inspector_nodes = self._gather_all_nodes(inspectors)
        graph_nodes = self._include_companion_nodes(inspector_nodes)
        nodes = self._map_unique_node_ids(graph_nodes)
        self._resolve_edge_node_refs(nodes)
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

    def get_node_by_id(
        self,
        node_id: str,
        node_type: str | None = None,
    ) -> BaseGraphNode[object]:
        """Return the graph node identified by ``node_id``."""
        node_idx = self._node_index.get(node_id)
        if node_idx is None:
            msg = f"Node {node_id!r} was not found in the node graph."
            raise LookupError(msg)
        node = cast(BaseGraphNode[object], self.rx_graph[node_idx])
        if node_type is not None and node.node_type != node_type:
            article = "an" if node_type[:1].lower() in "aeiou" else "a"
            msg = f"Node {node_id!r} is not {article} {node_type} node; got {node.node_type!r}."
            raise InvalidGraphError(msg)
        return node

    def _inspector_label(self, inspector: BaseGraphNodeInspector[Any]) -> str:
        return type(inspector).__qualname__

    def _gather_all_nodes(
        self,
        inspectors: Sequence[BaseGraphNodeInspector[Any]],
    ) -> list[tuple[BaseGraphNode[Any], str]]:
        """Collect ``(node, inspector_qualname)`` pairs from each inspector in order."""
        out: list[tuple[BaseGraphNode[Any], str]] = []
        for insp in inspectors:
            label = self._inspector_label(insp)
            for node in insp.get_graph_nodes():
                out.append((node, label))
        return out

    def _include_companion_nodes(
        self,
        flat: list[tuple[BaseGraphNode[Any], str]],
    ) -> list[tuple[BaseGraphNode[Any], str]]:
        """Append recursive companion nodes and fail immediately on duplicate ``node_id``."""
        out: list[tuple[BaseGraphNode[Any], str]] = []
        owners: dict[str, str] = {}
        expanded_node_ids: set[str] = set()

        for node, label in flat:
            nid = node.node_id
            if nid in owners:
                raise DuplicateNodeError(
                    key=nid,
                    first_inspector=owners[nid],
                    second_inspector=label,
                )
            owners[nid] = label
            out.append((node, label))

        cursor = 0
        while cursor < len(out):
            node, label = out[cursor]
            cursor += 1
            if node.node_id in expanded_node_ids:
                continue
            expanded_node_ids.add(node.node_id)
            for companion_node in node.get_companion_nodes():
                nid = companion_node.node_id
                if nid in owners:
                    raise DuplicateNodeError(
                        key=nid,
                        first_inspector=owners[nid],
                        second_inspector=label,
                    )
                owners[nid] = label
                out.append((companion_node, label))
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

    def _resolve_edge_node_refs(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        """Fill missing edge ``target_node`` references from resolved node ids."""
        for node in nodes.values():
            for edge in node.get_all_edges():
                target_node = nodes.get(edge.target_node_id)
                if edge.target_node is None and target_node is not None:
                    object.__setattr__(edge, "target_node", target_node)

    def _validate_referential_integrity(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        for source_id, node in nodes.items():
            for edge in node.get_all_edges():
                target_node = nodes.get(edge.target_node_id)
                if target_node is None:
                    raise InvalidGraphError(
                        f"Edge {edge.edge_name!r} from {source_id!r} references "
                        f"missing target_node_id {edge.target_node_id!r}.",
                    )
                if edge.target_node is not target_node:
                    raise InvalidGraphError(
                        f"Edge {edge.edge_name!r} from {source_id!r} has broken target_node "
                        f"for target_node_id {edge.target_node_id!r}.",
                    )

    def _validate_dag_acyclicity(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        ids = sorted(nodes.keys())
        if not ids:
            return
        g = rx.PyDiGraph()
        idx = {nid: g.add_node(nid) for nid in ids}
        has_dag = False
        for source_id, node in nodes.items():
            for edge in node.get_all_edges():
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
            for edge in node.get_all_edges():
                tidx = id_to_idx[edge.target_node_id]
                g.add_edge(sidx, tidx, edge)
        self._node_index = id_to_idx
        self._rx_graph = g
