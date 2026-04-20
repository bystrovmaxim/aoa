# src/action_machine/model/graph_model/action_graph_node.py
"""
ActionGraphNode — interchange node for ``BaseAction`` subclasses.

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

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class MyPingAction(BaseAction): ...
    n = ActionGraphNode(MyPingAction)
    assert n.node_type == "Action" and n.label == "MyPingAction"

Edge case: same interchange shape for any concrete ``BaseAction`` subclass type passed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, TypeVar, get_args, get_origin

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.legacy.binding.action_generic_params import _resolve_generic_arg
from action_machine.model.base_action import BaseAction
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import AGGREGATION, ASSOCIATION, COMPOSITION
from graph.qualified_name import cls_qualified_dotted_id

from .base_callable_graph_node import BaseCallableGraphNode, IntentCallableKind
from .params_graph_node import ParamsGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode
from .result_graph_node import ResultGraphNode

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionGraphNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: ``get_properties`` / ``get_domain_edge`` (``@meta``, ``ASSOCIATION``, ``is_dag=True``); ``get_params_edge`` / ``get_result_edge`` (``AGGREGATION``); ``get_regular_aspect_edges`` / ``get_summary_aspect_edges`` (``COMPOSITION``, own-class ``@regular_aspect`` / ``@summary_aspect``).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"

    def __init__(self, action_cls: type[TAction]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(action_cls),
            node_type=ActionGraphNode.NODE_TYPE,
            label=action_cls.__name__,
            properties=dict(ActionGraphNode.get_properties(action_cls)),
            edges=list(ActionGraphNode._get_all_edges(action_cls)),
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
        """Params schema edge (``AGGREGATION``), or ``None`` when the params type does not resolve."""
        params_type = cls.get_schema_generic_binding(action_cls, 0)
        if params_type is None:
            return None
        return BaseGraphEdge(
            edge_name="params",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type=cls.NODE_TYPE,
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(params_type),
            target_node_type=ParamsGraphNode.NODE_TYPE,
            target_node_obj=params_type,
            edge_relationship=AGGREGATION,
        )

    @classmethod
    def get_result_edge(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Result schema edge (``AGGREGATION``), or ``None`` when the result type does not resolve."""
        result_type = cls.get_schema_generic_binding(action_cls, 1)
        if result_type is None:
            return None
        return BaseGraphEdge(
            edge_name="result",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type=cls.NODE_TYPE,
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(result_type),
            target_node_type=ResultGraphNode.NODE_TYPE,
            target_node_obj=result_type,
            edge_relationship=AGGREGATION,
        )

    @classmethod
    def get_regular_aspect_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``COMPOSITION`` edge per own-class ``@regular_aspect`` from this action to the matching regular-aspect node.

        Target ids match :class:`RegularAspectGraphNode` (``action_dotted_id:method_name``).
        """
        action_id = cls_qualified_dotted_id(action_cls)
        edges: list[BaseGraphEdge] = []
        for aspect_callable in BaseCallableGraphNode.collect_own_class_callables_for_kind(
            action_cls,
            IntentCallableKind.REGULAR_ASPECT,
        ):
            method_name = BaseCallableGraphNode.resolve_method_name(aspect_callable)
            edges.append(
                BaseGraphEdge(
                    edge_name=method_name,
                    is_dag=False,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    source_node_obj=action_cls,
                    target_node_id=f"{action_id}:{method_name}",
                    target_node_type=RegularAspectGraphNode.NODE_TYPE,
                    target_node_obj=aspect_callable,
                    edge_relationship=COMPOSITION,
                ),
            )
        return edges

    @classmethod
    def get_summary_aspect_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``COMPOSITION`` edge per own-class ``@summary_aspect`` from this action to the matching summary-aspect node.

        Target ids match :class:`SummaryAspectGraphNode` (``action_dotted_id:method_name``).
        """
        action_id = cls_qualified_dotted_id(action_cls)
        edges: list[BaseGraphEdge] = []
        for aspect_callable in BaseCallableGraphNode.collect_own_class_callables_for_kind(
            action_cls,
            IntentCallableKind.SUMMARY_ASPECT,
        ):
            method_name = BaseCallableGraphNode.resolve_method_name(aspect_callable)
            edges.append(
                BaseGraphEdge(
                    edge_name=method_name,
                    is_dag=False,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    source_node_obj=action_cls,
                    target_node_id=f"{action_id}:{method_name}",
                    target_node_type=SummaryAspectGraphNode.NODE_TYPE,
                    target_node_obj=aspect_callable,
                    edge_relationship=COMPOSITION,
                ),
            )
        return edges

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
            is_dag=True,
            source_node_id=cls_qualified_dotted_id(action_cls),
            source_node_type=cls.NODE_TYPE,
            source_node_obj=action_cls,
            target_node_id=cls_qualified_dotted_id(domain_cls),
            target_node_type=DomainGraphNode.NODE_TYPE,
            target_node_obj=domain_cls,
            edge_relationship=ASSOCIATION,
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
        """Optional domain/params/result edges plus regular/summary aspect edges (never ``None`` entries)."""
        optional_edges = (
            cls.get_domain_edge(action_cls),
            cls.get_params_edge(action_cls),
            cls.get_result_edge(action_cls),
        )
        return (
            [e for e in optional_edges if e is not None]
            + cls.get_regular_aspect_edges(action_cls)
            + cls.get_summary_aspect_edges(action_cls)
        )
