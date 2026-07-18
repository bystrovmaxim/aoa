# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aoa.action_machine.auth.base_role import BaseRole


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``, with its own optional ``when=`` condition.

    ``reason`` is ``when``'s mandatory companion — see :func:`grant`. It travels with
    ``when`` all the way to :class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge`
    (``properties["when_reason"]``), which is where :class:`~aoa.action_machine.runtime.role_checker.RoleChecker`
    reads it back at denial time.
    """

    role: type[BaseRole]
    when: Callable[..., bool] | None = None
    reason: str | None = None


def grant(role: type[BaseRole], when: Callable[..., bool] | None = None, reason: str | None = None) -> Grant:
    """Build a ``Grant``: match ``role``, and if ``when`` is given, only when it returns ``True``.

    ``when=`` and ``reason=`` are given together or not at all: a condition that can
    reject the request must also say why, so the denial reported at runtime is a
    string the author chose on purpose — never a guess reconstructed after the fact.
    ``reason=""`` counts as not given — an empty string is not a reason.

    Raises:
        TypeError: ``role`` is not a ``BaseRole`` subclass.
        ValueError: ``when`` was given without a non-empty ``reason``, or vice versa.
    """
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    if (when is None) != (not reason):
        raise ValueError(
            "grant(): when= and reason= must be given together, or not at all — "
            f"got when={when!r}, reason={reason!r}."
        )
    return Grant(role=role, when=when, reason=reason)
