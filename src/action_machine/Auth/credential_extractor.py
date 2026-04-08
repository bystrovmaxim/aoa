"""
Base class for extracting credentials from a request.
All methods are asynchronous to allow I/O operations.
"""

from abc import ABC, abstractmethod
from typing import Any


class CredentialExtractor(ABC):
    """
    Base class for extracting credentials from a request.

    Concrete implementations must override the asynchronous extract method.
    If extraction does not require I/O, async def is still sufficient.
    """

    @abstractmethod
    async def extract(self, request_data: Any) -> dict[str, Any]:
        """
        Asynchronously extracts credentials from the request object.

        Args:
            request_data: the request object (for example, fastapi.Request)

        Returns:
            A dictionary with credentials or an empty dictionary.
        """
        pass
