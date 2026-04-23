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

    ``_depends_info`` (``@depends``)  →  :meth:`get_depends_edges`

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, TypeVar, get_args, get_origin

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.introspection_tools import CallableKind, IntentIntrospection, TypeIntrospection
from action_machine.legacy.binding.action_generic_params import _resolve_generic_arg
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import AGGREGATION, ASSOCIATION, COMPOSITION

from .compensator_graph_node import CompensatorGraphNode
from .error_handler_graph_node import ErrorHandlerGraphNode
from .params_graph_node import ParamsGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .result_graph_node import ResultGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionGraphNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: ``get_properties``; ``get_domain_edge`` / ``get_depends_edges`` / ``get_connection_edges`` / ``get_params_edge`` / ``get_result_edge`` each return ``list[BaseGraphEdge]`` (0 or 1 domain edge; 0..N ``@depends`` / ``@connection`` ``ASSOCIATION`` ``is_dag=True``; 0 or 1 params/result ``AGGREGATION``); ``get_regular_aspect_edges`` / ``get_summary_aspect_edges`` / ``get_compensator_edges`` / ``get_error_handler_edges`` (``COMPOSITION``, own-class ``@regular_aspect`` / ``@summary_aspect`` / ``@compensate`` / ``@on_error``).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"

    def __init__(self, action_cls: type[TAction]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(action_cls),
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
    def _depends_target_node_type(cls, dep_cls: type) -> str:
        """Interchange ``target_node_type`` for a ``@depends`` dependency class."""
        if issubclass(dep_cls, BaseAction):
            return cls.NODE_TYPE
        if issubclass(dep_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"

    @classmethod
    def _association_edges_to_declared_types(
        cls,
        action_cls: type[TAction],
        declared_types: list[type],
    ) -> list[BaseGraphEdge]:
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for target_cls in declared_types:
            edges.append(
                BaseGraphEdge(
                    edge_name=target_cls.__name__,
                    is_dag=True,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    source_node_obj=action_cls,
                    target_node_id=TypeIntrospection.full_qualname(target_cls),
                    target_node_type=cls._depends_target_node_type(target_cls),
                    target_node_obj=target_cls,
                    edge_relationship=ASSOCIATION,
                ),
            )
        return edges

    @classmethod
    def get_params_edge(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one params schema edge (``AGGREGATION``); empty when the params type does not resolve."""
        params_type = cls.get_schema_generic_binding(action_cls, 0)
        if params_type is None:
            return []
        return [
            BaseGraphEdge(
                edge_name="params",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=cls.NODE_TYPE,
                source_node_obj=action_cls,
                target_node_id=TypeIntrospection.full_qualname(params_type),
                target_node_type=ParamsGraphNode.NODE_TYPE,
                target_node_obj=params_type,
                edge_relationship=AGGREGATION,
            ),
        ]

    @classmethod
    def get_result_edge(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one result schema edge (``AGGREGATION``); empty when the result type does not resolve."""
        result_type = cls.get_schema_generic_binding(action_cls, 1)
        if result_type is None:
            return []
        return [
            BaseGraphEdge(
                edge_name="result",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=cls.NODE_TYPE,
                source_node_obj=action_cls,
                target_node_id=TypeIntrospection.full_qualname(result_type),
                target_node_type=ResultGraphNode.NODE_TYPE,
                target_node_obj=result_type,
                edge_relationship=AGGREGATION,
            ),
        ]

    @classmethod
    def get_regular_aspect_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``COMPOSITION`` edge per own-class ``@regular_aspect`` from this action to the matching regular-aspect node.

        Target ids match :class:`RegularAspectGraphNode` (``action_dotted_id:method_name``).
        """
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for aspect_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
            action_cls,
            CallableKind.REGULAR_ASPECT,
        ):
            method_name = TypeIntrospection.unwrapped_callable_name(aspect_callable)
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
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for aspect_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
            action_cls,
            CallableKind.SUMMARY_ASPECT,
        ):
            method_name = TypeIntrospection.unwrapped_callable_name(aspect_callable)
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
    def get_compensator_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``COMPOSITION`` edge per own-class ``@compensate`` from this action to the matching compensator node.

        Target ids match :class:`CompensatorGraphNode` (``action_dotted_id:method_name``).
        """
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for compensator_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
            action_cls,
            CallableKind.COMPENSATE,
        ):
            method_name = TypeIntrospection.unwrapped_callable_name(compensator_callable)
            edges.append(
                BaseGraphEdge(
                    edge_name=method_name,
                    is_dag=False,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    source_node_obj=action_cls,
                    target_node_id=f"{action_id}:{method_name}",
                    target_node_type=CompensatorGraphNode.NODE_TYPE,
                    target_node_obj=compensator_callable,
                    edge_relationship=COMPOSITION,
                ),
            )
        return edges

    @classmethod
    def get_error_handler_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``COMPOSITION`` edge per own-class ``@on_error`` from this action to the matching error-handler node.

        Target ids match :class:`ErrorHandlerGraphNode` (``action_dotted_id:method_name``).
        """
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for handler_callable in IntentIntrospection.collect_own_class_callables_by_callable_kind(
            action_cls,
            CallableKind.ON_ERROR,
        ):
            method_name = TypeIntrospection.unwrapped_callable_name(handler_callable)
            edges.append(
                BaseGraphEdge(
                    edge_name=method_name,
                    is_dag=False,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    source_node_obj=action_cls,
                    target_node_id=f"{action_id}:{method_name}",
                    target_node_type=ErrorHandlerGraphNode.NODE_TYPE,
                    target_node_obj=handler_callable,
                    edge_relationship=COMPOSITION,
                ),
            )
        return edges

    @classmethod
    def get_domain_edge(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one domain edge; empty when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        meta_info_dict = IntentIntrospection.meta_info_dict(action_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return []
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return []
        return [
            BaseGraphEdge(
                edge_name="domain",
                is_dag=True,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=cls.NODE_TYPE,
                source_node_obj=action_cls,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                target_node_obj=domain_cls,
                edge_relationship=ASSOCIATION,
            ),
        ]

    @classmethod
    def get_depends_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``ASSOCIATION`` edge per ``@depends`` declaration from this action to the declared class.

        Uses :meth:`~action_machine.introspection_tools.intent_introspection.IntentIntrospection.depends_declared_types`.
        """
        return cls._association_edges_to_declared_types(
            action_cls,
            IntentIntrospection.depends_declared_types(action_cls),
        )

    @classmethod
    def get_connection_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``ASSOCIATION`` edge per ``@connection`` declaration from this action to the resource class.

        Uses :meth:`~action_machine.introspection_tools.intent_introspection.IntentIntrospection.connection_declared_types`.
        """
        return cls._association_edges_to_declared_types(
            action_cls,
            IntentIntrospection.connection_declared_types(action_cls),
        )

    @classmethod
    def get_properties(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = IntentIntrospection.meta_info_dict(action_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def _get_all_edges(cls, action_cls: type[TAction]) -> list[BaseGraphEdge]:
        return (
            cls.get_domain_edge(action_cls)
            + cls.get_depends_edges(action_cls)
            + cls.get_connection_edges(action_cls)
            + cls.get_params_edge(action_cls)
            + cls.get_result_edge(action_cls)
            + cls.get_regular_aspect_edges(action_cls)
            + cls.get_summary_aspect_edges(action_cls)
            + cls.get_compensator_edges(action_cls)
            + cls.get_error_handler_edges(action_cls)
        )
