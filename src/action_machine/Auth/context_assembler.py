# src/action_machine/auth/context_assembler.py
"""
Abstract request metadata collector.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the interface for extracting request metadata (trace ID, client IP,
path, etc.) from protocol‑specific request objects. The assembled dictionary is
used to populate ``RequestInfo`` in the execution context.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The ``AuthCoordinator`` calls ``assemble(request_data)`` after successful
authentication. The returned dict is passed to the ``RequestInfo`` constructor,
and the resulting object becomes part of the ``Context`` returned to the adapter.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``assemble`` must be an async method.
- Must return a dictionary that can be unpacked into ``RequestInfo`` fields.
- Should not raise exceptions; return an empty dict if metadata is unavailable.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class HttpContextAssembler(ContextAssembler):
        async def assemble(self, request: Request) -> dict[str, Any]:
            return {
                "trace_id": request.headers.get("X-Trace-Id"),
                "client_ip": request.client.host,
                "request_path": request.url.path,
                "request_method": request.method,
            }

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The base class does not perform any validation; implementations must ensure
  the returned dict contains valid ``RequestInfo`` field names.
- Async is mandatory even if the implementation is synchronous.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract context assembler interface.
CONTRACT: Subclasses implement async ``assemble(request_data) -> dict[str, Any]``.
INVARIANTS: Returns a dict compatible with ``RequestInfo``; does not raise.
FLOW: request_data -> metadata dict -> RequestInfo -> Context.
FAILURES: None by contract; subclasses should handle missing data gracefully.
EXTENSION POINTS: Implement protocol‑specific metadata extraction.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from abc import ABC, abstractmethod
from typing import Any


class ContextAssembler(ABC):
    """
    Interface for the metadata collector.

    The assemble method receives the original request object (protocol‑specific)
    and returns a dictionary used to create ``RequestInfo``.
    """

    @abstractmethod
    async def assemble(self, request_data: Any) -> dict[str, Any]:
        """
        Asynchronously extract metadata from the request.

        Args:
            request_data: the request object (e.g., fastapi.Request)

        Returns:
            A dictionary with metadata for subsequent ``RequestInfo`` creation.
        """
        pass