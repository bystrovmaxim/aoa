# src/action_machine/auth/check_roles.py
"""
Decorator @check_roles — declare role requirements for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The @check_roles decorator is part of ActionMachine's intent grammar. It
declares which user roles are required to execute an action. At runtime,
ActionProductMachine reads the roles from ClassMetadata and compares them with
the roles of the user in the context. If the roles do not match, the action is
rejected with AuthorizationError.

═══════════════════════════════════════════════════════════════════════════════
SPECIAL VALUES
═══════════════════════════════════════════════════════════════════════════════

The special values are defined in ``auth/constants.py`` and re-exported via
``auth/__init__.py``:

    ROLE_NONE — the action does not require authentication. Any user
                (including anonymous) may execute the action.
    ROLE_ANY  — the action requires authentication, but any role is acceptable.

═══════════════════════════════════════════════════════════════════════════════
CONSTRAINTS (INVARIANTS)
═══════════════════════════════════════════════════════════════════════════════

- Applies only to classes, not functions, methods, or properties.
- The class must inherit RoleGateHost — the mixin that enables @check_roles.
- The spec argument must be a string, a list of strings, ROLE_NONE, or ROLE_ANY.
- An empty role list is forbidden — this is most likely an error.

═══════════════════════════════════════════════════════════════════════════════
INTEGRATION ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    @check_roles("admin")
        │
        ▼  Decorator writes to cls._role_info
    {"spec": "admin"}
        │
        ▼  MetadataBuilder → collectors.collect_role(cls)
    ClassMetadata.role = RoleMeta(spec="admin")
        │
        ▼  ActionProductMachine._check_action_roles(...)
    Compares spec against context.user.roles using ROLE_NONE/ROLE_ANY

═══════════════════════════════════════════════════════════════════════════════
USAGE EXAMPLE
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

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    TypeError — decorator applied to a non-class; class does not inherit RoleGateHost;
               spec has an invalid type.
    ValueError — an empty role list was provided; list items are not strings.
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.role_gate_host import RoleGateHost


def check_roles(spec: str | list[str]) -> Any:
    """
    Class-level decorator that declares role requirements for an action.

    Writes the dictionary ``{"spec": spec}`` to the target class attribute
    ``cls._role_info``. MetadataBuilder reads this dictionary when building
    ClassMetadata.role (RoleMeta).

    Args:
        spec: required roles. Valid values:
              - str: a single role ("admin") or a special value (ROLE_NONE, ROLE_ANY).
              - list[str]: multiple roles (["user", "manager"]).

    Returns:
        A decorator that writes _role_info to the class and returns the class
        unchanged.

    Raises:
        TypeError: spec is not a string or a list; decorator applied to a non-class;
                   class does not inherit RoleGateHost.
        ValueError: empty list; list items are not strings.

    Example:
        @check_roles("admin")
        class AdminAction(BaseAction[P, R]):
            ...

        @check_roles(ROLE_NONE)
        class PublicAction(BaseAction[P, R]):
            ...
    """
    # ── Validate spec ──
    if isinstance(spec, str):
        validated_spec: str | list[str] = spec
    elif isinstance(spec, list):
        if len(spec) == 0:
            raise ValueError(
                "@check_roles: an empty role list was provided. "
                "Specify at least one role or use ROLE_NONE."
            )
        for i, item in enumerate(spec):
            if not isinstance(item, str):
                raise ValueError(
                    f"@check_roles: role list item [{i}] must be a string, "
                    f"got {type(item).__name__}: {item!r}."
                )
        validated_spec = spec
    else:
        raise TypeError(
            f"@check_roles expects a string or a list of strings, "
            f"got {type(spec).__name__}: {spec!r}."
        )

    def decorator(cls: Any) -> Any:
        """
        Внутренний декоратор, применяемый к классу.

        Проверяет:
        1. cls — класс (type).
        2. cls наследует RoleGateHost.

        Затем записывает _role_info в cls.
        """
        if not isinstance(cls, type):
            raise TypeError(
                f"@check_roles can only be applied to a class. "
                f"Got object of type {type(cls).__name__}: {cls!r}."
            )

        if not issubclass(cls, RoleGateHost):
            raise TypeError(
                f"@check_roles was applied to class {cls.__name__}, "
                f"which does not inherit RoleGateHost. "
                f"Add RoleGateHost to the inheritance chain."
            )

        cls._role_info = {
            "spec": validated_spec,
        }

        return cls

    return decorator
