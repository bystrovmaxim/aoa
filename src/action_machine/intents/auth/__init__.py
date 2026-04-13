# src/action_machine/intents/auth/__init__.py
"""
ActionMachine authentication package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides authentication coordinators, role **marker types** (``BaseRole``),
decorators (``@check_roles``, ``@role_mode``), and abstract interfaces for
credential extraction, verification, and context assembly.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ┌──────────────────┐     ┌────────────────┐     ┌──────────────────┐
    │ CredentialExtract│ ──▶ │  Authenticator │ ──▶ │ ContextAssembler │
    └────────┬─────────┘     └────────┬───────┘     └────────┬─────────┘
             │                        │                      │
             └────────────────────────┴──────────────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │AuthCoordinator│
                              │  .process()   │ → Context (UserInfo.roles)
                              └──────────────┘

    Role model (types, not strings at runtime in snapshots):

        RoleModeIntent  ◀──  BaseRole  ◀──  your concrete *Role classes
              ▲                      │
              │               @role_mode(RoleMode.…)
              │                      │
        @role_mode                 subclassing (MRO) for implied roles
              │
        ContextAssembler maps external credentials → UserInfo(roles=(…BaseRole types))

        Action classes (RoleIntent) + @check_roles(AdminRole | [RoleA, RoleB] | …)
              │
              ├── RoleIntentInspector → facet ``role`` (per action)
              │
              ├── RoleModeIntentInspector → facet ``role_mode`` (lifecycle)
              │
              └── RoleClassInspector → facet ``role_class`` (requires_role)
              │
              ▼
        GateCoordinator.build() → RoleChecker at run time

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@check_roles`` requires the target class to inherit ``RoleIntent``.
- Stored role specs use ``BaseRole`` types and engine sentinels ``NoneRole`` /
  ``AnyRole``. ``UserInfo.roles`` holds assignable role types only (not sentinels).
- ``@role_mode`` applies only to ``RoleModeIntent`` subclasses (typically
  ``BaseRole``).
- ``AuthCoordinator`` requires non-null extractor, authenticator, and assembler.
- ``NoAuthCoordinator`` always returns an anonymous ``Context``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.auth import (
        AnyRole,
        BaseRole,
        NoneRole,
        RoleMode,
        check_roles,
        role_mode,
    )

    @role_mode(RoleMode.ALIVE)
    class AdminRole(BaseRole):
        name = "admin"
        description = "Administrator access."

    @check_roles(AdminRole)
    class AdminAction(BaseAction[...]):
        ...

    @check_roles(NoneRole)
    class PingAction(BaseAction[...]):
        ...

    auth = AuthCoordinator(extractor, authenticator, assembler)
    context = await auth.process(request)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``@check_roles`` or ``@role_mode`` is misapplied.
- ``AuthorizationError`` at runtime when role requirements are not met.
- ``NoAuthCoordinator`` provides no user identity; only works with ``NoneRole``
  actions unless you supply roles manually in tests.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Authentication package API surface.
CONTRACT: Export coordinators, role markers, decorators, and protocol bases.
INVARIANTS: Typed role specs; explicit opt-out via NoneRole / NoAuthCoordinator.
FLOW: request → AuthCoordinator → Context → RoleChecker vs @check_roles spec.
FAILURES: AuthorizationError; TypeError for decorator misuse.
EXTENSION POINTS: Custom CredentialExtractor / Authenticator / ContextAssembler.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.intents.auth.any_role import AnyRole
from action_machine.intents.auth.auth_coordinator import (
    AuthCoordinator,
    ContextAssembler,
    CredentialExtractor,
    NoAuthCoordinator,
)
from action_machine.intents.auth.authenticator import Authenticator
from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.auth.role_intent import RoleIntent
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.auth.role_mode_intent import RoleModeIntent

__all__ = [
    "AnyRole",
    "AuthCoordinator",
    "Authenticator",
    "BaseRole",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "NoneRole",
    "RoleIntent",
    "RoleMode",
    "RoleModeIntent",
    "check_roles",
    "role_mode",
]
