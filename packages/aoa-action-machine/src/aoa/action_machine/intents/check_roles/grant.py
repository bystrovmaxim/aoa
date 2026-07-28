# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.check_roles.reason_validation import require_reason_alongside

if TYPE_CHECKING:
    # Deferred: access_control pulls in most of the package, and that chain leads back
    # here, so importing it at the top raises ImportError.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``: the role, plus an optional condition
    the caller must also satisfy, plus the reason to give when that condition says no.

    The reason travels with the condition all the way to the moment of refusal, so the
    denial can explain itself in the developer's own words.

    Pairing the two is checked here rather than only in :func:`grant`, because ``Grant``
    can be built directly and would otherwise skip the check entirely.
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

    Raises:
        TypeError: ``role`` is not a ``BaseRole`` subclass.
        ValueError: ``reason`` was given without ``when``.
    """
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    return Grant(role=role, when=when, reason=reason)
