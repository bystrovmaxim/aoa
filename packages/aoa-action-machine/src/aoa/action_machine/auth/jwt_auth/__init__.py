# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/__init__.py
"""
Bearer/JWT authentication — ready-made coordinator gated behind the ``[jwt]`` extra.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Consume ``Authorization: Bearer <jwt>`` on every request and turn it into a
``Context`` — signature/expiry verified, ``UserInfo`` built from configured
claims. Issuing the token (the login side) is out of scope: an application's
own ``LoginAction`` signs tokens directly with PyJWT; this package only
verifies them.

Never imported from ``aoa.action_machine.auth`` (the core, always-available
namespace) — importing this subpackage explicitly is what opts into the
PyJWT dependency.

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install "aoa-action-machine[jwt]"

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``BearerCredentialExtractor``: pulls the token out of ``Authorization: Bearer ...``.
- ``JwtAuthenticator``: verifies signature/expiry/audience, maps claims to ``UserInfo``.
- ``HttpContextAssembler``: default ``RequestInfo`` projection for HTTP requests.
- ``JwtAuthCoordinator``: ``AuthCoordinator`` pre-wired with the three pieces above.
"""

try:
    import jwt  # noqa: F401
except ImportError:
    raise ImportError(
        "To use aoa.action_machine.auth.jwt_auth, install the optional dependency: "
        'pip install "aoa-action-machine[jwt]"'
    ) from None

from aoa.action_machine.auth.jwt_auth.bearer_credential_extractor import BearerCredentialExtractor
from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
from aoa.action_machine.auth.jwt_auth.jwt_auth_coordinator import JwtAuthCoordinator
from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator

__all__ = [
    "BearerCredentialExtractor",
    "HttpContextAssembler",
    "JwtAuthCoordinator",
    "JwtAuthenticator",
]
