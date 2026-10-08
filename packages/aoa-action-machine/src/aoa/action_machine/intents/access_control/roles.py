# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/roles.py
"""
Role matching for ``@check_roles`` — the engine that answers for the roles step.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` compares declared role requirements — the grants
``@check_roles`` wrote on the class, read back through
:class:`~aoa.action_machine.intents.check_roles.check_roles_intent_resolver.CheckRolesIntentResolver` —
against the authenticated user's role types. The declaration is the source: the cascade
needs no graph to ask this question, and the graph carries the same facts for anyone
who reads it. Matching uses
``issubclass(user_role, required)``; ``RoleMode.SILENCED`` user roles are ignored
entirely.

It **answers** — ``Refused`` naming the gate, or ``None`` when the caller may
continue — and never raises for a decision. ``TypeError`` is reserved for a
declaration it cannot read, which is a build-time mistake rather than something
about the caller:

- ``Refused(gate=CHECK_ROLES)`` — the caller holds none of the roles the operation lists;
- ``Refused(gate=WHEN)`` — a listed role is held, but the condition that grant declared refused.

Grants are tried in declaration order, ``any()`` semantics: the first grant whose role
matches *and* whose ``when=`` (if any) returns ``True`` wins — a grant whose role
matches but whose ``when=`` returns ``False`` is skipped, not fatal, so a later grant
can still win.

The shared ``guard=`` is deliberately **not** part of this answer. It is evaluated by
the cascade's own step (``aoa.action_machine.intents.access_control.cascade.guard_answer``),
so that "a matched role's condition refused" and "the operation's shared condition
refused" stay two different words.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    CheckRolesIntentResolver.resolve_grants(action_cls)  →  [Grant(role, when), …]
              │
              ├── GuestRole → allow unless its own when= refuses  ──▶ Refused(WHEN)
              ├── AnyRole  → require ≥1 non-SILENCED role type    ──▶ Refused(CHECK_ROLES)
              │
              └── type | tuple[type, …]
                        │
                        ▼
              RoleMode.declared_for → skip if SILENCED
                        │
                        ▼
              issubclass(user_role, required) ?  ── no role matched ──▶ Refused(CHECK_ROLES)
                        │
                        ▼
              grant.when(context.user) ?  ── matched, condition refused ──▶ Refused(WHEN)
                        │
                        ▼
                      None — the caller may continue

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: role matching, each matching grant's own condition, and the words that tell the
two refusals apart.

OUT: the shared ``guard=`` (its own step), raising for the caller, and any reason
text — the framework names the gate and lets the developer declare the rest.
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
from aoa.action_machine.intents.check_roles.grant import Grant
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode
from aoa.action_machine.model.base_action import BaseAction


class RoleChecker:
    """Enforces ``@check_roles`` using ``ActionGraphNode`` role edges and user role types."""

    @staticmethod
    def _spec_from_grants(grants: list[Grant]) -> Any:
        """Rebuild the ``@check_roles`` spec shape from the grants, in their own order."""
        parts = [grant.role for grant in grants]
        if len(parts) == 1:
            return parts[0]
        return tuple(parts)

    def check(
        self,
        context: Context,
        action_cls: type[BaseAction[Any, Any]],
        params: Any = None,
    ) -> Refused | None:
        """Answer for the roles the caller holds and for each matching grant's ``when=``.

        Returns ``Refused`` naming ``CHECK_ROLES`` or ``WHEN``, or ``None`` when the caller may
        continue. The shared ``guard=`` is deliberately not part of this answer: the cascade
        asks for it in a step of its own, so the two conditions stay distinguishable.

        Raises:
            MissingCheckRolesError: the operation declares no roles at all — a build-time
                mistake, caught while the capability is assembled.
            TypeError: the declaration cannot be read as roles at all.
        """
        grants = CheckRolesIntentResolver.resolve_grants(action_cls)
        role_spec = self._spec_from_grants(grants)

        if role_spec is GuestRole or role_spec is AnyRole:
            return self._sentinel_answer(context, grants, role_spec)
        if isinstance(role_spec, tuple) or (isinstance(role_spec, type) and issubclass(role_spec, BaseRole)):
            return self._concrete_answer(context, grants, role_spec)
        raise TypeError(f"Invalid reconstructed @check_roles spec: {role_spec!r} " f"({type(role_spec).__name__}).")

    @classmethod
    def _sentinel_answer(
        cls,
        context: Context,
        grants: list[Grant],
        role_spec: Any,
    ) -> Refused | None:
        """``GuestRole``/``AnyRole`` — exactly one grant, no role-matching search needed.

        ``grant(GuestRole, when=..., reason=...)``/``grant(AnyRole, when=..., reason=...)`` are
        valid declarations
        (both sentinels are ordinary ``BaseRole`` subclasses as far as ``grant()`` is
        concerned) and must not be silently ignored just because the sentinel itself
        bypasses role matching.
        """
        if role_spec is AnyRole and not _active_user_roles(context.user.roles):
            return Refused(gate=Gate.CHECK_ROLES)

        when = grants[0].when
        if when is not None and not when(context.user):
            return Refused(gate=Gate.WHEN, reason=grants[0].reason)
        return None

    @classmethod
    def _concrete_answer(
        cls,
        context: Context,
        grants: list[Grant],
        role_spec: Any,
    ) -> Refused | None:
        """A single role type or an OR-tuple of role types — search grants in order."""
        _ = role_spec
        active = _active_user_roles(context.user.roles)
        role_matched = False
        refused_reason: str | None = None
        for grant in grants:
            if not any(_user_role_grants_requirement(ur, grant.role) for ur in active):
                continue
            role_matched = True
            when = grant.when
            if when is not None and not when(context.user):
                if refused_reason is None:
                    refused_reason = grant.reason
                continue
            return None

        return _denial_answer(role_matched, refused_reason)


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


def _user_role_grants_requirement(user_role: type[BaseRole], required: type[BaseRole]) -> bool:
    if RoleMode.declared_for(user_role) is RoleMode.SILENCED:
        return False
    return issubclass(user_role, required)


def _denial_answer(role_matched: bool, refused_reason: str | None = None) -> Refused:
    """The word that tells "no listed role held" from "a matching role's condition refused".

    A condition always declares the reason it refuses with, so ``WHEN`` — the word for
    "a matching role's condition refused" — carries one. ``CHECK_ROLES`` means no listed
    role was held at all: no condition decided that, so there is nothing to explain and
    the answer carries the word alone (FR-012).
    """
    if role_matched:
        return Refused(gate=Gate.WHEN, reason=refused_reason)
    return Refused(gate=Gate.CHECK_ROLES)
