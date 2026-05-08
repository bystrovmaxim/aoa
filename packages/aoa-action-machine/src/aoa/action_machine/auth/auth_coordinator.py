# packages/aoa-action-machine/src/aoa/action_machine/auth/auth_coordinator.py
"""
Authentication and context assembly coordinator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Orchestrate the creation of an execution ``Context`` from protocol request data.
The coordinator sequentially invokes credential extraction, authentication, and
metadata assembly, returning a fully populated ``Context`` on success.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    request_data
         |
         v
    CredentialExtractor.extract()
         |
         v
    Authenticator.authenticate()
         |
         v
    ContextAssembler.assemble()
         |
         v
    Context(user=..., request=RequestInfo(...))

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``CredentialExtractor``: protocol-specific credential extraction.
- ``Authenticator``: credential verification and user resolution.
- ``ContextAssembler``: request metadata projection for ``RequestInfo``.
- ``AuthCoordinator``: orchestration pipeline for authenticated context.
- ``NoAuthCoordinator``: explicit open-access context provider.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aoa.action_machine.auth.authenticator import Authenticator
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo


class CredentialExtractor(ABC):
    """Extract protocol credentials for authentication pipeline."""

    @abstractmethod
    async def extract(self, request_data: Any) -> dict[str, Any]:
        """Return credentials dict or empty dict if none."""
        pass


class ContextAssembler(ABC):
    """Assemble request metadata consumed by ``RequestInfo``."""

    @abstractmethod
    async def assemble(self, request_data: Any) -> dict[str, Any]:
        """Return kwargs-compatible dict for ``RequestInfo``."""
        pass


class AuthCoordinator:
    """
AI-CORE-BEGIN
    ROLE: Authentication orchestration coordinator.
    CONTRACT: extract credentials -> authenticate user -> assemble request metadata.
    INVARIANTS: returns Context on success or None when flow cannot continue.
    AI-CORE-END
"""

    def __init__(
        self,
        extractor: CredentialExtractor,
        auth_instance: Authenticator,
        assembler: ContextAssembler,
    ) -> None:
        self.extractor = extractor
        self.authenticator = auth_instance
        self.assembler = assembler

    async def process(self, request_data: Any) -> Context | None:
        """Execute extract/auth/assemble flow and return ``Context`` or ``None``."""
        # Step 1: credential extraction
        credentials = await self.extractor.extract(request_data)
        if not credentials:
            return None

        # Step 2: authentication
        authenticated_user = await self.authenticator.authenticate(credentials)
        if not authenticated_user:
            return None

        # Step 3: metadata collection
        metadata = await self.assembler.assemble(request_data)
        req_info = RequestInfo(**metadata)

        # Step 4: build context
        return Context(user=authenticated_user, request=req_info)


class NoAuthCoordinator:
    """
    Explicit open-access coordinator that bypasses authentication.

    Keeps ``process(request_data)`` API compatibility with ``AuthCoordinator``
    and always returns a fresh anonymous ``Context``.
    """

    async def process(self, request_data: Any) -> Context:
        """Return a fresh anonymous ``Context`` for every call."""
        return Context()
