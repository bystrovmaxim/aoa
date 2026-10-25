# Feature Specification: Carry the authentication session id into the context

**Feature Branch**: `feature/issue-263-session-id`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/263 — feat(auth): carry the authentication session id into the context."

## Context: what is true today, measured on 2026-10-25

- **The context carries the caller, not the session.** `UserInfo` (frozen, `extra="forbid"`) carries `user_id: str | None` and a tuple of role classes. A consumer that needs the login-session identifier has no supported place to read it: the only stable key reachable from the context is `sub`, so two logins of the same user collapse into one principal.
- **The JWT pipeline projects two claims and nothing else.** `JwtAuthenticator` verifies signature, expiry, optional issuer/audience, then extracts `user_id` (default claim `sub`) and `roles` (default claim `roles`). There is no third claim path; a consumer decodes the already-verified token a second time or glues a session key onto `sub`.
- **The context path has two user entries.** `Ctx.User.user_id` and `Ctx.User.roles` resolve through `@context_requires`/`ContextView`; there is no `Ctx.User.session_id`.
- **Invalid identity is silently refused.** A verified token missing `sub` returns `None`. A numeric `sub` raises `InvalidSubjectError` inside the installed PyJWT 2.12.1 — even without a `subject=` argument — and the authenticator's broad `except Exception` turns it into `None`. A numeric custom user-id claim is coerced through `str(...)` instead of being refused.
- **The refusal path suppresses every exception.** Both JWT decoding and JWKS key resolution wrap their failure surface in `except Exception: return None`, so a programming error inside them is indistinguishable from an expired token.

## Clarifications

### Session 2026-10-25 — decisions carried from issue #263

- **Session identity is mandatory for JWT authentication.** Every successful JWT authentication must produce a session identifier; there is no disabled mode and no optional telemetry reading. This is a deliberate architectural decision and a breaking change for every JWT consumer, including server-to-server callers whose token model has no login session.
- **Both required identifiers share one contract.** The configured `user_id_claim` (default `sub`) and `session_id_claim` must each be a non-empty, non-whitespace-only string after verification. A violation raises `AuthenticationContractError` at the claim boundary; the diagnostic names the claim and the reason, never the value.
- **Fail-fast, not fail-silent.** An invalid signature, a malformed token or an expired lifetime stays an ordinary refusal (`None`). A configuration error, a programming error or an internal contract violation raises and aborts execution; it is never converted into `None` or an anonymous context. The previous missing-`sub` `None` behavior is changed to the contract exception.
- **The exception belongs to the repository's contract-error family.** `AuthenticationContractError` follows the same naming as `VerdictContractError`, `ResourceContractViolationError`, `IncludeContractViolationError`.
- **Values are opaque.** Every accepted identifier is carried byte-for-byte — leading/trailing whitespace and letter case included. There is no parsing, trimming, case folding, coercion (`str(...)`) or format validation; the only checks are "a string" and "non-blank".
- **Session lifecycle is the issuer's.** A new login gets a new identifier; a refresh within the same session preserves it. AOA only carries the value — it does not generate identifiers, store sessions, revoke, or detect reuse.
- **Session data is ordinary context data.** An Action aspect reads it through `@context_requires(Ctx.User.session_id)` and `ctx.get(...)`; an application `@access_decide` may request it and base its verdict on it. No special restriction on session-based access policies is introduced, and built-in role checks remain independent.
- **PyJWT's own subject check is part of the contract.** Installed PyJWT 2.12.1 raises `InvalidSubjectError` for a non-string `sub` without `subject=`; because that error is an `InvalidTokenError`, a blanket handler would swallow it again. The implementation classifies it as a contract failure before the general `InvalidTokenError` refusal, and preserves PyJWT's verification order — signature, then required claims, then expiry, issuer, audience, then subject.
- **A custom user-id claim does not license a broken registered `sub`.** With `user_id_claim="uid"`, a token whose `uid` is valid but whose registered `sub` is non-string is still rejected — the library checks `sub` before extraction — and the diagnostic names `sub`, not `uid`. Silently disabling `verify_sub` is forbidden; ignoring a registered `sub` would be a separate design decision.
- **Numeric subjects are a concrete migration.** A token with `{"sub": 12345}` is rejected; the issuer must emit `{"sub": "12345"}`. No silent numeric-to-string conversion remains.

