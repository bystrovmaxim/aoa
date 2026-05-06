# src/action_machine/graph_model/nodes/application_graph_node.py
"""
ApplicationGraphNode — interchange node for :class:`~action_machine.application.application.Application`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from the
``Application`` marker class (or a strict subclass). Interchange data lives in
``id``, ``node_type``, ``label``, ``properties``, and ``edges``; the marker
class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Application (or subclass ``type[TApp]``)
              │
              v
    ApplicationGraphNode(...)  ──>  frozen ``BaseGraphNode``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    from action_machine.application import Application

    n = ApplicationGraphNode(Application)
    assert n.node_type == "Application"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.application.application import Application
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_graph_node import BaseGraphNode

TApplication = TypeVar("TApplication", bound=Application)


@dataclass(init=False, frozen=True)
class ApplicationGraphNode(BaseGraphNode[type[TApplication]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange graph node for the application marker type.
    CONTRACT: Built from ``type[TApplication]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; ``properties`` carry ``name`` / ``description`` class attributes.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Application"

    def __init__(self, application_cls: type[TApplication]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(application_cls),
            node_type=ApplicationGraphNode.NODE_TYPE,
            label=application_cls.__name__,
            properties={
                "name": application_cls.name,
                "description": application_cls.description,
            },
            node_obj=application_cls,
        )
