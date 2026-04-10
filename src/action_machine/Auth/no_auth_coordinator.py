# src/action_machine/auth/no_auth_coordinator.py
"""
NoAuthCoordinator — authentication provider for open APIs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide an explicit “no authentication” coordinator that returns an anonymous
``Context`` for every request. Used for public APIs, examples, and health
endpoints where authentication is intentionally absent.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    request_data (ignored)
            │
            ▼
    NoAuthCoordinator.process()
            │
            ▼
    Context(user=UserInfo(user_id=None, roles=[]),
            request=RequestInfo(),
            runtime=RuntimeInfo())

The coordinator implements the same async ``process(request_data) -> Context``
interface as ``AuthCoordinator``, allowing adapters to use it as a drop‑in
replacement.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Always returns a valid ``Context`` (never ``None``).
- The returned ``Context`` contains an anonymous ``UserInfo`` (``user_id=None``,
  ``roles=[]``) and empty request/runtime info.
- The coordinator does not inspect or depend on the incoming ``request_data``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
    from action_machine.contrib.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

    # MCP adapter
    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Does not provide any user identity; actions that require specific roles or
  ``ROLE_ANY`` will fail with ``AuthorizationError``.
- Not suitable for endpoints that need real user context.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: No‑authentication coordinator.
CONTRACT: Async ``process(request_data) -> Context`` returning anonymous context.
INVARIANTS: Always returns non‑null Context; user is anonymous; ignores input.
FLOW: request → process() → anonymous Context.
FAILURES: None (always succeeds).
EXTENSION POINTS: Used wherever an auth coordinator is required but no auth is desired.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any

from action_machine.context.context import Context


class NoAuthCoordinator:
    """
    Authentication provider for open APIs.

    Always returns an anonymous Context without a user or roles.
    Used to explicitly declare the absence of authentication.
    """

    async def process(self, request_data: Any) -> Context:
        """Create an anonymous Context for every request."""
        return Context()
