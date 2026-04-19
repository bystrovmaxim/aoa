# src/action_machine/intents/auth/check_roles_decorator.py
"""
Decorator ``@check_roles`` — declare role requirements for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declare which **role types** are required to execute an action. The decorator
writes a normalized specification to ``cls._role_info["spec"]``, consumed by
``RoleIntentInspector`` and ``ActionProductMachine`` / ``RoleChecker``. The
spec must be ``NoneRole``, ``AnyRole``, a ``BaseRole`` subclass, or a
non-empty list of ``BaseRole`` subclasses (OR semantics). ``Context.user.roles``
holds the same ``BaseRole`` subclasses assigned to the user.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AdminRole)
            |
            v
    normalize spec to role-type contract
            |
            v
    cls._role_info = {"spec": ...}
            |
            +--> mode validation (UNUSED error, DEPRECATED warning)
            |
            v
    RoleIntentInspector -> role facet snapshot
            |
            v
    RoleChecker at runtime

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``check_roles``: public class decorator for action role requirements.
- ``_normalize_check_roles_spec``: accepted-shape validator + canonicalizer.
- ``_validate_required_role_modes``: compile-time mode checks for declared roles.
- Target invariants: ensure class target and ``RoleIntent`` inheritance.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to classes inheriting ``RoleIntent``.
- ``spec`` may be: ``NoneRole``, ``AnyRole``, a ``BaseRole`` subclass, or a
  non-empty ``list`` of ``BaseRole`` subclasses (homogeneous types only).
- Stored ``spec`` is always ``NoneRole``, ``AnyRole``, exactly one
  ``BaseRole`` subtype, or a **tuple** of ``BaseRole`` subtypes (OR semantics).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.auth import AnyRole, NoneRole, check_roles
    from action_machine.auth.base_role import BaseRole
    from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

    @role_mode(RoleMode.ALIVE)
    class AdminRole(BaseRole):
        name = "admin"
        description = "Administrator."

    @check_roles(AdminRole)
    class DeleteUserAction(BaseAction[...]):
        ...

    @check_roles([AdminRole, EditorRole])
    class PublishAction(BaseAction[...]):
        ...

    @check_roles(NoneRole)
    class PingAction(BaseAction[...]):
        ...

Edge case: ``@check_roles([])`` → ``ValueError``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError``: non-class target, missing ``RoleIntent``, invalid spec type,
  non-``BaseRole`` type, or heterogeneous list.
- ``ValueError``: empty list, or a required role is ``RoleMode.UNUSED``.
- ``DeprecationWarning``: a required role is ``RoleMode.DEPRECATED``.
- Does not prove global role topology; ``RoleClassInspector`` and
  ``RoleModeIntentInspector`` run at ``GraphCoordinator.build()``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Action role-requirement declaration module.
CONTRACT: ``@check_roles(spec)`` writes normalized ``_role_info`` for facet ``role``.
INVARIANTS: Target inherits RoleIntent; stored spec uses types + engine sentinels.
FLOW: decorator → normalize → _role_info → inspector.
FAILURES: TypeError / ValueError; ``DeprecationWarning`` for deprecated roles.
EXTENSION POINTS: N/A.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import warnings
from typing import Any

from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole
from action_machine.intents.auth.role_intent import RoleIntent
from action_machine.intents.role_mode.role_mode_decorator import RoleMode


def _normalize_check_roles_spec(spec: Any) -> Any:
    if spec is NoneRole or spec is AnyRole:
        return spec

    if isinstance(spec, str):
        raise TypeError(
            "@check_roles does not accept role name strings; pass a BaseRole "
            f"subclass, not {spec!r}. Use NoneRole or AnyRole for sentinel modes."
        )

    if isinstance(spec, type):
        if not issubclass(spec, BaseRole):
            raise TypeError(
                f"@check_roles expected a BaseRole subclass, got {spec!r}."
            )
        return spec

    if isinstance(spec, list):
        if len(spec) == 0:
            raise ValueError(
                "@check_roles: an empty role list was provided. "
                "Specify at least one role or use NoneRole."
            )
        if any(isinstance(x, str) for x in spec):
            raise TypeError(
                "@check_roles does not accept list[str]; use a list of BaseRole "
                "subclasses only."
            )
        if not all(isinstance(x, type) for x in spec):
            raise TypeError(
                "@check_roles: role list must contain only BaseRole subclasses; "
                f"got {spec!r}."
            )
        bad = [x for x in spec if not issubclass(x, BaseRole)]
        if bad:
            raise TypeError(
                "@check_roles: every list element must be a BaseRole "
                f"subclass; offending values: {bad!r}."
            )
        return tuple(spec)

    raise TypeError(
        f"@check_roles expects NoneRole, AnyRole, a BaseRole type, or a non-empty "
        f"list of BaseRole types; got {type(spec).__name__}: {spec!r}."
    )


def _validate_required_role_modes(normalized: Any) -> None:
    """Reject ``UNUSED``; warn on ``DEPRECATED`` (``RoleChecker`` enforces ``SILENCED``)."""
    if normalized in (NoneRole, AnyRole):
        return
    reqs: tuple[type[BaseRole], ...] = (
        (normalized,) if isinstance(normalized, type) else normalized
    )
    for r in reqs:
        mode = RoleMode.declared_for(r)
        if mode is RoleMode.UNUSED:
            raise ValueError(
                f"@check_roles cannot require role {r.__qualname__!r}: "
                f"it is marked RoleMode.UNUSED."
            )
        if mode is RoleMode.DEPRECATED:
            warnings.warn(
                f"@check_roles references deprecated role {r.__qualname__!r}.",
                DeprecationWarning,
                stacklevel=3,
            )


def _target_is_class_invariant(cls: Any) -> None:
    if not isinstance(cls, type):
        raise TypeError(
            f"@check_roles can only be applied to a class. "
            f"Got object of type {type(cls).__name__}: {cls!r}."
        )


def _target_inherits_role_intent_invariant(cls: type) -> None:
    if not issubclass(cls, RoleIntent):
        raise TypeError(
            f"@check_roles was applied to class {cls.__name__}, "
            f"which does not inherit RoleIntent. "
            f"Add RoleIntent to the inheritance chain."
        )


def check_roles(spec: Any) -> Any:
    """
    Class-level decorator that declares role requirements for an action.

    See module docstring for accepted ``spec`` shapes and normalization rules.
    """
    normalized = _normalize_check_roles_spec(spec)
    _validate_required_role_modes(normalized)

    def decorator(cls: Any) -> Any:
        _target_is_class_invariant(cls)
        _target_inherits_role_intent_invariant(cls)

        cls._role_info = {"spec": normalized}
        return cls

    return decorator
