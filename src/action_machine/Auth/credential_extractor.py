# src/action_machine/auth/credential_extractor.py
"""
Abstract credential extraction interface.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for extracting credentials from a protocol‑specific request
object. The extracted dictionary is passed to an ``Authenticator`` for
verification.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    request_data
          │
          ▼
    ┌─────────────────┐
    │CredentialExtract│  → credentials dict
    └─────────────────┘
          │
          ▼
    Authenticator.authenticate(credentials)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``extract`` must be an async method.
- Must return a dictionary (empty if no credentials found).
- Should not raise exceptions; return an empty dict for missing/invalid data.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class BearerTokenExtractor(CredentialExtractor):
        async def extract(self, request: Request) -> dict[str, Any]:
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                return {"token": auth[7:]}
            return {}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The base class does not perform extraction; subclasses must implement.
- Async is mandatory even for synchronous implementations.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract credential extractor interface.
CONTRACT: Subclasses implement async ``extract(request_data) -> dict[str, Any]``.
INVARIANTS: Returns a dict (empty if no credentials); does not raise.
FLOW: request_data -> credentials dict -> Authenticator.
FAILURES: None by contract; subclasses should return empty dict on failure.
EXTENSION POINTS: Implement protocol‑specific credential extraction.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from abc import ABC, abstractmethod
from typing import Any


class CredentialExtractor(ABC):
    """Abstract base class for extracting credentials from a request."""

    @abstractmethod
    async def extract(self, request_data: Any) -> dict[str, Any]:
        """
        Asynchronously extract credentials from the request object.

        Args:
            request_data: the request object (for example, fastapi.Request)

        Returns:
            A dictionary with credentials or an empty dictionary.
        """
        pass
