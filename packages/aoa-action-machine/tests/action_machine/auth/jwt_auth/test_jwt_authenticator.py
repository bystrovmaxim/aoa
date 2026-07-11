# tests/auth/jwt_auth/test_jwt_authenticator.py
"""Tests for JwtAuthenticator — verify a JWT and resolve claims to UserInfo."""

from __future__ import annotations

import json
import socket
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest.mock import Mock
from urllib.error import URLError

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

_SECRET = "unit-test-secret-key-not-for-production-use"
_ALGORITHM = "HS256"
_JWKS_URL = "https://issuer.example.com/.well-known/jwks.json"


# @role_mode is mandatory here, not optional decoration: the coordinator graph
# walks *every* BaseRole subclass alive in the process (pytest imports all test
# modules into one shared process), and chokes on any role missing _role_mode_info.
@role_mode(RoleMode.ALIVE)
class AdminRole(BaseRole):
    name = "admin"
    description = "Full access."


@role_mode(RoleMode.ALIVE)
class ViewerRole(BaseRole):
    name = "viewer"
    description = "Read-only access."


def _sign(payload: dict[str, Any], *, secret: str = _SECRET, algorithm: str = _ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": "alice",
        "roles": ["admin"],
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    payload.update(overrides)
    return payload


def _make_authenticator(**overrides: Any) -> JwtAuthenticator:
    kwargs: dict[str, Any] = {
        "secret_key": _SECRET,
        "algorithm": _ALGORITHM,
        "role_registry": {"admin": AdminRole, "viewer": ViewerRole},
    }
    kwargs.update(overrides)
    return JwtAuthenticator(**kwargs)


def _make_jwks_authenticator(**overrides: Any) -> JwtAuthenticator:
    kwargs: dict[str, Any] = {
        "jwks_url": _JWKS_URL,
        "algorithm": "RS256",
        "role_registry": {"admin": AdminRole, "viewer": ViewerRole},
    }
    kwargs.update(overrides)
    return JwtAuthenticator(**kwargs)


def _generate_rsa_keypair() -> tuple[str, Any]:
    """Return (private_key_pem, public_key_object) for a fresh, test-only RSA keypair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return private_pem, private_key.public_key()


def _stub_resolved_signing_key(authenticator: JwtAuthenticator, *, key: Any = None, error: Exception | None = None) -> None:
    """Replace the authenticator's PyJWKClient.get_signing_key_from_jwt with a fixed result/error.

    Bypasses the real network call entirely -- the JWKS document is never fetched.
    """
    mock_client = Mock()
    if error is not None:
        mock_client.get_signing_key_from_jwt = Mock(side_effect=error)
    else:
        mock_client.get_signing_key_from_jwt = Mock(return_value=Mock(key=key))
    authenticator._jwks_client = mock_client  # type: ignore[attr-defined]


def _serve_raw_response(body: bytes, *, content_type: str = "application/json") -> str:
    """Start a real, loopback-only HTTP server returning a fixed body; return its URL.

    Used to exercise JwtAuthenticator against genuine HTTP + JSON parsing failure
    modes (malformed body, wrong-shaped JSON) instead of stubbing PyJWKClient
    directly -- those failure modes live inside PyJWT's own fetch/parse code, not
    in anything JwtAuthenticator calls explicitly.
    """

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    return f"http://127.0.0.1:{port}/.well-known/jwks.json"


def _unreachable_url() -> str:
    """A URL nothing listens on -- bind a port, close it immediately, reuse the number."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}/.well-known/jwks.json"


# ═════════════════════════════════════════════════════════════════════════════
# Construction -- secret_key/jwks_url are mutually exclusive and required
# ═════════════════════════════════════════════════════════════════════════════


def test_both_secret_key_and_jwks_url_set_raises_value_error() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        JwtAuthenticator(secret_key=_SECRET, jwks_url=_JWKS_URL, role_registry={})


def test_neither_secret_key_nor_jwks_url_set_raises_value_error() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        JwtAuthenticator(role_registry={})


def test_secret_key_only_constructs_successfully() -> None:
    JwtAuthenticator(secret_key=_SECRET, role_registry={})


def test_jwks_url_only_constructs_successfully() -> None:
    JwtAuthenticator(jwks_url=_JWKS_URL, algorithm="RS256", role_registry={})


def test_jwks_url_with_symmetric_algorithm_raises_value_error() -> None:
    """JWKS publishes public keys -- pairing it with HS256 is a real misconfiguration, not a usable setup."""
    with pytest.raises(ValueError, match="asymmetric algorithm"):
        JwtAuthenticator(jwks_url=_JWKS_URL, algorithm="HS256", role_registry={})


# ═════════════════════════════════════════════════════════════════════════════
# Success
# ═════════════════════════════════════════════════════════════════════════════


async def test_valid_token_resolves_user_id_and_roles() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload())

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.user_id == "alice"
    assert result.roles == (AdminRole,)


