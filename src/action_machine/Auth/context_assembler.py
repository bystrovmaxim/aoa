"""
Abstract request metadata collector.

Concrete implementations should extract all metadata from the request object
that will subsequently be used to form RequestInfo in the context.
All methods are asynchronous to allow I/O operations.
"""

from abc import ABC, abstractmethod
from typing import Any


class ContextAssembler(ABC):
    """
    Interface for the metadata collector.

    The assemble method receives the original request object (protocol-specific)
    and returns a dictionary that will be used to create RequestInfo.
    The dictionary may contain fields: trace_id, request_timestamp, client_ip, etc.
    """

    @abstractmethod
    async def assemble(self, request_data: Any) -> dict[str, Any]:
        """
        Asynchronously extracts metadata from the request.

        Args:
            request_data: the request object (e.g., fastapi.Request)

        Returns:
            A dictionary with metadata for subsequent RequestInfo creation.
        """
        pass
