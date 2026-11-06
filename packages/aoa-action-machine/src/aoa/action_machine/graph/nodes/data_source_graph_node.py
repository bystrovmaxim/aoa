# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/data_source_graph_node.py
"""
DataSourceGraphNode — interchange node for ``BaseDataSource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A data source is one store several resources share (protocol 1.7). Its node carries
the ``@meta`` description and one ``application`` edge: a data source belongs to the
application, as a domain and a role do, and to no domain.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    type[BaseDataSource]  ── @meta description ──►  DataSourceGraphNode  ──application──►  Application
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from aoa.action_machine.application.application import Application
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.application_graph_edge import ApplicationGraphEdge
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.action_machine.resources.base_data_source import BaseDataSource
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TDataSourceClass = TypeVar("TDataSourceClass", bound=BaseDataSource)


@dataclass(init=False, frozen=True)
class DataSourceGraphNode(BaseGraphNode[type[TDataSourceClass]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseDataSource`` class.
    CONTRACT: ``properties["description"]`` from ``@meta``; :attr:`application` aggregates to the application node; :meth:`get_all_edges` returns that edge only.
    FAILURES: :exc:`~aoa.action_machine.exceptions.MissingMetaError` when the data source declares no ``@meta``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "DataSource"
    application: ApplicationGraphEdge = field(init=False, repr=False, compare=False)

    def __init__(self, data_source_cls: type[TDataSourceClass]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(data_source_cls),
            node_type=DataSourceGraphNode.NODE_TYPE,
            label=data_source_cls.__name__,
            properties={"description": MetaIntentResolver.resolve_description(data_source_cls)},
            node_obj=data_source_cls,
        )
        object.__setattr__(self, "application", ApplicationGraphEdge(Application))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {"description": str(self.properties["description"])},
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the application edge."""
        return [self.application]
