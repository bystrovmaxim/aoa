# src/action_machine/auth/no_auth_coordinator.py
"""
NoAuthCoordinator — authentication provider for open APIs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

NoAuthCoordinator is an explicit implementation of AuthCoordinator that creates
an anonymous Context for every request. It is used for APIs that do not require
authentication: public services, examples, health check endpoints.

The developer cannot "forget" to configure authentication because the
auth_coordinator parameter is required in BaseAdapter. For open APIs, the
developer intentionally passes NoAuthCoordinator(), explicitly declaring the
absence of authentication in code.

═══════════════════════════════════════════════════════════════════════════════
ANONYMOUS CONTEXT
═══════════════════════════════════════════════════════════════════════════════

NoAuthCoordinator.process() always returns a Context with:
- user: UserInfo(user_id=None, roles=[]) — anonymous user.
- request: empty RequestInfo.
- runtime: empty RuntimeInfo.

This ensures that ActionProductMachine._check_action_roles() behaves correctly:
actions with @check_roles(ROLE_NONE) pass, while actions requiring specific
roles are rejected with AuthorizationError.

═══════════════════════════════════════════════════════════════════════════════
USAGE EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
    from action_machine.contrib.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

    # For MCP:
    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )
"""

from typing import Any

from action_machine.context.context import Context


class NoAuthCoordinator:
    """
    Authentication provider for open APIs.

    Always returns an anonymous Context without a user or roles.
    Used to explicitly declare the absence of authentication.

    Implements the same interface as AuthCoordinator:
    async method process(request_data) -> Context.
    """

    async def process(self, request_data: Any) -> Context:
        """
        Creates an anonymous Context for every request.

        Does not perform any checks. Always returns a Context with empty
        UserInfo (user_id=None, roles=[]).

        Args:
            request_data: request data (ignored).

        Returns:
            Context — anonymous execution context.
        """
        return Context()
