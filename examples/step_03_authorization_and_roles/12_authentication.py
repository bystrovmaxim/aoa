"""A verified token becomes a user with role classes."""

from __future__ import annotations

import asyncio
import time

import jwt
from starlette.requests import Request

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator

# %% Setup


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


# This key is only for this local example.
DEMO_KEY = "local-tutorial-key-not-for-production-123456"


# %% Run


async def main() -> None:
    """A verified token becomes a user with role classes."""
    auth = JwtAuthCoordinator(secret_key=DEMO_KEY, role_registry={"manager": ManagerRole})
    token = jwt.encode({"sub": "m-1", "roles": ["manager"], "exp": int(time.time()) + 60}, DEMO_KEY, algorithm="HS256")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/orders/cancel",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "query_string": b"",
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )
    context = await auth.process(request)
    print("user:", context.user.user_id)
    print("roles:", [role.__name__ for role in context.user.roles])

    invalid = Request({**request.scope, "headers": [(b"authorization", b"Bearer invalid-token")]})
    print("invalid token:", await auth.process(invalid))


if __name__ == "__main__":
    asyncio.run(main())
