# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, source and target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
then constructor **source** as either a non-empty interchange id (``str``; no wired :attr:`source_node`) or a ``BaseGraphNode``-like object whose ``node_id`` yields that id and is stored as :attr:`source_node`,
**target_node_id** (:attr:`target_node_id`), optional wired :class:`~graph.base_graph_node.BaseGraphNode`
for **target**, and **properties**
(always a ``dict``, never ``None``; defaults to empty).

``source_node_type`` / ``target_node_type`` read interchange ``node_type`` from wired
``source_node`` / ``target_node``. They must not be overridden (:func:`~typing.final`).

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
        source="pkg.actions.MyAction",
        target_node_id="pkg.domains.SystemDomain",
    )

Edge case: same ``edge_name`` on different nodes — distinguish by interchange ``source`` id (:attr:`source_node_id`).
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
    ROLE: Interchange edge descriptor (slot, DAG, source/target ids, optional wired nodes, properties).
    CONTRACT: Concrete subclasses expose ``edge_relationship`` as their fixed :class:`~graph.edge_relationship.EdgeRelationship`. Keyword ``source`` is either a non-empty interchange id (``str``, no wired body) or a node-like instance with ``node_id`` (id + optional ``source_node`` body).
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
        source: Any,
        target_node_id: str,
        target_node: Any | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        edge_name_s = require_non_empty_str("edge_name", edge_name)

        source_node_wire: Any
        if isinstance(source, str):
            source_node_wire = None
            source_node_id_s = require_non_empty_str("source_node_id", source)
        else:
            source_node_wire = source
            try:
                raw_source_id = source.node_id
            except AttributeError as exc:
                msg = (
                    "source must be a non-empty interchange id (str) or an object exposing "
                    f"non-empty node_id str, not {type(source).__qualname__!r}"
                )
                raise TypeError(msg) from exc
            source_node_id_s = require_non_empty_str("source_node_id", raw_source_id)

        target_node_id_s = require_non_empty_str("target_node_id", target_node_id)

        object.__setattr__(self, "edge_name", edge_name_s)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "source_node_id", source_node_id_s)
        object.__setattr__(self, "source_node", source_node_wire)
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
            and self.source_node_id == other.source_node_id
            and self.target_node_id == other.target_node_id
            and self.properties == other.properties
        )

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.edge_name,
                self.is_dag,
                self.source_node_id,
                self.target_node_id,
                tuple(sorted(self.properties.items())),
            ),
        )

    @property
    @final
    def source_node_type(self) -> str:
        """Interchange vertex type string for ``source_node`` (must be wired)."""

        src = self.source_node
        if src is None:
            msg = (
                f"{type(self).__qualname__}({self.edge_name!r}): "
                "`source_node` must be wired to read ``source_node_type``."
            )
            raise RuntimeError(msg)
        return cast(str, src.node_type)

    @property
    @final
    def target_node_type(self) -> str:
        """Interchange vertex type string for ``target_node`` (must be wired)."""

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
