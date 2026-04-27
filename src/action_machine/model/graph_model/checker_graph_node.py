# src/action_machine/model/graph_model/checker_graph_node.py
"""
CheckerGraphNode — interchange node for one result-field checker on an aspect method.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for a single checker
row (``aspect_callable`` + ``checker_class`` + ``field``) on a concrete ``BaseAction`` subclass.
Host action and aspect method name come from :meth:`~action_machine.system_core.TypeIntrospection.owner_type_for_method` / :meth:`~action_machine.system_core.TypeIntrospection.unwrapped_callable_name` on ``aspect_callable``.
``node_id`` joins ``action_dotted_id``, ``aspect_method_name``, and ``field_name.strip()`` with ``:``.
``node_obj`` is a frozen :class:`CheckerGraphPayload` with the constructor inputs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    explicit host + aspect + checker field  ->  ``CheckerGraphNode(...)`` (outgoing edges live on :class:`RegularAspectGraphNode`).
    Interchange graph: hosts register built ``CheckerGraphNode`` instances via ``companion_nodes`` on :class:`RegularAspectGraphNode`; inspectors flatten them into ``get_graph_nodes()`` (see :class:`~graph.base_graph_node.BaseGraphNode`).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode

TYPE_CHECKER_PROPERTY_LABEL_EXPRESSION = re.compile(r"^Field(.+)Checker$")


def _type_checker_property_label(checker_class: type) -> str:
    """``FieldStringChecker`` → ``String``; otherwise :meth:`~type.__name__`."""
    name = checker_class.__name__
    m = TYPE_CHECKER_PROPERTY_LABEL_EXPRESSION.match(name)
    return m.group(1) if m else name


@dataclass(frozen=True)
class CheckerGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` on a checker interchange row.

    :attr:`properties` merges the constructor ``properties`` checker-kwargs dict (if any) with ``"TypeChecker"`` (short kind for ``Field*Checker``) and ``"required"`` (same keys as on :class:`~graph.base_graph_node.BaseGraphNode`).
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
    CONTRACT: ``action_cls`` / ``aspect_method_name`` come from ``aspect_callable``; ``node_id`` = ``TypeIntrospection.full_qualname(action_cls) + ':' + aspect_method_name + ':' + field_name.strip()``;
    ``label`` is ``field_name.strip()``; :attr:`NODE_TYPE` is ``Checker``; ``edges`` empty; interchange ``properties`` (on the node and on :class:`CheckerGraphPayload`) merge constructor ``properties`` with ``"TypeChecker"`` (middle segment of ``Field*Checker`` names) / ``"required"``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Checker"

    def __init__(
        self,
        aspect_callable: Callable[..., Any],
        checker_class: type,
        field_name: str,
        *,
        required: bool = False,
        properties: dict[str, Any] | None = None,
    ) -> None:
        action_cls = TypeIntrospection.owner_type_for_method(aspect_callable)
        aspect_method_name = TypeIntrospection.unwrapped_callable_name(aspect_callable)
        if not isinstance(checker_class, type):
            msg = f"checker_class must be a type, got {type(checker_class).__name__}"
            raise TypeError(msg)
        merged_properties: dict[str, Any] = {
            **({} if properties is None else dict(properties)),
            "TypeChecker": _type_checker_property_label(checker_class),
            "required": required,
        }
        node_obj = CheckerGraphPayload(
            action_cls=action_cls,
            aspect_method_name=aspect_method_name,
            checker_class=checker_class,
            field_name=field_name,
            required=required,
            properties=merged_properties,
        )
        action_id = TypeIntrospection.full_qualname(action_cls)
        checker_node_id = f"{action_id}:{aspect_method_name}:{field_name.strip()}"
        super().__init__(
            node_id=checker_node_id,
            node_type=CheckerGraphNode.NODE_TYPE,
            label=field_name.strip(),
            properties=merged_properties,
            node_obj=node_obj,
        )
