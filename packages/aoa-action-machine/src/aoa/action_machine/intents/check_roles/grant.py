# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.check_roles.reason_validation import require_reason_alongside


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``: an optional ``when=`` condition and its ``reason=``."""

    role: type[BaseRole]
    when: Callable[..., bool] | None = None
    reason: str | None = None


def grant(
    role: type[BaseRole],
    when: Callable[..., bool] | None = None,
    reason: str | None = None,
) -> Grant:
    """Build a ``Grant``: match ``role``, and if ``when`` is given, only when it returns ``True``.

    ``reason`` is what the caller is told when that condition refuses; it belongs to
    this grant alone, so each alternative can explain itself differently.
    """
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    require_reason_alongside(when, reason, condition_name="when", reason_name="reason")
    return Grant(role=role, when=when, reason=reason)
