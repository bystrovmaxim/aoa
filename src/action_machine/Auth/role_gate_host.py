# src/action_machine/auth/role_gate_host.py
"""
Module: RoleGateHost — marker mixin for the @check_roles decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

RoleGateHost is a marker mixin that allows the @check_roles decorator to be
applied to a class. During decorator application, the check is:

    if not issubclass(cls, RoleGateHost):
        raise TypeError("Class must inherit RoleGateHost")

Without inheriting from RoleGateHost, @check_roles raises TypeError. This
prevents accidental application of role restrictions to classes that are not
actions.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,                   ← marker: allows @check_roles
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
    ): ...

    @check_roles("admin")
    class AdminAction(BaseAction[P, R]):
        ...

    # @check_roles validates:
    #   issubclass(AdminAction, RoleGateHost) → True → OK
    #   Writes: cls._role_info = {"spec": "admin"}

    # MetadataBuilder.build(AdminAction) reads:
    #   cls._role_info → RoleMeta(spec="admin")

    # ActionProductMachine:
    #   metadata = coordinator.get(AdminAction)
    #   metadata.role.spec → "admin"
"""

from typing import Any, ClassVar


class RoleGateHost:
    """
    Marker mixin that enables the @check_roles decorator.

    A class that does NOT inherit RoleGateHost cannot be the target of
    @check_roles — the decorator raises TypeError on application.

    The mixin does not contain logic, fields, or methods. Its only purpose is
    to serve as a marker for issubclass() checks.

    Class-level attributes (created dynamically by the decorator):
        _role_info : dict | None
            Dictionary {"spec": str | list[str]} written by the
            @check_roles decorator. MetadataBuilder reads it when building
            ClassMetadata.role (RoleMeta).
    """

    # Annotation for mypy (created by the decorator)
    _role_info: ClassVar[dict[str, Any]]
