# src/graph/base_graph_node_inspector.py
"""
BaseGraphNodeInspector — abstract base for inspectors that feed :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``NodeGraphCoordinator`` aggregates :class:`~graph.base_graph_node.BaseGraphNode`
rows from inspector **instances**. Concrete subclasses specialize ``TRoot`` (the
axis type, e.g. ``BaseAction``) as ``class Foo(BaseGraphNodeInspector[BaseAction[Any, Any]]): ...``,
implement only :meth:`_get_node`; :meth:`_get_inspector_type` returns that ``TRoot`` class object.
:meth:`get_graph_nodes` walks the axis ``root`` and all transitive strict subclasses (see :meth:`_all_descendants_in_order`).
Hosts are omitted before :meth:`_get_node` when ``inspect.isabstract(cls)``, when
:func:`~graph.exclude_graph_model.excluded_from_graph_model` is true (hosts may be marked via
:func:`~graph.exclude_graph_model.exclude_graph_model`), or when the host is the generic ABC scaffold ``ExternalServiceResource`` (stripped type parameters)—it carries no coordinator ``@meta`` interchange row unlike concrete subclasses.

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
    for each T in _all_descendants_in_order(root):  (_should_skip_axis_host) → _get_node(T)
              │
              v
    get_graph_nodes()  ->  list[BaseGraphNode[Any]]
              │
              v
    NodeGraphCoordinator.build([...])

Hosts can expose additional target nodes through
:meth:`~graph.base_graph_node.BaseGraphNode.get_companion_nodes`; :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
adds those companions when assembling the full node set.
"""

from __future__ import annotations

import inspect
import typing
from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin

from graph.base_graph_node import BaseGraphNode
from graph.exclude_graph_model import excluded_from_graph_model


class BaseGraphNodeInspector[TRoot](ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract contract for interchange-node emission into ``NodeGraphCoordinator``.
    CONTRACT: Subclasses specialize ``TRoot`` in the base list and implement :meth:`_get_node` only; :meth:`get_graph_nodes` is final orchestration.
    INVARIANTS: Cannot be instantiated directly; not registered with ``GraphCoordinator`` by itself.
    AI-CORE-END
    """

    @staticmethod
    def _all_descendant_types(root: type) -> tuple[type, ...]:
        """Return all transitive strict subclasses of ``root`` (never ``root``), in deterministic order."""
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

    @staticmethod
    def _all_descendants_in_order(root: type) -> tuple[type, ...]:
        """
        Return ``root``, then every strict subclass of ``root`` (deterministic).

        Abstract vs concrete does not affect membership here; callers rely on :meth:`_should_skip_axis_host`.
        """
        return (root, *BaseGraphNodeInspector._all_descendant_types(root))

    @staticmethod
    def _axis_host_base_type(host: type) -> type:
        """Strip ``typing.Generic`` / PEP 695 parameterization to the underlying ``type``."""
        cur = host
        while True:
            origin = get_origin(cur)
            if origin is None:
                return cur
            cur = origin

    @staticmethod
    def _should_skip_axis_host(host: type) -> bool:
        """
        Omit hosts that never emit interchange facets: ABC-abstract classes, classes marked
        with :func:`~graph.exclude_graph_model.exclude_graph_model`, or the bare
        :class:`~action_machine.resources.external_service.external_service_resource.ExternalServiceResource`
        generic (``inspect.isabstract`` is false because it defines no abstractmethods).
        """
        if inspect.isabstract(host):
            return True
        if excluded_from_graph_model(host):
            return True
        # Lazy import: ``graph`` must not eagerly pull ``action_machine.resources`` at module load.
        from action_machine.resources.external_service.external_service_resource import (  # pylint: disable=import-outside-toplevel
            ExternalServiceResource,
        )

        return BaseGraphNodeInspector._axis_host_base_type(host) is ExternalServiceResource

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
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        """Return the interchange node for a single **non-abstract** host ``cls``, or ``None`` when suppressed."""

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """Collect nodes for axis hosts; skip ABC-abstract and generic scaffold types."""
        root = self._get_inspector_type()
        out: list[BaseGraphNode[Any]] = []
        for cls in self._all_descendants_in_order(root):
            if self._should_skip_axis_host(cls):
                continue
            node = self._get_node(cls)
            if node is not None:
                out.append(node)
        return out
