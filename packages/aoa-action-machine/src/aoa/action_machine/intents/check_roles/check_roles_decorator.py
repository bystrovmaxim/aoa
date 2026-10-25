# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_decorator.py
"""
Decorator ``@check_roles`` — declare role requirements for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declare which **role types** are required to execute an action. The decorator
writes one normalized specification to ``cls._role_info["spec"]``, consumed by
:class:`~aoa.action_machine.intents.access_control.roles.RoleChecker` and by
:class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge`. The spec is
a ``BaseRole`` subclass, a tuple of ``BaseRole`` subclasses (OR semantics), or the
``GuestRole`` / ``AnyRole`` sentinel — a sentinel may stand alone or beside ordinary
roles, where it keeps the meaning it has alone. ``Context.user.roles`` holds the
``BaseRole`` subclasses assigned to the user.

``@check_roles`` declares roles only. The condition layer it once carried
(``grant(...)``, ``when=``, ``guard=``, ``guard_reason=``) is gone: a condition
belongs in the operation's ``@access_decide`` method. The three removed keywords
are still refused here, at class definition, with a message that points at
``@access_decide`` rather than a bare ``TypeError``, so a migrating author is told
where the rule goes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AdminRole)
    @check_roles(CustomerRole, AdminRole)
    @check_roles(GuestRole, CustomerRole)
            |
            v
    normalize to role-type contract, deduplicate by identity in order
            |
            v
    cls._role_info = {"spec": ...}
            |
            +--> mode validation (UNUSED error, DEPRECATED warning)
            |
            v
    Interchange ``RoleGraphEdge`` (one per distinct role) + ``RoleChecker`` at runtime

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``check_roles``: public class decorator for action role requirements.
- ``_normalize_spec``: accepted-shape validator + canonicalizer for the whole
  declaration (one or more role arguments, or one tuple/list); collapses duplicates.
- ``_normalize_role``: the single-argument shape — a role type, a sentinel, or a
  non-empty tuple/list of role types.
- ``_removed_keyword_message``: the migration sentence for ``guard``/``guard_reason``/``when``.
- ``_validate_required_role_modes``: compile-time mode checks for declared roles.
- Target invariants: ensure class target.

"""
from __future__ import annotations

import warnings
from typing import Any

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.exceptions.decorator_argument_value_error import DecoratorArgumentValueError
from aoa.action_machine.exceptions.decorator_target_error import DecoratorTargetError
from aoa.action_machine.exceptions.role_spec_type_error import RoleSpecTypeError
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode


def _normalize_role(spec: Any) -> Any:
    """Normalize one accepted role argument into a role type or a tuple of role types."""
    if spec is GuestRole or spec is AnyRole:
        return spec

    if isinstance(spec, str):
        raise RoleSpecTypeError(
            "@check_roles does not accept role name strings; pass a BaseRole "
            f"subclass, not {spec!r}. Use GuestRole or AnyRole for sentinel modes."
        )

    if isinstance(spec, type):
        if not issubclass(spec, BaseRole):
            raise RoleSpecTypeError(f"@check_roles expected a BaseRole subclass, got {spec!r}.")
        return spec

    if isinstance(spec, (list, tuple)):
        if len(spec) == 0:
            raise DecoratorArgumentValueError(
                "@check_roles: an empty role collection was provided. "
                "Specify at least one role or use GuestRole."
            )
        if any(isinstance(x, str) for x in spec):
            raise RoleSpecTypeError("@check_roles does not accept str; use BaseRole subclasses only.")
        if not all(isinstance(x, type) for x in spec):
            raise RoleSpecTypeError(f"@check_roles: role collection must contain only BaseRole subclasses; got {spec!r}.")
        bad = [x for x in spec if not issubclass(x, BaseRole)]
        if bad:
            raise RoleSpecTypeError(
                f"@check_roles: every collection element must be a BaseRole subclass; offending values: {bad!r}."
            )
        return tuple(spec)

    raise RoleSpecTypeError(
        f"@check_roles expects GuestRole, AnyRole, a BaseRole type, or a non-empty "
        f"collection of BaseRole types; got {type(spec).__name__}: {spec!r}."
    )


