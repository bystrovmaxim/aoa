# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/grant.py
"""``grant`` — associate a role with an optional per-role condition for ``@check_roles``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aoa.action_machine.auth.base_role import BaseRole


@dataclass(frozen=True)
class Grant:
    """One role alternative inside ``@check_roles``, with its own optional ``when=`` condition."""

    role: type[BaseRole]
    when: Callable[..., bool] | None = None


def grant(role: type[BaseRole], when: Callable[..., bool] | None = None) -> Grant:
    """Build a ``Grant``: match ``role``, and if ``when`` is given, only when it returns ``True``."""
    if not isinstance(role, type) or not issubclass(role, BaseRole):
        raise TypeError(f"grant() expected a BaseRole subclass, got {role!r}.")
    return Grant(role=role, when=when)
