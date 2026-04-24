# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, source and target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
then **source** and **target** interchange ids, kinds, a single
**ArchiMate-style relationship** for the edge, and optional **properties** (always a ``dict``,
never ``None``; defaults to empty).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.node_id  +  edges: list[BaseGraphEdge(...)]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from graph.edge_relationship import ASSOCIATION

    BaseGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id="pkg.actions.MyAction",
        source_node_type="Action",
        target_node_id="pkg.domains.SystemDomain",
        target_node_type="Domain",
        edge_relationship=ASSOCIATION,
    )

Edge case: same ``edge_name`` on different nodes — distinguish by ``source_node_id``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from graph.edge_relationship import EdgeRelationship
from graph.validation import require_non_empty_str, require_non_null

if TYPE_CHECKING:
    from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class BaseGraphEdge:
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, DAG, source/target ids, kinds, relationship, properties).
    CONTRACT: ``edge_relationship`` uses :class:`~graph.edge_relationship.EdgeRelationship` (ArchiMate-style kinds).
    INVARIANTS: Frozen; ``is_dag`` is always set explicitly by the caller. ``properties`` is always a ``dict`` (never ``None``).
    String fields must be non-empty (after strip); ``edge_relationship`` must not be ``None``.
    AI-CORE-END
    """

    edge_name: str
    is_dag: bool
    source_node_id: str
    source_node_type: str
    source_node: BaseGraphNode[Any] | None
    target_node_id: str
    target_node_type: str
    target_node: BaseGraphNode[Any] | None
    edge_relationship: EdgeRelationship
    properties: dict[str, Any]

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        source_node_id: str,
        source_node_type: str,
        source_node: BaseGraphNode[Any] | None = None,
        target_node_id: str,
        target_node_type: str,
        target_node: BaseGraphNode[Any] | None = None,
        edge_relationship: EdgeRelationship,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge_name_s = require_non_empty_str("edge_name", edge_name)
        source_node_id_s = require_non_empty_str("source_node_id", source_node_id)
        source_node_type_s = require_non_empty_str("source_node_type", source_node_type)
        target_node_id_s = require_non_empty_str("target_node_id", target_node_id)
        target_node_type_s = require_non_empty_str("target_node_type", target_node_type)

        object.__setattr__(self, "edge_name", edge_name_s)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "source_node_id", source_node_id_s)
        object.__setattr__(self, "source_node_type", source_node_type_s)
        object.__setattr__(self, "source_node", source_node)
        object.__setattr__(self, "target_node_id", target_node_id_s)
        object.__setattr__(self, "target_node_type", target_node_type_s)
        object.__setattr__(self, "target_node", target_node)
        er_raw = require_non_null("edge_relationship", edge_relationship)
        if not isinstance(er_raw, EdgeRelationship):
            msg = f"edge_relationship must be EdgeRelationship, not {type(er_raw).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "edge_relationship", er_raw)

        if properties is None:
            props: dict[str, Any] = {}
        elif isinstance(properties, Mapping):
            props = dict(properties)
        else:
            msg = f"properties must be a mapping or None, not {type(properties).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "properties", props)
