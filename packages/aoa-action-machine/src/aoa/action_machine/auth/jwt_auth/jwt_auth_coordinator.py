# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_auth_coordinator.py
"""
JwtAuthCoordinator — ready-made AuthCoordinator for Bearer/JWT authentication.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Thin ``AuthCoordinator`` subclass wiring ``BearerCredentialExtractor`` +
``JwtAuthenticator`` + ``HttpContextAssembler`` (or a caller-supplied assembler)
into one ready-to-pass ``auth_coordinator=`` for ``FastApiAdapter``/``McpAdapter``.
No new ``process()`` logic — reuses the inherited
``extract -> authenticate -> assemble -> Context`` pipeline unchanged.

Issuing tokens (login) is out of scope: an application's own ``LoginAction``
signs tokens with PyJWT directly; this coordinator only verifies them on every
subsequent request.

    from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator

    auth = JwtAuthCoordinator(secret_key="...", role_registry={"admin": AdminRole})
    FastApiAdapter(machine=machine, auth_coordinator=auth).post("/orders", CreateOrderAction).build()
"""

from __future__ import annotations

from collections.abc import Mapping

from aoa.action_machine.auth.auth_coordinator import AuthCoordinator, ContextAssembler
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.bearer_credential_extractor import BearerCredentialExtractor
from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator


class JwtAuthCoordinator(AuthCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Ready-made AuthCoordinator for the "Authorization: Bearer <jwt>" scheme.
    CONTRACT: Construction assembles BearerCredentialExtractor + JwtAuthenticator + an HTTP ContextAssembler; process() is inherited from AuthCoordinator unchanged.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        audience: str | None = None,
        role_registry: Mapping[str, type[BaseRole]],
        user_id_claim: str = "sub",
        roles_claim: str = "roles",
        context_assembler: ContextAssembler | None = None,
    ) -> None:
        super().__init__(
            extractor=BearerCredentialExtractor(),
            auth_instance=JwtAuthenticator(
                secret_key=secret_key,
                algorithm=algorithm,
                audience=audience,
                role_registry=role_registry,
                user_id_claim=user_id_claim,
                roles_claim=roles_claim,
            ),
            assembler=context_assembler or HttpContextAssembler(),
        )
