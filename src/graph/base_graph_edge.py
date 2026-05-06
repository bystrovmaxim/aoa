# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
interchange **target_node_id** (:attr:`target_node_id`), optional wired
:class:`~graph.base_graph_node.BaseGraphNode` for **target**, and **properties**
(always a ``dict``, never ``None``; defaults to empty).

``target_node_type`` reads interchange ``node_type`` from a wired ``target_node`` and must
not be overridden (:func:`~typing.final`).

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
        target_node_id="pkg.domains.SystemDomain",
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast, final

from graph.edge_relationship import EdgeRelationship
from graph.validation import require_non_empty_str


@dataclass(init=False, frozen=True, eq=False)
class BaseGraphEdge(ABC):
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, DAG flag, target id, optional wired target node, properties).
    CONTRACT: Concrete subclasses expose ``edge_relationship`` as their fixed :class:`~graph.edge_relationship.EdgeRelationship`. ``target_node_id`` is a non-empty interchange id (``str``; typically matching another node's ``node_id``). ``target_node`` may be ``None`` until wired by a coordinator.
    INVARIANTS: Frozen; ``is_dag`` is always set explicitly by the caller. ``properties`` is always a ``dict`` (never ``None``). String fields must be non-empty (after strip).
    AI-CORE-END
    """

    edge_name: str
    is_dag: bool
    target_node_id: str
    target_node: Any
    properties: dict[str, Any]

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        target_node_id: str,
        target_node: Any | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge_name_s = require_non_empty_str("edge_name", edge_name)

        target_node_id_s = require_non_empty_str("target_node_id", target_node_id)

        object.__setattr__(self, "edge_name", edge_name_s)
        object.__setattr__(self, "is_dag", is_dag)
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

    def __eq__(self, other: object) -> bool:
        """Structural equality (ids, names, properties); wired node objects are ignored."""

        if type(self) is not type(other):
            return NotImplemented
        if not isinstance(other, BaseGraphEdge):
            return NotImplemented
        return (
            self.edge_name == other.edge_name
            and self.is_dag == other.is_dag
            and self.target_node_id == other.target_node_id
            and self.properties == other.properties
        )

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.edge_name,
                self.is_dag,
                self.target_node_id,
                tuple(sorted(self.properties.items())),
            ),
        )

    @property
    @final
    def target_node_type(self) -> str:
        """Interchange graph-node type string for ``target_node`` (must be wired)."""

        tgt = self.target_node
        if tgt is None:
            msg = (
                f"{type(self).__qualname__}({self.edge_name!r}): "
                "`target_node` must be wired to read ``target_node_type``."
            )
            raise RuntimeError(msg)
        return cast(str, tgt.node_type)

    @property
    @abstractmethod
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed ArchiMate-style relationship for this concrete edge type."""