### Session 2026-10-25 — clarify

- Q: Should the HTTP adapters (FastAPI/MCP) be in scope for `AuthenticationContractError`, or does the change stop at the authentication pipeline? → A: The adapters stay out of scope. The library raises, the adapter's existing behavior lets it bubble to an unhandled error, and no adapter change or adapter-level integration test is added. The docs demonstrate the distinction at the library layer (`None` vs exception).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the session identifier inside an Action (Priority: P1)

A developer writing an audit aspect needs the login-session identifier next to the caller's identity. They declare `@context_requires(Ctx.User.session_id)`, read it through the injected `ContextView`, and receive the exact non-empty string the issuer placed in the configured session claim — without decoding the token a second time or overloading `sub`.

**Why this priority**: This is the feature. Every other story protects it or states its boundaries.

**Independent Test**: Authenticate a signed token carrying the session claim, run an Action with an aspect that declares `Ctx.User.session_id`, and assert the aspect sees the exact claim value.

**Acceptance Scenarios**:

1. **Given** a verified token with a non-blank session claim, **When** an aspect declares `@context_requires(Ctx.User.session_id)`, **Then** `ctx.get(Ctx.User.session_id)` returns that exact string.
2. **Given** two tokens with the same `sub` and roles but different session claims, **When** both are authenticated, **Then** the aspect sees two distinct session identifiers.
3. **Given** two tokens representing refresh within one session, **When** both are authenticated, **Then** the aspect sees the same session identifier.

---

### User Story 2 - Enforce the required identifier contract (Priority: P1)

A maintainer wants a token that verifies but fails to carry a usable caller or session identifier to fail loudly at the source, naming the claim and the reason, instead of surfacing later as a missing value in an Action or a misleading "not authenticated".

**Why this priority**: The feature's value depends on the identifier being present and trustworthy; a silent refusal would erase the diagnosis the feature exists to preserve.

**Independent Test**: Feed signed, unexpired tokens with a missing, empty, whitespace-only or non-string user-id/session claim and assert the named contract error, before any context assembly or Action execution.

**Acceptance Scenarios**:

1. **Given** a verified token missing the configured user-id claim, **When** it is authenticated, **Then** `AuthenticationContractError` is raised naming that claim.
2. **Given** a verified token whose session claim is empty, whitespace-only or non-string, **When** it is authenticated, **Then** `AuthenticationContractError` is raised naming the session claim.
3. **Given** a verified token with a numeric `sub`, **When** it is authenticated, **Then** `AuthenticationContractError` is raised — the value is not coerced to a string.

---

### User Story 3 - Keep an invalid token a refusal, not an error (Priority: P1)

A caller presenting a token with a bad signature, a malformed body or an expired lifetime receives the ordinary "not authenticated" refusal, even when that token also carries a broken identifier — verification failures stay refusals, and only a token that passes verification can trigger the contract error.

**Why this priority**: The fail-fast contract must not widen the refusal path into an exception path for unverified input, which would change the adapter's 401 behavior for attackers and stale tokens.

**Independent Test**: Combine broken identifiers with invalid signature, expired lifetime, wrong audience and wrong issuer; each must yield `None` and none may raise the contract error prematurely.

**Acceptance Scenarios**:

1. **Given** a token with a bad signature and a numeric `sub`, **When** it is authenticated, **Then** the result is `None`, not a contract error.
2. **Given** an expired token with a missing session claim, **When** it is authenticated, **Then** the result is `None`, not a contract error.
3. **Given** a verified token with wrong configured audience and a whitespace-only session claim, **When** it is authenticated, **Then** the result is `None`.

---

### User Story 4 - Base an access decision on the session (Priority: P2)

A developer writes an application access policy that distinguishes callers by session. The `@access_decide` method declares `@context_requires(Ctx.User.session_id)`, reads the value through its `ContextView`, and decides; built-in role checks stay independent of the session.

**Why this priority**: The issue deliberately leaves session-based authorization to application code; this story pins that boundary and guards against the framework either forbidding it or silently wiring it in.

**Independent Test**: Run an Action whose `@access_decide` keys on the session identifier and observe different verdicts for different sessions with identical `sub` and roles.

**Acceptance Scenarios**:

