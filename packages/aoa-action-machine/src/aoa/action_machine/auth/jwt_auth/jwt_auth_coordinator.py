# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_auth_coordinator.py
"""
JwtAuthCoordinator — ready-made AuthCoordinator for Bearer/JWT authentication.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Thin ``AuthCoordinator`` subclass wiring a ``CredentialExtractor``
(``BearerCredentialExtractor`` by default, or a caller-supplied extractor --
e.g. ``CookieCredentialExtractor`` for same-site cookie-based SSO) +
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

    # Same-site cookie transport instead of the "Authorization: Bearer" header --
    # everything else about the pipeline (signature/expiry/roles) is unchanged:
    from aoa.action_machine.auth.jwt_auth import CookieCredentialExtractor

    auth = JwtAuthCoordinator(
        secret_key="...",
        role_registry={"admin": AdminRole},
        credential_extractor=CookieCredentialExtractor(cookie_name="session"),
    )

    # A central identity provider issuing RS256 tokens (Keycloak, Auth0, Google,
    # an in-house token service) instead of a co-deployed secret -- no key
    # material on this consumer at all, zero-downtime rotation via `kid`:
    auth = JwtAuthCoordinator(
        jwks_url="https://sso.example.com/.well-known/jwks.json",
        algorithm="RS256",
        issuer="https://sso.example.com",
        role_registry={"admin": AdminRole},
    )
"""

from __future__ import annotations

from collections.abc import Mapping

from aoa.action_machine.auth.auth_coordinator import AuthCoordinator, ContextAssembler, CredentialExtractor
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.bearer_credential_extractor import BearerCredentialExtractor
from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator


class JwtAuthCoordinator(AuthCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Ready-made AuthCoordinator for JWT authentication over a pluggable credential transport and key source.
    CONTRACT: Construction assembles a CredentialExtractor (BearerCredentialExtractor by default, or the caller-supplied credential_extractor) + JwtAuthenticator + an HTTP ContextAssembler; process() is inherited from AuthCoordinator unchanged. secret_key/jwks_url are forwarded to JwtAuthenticator as-is -- exactly one of the two must be set, or construction raises ValueError.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        jwks_url: str | None = None,
        algorithm: str = "HS256",
        audience: str | None = None,
        issuer: str | None = None,
        role_registry: Mapping[str, type[BaseRole]],
        user_id_claim: str = "sub",
        roles_claim: str = "roles",
        credential_extractor: CredentialExtractor | None = None,
        context_assembler: ContextAssembler | None = None,
    ) -> None:
        super().__init__(
            extractor=credential_extractor or BearerCredentialExtractor(),
            auth_instance=JwtAuthenticator(
                secret_key=secret_key,
                jwks_url=jwks_url,
                algorithm=algorithm,
                audience=audience,
                issuer=issuer,
                role_registry=role_registry,
                user_id_claim=user_id_claim,
                roles_claim=roles_claim,
            ),
            assembler=context_assembler or HttpContextAssembler(),
        )
