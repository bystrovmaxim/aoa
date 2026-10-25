# Research — a mandatory session id in the JWT authentication contract

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-25

## The PyJWT 2.12.1 facts this contract rests on

Verified against the installed library in the repository's environment (`.venv`, PyJWT 2.12.1), because the fail-fast boundary is a promise about real library behaviour, not an assumption.

| Fact | Where it was confirmed | Consequence for the design |
| --- | --- | --- |
| `verify_sub` defaults to `True` | `jwt/api_jwt.py` `_get_default_options()` | PyJWT checks the type of the registered `sub` even when no `subject=` is passed |
| `sub: 12345` → `InvalidSubjectError("Subject must be a string")` | reproduced: `jwt.decode(token, key, algorithms=[...], options={"require": ["exp"]})` | a numeric `sub` never reaches the extraction code — the library raises first |
| `sub: "12345"` → decoded; missing `sub` → decoded | reproduced | only the non-string shape fails inside `decode`; absence is caught at extraction |
| signature is verified before claim validation | `decode_complete`: `_jws.decode_complete` then `_validate_claims` | a bad signature is `None` before any claim is read |
| claim order is required → iat → nbf → exp → iss → aud → sub → jti | `_validate_claims` | expiry/issuer/audience precede subject, so a broken claim never masks a verification failure |
| `InvalidSubjectError` subclasses `InvalidTokenError` | `jwt/exceptions.py` MRO | `except InvalidTokenError: return None` would swallow the numeric-`sub` contract violation |

## D1 — The session field lives on `UserInfo`, optional by default

**Decision**: `UserInfo` gains `session_id: str | None = None`; only the JWT path is required to populate it, so anonymous/non-JWT contexts stay legal.

**Rationale**: `UserInfo` is the typed contract every authenticator projects into; a third field there is the smallest change that makes the session readable through `ContextView` without a second decode. Optional keeps `NoAuthCoordinator` and any non-JWT authenticator untouched.

**Alternatives considered**:
- *A subclass `SessionUserInfo(UserInfo)`.* Rejected: `JwtAuthenticator` constructs the base class, so the session would not flow through the standard pipeline without also changing what the authenticator builds.
- *A separate `SessionInfo` context component.* Rejected for now: one field does not justify a new component; the spec records it as the right move if a third such field ever appears.

## D2 — `session_id_claim` is mandatory, with no disabled mode

**Decision**: both `JwtAuthenticator` and `JwtAuthCoordinator` take a required keyword-only `session_id_claim: str`; omission raises `TypeError`, and a `None`/empty/non-string name raises `ValueError` at construction.

**Rationale**: session identity is a deliberate architectural decision, not an opt-in telemetry feature. A default `None` would let a deployment silently run without the identifier the contract promises.

**Alternatives considered**:
- *Optional with `None` default.* Rejected in the issue: it reintroduces a disabled mode the decision explicitly removes.
- *Hardcode `"sid"`.* Rejected: the claim name is configuration; different issuers call it differently.

## D3 — Both required identifiers share one contract

**Decision**: the configured `user_id_claim` (default `sub`) and `session_id_claim` are validated identically after verification — a non-blank string, carried verbatim, or `AuthenticationContractError`.

**Rationale**: the previous missing-`sub` `None` and the `str(...)` coercion are the same "silently erase the issuer's bug" shape the session check exists to forbid. Two mandatory claims with two failure semantics would be incoherent.

**Alternatives considered**: keep `sub` → `None` while tightening only `sid`. Rejected: it would leave the most important required identifier silently misdiagnosed as "not authenticated".

## D4 — `AuthenticationContractError`, not a new failure of the refusal path

**Decision**: a dedicated `AuthenticationContractError` in the repository's `*ContractError` family, raised at the claim boundary and carrying the claim name and reason — never the value.

**Rationale**: `None` would reject the token but erase the diagnosis ("not authenticated" is false when the issuer signed a broken claim). The name matches `VerdictContractError`, `ResourceContractViolationError`, `IncludeContractViolationError`.

