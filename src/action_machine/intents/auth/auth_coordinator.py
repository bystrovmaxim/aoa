# src/action_machine/intents/auth/auth_coordinator.py
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

::

    request_data
          │
          ▼
    ┌─────────────────┐
    │CredentialExtract│  → credentials (dict)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Authenticator  │  → UserInfo | None
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ContextAssembler │  → metadata dict
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │     Context     │  (user + request info)
    └─────────────────┘

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The three components (extractor, authenticator, assembler) must be supplied
  and must not be ``None``.
- If any step returns ``None`` or an empty result, the whole process returns
  ``None`` (no context).
- The returned ``Context`` contains at least an anonymous ``UserInfo`` if
  authentication succeeded, and a ``RequestInfo`` built from assembler output.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    extractor = MyCredentialExtractor()
    authenticator = MyAuthenticator()
    assembler = MyContextAssembler()

    coordinator = AuthCoordinator(extractor, authenticator, assembler)
    context = await coordinator.process(request)
    if context:
        user_id = context.user.user_id

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Any exception raised by the components propagates to the caller; the
  coordinator does not catch or handle errors.
- The coordinator is synchronous in its initialization but asynchronous in
  ``process()``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Authentication orchestration module.
CONTRACT: Accept request data, delegate to extractor/authenticator/assembler, return Context or None.
INVARIANTS: All three components required; returns None if any step fails.
FLOW: extract -> authenticate -> assemble -> build Context.
FAILURES: Propagates component exceptions; returns None on missing data.
EXTENSION POINTS: Custom implementations of CredentialExtractor/Authenticator/ContextAssembler.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from action_machine.intents.auth.authenticator import Authenticator
from action_machine.intents.context.context import Context
from action_machine.intents.context.request_info import RequestInfo


class CredentialExtractor(ABC):
    """Extract credentials from a protocol-specific request; used by ``AuthCoordinator``."""

    @abstractmethod
    async def extract(self, request_data: Any) -> dict[str, Any]:
        """Return credentials dict or empty dict if none."""
        pass


class ContextAssembler(ABC):
    """Build request metadata for ``RequestInfo``; used by ``AuthCoordinator``."""

    @abstractmethod
    async def assemble(self, request_data: Any) -> dict[str, Any]:
        """Return kwargs-compatible dict for ``RequestInfo``."""
        pass


class AuthCoordinator:
    """
    Coordinator that manages the creation of execution context.

    Sequentially performs credential extraction, authentication, and request
    metadata assembly.
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
        """Asynchronously perform the full authentication and context assembly flow."""
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
    Explicit “no authentication” coordinator for open APIs.

    Implements the same async ``process(request_data) -> Context`` surface as
    ``AuthCoordinator``, but always returns an anonymous ``Context`` (never
    ``None``). ``request_data`` is ignored.
    """

    async def process(self, request_data: Any) -> Context:
        """Return a fresh anonymous ``Context`` for every call."""
        return Context()
