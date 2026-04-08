"""
Base class for all authenticators.
Transforms provided credentials into user information.
All methods are asynchronous to allow I/O operations.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..context.user_info import UserInfo


class Authenticator(ABC):
    """
    Base class for all authenticators.

    Concrete implementations must override the asynchronous authenticate method.
    If an implementation does not perform real I/O, it can still be async and
    return the result normally.
    """

    @abstractmethod
    async def authenticate(self, credentials: Any) -> UserInfo | None:
        """
        Asynchronously verifies credentials and returns user information.

        Args:
            credentials: credentials (API key string, login/password, JWT, etc.)

        Returns:
            UserInfo on success, otherwise None.
        """
        pass