def _dedupe_roles(roles: tuple[type[BaseRole], ...]) -> tuple[type[BaseRole], ...]:
    """Collapse duplicate roles by identity, preserving first-declaration order."""
    seen: list[type[BaseRole]] = []
    for role in roles:
        if role not in seen:
            seen.append(role)
    return tuple(seen)


def _normalize_spec(specs: tuple[Any, ...]) -> Any:
    """Validate and canonicalize the whole declaration into one spec shape."""
    if len(specs) == 0:
        raise RoleSpecTypeError("@check_roles requires at least one role.")

    if len(specs) == 1:
        normalized = _normalize_role(specs[0])
        roles = normalized if isinstance(normalized, tuple) else (normalized,)
    else:
        roles = tuple(specs)
        for role in roles:
            if not (isinstance(role, type) and issubclass(role, BaseRole)):
                raise RoleSpecTypeError(
                    f"@check_roles expected BaseRole subclasses, got {role!r}. "
                    "Conditions moved to @access_decide; a role declaration is roles only."
                )

    roles = _dedupe_roles(roles)
    return roles[0] if len(roles) == 1 else roles


def _removed_keyword_message(unsupported: dict[str, Any]) -> str:
    """Migration sentence for the keywords the removed condition layer used."""
    names = ", ".join(repr(k) for k in ("guard", "guard_reason", "when") if k in unsupported)
    return (
        f"@check_roles declares roles only; {names} belonged to the removed condition layer. "
        "Move the condition into the operation's @access_decide method and return "
        'Refused("REASON") or FORBIDDEN_OBJECT for the branch that used to refuse.'
    )


def _validate_required_role_modes(normalized: Any) -> None:
    """Reject ``UNUSED``; warn on ``DEPRECATED`` (``RoleChecker`` enforces ``SILENCED``)."""
    if normalized is GuestRole or normalized is AnyRole:
        return
    reqs: tuple[type[BaseRole], ...] = (normalized,) if isinstance(normalized, type) else normalized
    for r in reqs:
        if r is GuestRole or r is AnyRole:
            continue
        mode = RoleMode.declared_for(r)
        if mode is RoleMode.UNUSED:
            raise RoleSpecTypeError(
                f"@check_roles cannot require role {r.__qualname__!r}: it is marked RoleMode.UNUSED."
            )
        if mode is RoleMode.DEPRECATED:
            warnings.warn(
                f"@check_roles references deprecated role {r.__qualname__!r}.",
                DeprecationWarning,
                stacklevel=3,
            )


def _target_is_class_invariant(cls: Any) -> None:
    if not isinstance(cls, type):
        raise DecoratorTargetError(
            f"@check_roles can only be applied to a class. Got object of type {type(cls).__name__}: {cls!r}."
        )


def check_roles(*specs: Any, **unsupported: Any) -> Any:
    """
    Class-level decorator that declares the roles required to run an action.

    Accepted: one or more ``BaseRole`` subclasses (a sentinel included), or, as the
    only argument, a non-empty tuple/list of ``BaseRole`` subclasses. Several
    positional roles and a tuple of roles mean the same thing — a choice where any
    alternative is enough, and a sentinel keeps the meaning it has alone.

    Removed: ``grant(...)``/``Grant`` no longer exist; the keywords ``guard=``,
    ``guard_reason=`` and ``when=`` are refused here with a message naming
    ``@access_decide``. A condition now lives in the operation's ``@access_decide``
    method.
    """
    if unsupported:
        removed = [k for k in ("guard", "guard_reason", "when") if k in unsupported]
        if removed:
            raise RoleSpecTypeError(_removed_keyword_message(unsupported))
        raise RoleSpecTypeError(
            f"@check_roles got unsupported keyword(s) {sorted(unsupported)!r}; a role declaration takes roles only."
        )

    normalized_spec = _normalize_spec(specs)
    _validate_required_role_modes(normalized_spec)

    def decorator(cls: Any) -> Any:
        _target_is_class_invariant(cls)

        cls._role_info = {"spec": normalized_spec}
        return cls

    return decorator
