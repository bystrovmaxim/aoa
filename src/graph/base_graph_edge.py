# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, source and target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
then **source** and **target** interchange ids, optional wired :class:`~graph.base_graph_node.BaseGraphNode`
object references once the graph is assembled, and **properties**
(always a ``dict``, never ``None``; defaults to empty).

``source_node_type`` / ``target_node_type`` are read-only properties derived from wired
:class:`~graph.base_graph_node.BaseGraphNode` instances when possible; subclasses may
override properties when stubs intentionally omit references (see interchange docs).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.node_id  +  edges: list[BaseGraphEdge(...)]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from graph.association_graph_edge import AssociationGraphEdge

    AssociationGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id="pkg.actions.MyAction",
        target_node_id="pkg.domains.SystemDomain",
    )

Edge case: same ``edge_name`` on different nodes — distinguish by ``source_node_id``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from graph.edge_relationship import EdgeRelationship
from graph.validation import require_non_empty_str


@dataclass(init=False, frozen=True)
class BaseGraphEdge(ABC):
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, DAG, source/target ids, optional wired nodes, properties).
    CONTRACT: Concrete subclasses expose ``edge_relationship`` as their fixed :class:`~graph.edge_relationship.EdgeRelationship`.
    INVARIANTS: Frozen; ``is_dag`` is always set explicitly by the caller. ``properties`` is always a ``dict`` (never ``None``).
    String fields must be non-empty (after strip).
    AI-CORE-END
    """

    edge_name: str
    is_dag: bool
    source_node_id: str
    source_node: Any
    target_node_id: str
    target_node: Any
    properties: dict[str, Any]

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        source_node_id: str,
        source_node: Any | None = None,
        target_node_id: str,
        target_node: Any | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge_name_s = require_non_empty_str("edge_name", edge_name)
        source_node_id_s = require_non_empty_str("source_node_id", source_node_id)
        target_node_id_s = require_non_empty_str("target_node_id", target_node_id)

        object.__setattr__(self, "edge_name", edge_name_s)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "source_node_id", source_node_id_s)
        object.__setattr__(self, "source_node", source_node)
        object.__setattr__(self, "target_node_id", target_node_id_s)
        object.__setattr__(self, "target_node", target_node)

        if properties is None:
            props: dict[str, Any] = {}
        elif isinstance(properties, Mapping):
            props = dict(properties)
        else:
            msg = f"properties must be a mapping or None, not {type(properties).__name__}"
            raise TypeError(msg)
        object.__setattr__(self, "properties", props)

    @property
    def source_node_type(self) -> str:
        """Derived from wired ``source_node`` when present; subclasses may override."""

        src = self.source_node
        if src is None:
            msg = (
                f"{type(self).__qualname__}({self.edge_name!r}): source_node unset — "
                "override source_node_type or wire the interchange graph."
            )
            raise RuntimeError(msg)
        return cast(str, src.node_type)

    @property
    def target_node_type(self) -> str:
        """Derived from wired ``target_node`` when present; subclasses may override."""

        tgt = self.target_node
        if tgt is None:
            msg = (
                f"{type(self).__qualname__}({self.edge_name!r}): target_node unset — "
                "override target_node_type or finish graph resolution."
            )
            raise RuntimeError(msg)
        return cast(str, tgt.node_type)

    @property
    @abstractmethod
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed ArchiMate-style relationship for this concrete edge type."""
