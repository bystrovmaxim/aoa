# src/action_machine/domain/domain_graph_node.py
"""
DomainGraphNode — interchange node for BaseDomain marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
a ``BaseDomain`` subclass. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the domain class is the same object as
:attr:`~action_machine.graph.base_graph_node.BaseGraphNode.obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TDomain]   (``TDomain`` bound to ``BaseDomain``)
              │
              v
    DomainGraphNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The domain class is available as :attr:`~action_machine.graph.base_graph_node.BaseGraphNode.obj`.
- ``label`` is the domain class ``__name__``; ``properties`` hold ``name`` / ``description``; ``edges`` include informational ``belongs_to`` → ``ApplicationContext`` (facet parity).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop context"

    n = DomainGraphNode(ShopDomain)
    assert n.node_type == "Domain" and n.label == "ShopDomain"

Edge case: same interchange shape for any concrete ``BaseDomain`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; ``BaseDomain`` concrete subclasses are validated at class definition where applicable.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Domain-scoped BaseGraphNode bridge for BaseDomain subclasses.
CONTRACT: Construct from ``type[TDomain]`` via ``parse``; ``node_type="Domain"``; dotted-path ``id``; label = class name; ``name``/``description`` in ``properties``; ``belongs_to`` ``ApplicationContext`` in ``edges``.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: domain class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode, Payload
from action_machine.legacy.interchange_vertex_labels import APPLICATION_VERTEX_TYPE

TDomain = TypeVar("TDomain", bound=BaseDomain)


@dataclass(init=False, frozen=True)
class DomainGraphNode(BaseGraphNode[type[TDomain]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a bounded-context domain marker.
    CONTRACT: Built from ``type[TDomain]``; dotted ``id``, ``__name__`` label; ``properties`` carry ``name`` / ``description`` (facet ``node_meta`` parity); ``belongs_to`` → ``ApplicationContext`` in ``edges``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, domain_cls: type[TDomain]) -> Payload:
        # Local import: avoid loading ``application`` package (and inspector) during ``domain`` import.
        from action_machine.application.application_context import (  # pylint: disable=import-outside-toplevel
            ApplicationContext,
        )

        app_id = qualified_dotted_name(ApplicationContext)
        return Payload(
            id=qualified_dotted_name(domain_cls),
            node_type="Domain",
            label=domain_cls.__name__,
            properties={
                "name": domain_cls.name,
                "description": domain_cls.description,
            },
            edges=[
                BaseGraphEdge(
                    link_name="belongs_to",
                    target_id=app_id,
                    target_node_type=APPLICATION_VERTEX_TYPE,
                    is_dag=False,
                    target_cls=ApplicationContext,
                ),
            ],
        )
