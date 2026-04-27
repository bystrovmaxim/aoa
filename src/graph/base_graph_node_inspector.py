# src/graph/base_graph_node_inspector.py
"""
BaseGraphNodeInspector — abstract base for inspectors that feed :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``NodeGraphCoordinator`` aggregates :class:`~graph.base_graph_node.BaseGraphNode`
rows from inspector **instances**. Concrete subclasses specialize ``TRoot`` (the
axis type, e.g. ``BaseAction``) as ``class Foo(BaseGraphNodeInspector[BaseAction[Any, Any]]): ...``,
implement only :meth:`_get_type_nodes`; :meth:`_get_inspector_type` returns that ``TRoot`` class object.
:meth:`get_graph_nodes` walks the root plus all strict subclasses (see :meth:`_all_descendant_types`).

Inspectors that also participate in the main facet graph typically inherit both
:class:`~graph.base_intent_inspector.BaseIntentInspector` and ``BaseGraphNodeInspector``.
:class:`~graph.base_inspector.BaseInspector` remains the minimal hook type for other
call sites; this class is the **typed** contract for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` only.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    _get_inspector_type()  ->  ``type`` (root class object from ``BaseGraphNodeInspector[TRoot]``)
              │
              v
    _get_type_nodes(root)  +  for each T in _all_descendant_types(root): _get_type_nodes(T)
              │
              v
    get_graph_nodes()  ->  list[BaseGraphNode[Any]]
              │
              v
    NodeGraphCoordinator.build([...])

When a host emits edges to targets that have **no** dedicated inspector axis (no ``type`` to walk),
attach those ``BaseGraphNode`` instances on the host's
:attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` and **also** append the same instances
to the flat list returned from :meth:`get_graph_nodes` so :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
can resolve ``target_node_id``.
"""

from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin

from graph.base_graph_node import BaseGraphNode


class BaseGraphNodeInspector[TRoot](ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract contract for interchange-node emission into ``NodeGraphCoordinator``.
    CONTRACT: Subclasses specialize ``TRoot`` in the base list and implement :meth:`_get_type_nodes` only; :meth:`get_graph_nodes` is final orchestration.
    INVARIANTS: Cannot be instantiated directly; not registered with ``GraphCoordinator`` by itself.
    AI-CORE-END
    """

    @staticmethod
    def _all_descendant_types(root: type) -> tuple[type, ...]:
        """Return all transitive subclasses of ``root`` in deterministic order."""
        if not isinstance(root, type):
            msg = f"root must be a type, not {type(root).__name__}"
            raise TypeError(msg)
        found: list[type] = []
        stack: list[type] = list(root.__subclasses__())
        seen: set[type] = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            found.append(cur)
            stack.extend(cur.__subclasses__())
        found.sort(key=lambda t: (t.__module__, t.__qualname__))
        return tuple(found)

    def _get_inspector_type(self) -> type:
        """Return the root axis type from ``BaseGraphNodeInspector[TRoot]``."""
        owner_cls = type(self)
        bases = getattr(owner_cls, "__orig_bases__", ()) or ()
        for base in bases:
            if get_origin(base) is not BaseGraphNodeInspector:
                continue
            args = get_args(base)
            if len(args) != 1:
                continue
            arg0 = args[0]
            if arg0 is typing.Any:
                msg = (
                    f"{owner_cls.__qualname__} must specialize BaseGraphNodeInspector[T] with a concrete "
                    "axis type T, not typing.Any"
                )
                raise TypeError(msg)
            root = get_origin(arg0) if get_origin(arg0) is not None else arg0
            if not isinstance(root, type):
                msg = f"BaseGraphNodeInspector type argument must resolve to a type, got {root!r}"
                raise TypeError(msg)
            return root
        msg = (
            f"{owner_cls.__qualname__} must inherit BaseGraphNodeInspector[T] with exactly one type argument "
            "(the root axis class object)."
        )
        raise TypeError(msg)

    @abstractmethod
    def _get_type_nodes(self, cls: type) -> list[BaseGraphNode[Any]]:
        """Return interchange nodes for a single concrete or abstract ``cls`` (may be empty)."""

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """Collect nodes for the root axis and all descendant types."""
        root = self._get_inspector_type()
        out: list[BaseGraphNode[Any]] = []
        out.extend(self._get_type_nodes(root))
        for cls in self._all_descendant_types(root):
            out.extend(self._get_type_nodes(cls))
        return out