async def test_multiple_roles_all_mapped() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles=["admin", "viewer"]))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert set(result.roles) == {AdminRole, ViewerRole}


async def test_unmapped_role_names_are_dropped_not_rejected() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles=["admin", "some_unknown_role"]))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == (AdminRole,)


async def test_malformed_roles_claim_yields_empty_roles_not_failure() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles="not-a-list"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == ()


async def test_missing_roles_claim_yields_empty_roles() -> None:
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["roles"]
    token = _sign(payload)

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == ()


async def test_custom_claim_names() -> None:
    authenticator = _make_authenticator(user_id_claim="user_id", roles_claim="perms")
    now = datetime.now(UTC)
    token = _sign({"user_id": "bob", "perms": ["viewer"], "iat": now, "exp": now + timedelta(minutes=5)})

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.user_id == "bob"
    assert result.roles == (ViewerRole,)


async def test_matching_audience_succeeds() -> None:
    authenticator = _make_authenticator(audience="my-api")
    token = _sign(_valid_payload(aud="my-api"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None


async def test_matching_issuer_succeeds() -> None:
    authenticator = _make_authenticator(issuer="https://issuer.example.com")
    token = _sign(_valid_payload(iss="https://issuer.example.com"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None


async def test_issuer_none_does_not_validate_iss() -> None:
    """Regression: omitting issuer= keeps today's behavior -- iss is not checked at all."""
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(iss="https://anyone-can-claim-this.example.com"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None


async def test_audience_none_but_token_has_aud_returns_none() -> None:
    """Asymmetric with issuer: PyJWT enforces aud whenever present on the token, regardless of audience=."""
    authenticator = _make_authenticator()  # audience=None (default)
    token = _sign(_valid_payload(aud="some-api"))

    result = await authenticator.authenticate({"token": token})

    assert result is None


async def test_jwks_valid_rs256_token_verifies_to_user_info() -> None:
    private_pem, public_key = _generate_rsa_keypair()
    authenticator = _make_jwks_authenticator()
    _stub_resolved_signing_key(authenticator, key=public_key)
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "alice", "roles": ["admin"], "iat": now, "exp": now + timedelta(minutes=30)},
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-kid-1"},
    )

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.user_id == "alice"
    assert result.roles == (AdminRole,)


async def test_jwks_resolved_key_mismatched_signature_returns_none() -> None:
    """The kid resolves to a real key -- just not the one the token was actually signed with."""
    signing_pem, _ = _generate_rsa_keypair()
    _, other_public_key = _generate_rsa_keypair()
    authenticator = _make_jwks_authenticator()
    _stub_resolved_signing_key(authenticator, key=other_public_key)
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "alice", "roles": ["admin"], "iat": now, "exp": now + timedelta(minutes=30)},
        signing_pem,
        algorithm="RS256",
        headers={"kid": "test-kid-1"},
    )

    result = await authenticator.authenticate({"token": token})

    assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Failure -> None, never raises
# ═════════════════════════════════════════════════════════════════════════════


async def test_no_token_in_credentials_returns_none() -> None:
    authenticator = _make_authenticator()
    assert await authenticator.authenticate({}) is None


async def test_expired_token_returns_none() -> None:
    authenticator = _make_authenticator()
    past = datetime.now(UTC) - timedelta(minutes=5)
    token = _sign(_valid_payload(iat=past - timedelta(minutes=30), exp=past))

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_secret_key_returns_none() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(), secret="a-completely-different-unit-test-secret-key")

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_algorithm_returns_none() -> None:
    authenticator = _make_authenticator(algorithm="HS256")
    token = _sign(_valid_payload(), secret=_SECRET + "-padded-for-hs384-min-key-length", algorithm="HS384")

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_audience_returns_none() -> None:
    authenticator = _make_authenticator(audience="my-api")
    token = _sign(_valid_payload(aud="a-different-api"))

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_issuer_returns_none() -> None:
    authenticator = _make_authenticator(issuer="https://issuer.example.com")
    token = _sign(_valid_payload(iss="https://a-different-issuer.example.com"))

    assert await authenticator.authenticate({"token": token}) is None


