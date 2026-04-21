# src/action_machine/model/graph_model/checker_graph_node.py
"""
CheckerGraphNode — interchange node for one result-field checker on an aspect method.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for a single checker
row (``aspect method`` + ``checker_class`` + ``field``) on a concrete ``BaseAction`` subclass.
``node_id`` joins ``action_dotted_id``, ``aspect_method_name``, and ``field_name.strip()`` with ``:``.
``node_obj`` is a frozen :class:`CheckerGraphPayload` with the constructor inputs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    explicit host + aspect + checker field  ->  ``CheckerGraphNode(...)``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.introspection_tools import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class CheckerGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` on a checker interchange row.

    :attr:`properties` merges the constructor ``properties`` checker-kwargs dict (if any) with ``"TypeChecker"`` and ``"required"`` (same keys as on :class:`~graph.base_graph_node.BaseGraphNode`).
    """

    action_cls: type
    aspect_method_name: str
    checker_class: type
    field_name: str
    required: bool
    properties: dict[str, Any]


@dataclass(init=False, frozen=True)
class CheckerGraphNode(BaseGraphNode[CheckerGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one checker binding on a regular or summary aspect method.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(action_cls) + ':' + aspect_method_name + ':' + field_name.strip()``;
    ``label`` is ``field_name.strip()``; :attr:`NODE_TYPE` is ``Checker``; interchange ``properties`` (on the node and on :class:`CheckerGraphPayload`) merge constructor ``properties`` with ``"TypeChecker"`` / ``"required"``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Checker"

    def __init__(
        self,
        action_cls: type,
        aspect_method_name: str,
        checker_class: type,
        field_name: str,
        *,
        required: bool = False,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(action_cls, type):
            msg = f"action_cls must be a type, got {type(action_cls).__name__}"
            raise TypeError(msg)
        if not isinstance(checker_class, type):
            msg = f"checker_class must be a type, got {type(checker_class).__name__}"
            raise TypeError(msg)
        properties: dict[str, Any] = {
            **({} if properties is None else dict(properties)),
            "TypeChecker": checker_class.__name__,
            "required": required,
        }
        node_obj = CheckerGraphPayload(
            action_cls=action_cls,
            aspect_method_name=aspect_method_name,
            checker_class=checker_class,
            field_name=field_name,
            required=required,
            properties=properties,
        )
        action_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=f"{action_id}:{aspect_method_name}:{field_name.strip()}",
            node_type=CheckerGraphNode.NODE_TYPE,
            label=field_name.strip(),
            properties=properties,
            edges=[],
            node_obj=node_obj,
        )
