# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.check_roles.reason_validation import require_reason_alongside

if TYPE_CHECKING:
    # Deferred: access_control transitively imports nearly the whole package (via
    # model.base_schema); grant.py sits inside that same transitive chain (loaded by
    # intents/check_roles/__init__.py), so a top-level import would cycle depending
    # on which module happens to be imported first. Only the type annotations below
    # need it -- the one runtime construction lives in reason_validation.py now.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``, with its own optional ``when=`` condition.

    ``reason`` is ``when``'s companion — see :func:`grant`. It travels with
    ``when`` all the way to :class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge`
    (``properties["when_reason"]``), which is where :class:`~aoa.action_machine.runtime.role_checker.RoleChecker`
    reads it back at denial time and passes it straight into the ``AuthorizationError`` it raises.

    ``reason=``'s pairing with ``when=`` (type-checked, required together, defaulted
    when ``when=`` is given alone) is enforced here, in ``__post_init__`` — not only
    in :func:`grant`'s own body — because ``Grant`` is public and importable on its
    own; constructing it directly bypasses any validation that lives solely in the
    factory function (baseverdict-audit finding 1, fourth document). ``grant()``
    itself is now a thin wrapper that only checks ``role``.
    """

    role: type[BaseRole]
    when: Callable[..., bool] | None = None
    reason: FailSecurityVerdict | None = None

    def __post_init__(self) -> None:
        reason = require_reason_alongside(
            self.when, self.reason, condition_name="when", context="Grant", default_reason="FORBIDDEN_GRANT"
        )
        if reason is not self.reason:
            object.__setattr__(self, "reason", reason)


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
    instead of being forced to invent one. Enforced by ``Grant.__post_init__``, not
    here — this function only checks ``role``.

    Raises:
        TypeError: ``role`` is not a ``BaseRole`` subclass.
        ValueError: ``reason`` was given without ``when``.
    """
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    return Grant(role=role, when=when, reason=reason)
