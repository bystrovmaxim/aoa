```python
# src/action_machine/auth/role_gate_host.py
"""
RoleGateHost — marker mixin for the @check_roles decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the gate‑host marker that enables the ``@check_roles`` decorator.
Classes that inherit ``RoleGateHost`` may declare role restrictions; the
decorator validates this inheritance at application time.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class BaseAction(ABC, RoleGateHost, ...):
        pass

    @check_roles("admin")
    class AdminAction(BaseAction):
        ...

    # @check_roles checks:
    #   issubclass(AdminAction, RoleGateHost) → True
    #   writes cls._role_info = {"spec": "admin"}

    # RoleGateHostInspector reads _role_info → Snapshot → graph node "role"
    # ActionProductMachine reads spec via GateCoordinator.get_snapshot(cls, "role")

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleGateHost`` is a pure marker; it contains no logic, fields, or methods.
- Classes that declare ``@check_roles`` must inherit ``RoleGateHost``.
- The decorator writes ``_role_info`` on the target class; the inspector reads
  it for graph construction.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import RoleGateHost, check_roles

    @check_roles("admin")
    class AdminAction(BaseAction[P, R]):   # BaseAction already inherits RoleGateHost
        ...

Edge case (raises TypeError):
    @check_roles("user")
    class NotAnAction:                     # does not inherit RoleGateHost
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Applying ``@check_roles`` to a class missing ``RoleGateHost`` raises
  ``TypeError`` at import time.
- The marker itself performs no runtime validation; role enforcement is handled
  by ``ActionProductMachine``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Gate‑host marker for role declarations.
CONTRACT: Subclass inclusion required for ``@check_roles``; provides ``_role_info`` slot.
INVARIANTS: Pure marker; decorated classes must be subclasses.
FLOW: decorator check → _role_info write → inspector read → runtime role check.
FAILURES: TypeError on missing inheritance.
EXTENSION POINTS: None (marker only).
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any, ClassVar


class RoleGateHost:
    """
    Marker mixin that enables the ``@check_roles`` decorator.

    Classes lacking this mixin cannot be decorated with ``@check_roles``.
    The decorator stores the role specification in the ``_role_info``
    class variable.
    """

    _role_info: ClassVar[dict[str, Any]]
```