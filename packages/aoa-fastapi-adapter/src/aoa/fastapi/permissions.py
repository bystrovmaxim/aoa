# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions.py
"""
Resolver helpers for ``POST /permissions/resolve`` (issue #130, PR 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two small, independent pieces of glue between the wire protocol
(:mod:`aoa.fastapi.permissions_schema`) and the machine's existing
``machine.check_access_decide`` primitive:

- :func:`build_action_index` / :func:`resolve_action_class` — map a wire
  ``operation`` string (an action class's bare ``__name__``, e.g.
  ``"CancelOrderAction"``) to its registered class via the graph, so the
  frontend never has to know a module path. A name shared by two different
  action classes is a configuration error, caught once at index-build time
  (adapter ``build()``), not repeated per request.

- :func:`to_wire` — project the internal ``AccessVerdict`` onto the wire
  ``Verdict`` shape. Deliberately conservative in this PR: ``scope`` only ever
  reports ``"role"`` or ``None`` (never ``"object"``, even when the machine
  really evaluated a level-3 ``access_decide``), and ``entities``/``reason_code``/
  ``expires_at`` stay at their reserved defaults. See PR 8 for why: reporting a
  real object-level verdict is only safe once a rate limit exists to stop it
  from becoming an ID-enumeration oracle.
"""

from __future__ import annotations

from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import AccessVerdict
from aoa.action_machine.model.base_action import BaseAction
from aoa.fastapi.permissions_schema import Verdict


def build_action_index(graph_coordinator: NodeGraphCoordinator) -> dict[str, type[BaseAction]]:  # type: ignore[type-arg]
    """
    Build a ``{bare class name: action class}`` index from every registered action.

    Raises:
        ValueError: two different action classes share the same bare ``__name__``
            (``ActionGraphNode.label``) — a configuration error caught once here,
            at index-build time, rather than silently resolving to the wrong class
            on every matching request.
    """
    index: dict[str, type[BaseAction]] = {}  # type: ignore[type-arg]
    for node in graph_coordinator.get_nodes_by_type(ActionGraphNode.NODE_TYPE):
        name = node.label
        action_class = node.node_obj
        existing = index.get(name)
        if existing is not None and existing is not action_class:
            raise ValueError(
                f"Duplicate action name {name!r}: both {existing!r} and {action_class!r} are "
                "registered under the same operation name. Rename one of the action classes — "
                "the resolver cannot tell them apart on the wire."
            )
        index[name] = action_class
    return index


def resolve_action_class(
    operation: str,
    action_index: dict[str, type[BaseAction]],  # type: ignore[type-arg]
) -> type[BaseAction]:  # type: ignore[type-arg]
    """
    Look up the action class registered under a wire ``operation`` name.

    Raises:
        LookupError: no action is registered under ``operation``. Per-item
            isolation (a ``reason_code`` like ``UNKNOWN_ACTION`` instead of
            failing the whole batch) is PR 2's job, not this one's.
    """
    action_class = action_index.get(operation)
    if action_class is None:
        raise LookupError(f"Unknown operation {operation!r}: no action is registered under this name.")
    return action_class


def to_wire(verdict: AccessVerdict) -> Verdict:
    """
    Project an internal ``AccessVerdict`` onto the wire ``Verdict`` shape.

    ``scope`` is ``"role"`` whenever some cascade level rejected the check
    (``level`` is 1, 2, or 3), and ``None`` when the check passed outright
    (``AccessVerdict`` sets ``level=None`` exactly when ``allowed=True``).
    This PR never reports ``scope: "object"`` even for a real level-3 rejection
    — see the module docstring and PR 8.
    """
    return Verdict(
        allowed=verdict.allowed,
        scope="role" if verdict.level is not None else None,
        level=verdict.level,  # type: ignore[arg-type]
        reason=verdict.reason,
        reason_code=None,
        entities=[],
        expires_at=None,
    )
