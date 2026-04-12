# src/action_machine/auth/role_mode_decorator.py
"""
Class decorator that attaches lifecycle mode scratch to role declaration classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@role_mode`` stores ``RoleMode`` on a role class so ``RoleChecker`` and graph
inspectors share one source of truth (``cls._role_mode_info``), analogous to
how ``@check_roles`` writes ``_role_info`` on actions.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The decorated class must inherit ``RoleModeIntent`` (``TypeError`` otherwise).
- The decorator sets ``cls._role_mode_info`` to a mapping containing at least
  ``"mode"`` → ``RoleMode`` member.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @role_mode(RoleMode.ALIVE)
    class ExampleRole(BaseRole):
        ...

    → ExampleRole._role_mode_info == {"mode": RoleMode.ALIVE}

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: decorate a ``BaseRole`` subclass.

Edge case: decorate ``object`` → ``TypeError`` mentioning ``RoleModeIntent``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Does not validate ``name`` / ``description``; ``BaseRole.__init_subclass__``
  handles declarative metadata.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role lifecycle decorator (symmetric to ``@check_roles`` on actions).
CONTRACT: Guard MRO; write ``_role_mode_info`` with ``mode`` key.
INVARIANTS: Target must subclass ``RoleModeIntent``.
FLOW: Import-time class object → augmented class returned to definition scope.
FAILURES: TypeError when intent missing from MRO.
EXTENSION POINTS: Inspectors read the same scratch during ``build()``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from action_machine.auth.role_mode import RoleMode
from action_machine.auth.role_mode_intent import RoleModeIntent

_RT = TypeVar("_RT", bound=type[RoleModeIntent])


def role_mode(mode: RoleMode) -> Callable[[_RT], _RT]:
    """
    Attach ``RoleMode`` metadata to a role class (``_role_mode_info``).

    Must be applied to classes that inherit ``RoleModeIntent`` (e.g. via
    ``BaseRole``).
    """

    def decorator(cls: _RT) -> _RT:
        if not isinstance(cls, type):
            raise TypeError(f"@role_mode applies only to classes, got {type(cls)!r}.")
        if not issubclass(cls, RoleModeIntent):
            raise TypeError(
                f"@role_mode was applied to {cls.__name__!r}, which does not inherit "
                f"RoleModeIntent. Role classes must extend BaseRole (or another "
                f"RoleModeIntent subtype)."
            )
        cls._role_mode_info = {"mode": mode}
        return cls

    return decorator
