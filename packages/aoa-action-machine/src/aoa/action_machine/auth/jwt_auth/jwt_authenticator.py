# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_authenticator.py
"""
JwtAuthenticator — verify a JWT and resolve it to a UserInfo.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Authenticator`` implementation that verifies a JWT's signature, expiry, and
(optionally) audience via PyJWT, then extracts ``user_id`` and ``roles`` from
configured claims. Role names inside the token are plain strings; ``role_registry``
maps each known name to the ``BaseRole`` subclass ``UserInfo.roles`` expects.
Unmapped names are dropped, not rejected — a token may legitimately carry role
names that mean nothing to this particular service.

Any verification failure (expired, bad signature, wrong audience, malformed
token, missing ``exp`` claim, missing/empty user id claim) returns ``None`` —
per the ``Authenticator`` contract, invalid credentials are ``None``, never an
exception.

Issuing tokens (login) is out of scope for this class — an application's own
``LoginAction`` signs tokens with PyJWT directly; ``JwtAuthenticator`` only
verifies them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import jwt

from aoa.action_machine.auth.authenticator import Authenticator
from aoa.action_machine.auth.base_role import BaseRole

if TYPE_CHECKING:
    from aoa.action_machine.context.user_info import UserInfo


class JwtAuthenticator(Authenticator):
    """
    AI-CORE-BEGIN
    ROLE: Verify a JWT (signature, expiry, optional audience) and build UserInfo from its claims.
    CONTRACT: Any verification or shape failure returns None; never raises. A token with no ``exp`` claim at all is rejected — expiry is mandatory, not merely checked when present.
    INVARIANTS: algorithms allowlist passed to jwt.decode is exactly one algorithm — the one this authenticator was configured with, never the token's own alg header.
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
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._audience = audience
        self._role_registry = role_registry
        self._user_id_claim = user_id_claim
        self._roles_claim = roles_claim

    async def authenticate(self, credentials: Any) -> UserInfo | None:
        from aoa.action_machine.context.user_info import UserInfo  # pylint: disable=import-outside-toplevel

        token = credentials.get("token")
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                options={"require": ["exp"]},
            )
        except jwt.PyJWTError:
            return None

        user_id = payload.get(self._user_id_claim)
        if not user_id:
            return None

        raw_roles = payload.get(self._roles_claim)
        roles = (
            tuple(self._role_registry[name] for name in raw_roles if name in self._role_registry)
            if isinstance(raw_roles, list)
            else ()
        )

        return UserInfo(user_id=str(user_id), roles=roles)
