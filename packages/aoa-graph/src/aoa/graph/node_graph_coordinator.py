# packages/aoa-graph/src/aoa/graph/node_graph_coordinator.py
"""
NodeGraphCoordinator — transactional assembly of interchange ``*Node`` graphs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collects :class:`~aoa.graph.base_graph_node.BaseGraphNode` instances from
registered :class:`~aoa.graph.base_graph_node_inspector.BaseGraphNodeInspector`
**instances** (each implements :meth:`~aoa.graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`),
validates **unique**
:attr:`~aoa.graph.base_graph_node.BaseGraphNode.node_id` keys, **referential
integrity** of :class:`~aoa.graph.base_graph_edge.BaseGraphEdge.target_node_id`
(for every edge emitted by :meth:`~aoa.graph.base_graph_node.BaseGraphNode.get_all_edges`, including
``parent_action`` / ``parent_role`` / ``parent_domain`` generalization rows when present),
and **acyclicity** of edges marked ``is_dag=True``, then retains a canonical
``dict[str, BaseGraphNode]`` plus typed edge indexes for efficient reads and export.

Read nodes via :meth:`get_all_nodes`, :meth:`get_node_by_id`, :meth:`get_nodes_by_type`,
and JSON via :meth:`to_json`.

This coordinator is **domain-agnostic**: it does not interpret ``node_type`` or
``edge_name`` beyond validation and DAG checks. It recursively expands inspector rows
with each node's :meth:`~aoa.graph.base_graph_node.BaseGraphNode.get_companion_nodes` result
before validating and materializing the graph.

The merged graph reflects **everything inspectors emitted for the loaded process**.
Unexpected rows (duplicate ids, dangling targets, forbidden ``is_dag`` cycles, stray action types) indicate import or wiring issues to fix—not something to silently drop during inspection.

**JSON export:** :meth:`NodeGraphCoordinator.to_json` assembles a JSON object with
``schema_version``, ``nodes``, and ``edges`` (each node includes ``id``, ``type``,
``label``, ``properties``; each edge includes ``source_id``, ``target_id``,
``type``, ``relationship``, ``is_dag``, ``properties``) suitable for rebuilding a
``networkx.DiGraph`` keyed by node ``id``. Callers may still pass ``export_json_schema`` to
:meth:`build` for API compatibility; it is not used by :meth:`to_json`.

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
    indexes  ->  get_all_nodes / by-type accessors / :meth:`to_json`

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    coord = NodeGraphCoordinator()
    coord.build([adapter], export_json_schema=None)

Edge case: empty inspector list completes without error.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

from aoa.graph import _dag
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.exceptions import DuplicateNodeError, InvalidGraphError

_BUILD_REQUIRED_MSG = "This NodeGraphCoordinator operation is only available after a successful build()."


class NodeGraphCoordinator:
    """
    AI-CORE-BEGIN
    ROLE: Build validated interchange graph from ``BaseGraphNode`` contributions with indexes.
    CONTRACT: ``build`` with :class:`~aoa.graph.base_graph_node_inspector.BaseGraphNodeInspector` instances; each ``get_graph_nodes()``;
        then serve interchange nodes via :meth:`get_all_nodes`, :meth:`get_node_by_id`, type helpers; graph shape is authoritative for loaded scope.
        Optional ``export_json_schema`` at :meth:`build` is accepted for backward-compatible call sites.
    INVARIANTS: Duplicate id / missing target / DAG cycle raise during build; public read APIs unavailable until ``build`` succeeds.
    AI-CORE-END
    """

    __slots__ = (
        "_built",
        "_edge_types",
        "_edges",
        "_edges_by_source",
        "_edges_by_target",
        "_edges_by_type",
        "_node_types",
        "_nodes",
        "_nodes_by_type",
    )

    def __init__(self) -> None:
        self._built: bool = False
        self._edge_types: frozenset[str] | None = None
        self._edges: list[tuple[str, str, BaseGraphEdge]] | None = None
        self._edges_by_source: dict[str, list[tuple[str, BaseGraphEdge]]] | None = None
        self._edges_by_target: dict[str, list[tuple[str, BaseGraphEdge]]] | None = None
        self._edges_by_type: dict[str, list[tuple[str, str, BaseGraphEdge]]] | None = None
        self._node_types: frozenset[str] | None = None
        self._nodes: dict[str, BaseGraphNode[Any]] | None = None
        self._nodes_by_type: dict[str, list[str]] | None = None

    def build(
        self,
        inspectors: Sequence[BaseGraphNodeInspector[Any]],
        *,
        export_json_schema: dict[str, Any] | None = None,
    ) -> None:
        """
        Collect nodes from each inspector instance via :meth:`BaseGraphNodeInspector.get_graph_nodes`,
        validate, index, and store the graph for read APIs.

        Args:
            inspectors: Inspector instances contributing interchange nodes.
            export_json_schema: Ignored; retained only for backward-compatible keyword arguments.

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
        nodes = self._expand_and_collect(inspector_nodes)
        dag_adjacency = self._single_pass_validate_and_wire(nodes)
        self._validate_dag_acyclicity(nodes, dag_adjacency)
        self._nodes = nodes
        self._build_indexes(nodes)
        _ = export_json_schema
        self._built = True

    def get_all_nodes(self) -> tuple[BaseGraphNode[Any], ...]:
        """
        Return every :class:`~aoa.graph.base_graph_node.BaseGraphNode` sorted by ``node_id``.

        Raises:
            RuntimeError: :meth:`build` has not completed successfully on this coordinator.
        """
        if not self._built or self._nodes is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        return tuple(self._nodes[nid] for nid in sorted(self._nodes))

    def get_node_by_id(
        self,
        node_id: str,
        node_type: str | None = None,
    ) -> BaseGraphNode[object]:
        """Return the graph node identified by ``node_id``."""
        if not self._built or self._nodes is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        node = self._nodes.get(node_id)
        if node is None:
            msg = f"Node {node_id!r} was not found in the node graph."
            raise LookupError(msg)
        node = cast(BaseGraphNode[object], node)
        if node_type is not None and node.node_type != node_type:
            article = "an" if node_type[:1].lower() in "aeiou" else "a"
            msg = f"Node {node_id!r} is not {article} {node_type} node; got {node.node_type!r}."
            raise InvalidGraphError(msg)
        return node

    def to_json(self) -> str:
        """
        Serialize the built interchange graph to JSON.

        Raises:
            RuntimeError: :meth:`build` has not completed successfully on this coordinator.
        """
        if not self._built or self._nodes is None or self._edges is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        nodes = sorted(self._nodes.values(), key=lambda n: n.node_id)
        edge_dicts: list[dict[str, Any]] = [
            edge.to_dict(source_id=source_id) for source_id, _target_id, edge in self._edges
        ]
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "nodes": [node.to_dict() for node in nodes],
            "edges": sorted(
                edge_dicts,
                key=lambda e: (e["source_id"], e["type"], e["target_id"]),
            ),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def get_nodes_by_type(self, node_type: str) -> tuple[BaseGraphNode[Any], ...]:
        """Return all nodes of the given ``node_type`` sorted by ``node_id``."""
        self._require_indexes()
        nodes_map = self._nodes
        by_type = self._nodes_by_type
        if nodes_map is None or by_type is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        ids = by_type.get(node_type)
        if not ids:
            return ()
        return tuple(nodes_map[nid] for nid in ids)

    def get_edges_by_type(self, edge_type: str) -> tuple[tuple[str, str, BaseGraphEdge], ...]:
        """Return edges with ``edge.edge_name == edge_type`` (any interchange name, including ``parent_*``)."""
        self._require_indexes()
        by_et = self._edges_by_type
        if by_et is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        rows = by_et.get(edge_type)
        if not rows:
            return ()
        return tuple(rows)

    def get_available_types(self) -> dict[str, frozenset[str]]:
        """Return ``node_types`` and ``edge_types`` present after the last :meth:`build`."""
        self._require_indexes()
        nt = self._node_types
        et = self._edge_types
        if nt is None or et is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)
        return {
            "node_types": nt,
            "edge_types": et,
        }

    def _require_indexes(self) -> None:
        if not self._built or self._nodes is None or self._nodes_by_type is None:
            raise RuntimeError(_BUILD_REQUIRED_MSG)

    def _build_indexes(self, nodes: dict[str, BaseGraphNode[Any]]) -> None:
        """Build type/source/target edge indexes in one pass (deterministic sort where needed)."""
        nodes_by_type: dict[str, list[str]] = {}
        edge_triples: list[tuple[str, str, BaseGraphEdge]] = []
        edges_by_type: dict[str, list[tuple[str, str, BaseGraphEdge]]] = {}
        edges_by_source: dict[str, list[tuple[str, BaseGraphEdge]]] = {}
        edges_by_target: dict[str, list[tuple[str, BaseGraphEdge]]] = {}

        for node_id, node in nodes.items():
            nodes_by_type.setdefault(node.node_type, []).append(node_id)
            for edge in node.get_all_edges():
                tgt = edge.target_node_id
                triple = (node_id, tgt, edge)
                edge_triples.append(triple)
                edges_by_type.setdefault(edge.edge_name, []).append(triple)
                edges_by_source.setdefault(node_id, []).append((tgt, edge))
                edges_by_target.setdefault(tgt, []).append((node_id, edge))

        for id_list in nodes_by_type.values():
            id_list.sort()

        edge_triples.sort(key=lambda tr: (tr[0], tr[2].edge_name, tr[1]))
        for triple_list in edges_by_type.values():
            triple_list.sort(key=lambda tr: (tr[0], tr[2].edge_name, tr[1]))
        for pairs in edges_by_source.values():
            pairs.sort(key=lambda p: (p[1].edge_name, p[0]))
        for pairs in edges_by_target.values():
            pairs.sort(key=lambda p: (p[1].edge_name, p[0]))

        self._nodes_by_type = nodes_by_type
        self._edges = edge_triples
        self._edges_by_type = edges_by_type
        self._edges_by_source = edges_by_source
        self._edges_by_target = edges_by_target
        self._node_types = frozenset(nodes_by_type.keys())
        self._edge_types = frozenset(edges_by_type.keys())

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

    def _expand_and_collect(
        self,
        flat: list[tuple[BaseGraphNode[Any], str]],
    ) -> dict[str, BaseGraphNode[Any]]:
        """Expand companions and return unique ``node_id -> node``; one ``owners`` map for duplicates."""
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

        nodes: dict[str, BaseGraphNode[Any]] = {}
        for node, _ in out:
            nodes[node.node_id] = node
        return nodes

    def _single_pass_validate_and_wire(
        self,
        nodes: dict[str, BaseGraphNode[Any]],
    ) -> dict[str, list[str]]:
        """Wire edges, validate targets, and collect ``is_dag`` adjacency in one graph pass."""
        dag_adjacency: dict[str, list[str]] = {}

        for source_id, node in nodes.items():
            for edge in node.get_all_edges():
                target_id = edge.target_node_id
                target_node = nodes.get(target_id)

                if edge.target_node is None and target_node is not None:
                    object.__setattr__(edge, "target_node", target_node)

                if target_node is None:
                    raise InvalidGraphError(
                        f"Edge {edge.edge_name!r} from {source_id!r} references "
                        f"missing target_node_id {target_id!r}.",
                    )
                if edge.target_node is not target_node:
                    raise InvalidGraphError(
                        f"Edge {edge.edge_name!r} from {source_id!r} has broken target_node "
                        f"for target_node_id {target_id!r}.",
                    )

                if edge.is_dag:
                    dag_adjacency.setdefault(source_id, []).append(target_id)

        return dag_adjacency

    def _validate_dag_acyclicity(
        self,
        nodes: dict[str, BaseGraphNode[Any]],
        dag_adjacency: dict[str, list[str]],
    ) -> None:
        """Reject directed cycles in the ``is_dag`` edge slice (pure Python)."""
        ids = sorted(nodes.keys())
        if not ids:
            return
        if not any(dag_adjacency.values()):
            return
        if not _dag.is_dag_slice_acyclic(dag_adjacency, ids):
            raise InvalidGraphError(
                "Edges with is_dag=True form a directed cycle. "
                "Review interchange link wiring.",
            )
