# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_authenticator.py
"""
JwtAuthenticator — verify a JWT and resolve it to a UserInfo.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Authenticator`` implementation that verifies a JWT's signature, expiry, and
(optionally) audience/issuer via PyJWT, then extracts ``user_id`` and ``roles``
from configured claims. Role names inside the token are plain strings;
``role_registry`` maps each known name to the ``BaseRole`` subclass
``UserInfo.roles`` expects. Unmapped names are dropped, not rejected — a token
may legitimately carry role names that mean nothing to this particular service.

Two verification-key sources, mutually exclusive:

- ``secret_key``: a single static key (HS256 within one service, or a mounted
  RS256/ES256 public key). Rotating it invalidates every outstanding token at
  once.
- ``jwks_url``: an OIDC-style JWKS endpoint (RFC 7517). The token's ``kid``
  header selects which published key verifies it, so the issuer can publish
  old+new keys, sign new tokens with the new key, and retire the old one only
  after outstanding tokens expire — zero-downtime rotation, no key material on
  the consumer at all. Requires ``PyJWT[crypto]`` (RS256/ES256 verification
  needs the ``cryptography`` package). Only meaningful with an asymmetric
  ``algorithm`` (RS*/PS*/ES*/EdDSA) — JWKS publishes public keys, so pairing
  it with a symmetric algorithm (HS256/HS384/HS512) is rejected at
  construction, not silently accepted.

Any verification failure (expired, bad signature, wrong audience, wrong
issuer, malformed token, missing ``exp`` claim, missing/empty user id claim,
unresolvable JWKS key, JWKS endpoint unreachable, malformed JWKS document)
returns ``None`` — per the ``Authenticator`` contract, invalid credentials are
``None``, never an exception. JWKS resolution and token verification both
catch broadly (not just ``PyJWTError``): the JWKS response is untrusted
external input, and its failure modes span network errors, JSON parsing, and
third-party key parsing — not a fixed, enumerable exception set.

Issuing tokens (login) is out of scope for this class — an application's own
``LoginAction`` signs tokens with PyJWT directly; ``JwtAuthenticator`` only
verifies them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import jwt
from jwt.algorithms import requires_cryptography

from aoa.action_machine.auth.authenticator import Authenticator
from aoa.action_machine.auth.base_role import BaseRole

if TYPE_CHECKING:
    from aoa.action_machine.context.user_info import UserInfo


class JwtAuthenticator(Authenticator):
    """
    AI-CORE-BEGIN
    ROLE: Verify a JWT (signature, expiry, optional audience/issuer) against a static key or a JWKS endpoint, and build UserInfo from its claims.
    CONTRACT: Exactly one of secret_key/jwks_url must be given -- both or neither raises ValueError at construction; jwks_url with a symmetric algorithm also raises ValueError. Any verification, key-resolution, or shape failure returns None; never raises. A token with no ``exp`` claim at all is rejected -- expiry is mandatory, not merely checked when present.
    INVARIANTS: algorithms allowlist passed to jwt.decode is exactly one algorithm -- the one this authenticator was configured with, never the token's own alg header.
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
    ) -> None:
        if (secret_key is None) == (jwks_url is None):
            raise ValueError(
                "JwtAuthenticator requires exactly one of secret_key or jwks_url -- got "
                f"secret_key={'<set>' if secret_key is not None else None}, jwks_url={jwks_url!r}."
            )
        if jwks_url is not None and algorithm not in requires_cryptography:
            raise ValueError(
                f"jwks_url requires an asymmetric algorithm (RS*/PS*/ES*/EdDSA); got algorithm={algorithm!r}. "
                "JWKS publishes public keys -- pairing it with a symmetric algorithm (HS256/HS384/HS512) is "
                "not a meaningful configuration."
            )
        self._secret_key = secret_key
        self._jwks_client = jwt.PyJWKClient(jwks_url, cache_jwk_set=True) if jwks_url is not None else None
        self._algorithm = algorithm
        self._audience = audience
        self._issuer = issuer
        self._role_registry = role_registry
        self._user_id_claim = user_id_claim
        self._roles_claim = roles_claim

    async def authenticate(self, credentials: Any) -> UserInfo | None:
        from aoa.action_machine.context.user_info import UserInfo  # pylint: disable=import-outside-toplevel

        token = credentials.get("token")
        if not token:
            return None

        if self._jwks_client is not None:
            try:
                signing_key: str | bytes = self._jwks_client.get_signing_key_from_jwt(token).key
            except Exception:
                # Unknown/missing kid, endpoint unreachable, malformed JWKS document (bad
                # JSON, wrong shape) -- PyJWKClient's own failure modes span PyJWTError,
                # urllib.error.URLError, json.JSONDecodeError, and plain AttributeError on
                # a malformed key entry, none of which is a fixed, enumerable set. All fail
                # closed to "invalid credentials", never an unhandled exception -- this is
                # untrusted external input (the JWKS response), not a programming error.
                return None
        else:
            signing_key = self._secret_key  # type: ignore[assignment]  # not None: XOR-validated in __init__

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp"]},
            )
        except Exception:
            # Same fail-closed reasoning as above -- jwt.decode's own failure surface
            # (PyJWTError and its subclasses) is what's expected, but this is still
            # untrusted external input driving a security decision.
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
