# src/action_machine/auth/__init__.py
"""
ActionMachine authentication package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the authentication and authorization system for ActionMachine.
Components include role declaration decorators, authentication coordinators,
and abstract interfaces for credential extraction, verification, and context
assembly.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ┌──────────────────┐     ┌────────────────┐     ┌──────────────────┐
    │ CredentialExtract│ ──▶ │  Authenticator │ ──▶ │ ContextAssembler │
    │ (credential      │     │  (credential   │     │  (metadata       │
    │  extraction)     │     │   verification)│     │   assembly)      │
    └──────────────────┘     └────────────────┘     └──────────────────┘
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │ AuthCoordinator│
                              │ .process()     │ → Context
                              └──────────────┘

Components exported:
- ``check_roles``: decorator for role restrictions, writes ``_role_info``.
- ``ROLE_NONE`` / ``ROLE_ANY``: special role markers.
- ``AuthCoordinator``: orchestrates credential extraction, authentication,
  and context assembly.
- ``NoAuthCoordinator``: explicit no‑authentication provider.
- Abstract bases: ``CredentialExtractor``, ``Authenticator``, ``ContextAssembler``.
- ``RoleGateHost``: marker mixin enabling ``@check_roles``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@check_roles`` requires the target class to inherit ``RoleGateHost``.
- ``ROLE_NONE`` allows anonymous access; ``ROLE_ANY`` requires any authenticated role.
- ``AuthCoordinator`` requires non‑null extractor, authenticator, and assembler.
- ``NoAuthCoordinator`` always returns an anonymous ``Context``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles("admin")
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    @check_roles(["user", "manager"])
    class OrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # AuthCoordinator usage
    auth = AuthCoordinator(extractor, authenticator, assembler)
    context = await auth.process(request)

    # Open API with explicit no‑auth
    auth = NoAuthCoordinator()
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``@check_roles`` is applied to a class missing ``RoleGateHost``.
- ``AuthorizationError`` at runtime when role requirements are not met.
- ``NoAuthCoordinator`` provides no user identity; only works with ``ROLE_NONE`` actions.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Authentication package API surface.
CONTRACT: Export role decorators, markers, coordinators, and abstract interfaces.
INVARIANTS: Metadata written to ``_role_info``; coordinators produce ``Context``.
FLOW: request -> extract -> authenticate -> assemble -> context -> role check.
FAILURES: AuthorizationError at runtime; TypeError for decorator misuse.
EXTENSION POINTS: Implement custom CredentialExtractor/Authenticator/ContextAssembler.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from .auth_coordinator import AuthCoordinator
from .authenticator import Authenticator
from .check_roles import check_roles
from .constants import ROLE_ANY, ROLE_NONE
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor
from .no_auth_coordinator import NoAuthCoordinator
from .role_gate_host import RoleGateHost

__all__ = [
    "ROLE_ANY",
    "ROLE_NONE",
    "AuthCoordinator",
    "Authenticator",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "RoleGateHost",
    "check_roles",
]