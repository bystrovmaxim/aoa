# src/action_machine/auth/__init__.py
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
        @role_mode                 includes tuple (composition)
              │
        StringRoleRegistry.resolve("token")   ← runtime: map user role string → type

        Action classes (RoleIntent) + @check_roles(AdminRole | [RoleA, RoleB] | …)
              │
              ├── RoleIntentInspector → facet ``role`` (per action)
              │
              ├── RoleModeIntentInspector → facet ``role_mode`` (lifecycle)
              │
              └── RoleClassInspector → facet ``role_class`` (includes + requires_role)
              │
              ▼
        GateCoordinator.build() → RoleChecker at run time

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@check_roles`` requires the target class to inherit ``RoleIntent``.
- Stored role specs use ``BaseRole`` types only; ``ROLE_NONE`` / ``ROLE_ANY`` are
  sentinel objects. ``StringRoleRegistry`` is for resolving user token strings
  at runtime, not for ``@check_roles`` arguments.
- ``@role_mode`` applies only to ``RoleModeIntent`` subclasses (typically
  ``BaseRole``).
- ``AuthCoordinator`` requires non-null extractor, authenticator, and assembler.
- ``NoAuthCoordinator`` always returns an anonymous ``Context``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import (
        BaseRole,
        RoleMode,
        check_roles,
        role_mode,
        ROLE_NONE,
        ROLE_ANY,
    )

    @role_mode(RoleMode.ALIVE)
    class AdminRole(BaseRole):
        name = "admin"
        description = "Administrator access."
        includes = ()

    @check_roles(AdminRole)
    class AdminAction(BaseAction[...]):
        ...

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[...]):
        ...

    auth = AuthCoordinator(extractor, authenticator, assembler)
    context = await auth.process(request)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``@check_roles`` or ``@role_mode`` is misapplied.
- ``AuthorizationError`` at runtime when role requirements are not met.
- ``NoAuthCoordinator`` provides no user identity; only works with ``ROLE_NONE``
  actions unless you supply roles manually in tests.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Authentication package API surface.
CONTRACT: Export coordinators, role markers, decorators, and protocol bases.
INVARIANTS: Typed role specs; explicit opt-out via ROLE_NONE / NoAuthCoordinator.
FLOW: request → AuthCoordinator → Context → RoleChecker vs @check_roles spec.
FAILURES: AuthorizationError; TypeError for decorator misuse.
EXTENSION POINTS: Custom CredentialExtractor / Authenticator / ContextAssembler.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .auth_coordinator import AuthCoordinator
from .authenticator import Authenticator
from .base_role import BaseRole
from .check_roles import check_roles
from .constants import ROLE_ANY, ROLE_NONE
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor
from .no_auth_coordinator import NoAuthCoordinator
from .role_intent import RoleIntent
from .role_mode import RoleMode, get_declared_role_mode
from .role_mode_decorator import role_mode
from .role_mode_intent import RoleModeIntent
from .string_role_registry import StringRoleRegistry

__all__ = [
    "ROLE_ANY",
    "ROLE_NONE",
    "AuthCoordinator",
    "Authenticator",
    "BaseRole",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "RoleIntent",
    "RoleMode",
    "RoleModeIntent",
    "StringRoleRegistry",
    "check_roles",
    "get_declared_role_mode",
    "role_mode",
]