async def test_jwks_unknown_kid_returns_none() -> None:
    """The kid on the token doesn't match any published key -- PyJWKClientError, fail closed."""
    authenticator = _make_jwks_authenticator()
    _stub_resolved_signing_key(
        authenticator,
        error=jwt.exceptions.PyJWKClientError('Unable to find a signing key that matches: "unknown-kid"'),
    )

    assert await authenticator.authenticate({"token": "irrelevant-placeholder-token"}) is None


async def test_jwks_endpoint_unreachable_returns_none() -> None:
    """The JWKS endpoint is down/unresolvable -- URLError doesn't subclass PyJWTError, fail closed anyway."""
    authenticator = _make_jwks_authenticator()
    _stub_resolved_signing_key(authenticator, error=URLError("Name or service not known"))

    assert await authenticator.authenticate({"token": "irrelevant-placeholder-token"}) is None


async def test_jwks_endpoint_truly_unreachable_returns_none() -> None:
    """Same scenario as above, but through the real, un-mocked jwt.PyJWKClient against a closed port."""
    authenticator = _make_jwks_authenticator(jwks_url=_unreachable_url())

    assert await authenticator.authenticate({"token": "irrelevant-placeholder-token"}) is None


async def test_jwks_malformed_json_response_returns_none() -> None:
    """The endpoint responds, but the body isn't valid JSON at all -- still fails closed, never raises."""
    jwks_url = _serve_raw_response(b"this is not json {{{")
    authenticator = _make_jwks_authenticator(jwks_url=jwks_url)

    assert await authenticator.authenticate({"token": "irrelevant-placeholder-token"}) is None


async def test_jwks_wrong_shaped_json_response_returns_none() -> None:
    """Valid JSON, but not a JWKS document -- a key entry that isn't even a dict."""
    jwks_url = _serve_raw_response(json.dumps({"keys": ["not-a-dict-entry"]}).encode())
    authenticator = _make_jwks_authenticator(jwks_url=jwks_url)

    assert await authenticator.authenticate({"token": "irrelevant-placeholder-token"}) is None


async def test_missing_user_id_claim_returns_none() -> None:
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["sub"]
    token = _sign(payload)

    assert await authenticator.authenticate({"token": token}) is None


async def test_missing_exp_claim_returns_none() -> None:
    """Expiry is mandatory -- a token that never expires is rejected outright."""
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["exp"]
    token = _sign(payload)

    assert await authenticator.authenticate({"token": token}) is None


async def test_malformed_token_returns_none() -> None:
    authenticator = _make_authenticator()
    assert await authenticator.authenticate({"token": "not-a-jwt-at-all"}) is None