**Alternatives considered**: return `None` for all invalid claims. Rejected — it is the exact behaviour the feature removes, and it contradicts the fail-fast spirit (an issuer bug must crash loudly, not surface as a 401).

## D5 — Fail-fast vs. fail-silent is a boundary, not a blanket

**Decision**: verification failures (bad signature, malformed body, expired lifetime, wrong audience/issuer, missing `exp`, JWKS/network availability) stay `None`; configuration errors, programming errors and contract violations raise and propagate.

**Rationale**: the first set is untrusted external input — an attacker or a stale token — and belongs to the adapter's "not authenticated" path. The second set is a defect in our code or the issuer's, and must abort execution so it is found, not hidden.

**Alternatives considered**: raise on everything. Rejected — it would turn every attacker-supplied bad token into a server error.

## D6 — PyJWT's subject check is classified before the general refusal

**Decision**: `InvalidSubjectError` is caught and translated to `AuthenticationContractError` **before** the general `InvalidTokenError → None` handler, preserving the original cause; the general handler keeps the other verification failures.

**Rationale**: `InvalidSubjectError` is an `InvalidTokenError` subclass, so a naive narrow handler would swallow the numeric-`sub` contract violation exactly as the old broad `except` did. Order matters, and the plan records it as a hard regression, not a convention.

**Alternatives considered**: leave `InvalidSubjectError` as a refusal. Rejected — it would reintroduce the silent coercion-adjacent behaviour the spec forbids.

## D7 — The broad `except Exception` is narrowed by cause, not deleted

**Decision**: the two `except Exception: return None` blocks become cause-aware — identified external-input/verification failures keep `None`, unexpected implementation exceptions propagate — and the `Authenticator`/`JwtAuthenticator`/coordinator contracts drop the "all exceptions become `None`" promise.

**Rationale**: the broad catch is a fail-fast debt: it makes a programming error inside JWT/JWKS handling indistinguishable from an expired token. The constitution's "debt paid as files are touched" applies to exactly the files this change touches.

**Alternatives considered**: keep the broad catch and only add the session check. Rejected — it would leave the very suppression that the fail-fast contract is designed to remove, one line above the new contract check.

## D8 — Values are opaque

**Decision**: every accepted identifier is carried byte-for-byte; the only checks are "a string" and "non-blank" (reject empty and `str.isspace()`-only). No trim, lower, parse, case fold or format validation; `" Session-A "` survives intact.

**Rationale**: the format is the issuer's contract, not AOA's. Touching the value would make AOA a participant in a format it does not own.

**Alternatives considered**: strip/normalise. Rejected — it would corrupt an opaque value and hide an issuer bug instead of surfacing it.

## D9 — A custom `user_id_claim` does not license a broken registered `sub`

**Decision**: with `user_id_claim="uid"`, a token whose `uid` is valid but whose registered `sub` is non-string is still rejected — PyJWT checks `sub` before extraction — and the diagnostic names `sub`, not `uid`. Silently setting `verify_sub=False` is forbidden.

**Rationale**: a non-string `sub` violates the JWT spec regardless of whether AOA reads `sub`; fail-fast keeps that visible. The custom-claim regression asserts the rejection and the correct diagnostic field.

**Alternatives considered**: `verify_sub=False` for custom claims. Rejected — it silently relaxes a registered-claim check to accept a malformed token, the opposite of the contract's intent.

## D10 — The numeric-`sub` migration is a concrete, not a generalised, note

**Decision**: the documentation shows exactly `{"sub": 12345}` → `AuthenticationContractError` and `{"sub": "12345"}` → accepted, without claiming it is the most common case.

**Rationale**: the previous `str(...)` coercion and the broad catch made numeric `sub` a silent `None`; the migration turns that into an explicit before/after. The spec's wording avoids an unsupported frequency claim.

**Alternatives considered**: describe it as "the most common case". Rejected — no data supports that, and the issue records it as a concrete incompatibility instead.
