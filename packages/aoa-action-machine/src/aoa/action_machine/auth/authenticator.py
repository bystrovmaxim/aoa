# packages/aoa-action-machine/src/aoa/action_machine/auth/authenticator.py
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

    request -> extractor -> credentials
                             |
                             v
                     Authenticator.authenticate()
                             |
                +------------+------------+
                |                         |
                v                         v
             UserInfo                    None

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aoa.action_machine.context.user_info import UserInfo


class Authenticator(ABC):
    """
AI-CORE-BEGIN
    ROLE: Extension point for credential verification implementations.
    CONTRACT: Implement async ``authenticate(credentials) -> UserInfo | None``.
    INVARIANTS: Return ``None`` for invalid credentials instead of exceptions.
    AI-CORE-END
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
