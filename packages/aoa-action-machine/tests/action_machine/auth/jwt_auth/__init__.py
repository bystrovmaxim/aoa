# tests/auth/jwt_auth/__init__.py
"""
Tests for the Bearer/JWT ready-made coordinator (``aoa.action_machine.auth.jwt_auth``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers the ``[jwt]`` extra: extracting a Bearer token from a request, verifying
a JWT and resolving it to ``UserInfo``, projecting HTTP request metadata into
``RequestInfo`` kwargs, and the ``JwtAuthCoordinator`` that wires all three into
a ready-to-use ``AuthCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/auth/jwt_auth/
    ├── test_bearer_credential_extractor.py — Authorization: Bearer <token> parsing
    ├── test_http_context_assembler.py      — RequestInfo kwargs from an HTTP request
    ├── test_jwt_authenticator.py           — signature/expiry/audience verification, role mapping
    └── test_jwt_auth_coordinator.py        — full pipeline wired end to end via a FastAPI app
"""
