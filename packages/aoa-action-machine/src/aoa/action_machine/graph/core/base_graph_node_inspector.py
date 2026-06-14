# packages/aoa-action-machine/src/aoa/action_machine/graph/core/base_graph_node_inspector.py
"""
BaseGraphNodeInspector — abstract base for inspectors that feed :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``NodeGraphCoordinator`` aggregates :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode`
rows from inspector **instances**. Concrete subclasses specialize ``TRoot`` (the
axis type, e.g. ``BaseAction``) as ``class Foo(BaseGraphNodeInspector[BaseAction[Any, Any]]): ...``,
implement only :meth:`_get_node`; :meth:`_get_inspector_type` returns that ``TRoot`` class object.
:meth:`get_graph_nodes` walks ``root``, then transitive strict subclasses of ``root`` (see :meth:`_all_descendant_types`).
Hosts are omitted before :meth:`_get_node` only when the class declares :func:`~aoa.action_machine.graph.core.exclude_graph_model.exclude_graph_model`
on its own namespace (via :func:`~aoa.action_machine.graph.core.exclude_graph_model.excluded_from_graph_model` — the decorator is never inherited).

Inspectors deliberately **mirror what is already loaded** in the interpreter for the axis (for example every strict subclass under ``root`` that is visited). They are not filters for “junk” vertices: stray test/sample classes that were imported alongside production code belong in the interchange graph until you fix imports, packaging boundaries, or opt hosts out explicitly with ``exclude_graph_model``. A production build surfacing duplicates, cycles, or odd nodes usually means scope pollution to correct upstream.

**One narrow exception** applies to stale redefinitions from interactive environments (e.g. Jupyter). When a class is re-executed in a notebook, Python keeps the old object alive in ``__subclasses__()`` while the module namespace already points to the new one. ``_all_descendant_types`` silently drops such superseded objects via :meth:`_is_stale_redefinition` — this is not “junk filtering” but identity resolution: only the object currently reachable from the module namespace is treated as the live definition.

This ABC is the **typed** contract for :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator` interchange-node inspectors.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    _get_inspector_type()  ->  ``type`` (root class object from ``BaseGraphNodeInspector[TRoot]``)
              │
              v
    for each T in ``(root, *_all_descendant_types(root))``:  (skip if excluded via ``exclude_graph_model``) → :meth:`_get_node`(T)
              │
              v
    get_graph_nodes()  ->  list[BaseGraphNode[Any]]
              │
              v
    NodeGraphCoordinator.build([...])

Hosts can expose additional target nodes through
:meth:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode.get_companion_nodes`; :class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`
adds those companions when assembling the full node set.
"""

from __future__ import annotations

import sys
import typing
from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin

from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model


class BaseGraphNodeInspector[TRoot](ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract contract for interchange-node emission into ``NodeGraphCoordinator``.
    CONTRACT: Subclasses specialize ``TRoot`` in the base list and implement :meth:`_get_node` only; :meth:`get_graph_nodes` is final orchestration; visited hosts reflect the **loaded runtime scope** under ``TRoot`` (subclasses reachable after imports), without hiding stray test/sample types—use packaging, imports, or ``exclude_graph_model`` to sanitize; coordinators surface structural problems as early diagnostics.
    INVARIANTS: Cannot be instantiated directly; must be subclassed for node emission.
    AI-CORE-END
    """

    @staticmethod
    def _is_stale_redefinition(cls: type) -> bool:
        """Return True when ``cls`` has been superseded by a newer definition in its module.

        A class is considered stale only when all of the following hold:
        - its module is present in ``sys.modules``,
        - its ``__qualname__`` contains no ``<locals>`` segment (i.e. not defined inside a function),
        - the qualname resolves to a concrete object in that module,
        - and that object is *not* ``cls`` itself.

        In every other case the class is kept, so the filter is purely additive for
        interactive environments (e.g. Jupyter) and is a no-op in production.
        """
        if "<locals>" in cls.__qualname__:
            return False
        module = sys.modules.get(cls.__module__)
        if module is None:
            return False
        obj: object = module
        for part in cls.__qualname__.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return False
        return obj is not cls

    @staticmethod
    def _all_descendant_types(root: type) -> tuple[type, ...]:
        """Return all transitive strict subclasses of ``root`` (never ``root``), in deterministic order.

        Stale redefinitions (e.g. from Jupyter cell re-runs) are silently excluded via
        :meth:`_is_stale_redefinition` before the result is sorted.
        """
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
        live = [cls for cls in found if not BaseGraphNodeInspector._is_stale_redefinition(cls)]
        live.sort(key=lambda t: (t.__module__, t.__qualname__))
        return tuple(live)

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
        """Return the interchange node for host ``cls``, or ``None`` when omitted."""

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """Collect nodes for axis hosts; skip hosts marked with ``exclude_graph_model`` only."""
        root = self._get_inspector_type()
        out: list[BaseGraphNode[Any]] = []
        for cls in (root, *BaseGraphNodeInspector._all_descendant_types(root)):
            if excluded_from_graph_model(cls):
                continue
            node = self._get_node(cls)
            if node is not None:
                out.append(node)
        return out
