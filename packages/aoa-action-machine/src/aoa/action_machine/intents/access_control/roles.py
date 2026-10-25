# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/roles.py
"""
Role matching for ``@check_roles`` — the engine that answers for the roles step.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` compares the declared role specification — the single
``spec`` ``@check_roles`` wrote on the class, read back through
:class:`~aoa.action_machine.intents.check_roles.check_roles_intent_resolver.CheckRolesIntentResolver` —
against the authenticated user's role types. The declaration is the source: the
cascade needs no graph to ask this question, and the graph carries the same facts
for anyone who reads it. Matching uses ``issubclass(user_role, required)``;
``RoleMode.SILENCED`` user roles are ignored entirely.

The step answers one question — "does the caller hold a role the operation
lists" — and it answers it with ``Refused(gate=CHECK_ROLES)`` or with ``None``.
It never evaluates a condition and never raises for a decision. A sentinel inside
a declaration keeps the meaning it has alone: ``GuestRole`` among the alternatives
makes the whole declaration open, and ``AnyRole`` among them requires the caller
to hold at least one role that is not silenced.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    CheckRolesIntentResolver.resolve_check_roles(action_cls)  →  type | tuple[type, …]
              │
              ├── GuestRole among the alternatives  ──▶ None (open)
              ├── AnyRole among them, no active role ──▶ Refused(CHECK_ROLES)
              │
              └── type | tuple[type, …]
                        │
                        ▼
              any issubclass(user_role, required) over the caller's active roles ?
                        │
                        ├── yes ──▶ None — the caller may continue
                        └── no  ──▶ Refused(CHECK_ROLES)

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: role matching and the single word that refuses it.

OUT: raising for the caller, any reason text — the role step carries no reason
because no condition decided the refusal — and every object rule, which belongs to
``@access_decide`` and its own step.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.access_control.gate import Gate
from aoa.action_machine.intents.access_control.refused import Refused
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode
from aoa.action_machine.model.base_action import BaseAction


class RoleChecker:
    """Enforces ``@check_roles`` from the declared role spec and user role types."""

    def check(
        self,
        context: Context,
        action_cls: type[BaseAction[Any, Any]],
    ) -> Refused | None:
        """Answer for the roles the caller holds.

        Returns ``Refused`` naming ``CHECK_ROLES``, or ``None`` when the caller may
        continue. A sentinel keeps the meaning it has alone: ``GuestRole`` anywhere in
        the declaration opens it, ``AnyRole`` anywhere in it requires at least one role
        that is not silenced.

        Raises:
            MissingCheckRolesError: the operation declares no roles at all — a build-time
                mistake, caught while the capability is assembled.
        """
        spec = CheckRolesIntentResolver.resolve_check_roles(action_cls)
        alternatives = spec if isinstance(spec, tuple) else (spec,)

        if GuestRole in alternatives:
            return None

        active = _active_user_roles(context.user.roles)

        if AnyRole in alternatives:
            return None if active else Refused(gate=Gate.CHECK_ROLES)

        if any(any(issubclass(user_role, required) for user_role in active) for required in alternatives):
            return None

        return Refused(gate=Gate.CHECK_ROLES)


def _active_user_roles(
    user_roles: tuple[type[BaseRole], ...],
) -> list[type[BaseRole]]:
    """Drop role types that are ``RoleMode.SILENCED``."""
    out: list[type[BaseRole]] = []
    for rt in user_roles:
        if RoleMode.declared_for(rt) is RoleMode.SILENCED:
            continue
        out.append(rt)
    return out
