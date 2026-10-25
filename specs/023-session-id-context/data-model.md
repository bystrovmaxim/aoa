# Data model — the caller, the session and the failure taxonomy

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-25

The change moves no data. This page fixes what each layer carries and, above all, which failure is a refusal and which is a contract error — so "fail fast" is a statement with a boundary rather than a promise.

## 1. The context

`UserInfo` is the caller's identity slice inside `Context`. After this change it carries three fields; the first two are unchanged, the third is new.

```python
class UserInfo(BaseSchema):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str | None = None
    session_id: str | None = None
    roles: tuple[type[BaseRole], ...] = Field(default_factory=tuple)
```

| Field | Type | JWT path | Anonymous / non-JWT path |
| --- | --- | --- | --- |
| `user_id` | `str \| None` | a non-blank string from the configured `user_id_claim` | `None` |
| `session_id` | `str \| None` | a non-blank string from the configured `session_id_claim` | `None` |
| `roles` | `tuple[type[BaseRole], ...]` | role classes mapped via `role_registry` | `()` |

| Rule | Statement | Requirement |
| --- | --- | --- |
| Frozen, forbid-extra | the field does not loosen the closed schema | FR-001 |
| Serialised | `model_dump()` / JSON schema now include `session_id` (often `null`) | FR-001 |
| Session populated on success | every successful JWT authentication fills `session_id`; `None` is forbidden there | FR-004 |

The path constant is `Ctx.User.session_id == "user.session_id"`, resolved through the same `@context_requires`/`ContextView` mechanism as the other two fields.

## 2. The required identifiers

Both identifiers are read from the decoded payload and held to the same contract.

| Identifier | Claim (configurable) | Default | Accepted | Rejected |
| --- | --- | --- | --- | --- |
| user id | `user_id_claim` | `sub` | non-blank string | missing, null, empty, whitespace-only, non-string |
| session id | `session_id_claim` | — (required) | non-blank string | missing, null, empty, whitespace-only, non-string |

| Rule | Statement | Requirement |
| --- | --- | --- |
| Non-blank | `""` and `str.isspace()`-only values are invalid, as are `None` and non-strings | FR-005 |
| Verbatim | `" Session-A "` is carried exactly; no trim, lower, parse or format check | FR-008 |
| No coercion | `sub: 12345` is a violation, not `"12345"` | FR-009 |
| Symmetric | the two identifiers share one validator, one error | FR-007 |

## 3. The failure taxonomy

The distinguishing question is **not** the exception type alone — it is the cause and the boundary.

| Case | Outcome | Why |
| --- | --- | --- |
| bad signature, malformed body, expired lifetime, wrong audience/issuer, missing `exp`, JWKS/network unavailable | `None` | untrusted external input / stale token — the adapter's "not authenticated" |
| verified token with a missing/invalid required user-id or session claim | `AuthenticationContractError` | the issuer broke the mandatory claim contract — an error, not a refusal |
| numeric registered `sub` (even with a custom `user_id_claim`) | `AuthenticationContractError` naming `sub` | PyJWT's `InvalidSubjectError`, classified before the general `InvalidTokenError` |
| invalid claim name at construction (`None`/empty/non-string) | `ValueError` | configuration error, fail fast at construction |
| unexpected implementation exception in JWT/JWKS handling | propagates | programming error, must not be swallowed |

| Rule | Statement | Requirement |
| --- | --- | --- |
| Verification first | a broken claim never masks a verification failure: signature, then required, then expiry, issuer, audience, then subject | FR-006, FR-014 |
| No premature contract error | an unverified/expired token with bad claims still yields `None` | FR-006 |
| No `verify_sub=False` | the registered-`sub` check stays on for custom claims; ignoring it would be a separate decision | FR-015 |
| Diagnosis without the value | the error names the claim and the reason, never the token or the claim's value | FR-005 |

## 4. What is not modelled here

- **Sessions themselves.** No session store, no logout, no revocation, no refresh, no uniqueness/reuse detection — the issuer owns the lifecycle (FR-010).
- **The HTTP adapters.** The error propagates through the coordinator to the adapter and surfaces on its existing unhandled-error path; no adapter change (clarification of 2026-10-25).
- **The token's format.** Beyond "a string" and "non-blank", the claim's shape is the issuer's contract.

## 5. Invariants the checks must be able to break

| Invariant | Break that must fail a check |
| --- | --- |
| Session reaches the context | drop `session_id=` from the `UserInfo` construction; the aspect integration test must fail |
| Missing/blank required claim raises | change the check back to `return None`; the regression must fail |
| Numeric `sub` is a contract error | place a general `InvalidTokenError` handler ahead of the subject-specific one; the numeric-`sub` test must fail |
| Verification precedes the contract error | raise the contract error before signature/expiry checks; the precedence test must fail |
| Values stay verbatim | trim/normalise the value; the `" Session-A "` test must fail |
| Programming errors propagate | re-broaden the `except`; the injected-`RuntimeError` test must fail |
| Session-based access is possible | forbid `Ctx.User.session_id` in `@access_decide`; the access-decision test must fail |
