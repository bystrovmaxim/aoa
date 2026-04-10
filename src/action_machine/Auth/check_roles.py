```python
# src/action_machine/auth/check_roles.py
"""
Decorator ``@check_roles`` — declare role requirements for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declare which user roles are required to execute an action. The decorator writes
the role specification to ``cls._role_info``, which is consumed by the inspector
and coordinator. At runtime, ``ActionProductMachine`` compares the spec against
the user's roles and raises ``AuthorizationError`` on mismatch.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles("admin")
          │
          ▼
    cls._role_info = {"spec": "admin"}
          │
          ▼
    RoleGateHostInspector → Snapshot + graph node ``role``
          │
          ▼
    GateCoordinator.get_snapshot(cls, "role")
          │
          ▼
    ActionProductMachine._check_action_roles()
          │
          ▼
    AuthorizationError or pass

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to classes inheriting ``RoleGateHost``.
- ``spec`` must be a non‑empty string, a non‑empty list of strings, ``ROLE_NONE``,
  or ``ROLE_ANY``.
- An empty list or empty string is forbidden.
- The decorator writes ``_role_info`` on the class; the inspector reads it.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles("admin")
    class DeleteUserAction(BaseAction[DeleteParams, DeleteResult]):
        ...

    @check_roles(["user", "manager"])
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles(ROLE_ANY)
    class ProfileAction(BaseAction[ProfileParams, ProfileResult]):
        ...

Edge case (raises ValueError):
    @check_roles([])   # empty list

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError``: applied to non‑class, missing ``RoleGateHost``, invalid spec type.
- ``ValueError``: empty role list, list items not strings.
- The decorator does not validate that roles actually exist; that is deferred to
  runtime or coordinator validation.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role requirement declaration module.
CONTRACT: ``@check_roles(spec)`` writes ``_role_info``; spec may be str, list[str], ROLE_NONE, or ROLE_ANY.
INVARIANTS: Class must inherit RoleGateHost; spec non‑empty; list items strings.
FLOW: decorator -> _role_info -> inspector snapshot -> coordinator -> runtime check.
FAILURES: TypeError / ValueError on invalid declaration.
EXTENSION POINTS: New role markers should follow the same metadata contract.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.role_gate_host import RoleGateHost


def _spec_type_invariant(spec: Any) -> str | list[str]:
    if isinstance(spec, str):
        return spec
    if isinstance(spec, list):
        return spec
    raise TypeError(
        f"@check_roles expects a string or a list of strings, "
        f"got {type(spec).__name__}: {spec!r}."
    )


def _spec_non_empty_list_invariant(spec: str | list[str]) -> None:
    if isinstance(spec, list) and len(spec) == 0:
        raise ValueError(
            "@check_roles: an empty role list was provided. "
            "Specify at least one role or use ROLE_NONE."
        )


def _spec_list_items_are_str_invariant(spec: str | list[str]) -> None:
    if isinstance(spec, list):
        for i, item in enumerate(spec):
            if not isinstance(item, str):
                raise ValueError(
                    f"@check_roles: role list item [{i}] must be a string, "
                    f"got {type(item).__name__}: {item!r}."
                )


def _target_is_class_invariant(cls: Any) -> None:
    if not isinstance(cls, type):
        raise TypeError(
            f"@check_roles can only be applied to a class. "
            f"Got object of type {type(cls).__name__}: {cls!r}."
        )


def _target_inherits_role_gate_host_invariant(cls: type) -> None:
    if not issubclass(cls, RoleGateHost):
        raise TypeError(
            f"@check_roles was applied to class {cls.__name__}, "
            f"which does not inherit RoleGateHost. "
            f"Add RoleGateHost to the inheritance chain."
        )


def check_roles(spec: str | list[str]) -> Any:
    """
    Class-level decorator that declares role requirements for an action.

    ═══════════════════════════════════════════════════════════════════════════
    AI-CORE-BEGIN
    ═══════════════════════════════════════════════════════════════════════════
    ROLE: Public decorator contract for role restrictions.
    CONTRACT: Validate spec and target class, then attach ``_role_info``.
    INVARIANTS: Target must be class and inherit RoleGateHost; spec non‑empty.
    FLOW: validation -> _role_info write -> inspector consumption -> runtime check.
    FAILURES: TypeError / ValueError on contract violation.
    EXTENSION POINTS: Special values ROLE_NONE / ROLE_ANY defined in constants.
    AI-CORE-END
    ═══════════════════════════════════════════════════════════════════════════
    """
    validated_spec = _spec_type_invariant(spec)
    _spec_non_empty_list_invariant(validated_spec)
    _spec_list_items_are_str_invariant(validated_spec)

    def decorator(cls: Any) -> Any:
        _target_is_class_invariant(cls)
        _target_inherits_role_gate_host_invariant(cls)

        cls._role_info = {"spec": validated_spec}
        return cls

    return decorator
```