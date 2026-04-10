# src/action_machine/auth/authenticator.py
"""
Abstract base class for credential authenticators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the interface for transforming credentials extracted from a request into
a ``UserInfo`` object. Concrete implementations perform the actual verification
(e.g., API key check, JWT validation, database lookup).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The ``AuthCoordinator`` calls ``authenticate(credentials)`` after credential
extraction. The authenticator returns a ``UserInfo`` on success, or ``None`` if
the credentials are invalid.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``authenticate`` must be an async method.
- Must return either a valid ``UserInfo`` instance or ``None``.
- Must not raise exceptions for invalid credentials; return ``None`` instead.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class ApiKeyAuthenticator(Authenticator):
        async def authenticate(self, credentials: dict) -> UserInfo | None:
            api_key = credentials.get("api_key")
            if api_key == "secret":
                return UserInfo(user_id="api-user", roles=["service"])
            return None

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The base class does not perform any validation; that is left to subclasses.
- Async is mandatory even if the implementation is synchronous (use
  ``async def`` and return the result normally).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract authenticator interface.
CONTRACT: Subclasses implement async ``authenticate(credentials) -> UserInfo | None``.
INVARIANTS: Returns None for invalid credentials; does not raise exceptions.
FLOW: credentials -> verification -> UserInfo (or None).
FAILURES: None by contract; subclasses should not raise.
EXTENSION POINTS: Implement custom authentication logic.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from abc import ABC, abstractmethod
from typing import Any

from ..context.user_info import UserInfo


class Authenticator(ABC):
    """
    Abstract base class for all authenticators.

    Concrete implementations must override the asynchronous ``authenticate``
    method.
    """

    @abstractmethod
    async def authenticate(self, credentials: Any) -> UserInfo | None:
        """
        Asynchronously verify credentials and return user information.

        Args:
            credentials: credentials (API key string, login/password, JWT, etc.)

        Returns:
            UserInfo on success, otherwise None.
        """
        pass