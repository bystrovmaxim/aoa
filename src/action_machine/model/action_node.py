# src/action_machine/model/action_node.py
"""
ActionNode — interchange node for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
an action **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TAction]   (``TAction`` bound to ``BaseAction``)
              │
              v
    ``BaseAction[P, R]``  →  :meth:`get_schema_generic_binding` with index ``0`` / ``1`` (or :meth:`get_params_edge` / :meth:`get_result_edge`)

    ActionNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class MyPingAction(BaseAction): ...
    n = ActionNode(MyPingAction)
    assert n.node_type == "Action" and n.label == "MyPingAction"

Edge case: same interchange shape for any concrete ``BaseAction`` subclass type passed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeVar, get_args, get_origin

from action_machine.domain.base_domain import BaseDomain
from action_machine.legacy.binding.action_generic_params import _resolve_generic_arg
from action_machine.model.base_action import BaseAction
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import EdgeRelationship
from graph.qualified_name import cls_qualified_dotted_id

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: ``get_properties`` / ``get_domain_edge`` (``@meta``); ``get_schema_generic_binding`` / ``get_params_edge`` / ``get_result_edge`` (``BaseAction[P,R]``).
    AI-CORE-END
    """

    def __init__(self, action_cls: type[TAction]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(action_cls),
            node_type="Action",
            label=action_cls.__name__,
            properties=dict(ActionNode.get_properties(action_cls)),
            edges=list(ActionNode._get_all_edges(action_cls)),
            node_obj=action_cls,
        )

    @classmethod
    def get_schema_generic_binding(
        cls,
        action_cls: type[TAction],
        type_arg_index: Literal[0, 1],
    ) -> type | None:
        """
        Resolve one schema type parameter from the first parameterized ``BaseAction[P, R]`` base
        in the action MRO.

        Args:
            action_cls: Concrete action class.
            type_arg_index: ``0`` for params ``P`` (``args[0]``), ``1`` for result ``R`` (``args[1]``).

        Returns:
            Resolved type, or ``None`` when no matching base, too few type args, or unresolved type.
        """
        for klass in action_cls.__mro__:
            for base in getattr(klass, "__orig_bases__", ()):
                if get_origin(base) is BaseAction:
                    args = get_args(base)
                    if len(args) <= type_arg_index:
                        return None
                    return _resolve_generic_arg(args[type_arg_index], action_cls)
        return None

    @classmethod
    def get_params_edge(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Params schema edge, or ``None`` when the params type does not resolve."""
        params_type = cls.get_schema_generic_binding(action_cls, 0)
        if params_type is None:
            return None
        return BaseGraphEdge(
            edge_name="params",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type="Action",
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(params_type),
            target_node_type="params_schema",
            target_node_obj=params_type,
            edge_relationship=EdgeRelationship.FLOW,
        )

    @classmethod
    def get_result_edge(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Result schema edge, or ``None`` when the result type does not resolve."""
        result_type = cls.get_schema_generic_binding(action_cls, 1)
        if result_type is None:
            return None
        return BaseGraphEdge(
            edge_name="result",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type="Action",
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(result_type),
            target_node_type="result_schema",
            target_node_obj=result_type,
            edge_relationship=EdgeRelationship.FLOW,
        )

    @classmethod
    def _meta_info_dict(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``_meta_info`` written by ``@meta``, or empty ``dict`` when absent or not a mapping."""
        raw = getattr(action_cls, "_meta_info", None)
        return raw if isinstance(raw, dict) else {}

    @classmethod
    def get_domain_edge(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Domain edge, or ``None`` when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        meta_info_dict = cls._meta_info_dict(action_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return None
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return None
        return BaseGraphEdge(
            edge_name="domain",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type="Action",
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(domain_cls),
            target_node_type="Domain",
            target_node_obj=domain_cls,
            edge_relationship=EdgeRelationship.ASSOCIATION,
        )

    @classmethod
    def get_properties(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = cls._meta_info_dict(action_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def _get_all_edges(cls, action_cls: type[TAction]) -> list[BaseGraphEdge]:
        """From :meth:`get_domain_edge`, :meth:`get_params_edge`, :meth:`get_result_edge` — drops ``None``."""
        return [
            e
            for e in (
                cls.get_domain_edge(action_cls),
                cls.get_params_edge(action_cls),
                cls.get_result_edge(action_cls),
            )
            if e is not None
        ]
