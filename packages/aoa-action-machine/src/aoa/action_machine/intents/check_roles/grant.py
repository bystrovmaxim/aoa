# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aoa.action_machine.auth.base_role import BaseRole

if TYPE_CHECKING:
    # Deferred: access_control transitively imports nearly the whole package (via
    # model.base_schema); grant.py sits inside that same transitive chain (loaded by
    # intents/check_roles/__init__.py), so a top-level import would cycle depending
    # on which module happens to be imported first. The one runtime construction
    # (FailSecurityVerdict("FORBIDDEN_GRANT") below) imports locally instead.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``, with its own optional ``when=`` condition.

    ``reason`` is ``when``'s companion — see :func:`grant`. It travels with
    ``when`` all the way to :class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge`
    (``properties["when_reason"]``), which is where :class:`~aoa.action_machine.runtime.role_checker.RoleChecker`
    reads it back at denial time and passes it straight into the ``AuthorizationError`` it raises.
    """

    role: type[BaseRole]
    when: Callable[..., bool] | None = None
    reason: FailSecurityVerdict | None = None


def grant(
    role: type[BaseRole],
    when: Callable[..., bool] | None = None,
    reason: FailSecurityVerdict | None = None,
) -> Grant:
    """Build a ``Grant``: match ``role``, and if ``when`` is given, only when it returns ``True``.

    ``reason=`` without ``when=`` is meaningless — nothing can reject, so there is
    nothing to explain. ``when=`` without ``reason=`` defaults to
    ``FailSecurityVerdict("FORBIDDEN_GRANT")`` rather than erroring: a developer who
    does not care to write a specific reason gets a generic, framework-owned one
    instead of being forced to invent one.

    Raises:
        TypeError: ``role`` is not a ``BaseRole`` subclass.
        ValueError: ``reason`` was given without ``when``.
    """
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    if reason is not None and when is None:
        raise ValueError("grant(): reason= was given without when= — there is no condition for it to explain.")
    if when is not None and reason is None:
        # pylint: disable-next=import-outside-toplevel
        from aoa.action_machine.intents.access_control import FailSecurityVerdict  # see TYPE_CHECKING note above

        reason = FailSecurityVerdict("FORBIDDEN_GRANT")
    return Grant(role=role, when=when, reason=reason)
