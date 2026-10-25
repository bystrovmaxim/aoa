# Contract — JWT authentication with a mandatory session identifier

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Date**: 2026-10-25

This page is the external contract of the JWT authentication pipeline after the change. It is what a consumer, an issuer and a test author read to know what is accepted, what is refused and what raises.

## 1. The public surface

```python
JwtAuthenticator(
    *,
    secret_key: str | None = None,
    jwks_url: str | None = None,
    algorithm: str = "HS256",
    audience: str | None = None,
    issuer: str | None = None,
    role_registry: Mapping[str, type[BaseRole]],
    user_id_claim: str = "sub",
    roles_claim: str = "roles",
    session_id_claim: str,            # required, no default
)

JwtAuthCoordinator(
    *,                                  # same parameters, forwarded unchanged
    session_id_claim: str,            # required, no default
    credential_extractor=None,
    context_assembler=None,
)
```

| Change | Statement |
| --- | --- |
| `session_id_claim` required | omitting it fails at construction (`TypeError`); there is no disabled mode |
| Claim name validated | `None`, empty or non-string → `ValueError` at construction |
| `sub` behaviour changed | a missing/invalid `sub` in a verified token now raises `AuthenticationContractError`, not `None`; no `str(...)` coercion |

## 2. The pipeline

```text
extract credentials
   → verify signature, expiry, issuer, audience   (failure → None)
   → enforce required identifiers                 (failure → AuthenticationContractError)
   → map roles                                    (unmapped names dropped, as before)
   → UserInfo(user_id, session_id, roles)
   → Context
```

## 3. What is a refusal, and what raises

| Input | Outcome |
| --- | --- |
| bad signature, malformed body, expired lifetime, wrong configured audience/issuer | `None` |
| missing `exp` | `None` |
| JWKS endpoint unreachable / malformed JWKS document | `None` (availability/external-input policy) |
| verified token missing `sub` or the configured user-id claim | `AuthenticationContractError` naming the claim |
| verified token whose `sub` is non-string (PyJWT raises `InvalidSubjectError`) | `AuthenticationContractError` naming `sub` |
| verified token missing/blank/non-string session claim | `AuthenticationContractError` naming the claim |
| invalid `session_id_claim` name at construction | `ValueError` |
| unexpected implementation exception inside JWT/JWKS handling | propagates unchanged |

## 4. The identifiers

- **Non-blank string**: `""` and any `str.isspace()`-only value (tabs, newlines, Unicode whitespace) are invalid.
- **Opaque**: accepted values are carried byte-for-byte — `" Session-A "` stays `" Session-A "`. No trim, lower, parse, case fold or format validation.
- **No coercion**: `{"sub": 12345}` is refused; the issuer must emit `{"sub": "12345"}`.
- **Symmetric**: the user-id and session claims share one validator and one error.

## 5. Access from an Action

```python
@regular_aspect("Read the authentication session")
@context_requires(Ctx.User.session_id)
async def read_session(self, params, state, box, connections, ctx):
    session_id = ctx.get(Ctx.User.session_id)   # the exact non-blank string
    return {"session_id": session_id}
```

`session_id` is ordinary typed context data: an aspect and an application `@access_decide` may request and use it; built-in role checks stay independent of it.

## 6. Session semantics

One login session = one identifier. The issuer assigns a new identifier per login and preserves it across refresh. AOA carries the value and does not generate identifiers, store sessions, revoke, or detect reuse.
