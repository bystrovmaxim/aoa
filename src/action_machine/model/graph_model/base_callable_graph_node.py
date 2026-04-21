# src/action_machine/model/graph_model/base_callable_graph_node.py
"""
BaseCallableGraphNode — abstract :class:`~graph.base_graph_node.BaseGraphNode` for action-hosted callables.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Shared interchange plumbing for pipeline callables attached to a ``BaseAction``
subclass (regular/summary aspects, compensators, ``@on_error`` handlers, …):
``node_obj`` is always the **callable**; the host action class comes from
:meth:`Introspection.owner_type_for_method`, and the Python method name from
:meth:`Introspection.unwrapped_callable_name`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    :meth:`Introspection.owner_type_for_method`  ->  host class
    :meth:`Introspection.unwrapped_callable_name`  ->  method name for ``label`` / ``node_id`` fragments

    Own-class intent scan: :class:`CallableKind` with
    :meth:`Introspection.collect_own_class_callables_by_callable_kind`.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from typing import Any

from graph.base_graph_node import BaseGraphNode


class BaseCallableGraphNode(BaseGraphNode[Callable[..., Any]], ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract base for interchange nodes whose ``node_obj`` is a callable on a ``BaseAction`` host.
    CONTRACT: Subclasses supply concrete ``NODE_TYPE`` / ``node_id`` rules; host class via :meth:`Introspection.owner_type_for_method`, method name from :meth:`Introspection.unwrapped_callable_name`.
    AI-CORE-END
    """
