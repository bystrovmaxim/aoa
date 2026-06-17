"""
02_custom_auth_coordinator.py — Write your own authentication coordinator

A coordinator turns a raw transport request into an execution `Context` *before*
the machine runs. Its whole contract is one async method:

    async def process(self, request_data) -> Context | None

Return a `Context` (identity + request metadata) on success, or `None` when the
flow cannot continue. `None` is NOT a hard reject at the boundary — shipped
adapters fall back to an anonymous `Context()`, and `@check_roles` makes the
actual allow/deny decision. Auth *produces* identity; authorization *enforces*.

The recommended path is to reuse the shipped `AuthCoordinator`, which already
orchestrates three small pieces you implement:

    request -> CredentialExtractor.extract() -> credentials dict
            -> Authenticator.authenticate()   -> UserInfo | None
            -> ContextAssembler.assemble()     -> RequestInfo kwargs
            -> Context(user=..., request=...)

Here the "request" is a tiny stand-in object (headers + path) — enough to show
the contract end-to-end, in process.

How-to: ../../docs/how-to/authoring-auth-coordinator_draft.md

Run:
    uv run python examples/how_to/02_custom_auth_coordinator.py
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from aoa.action_machine.auth import (
    AuthCoordinator,
    Authenticator,
    BaseRole,
    ContextAssembler,
    CredentialExtractor,
)
from aoa.action_machine.context import Context, UserInfo


# ── A role the caller may carry (type-as-capability, name ends in "Role") ────
class AdminRole(BaseRole):
    name = "admin"
    description = "Full administrative access."


# ── A stand-in for a transport request (FastAPI Request, MCP ctx, ...) ───────
@dataclass
class FakeRequest:
    headers: dict[str, str] = field(default_factory=dict)
    path: str = "/"


# Pretend key store: api-key -> (user_id, roles)
_KEYS = {"secret-123": ("agent_7", (AdminRole,))}


# ── 1. Extractor: pull credentials out of the protocol request ───────────────
class ApiKeyExtractor(CredentialExtractor):
    async def extract(self, request_data: Any) -> dict[str, Any]:
        key = request_data.headers.get("x-api-key")
        return {"api_key": key} if key else {}     # empty dict => no credentials


# ── 2. Authenticator: verify credentials, resolve a UserInfo ─────────────────
class ApiKeyAuthenticator(Authenticator):
    async def authenticate(self, credentials: Any) -> UserInfo | None:
        record = _KEYS.get(credentials.get("api_key"))
        if record is None:
            return None                             # invalid => None, never raise
        user_id, roles = record
        return UserInfo(user_id=user_id, roles=roles)


# ── 3. Assembler: project request metadata into RequestInfo kwargs ───────────
class HttpContextAssembler(ContextAssembler):
    async def assemble(self, request_data: Any) -> dict[str, Any]:
        return {
            "request_path": request_data.path,
            "trace_id": request_data.headers.get("x-trace-id"),
            "protocol": "http",
        }


async def main() -> None:
    # Compose the three parts into the shipped orchestration.
    coordinator = AuthCoordinator(
        ApiKeyExtractor(), ApiKeyAuthenticator(), HttpContextAssembler(),
    )

    # Valid key -> populated Context.
    ok = await coordinator.process(FakeRequest(
        headers={"x-api-key": "secret-123", "x-trace-id": "abc-1"}, path="/orders",
    ))
    print("valid key   ->", ok and (ok.user.user_id, [r.name for r in ok.user.roles], ok.request.trace_id))

    # Bad key -> None (adapter would fall back to anonymous Context()).
    bad = await coordinator.process(FakeRequest(headers={"x-api-key": "nope"}, path="/orders"))
    print("invalid key ->", bad)

    # No credentials -> None as well (extractor returned empty dict).
    anon = await coordinator.process(FakeRequest(path="/orders"))
    print("no creds    ->", anon)


if __name__ == "__main__":
    asyncio.run(main())
