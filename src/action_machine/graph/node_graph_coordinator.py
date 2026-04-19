# src/action_machine/graph/node_graph_coordinator.py
"""
NodeGraphCoordinator — transactional assembly of interchange ``*Node`` graphs in ``rustworkx``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collects :class:`~action_machine.graph.base_graph_node.BaseGraphNode` instances from
registered **sources** (typically lightweight inspector adapters), validates **unique**
:attr:`~action_machine.graph.base_graph_node.BaseGraphNode.id` keys, **referential
integrity** of :class:`~action_machine.graph.base_graph_edge.BaseGraphEdge.target_id`,
and **acyclicity** of edges marked ``is_dag=True``, then builds a single
``rustworkx.PyDiGraph`` whose vertex weights are the Python ``*Node`` objects and whose
edge weights are the corresponding :class:`~action_machine.graph.base_graph_edge.BaseGraphEdge`
instances.

This coordinator is **domain-agnostic**: it does not interpret ``node_type`` or
``link_name`` beyond validation and DAG checks.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors: Sequence[GraphNodeSource]
              │
              v
    for each: get_graph_nodes()  ->  merge into dict[id -> BaseGraphNode]
              │
              ├─ duplicate id  -> DuplicateNodeError
              ├─ missing target_id  -> InvalidGraphError
              ├─ is_dag cycle  -> InvalidGraphError
              v
    _build_rustworkx_graph: PyDiGraph vertices = *Node, edges = BaseGraphEdge

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- :meth:`build` runs at most once per coordinator instance.
- Vertex index order follows sorted ``id`` strings for deterministic insertion order.
- Only outgoing edges with ``is_dag=True`` participate in acyclicity; other edges may form cycles.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    coord = NodeGraphCoordinator()
    coord.build([adapter])
    g = coord.get_graph()

Edge case: empty inspector list builds an empty graph and an empty ``nodes`` map.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Does not merge multiple contributions to the same logical node; duplicate ``id`` raises
  :class:`~action_machine.graph.exceptions.DuplicateNodeError`.
- Does not materialize missing targets; every ``target_id`` must appear as some node ``id``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Interchange-node graph coordinator (parallel to facet ``GraphCoordinator``).
CONTRACT: ``build(inspectors)``; read ``nodes`` / ``get_graph()`` after success.
INVARIANTS: Built-once; rustworkx stores node/edge Python payloads; DAG slice uses ``is_dag``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import rustworkx as rx

from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode
from action_machine.graph.exceptions import DuplicateNodeError, InvalidGraphError


@runtime_checkable
class GraphNodeSource(Protocol):
    """
    AI-CORE-BEGIN
    ROLE: Provider of interchange nodes for :class:`NodeGraphCoordinator`.
    CONTRACT: Implement ``get_graph_nodes`` (instance or classmethod); return sequence of ``BaseGraphNode``.
    AI-CORE-END
    """

    def get_graph_nodes(self) -> Sequence[BaseGraphNode[Any]]:
        """Return zero or more frozen interchange nodes."""
        ...


def _inspector_label(inspector: object) -> str:
    if isinstance(inspector, type):
        return inspector.__qualname__
    return type(inspector).__qualname__


def _collect_nodes(
    inspectors: Sequence[GraphNodeSource],
) -> dict[str, BaseGraphNode[Any]]:
    nodes: dict[str, BaseGraphNode[Any]] = {}
    owners: dict[str, str] = {}
    for insp in inspectors:
        label = _inspector_label(insp)
        chunk = insp.get_graph_nodes()
        for node in chunk:
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


def _validate_referential_integrity(nodes: dict[str, BaseGraphNode[Any]]) -> None:
    ids = set(nodes.keys())
    for source_id, node in nodes.items():
        for edge in node.edges:
            if edge.target_id not in ids:
                raise InvalidGraphError(
                    f"Link {edge.link_name!r} from {source_id!r} references "
                    f"missing target_id {edge.target_id!r}.",
                )


def _validate_dag_acyclicity(nodes: dict[str, BaseGraphNode[Any]]) -> None:
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


class NodeGraphCoordinator:
    """
    AI-CORE-BEGIN
    ROLE: Build rustworkx graph from ``BaseGraphNode`` contributions.
    CONTRACT: ``build`` once; ``nodes`` and ``get_graph`` after build.
    INVARIANTS: Duplicate id / missing target / DAG cycle raise during build.
    AI-CORE-END
    """

    __slots__ = ("_built", "_graph", "_nodes")

    def __init__(self) -> None:
        self._built: bool = False
        self._nodes: dict[str, BaseGraphNode[Any]] = {}
        self._graph: rx.PyDiGraph = rx.PyDiGraph()

    def build(self, inspectors: Sequence[GraphNodeSource]) -> None:
        """
        Collect nodes from each source, validate, and build the ``rustworkx`` graph.

        Raises:
            DuplicateNodeError: two sources contributed the same ``node.id``.
            InvalidGraphError: missing ``target_id`` or a cycle among ``is_dag`` edges.
            RuntimeError: if :meth:`build` was already called on this instance.
        """
        if self._built:
            msg = "NodeGraphCoordinator.build() was already called on this instance."
            raise RuntimeError(msg)
        nodes = _collect_nodes(inspectors)
        _validate_referential_integrity(nodes)
        _validate_dag_acyclicity(nodes)
        self._build_rustworkx_graph(nodes)
        self._built = True

    def _build_rustworkx_graph(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        g = rx.PyDiGraph()
        id_to_idx: dict[str, int] = {}
        for nid in sorted(nodes.keys()):
            id_to_idx[nid] = g.add_node(nodes[nid])
        for source_id, node in nodes.items():
            sidx = id_to_idx[source_id]
            for edge in node.edges:
                tidx = id_to_idx[edge.target_id]
                g.add_edge(sidx, tidx, edge)
        self._graph = g
        self._nodes = dict(nodes)

    def _require_built(self) -> None:
        if not self._built:
            msg = "NodeGraphCoordinator is not built; call build() first."
            raise RuntimeError(msg)

    @property
    def is_built(self) -> bool:
        """True after a successful :meth:`build`."""
        return self._built

    @property
    def nodes(self) -> Mapping[str, BaseGraphNode[Any]]:
        """Map ``node.id`` → ``BaseGraphNode`` (read-only). Requires built coordinator."""
        self._require_built()
        return MappingProxyType(self._nodes)

    def get_graph(self) -> rx.PyDiGraph:
        """
        Return a copy of the built ``PyDiGraph``.

        Vertex weights are ``BaseGraphNode`` instances; edge weights are ``BaseGraphEdge``.
        """
        self._require_built()
        return self._graph.copy()

    def get_node(self, node_id: str) -> BaseGraphNode[Any]:
        """Return the interchange node for ``node_id``."""
        self._require_built()
        try:
            return self._nodes[node_id]
        except KeyError as e:
            msg = f"No interchange node with id {node_id!r}."
            raise KeyError(msg) from e
