# src/action_machine/auth/auth_coordinator.py
"""
Authentication and context assembly coordinator.

Combines credential extraction, authentication, and metadata collection.
All methods are asynchronous because they delegate work to async components.
"""

from typing import Any

# Strict and explicit imports instead of facades
from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo

from .authenticator import Authenticator
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor


class AuthCoordinator:
    """
    Coordinator that manages the creation of execution context.

    It sequentially performs:
    1. credential extraction from the request.
    2. authentication (credential verification).
    3. request metadata assembly.
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
        """
        Asynchronously performs the full authentication and context assembly flow.
        """
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
        return Context(
            user=authenticated_user,
            request=req_info
        )