1. **Given** an `@access_decide` declaring `@context_requires(Ctx.User.session_id)`, **When** two callers share `sub` and roles but differ in session, **Then** the policy may return different verdicts.
2. **Given** the same Action without a session-dependent policy, **When** only the session changes, **Then** built-in role and access verdicts are unchanged.

---

### User Story 5 - Migrate an issuer to the new contract (Priority: P3)

An operator whose tokens carry a numeric `sub` — a shape the previous authenticator silently accepted or coerced — learns from the documentation exactly which token now fails and what to emit instead, and updates the issuer without guessing.

**Why this priority**: It is a breaking change for every JWT issuer; the migration note turns an unexplained production failure into a one-line fix.

**Independent Test**: Read the migration documentation and the runnable example, then confirm the documented before/after token pair matches the enforced behavior.

**Acceptance Scenarios**:

1. **Given** the migration documentation, **When** it is read, **Then** it shows `{"sub": 12345}` → contract error and `{"sub": "12345"}` → accepted.
2. **Given** the runnable example, **When** it is executed, **Then** it produces a future expiry at run time and demonstrates both outcomes with real signed tokens.

---

### Edge Cases

- **Whitespace-only vs. padded values.** `" "`, tabs, newlines and Unicode whitespace are rejected; `" Session-A "` is accepted and preserved verbatim, spaces included.
- **Numeric, boolean, list and object identifiers.** Every non-string shape is rejected at the claim boundary; none is coerced.
- **A missing `exp`.** Kept as an ordinary refusal (`None`); it never triggers the contract error.
- **A custom `user_id_claim` with a malformed registered `sub`.** The token is still rejected because the library checks the registered `sub`; the diagnostic names `sub`, not the custom claim.
- **A verified token with all checks passing but a blank identifier.** The contract error fires at extraction, before `UserInfo` or `Context` is built.
- **Two logins of one user and a refresh of one login.** Distinct sessions produce distinct identifiers; refresh preserves one identifier.
- **An anonymous, non-JWT context.** `UserInfo()` with `session_id=None` remains legal; only the JWT path requires a populated session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `UserInfo` MUST carry an optional `session_id` field, `None` by default, while keeping the frozen, `extra="forbid"` contract; its serialized form includes `session_id`.
- **FR-002**: `Ctx.User.session_id` MUST resolve `"user.session_id"` through the existing `@context_requires`/`ContextView` mechanism.
- **FR-003**: The JWT authenticator and coordinator MUST require a `session_id_claim` configuration; omitting it fails at construction, and a `None`, empty or non-string claim name is rejected at construction.
- **FR-004**: Every successful JWT authentication MUST produce a non-blank string `session_id`; a successful JWT authentication with `session_id=None` is forbidden.
- **FR-005**: After token verification, a missing, null, empty, whitespace-only or non-string value of the configured user-id or session claim MUST raise `AuthenticationContractError` at the claim boundary, naming the claim and reason without exposing the value, before any `UserInfo`/`Context` creation.
- **FR-006**: An invalid signature, malformed body or expired lifetime MUST remain an ordinary refusal (`None`), including when the token also carries invalid identifiers.
- **FR-007**: The same fail-fast contract MUST apply to both required identifiers — the configured `user_id_claim` (default `sub`) and `session_id_claim` — with no disabled mode for either.
- **FR-008**: Accepted identifiers MUST be carried byte-for-byte — whitespace and case included — with no parsing, trimming, case folding, coercion or format validation beyond "a string" and "non-blank".
- **FR-009**: A numeric user-id claim MUST NOT be converted to a string; it is a contract violation like any other non-string value.
- **FR-010**: Session lifecycle MUST remain the issuer's: a new login gets a new identifier, refresh within a session preserves it, and AOA only carries the value — no generation, uniqueness checks, session store, logout or revocation.
- **FR-011**: Application code — Action aspects and `@access_decide` — MUST be able to request `Ctx.User.session_id` and use it in behavior and access decisions; no restriction on session-based policies is introduced, and built-in role checks stay independent of it.
- **FR-012**: Configuration errors, programming errors and internal contract violations MUST raise and abort execution; they MUST NOT be converted into `None`, an ordinary refusal or an anonymous context.
- **FR-013**: Broad exception suppression around JWT decoding and JWKS resolution MUST be replaced with cause-aware handling: identified external-input/verification failures keep their refusal policy, and unexpected implementation exceptions propagate.
- **FR-014**: A verified token whose registered subject is non-string MUST be rejected as a contract violation, not silently refused; the refusal path MUST NOT swallow it, and the contract exception MUST be raised only after signature, required-claim, expiry, issuer and audience checks succeed.
- **FR-015**: With a custom `user_id_claim`, a non-string registered `sub` MUST still be rejected with a diagnostic naming `sub` (not the custom claim), and the implementation MUST NOT silently disable `verify_sub`.
- **FR-016**: The documentation, runnable examples, changelog and version MUST ship with the change and state the mandatory-session decision, the numeric-`sub` migration and both failure modes.

