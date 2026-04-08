# src/action_machine/auth/__init__.py
"""
ActionMachine authentication package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Contains all components of the authentication and authorization system:

- **check_roles** — decorator function for declaring role restrictions on an
  action class. Writes the role specification to ``cls._role_info``.

- **ROLE_NONE** — string marker constant for "authentication not required." The
  action is available to any user, including anonymous users.

- **ROLE_ANY** — string marker constant for "any role is acceptable." The action
  requires authentication, but the specific role is not important.

- **AuthCoordinator** — authentication process coordinator. Combines three
  components: CredentialExtractor → Authenticator → ContextAssembler. It
  sequentially extracts credentials, validates them, and builds a Context with
  user and request information.

- **NoAuthCoordinator** — provider for open APIs. Always returns an anonymous
  Context without a user or roles. Used to explicitly declare the absence of
  authentication.

- **CredentialExtractor** — abstract extractor for credentials from a protocol
  request (HTTP, MCP, etc.).

- **Authenticator** — abstract authenticator. Transforms credentials into user
  information (UserInfo).

- **ContextAssembler** — abstract request metadata assembler
  (trace_id, client_ip, request_path, etc.).

- **RoleGateHost** — marker mixin that enables @check_roles. Inherited by
  BaseAction.

═══════════════════════════════════════════════════════════════════════════════
TYPICAL USAGE
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

═══════════════════════════════════════════════════════════════════════════════
AUTHENTICATION ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

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
