# src/action_machine/model/action_node.py
"""
ActionNode — interchange node for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
an action **class** object **without** retaining a reference to that class on the
node instance. All interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``links``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TAction]   (``TAction`` bound to ``BaseAction``)
              │
              v
    ``BaseAction[P, R]``  →  :meth:`get_schema_generic_binding` (or :meth:`get_params_link` / :meth:`get_result_link`)

    ActionNode.parse / ``get_properties`` / ``get_domain_link``  →  frozen ``BaseGraphNode``

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The action class is not stored on :class:`ActionNode` instances (only interchange fields).
- ``label`` is the action class ``__name__``. :meth:`get_properties` fills ``properties``;
  :meth:`get_domain_link`, :meth:`get_params_link`, and :meth:`get_result_link` each return a :class:`~action_machine.graph.base_graph_edge.BaseGraphEdge` or ``None``. :meth:`_get_all_links` collects non-``None`` edges for ``parse``.

  :meth:`get_schema_generic_binding` returns resolved params/result types (or ``None``); :meth:`get_params_link` / :meth:`get_result_link` apply :func:`~action_machine.common.qualified_dotted_name` when building edges.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class MyPingAction(BaseAction): ...
    n = ActionNode(MyPingAction)
    assert n.node_type == "Action" and n.label == "MyPingAction"

Edge case: same interchange shape for any concrete ``BaseAction`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseAction`` subclasses are validated where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseAction`` subclasses.
CONTRACT: ``parse`` builds the node; helpers: :meth:`get_properties`, :meth:`get_domain_link`, :meth:`get_schema_generic_binding` (or :meth:`get_params_link` / :meth:`get_result_link`).
INVARIANTS: Immutable node; no action type reference on the instance.
FLOW: action class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, TypeVar, get_args, get_origin

from action_machine.common import qualified_dotted_name
from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode
from action_machine.model.base_action import BaseAction
from action_machine.runtime.binding.action_generic_params import _resolve_generic_arg

TAction = TypeVar("TAction", bound=BaseAction)


@dataclass(init=False, frozen=True)
class ActionNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: ``get_properties`` / ``get_domain_link`` (``@meta``); ``get_schema_generic_binding`` / ``get_params_link`` / ``get_result_link`` (``BaseAction[P,R]``).
    AI-CORE-END
    """

    @classmethod
    def get_schema_generic_binding(
        cls,
        action_cls: type[TAction],
    ) -> tuple[type | None, type | None]:
        """
        One pass over ``BaseAction[P, R]``: resolved params and result schema **types**.

        Resolves ``P`` and ``R`` from the first parameterized ``BaseAction[P, R]`` base in the
        action MRO (either type may be unresolved → ``None`` on that side).

        Returns:
            ``(params_type, result_type)`` — use :meth:`get_params_link` / :meth:`get_result_link`
            for :class:`~action_machine.graph.base_graph_edge.BaseGraphEdge` with ``qualified_dotted_name`` applied.
        """
        params_type: type | None = None
        result_type: type | None = None
        for klass in action_cls.__mro__:
            for base in getattr(klass, "__orig_bases__", ()):
                if get_origin(base) is BaseAction:
                    args = get_args(base)
                    if len(args) >= 2:
                        params_type = _resolve_generic_arg(args[0], action_cls)
                        result_type = _resolve_generic_arg(args[1], action_cls)
                        break
            else:
                continue
            break
        return params_type, result_type

    @classmethod
    def get_params_link(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Params schema edge, or ``None`` when the params type does not resolve."""
        params_type, _ = cls.get_schema_generic_binding(action_cls)
        if params_type is None:
            return None
        return BaseGraphEdge(
            link_name="params",
            target_id=qualified_dotted_name(params_type),
            is_dag=False,
        )

    @classmethod
    def get_result_link(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Result schema edge, or ``None`` when the result type does not resolve."""
        _, result_type = cls.get_schema_generic_binding(action_cls)
        if result_type is None:
            return None
        return BaseGraphEdge(
            link_name="result",
            target_id=qualified_dotted_name(result_type),
            is_dag=False,
        )

    @classmethod
    def _meta_info_dict(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``_meta_info`` written by ``@meta``, or empty ``dict`` when absent or not a mapping."""
        raw = getattr(action_cls, "_meta_info", None)
        return raw if isinstance(raw, dict) else {}

    @classmethod
    def get_domain_link(
        cls,
        action_cls: type[TAction],
    ) -> BaseGraphEdge | None:
        """Domain edge, or ``None`` when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        meta = cls._meta_info_dict(action_cls)
        dom = meta.get("domain")
        if dom is None:
            return None
        if not isinstance(dom, type) or not issubclass(dom, BaseDomain):
            return None
        return BaseGraphEdge(
            link_name="domain",
            target_id=qualified_dotted_name(dom),
            is_dag=False,
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
    def _get_all_links(cls, action_cls: type[TAction]) -> list[BaseGraphEdge]:
        """From :meth:`get_domain_link`, :meth:`get_params_link`, :meth:`get_result_link` — drops ``None``."""
        return [
            e
            for e in (
                cls.get_domain_link(action_cls),
                cls.get_params_link(action_cls),
                cls.get_result_link(action_cls),
            )
            if e is not None
        ]

    @classmethod
    def parse(cls, action_cls: type[TAction]) -> Any:
        return SimpleNamespace(
            id=qualified_dotted_name(action_cls),
            node_type="Action",
            label=action_cls.__name__,
            properties=cls.get_properties(action_cls),
            links=cls._get_all_links(action_cls),
        )