### Key Entities

- **Session identifier**: One login session's opaque, non-blank string. The issuer assigns a new one per login and preserves it across refresh; AOA carries it without interpreting it.
- **Required identifier**: The configured `user_id_claim` and `session_id_claim`, each held to the same non-blank-string contract after verification.
- **Contract error**: `AuthenticationContractError`, raised at the claim boundary when a verified token violates the required-identifier contract; distinct from an ordinary refusal (`None`) for unverified or expired tokens.
- **Context**: The per-call environment slice (`UserInfo` + request/runtime); after this change its `UserInfo` carries `session_id` alongside `user_id` and `roles`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of required-identifier violation cases — missing, null, empty, whitespace-only, non-string, and numeric-`sub` — raise `AuthenticationContractError` with the correct claim name and reason.
- **SC-002**: 100 % of verification failures — bad signature, malformed body, expired lifetime, wrong audience, wrong issuer, missing `exp` — return `None`, even when combined with invalid identifiers.
- **SC-003**: 100 % of accepted identifiers reach the context byte-for-byte, including `" Session-A "` and case-sensitive values.
- **SC-004**: Every successful JWT authentication produces a populated `session_id`; zero successful authentications yield `None`.
- **SC-005**: The existing JWT, role and access test suites stay green after call sites are migrated to the required parameter, with no change to built-in role/permission verdicts.
- **SC-006**: The full repository check run is green, runnable examples execute with real signed tokens and a run-time expiry, and the numeric-`sub` before/after pair is demonstrated in the documentation.

## Assumptions

- The mandatory session decision is a deliberate architectural position, not a JWT technical requirement; the breaking change and its migration are accepted by the maintainer.
- The installed JWT library is PyJWT 2.12.1; its subject-shape validation and verification ordering are relied upon and locked by regression tests against real signed tokens.
- Session-based authorization is the application's responsibility; AOA only guarantees that the identifier is present and carried faithfully, not that it is unique — the issuer owns uniqueness.
- `sub` remains a valid, configurable user identifier source; the contract is tightened, not its meaning changed.

## Out of scope

- Issuing tokens and defining the session claim's format (the consuming service does that).
- Storing sessions, logout, revocation, refresh and uniqueness/reuse detection.
- Validating the claim's format beyond "a string" and "non-blank".
- Changing the meaning of `sub` or replacing the user identifier with the session identifier.
- The HTTP adapters (FastAPI/MCP): the contract error surfaces through their existing unhandled-error path; no adapter change or adapter integration test is in scope.

## Dependencies

- The existing `JwtAuthenticator`, `JwtAuthCoordinator`, `UserInfo` and `Ctx.User` surface this feature extends; the previous missing-`sub` `None` behavior is superseded in place.
- `AuthenticationContractError` follows the repository's exception conventions; the `Authenticator`, `JwtAuthenticator` and coordinator contracts/docstrings are updated to remove the "all exceptions become `None`" promise.
- The PyJWT-specific regression cases depend on the installed 2.12.1 and are verified with real signed tokens.

## Verification

- The check that today asserts a missing `sub` yields `None` is inverted: a verified token missing the user-id claim must raise `AuthenticationContractError`, while a bad-signature or expired token still yields `None`.
- Adversarial pairs: placing a general `InvalidTokenError` refusal handler ahead of the subject-specific classification must make the numeric-`sub` regression fail; raising the contract error before signature/expiry verification must make the precedence regression fail. Each break is introduced in isolation and restored.
- The numeric-`sub` and custom-claim cases are exercised against the installed PyJWT with real signed, unexpired tokens, and the migration example executes with a run-time expiry.
- The documentation, the check run taken to zero and the changelog article follow the usual tail; the two accepted remarks of the check run are not acted on.
