# Quickstart — proving the session id flows and the contract holds

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-25

This page is a validation guide, not an implementation guide. Each scenario is a runnable proof of one contract point; the exact code lives in the example scripts and notebooks named in the documentation tail, and the requirements they prove are linked below.

## Prerequisites

- The repository's own environment: `uv run python …` (Python 3.12, pydantic 2.x, PyJWT 2.12.1 with `crypto`).
- A signing key and a `LoginAction`-style issuer that puts `sub`, `roles`, `sid`, `iat`, `exp` into the token.

## Scenario 1 — the session id reaches an aspect

1. Sign a token carrying `{"sub": "alice", "roles": ["user"], "sid": "session-A", "exp": <future>}`.
2. Build `JwtAuthCoordinator(secret_key=..., role_registry=..., session_id_claim="sid")`.
3. Run an Action with an aspect decorated `@context_requires(Ctx.User.session_id)`.
4. Assert `ctx.get(Ctx.User.session_id) == "session-A"`.

**Proves**: FR-002, FR-004, FR-011; SC-003.

## Scenario 2 — a verified token with a broken claim raises

For each of these signed, unexpired payloads, `authenticate()` must raise `AuthenticationContractError` naming the claim:

- `{"sub": "alice", "sid": ""}` — empty session;
- `{"sub": "alice", "sid": " "}` — whitespace-only session;
- `{"sub": "alice"}` — missing session;
- `{"sid": "session-A"}` — missing `sub`;
- `{"sub": 12345, "sid": "session-A"}` — numeric `sub` (PyJWT's own `InvalidSubjectError` path).

**Proves**: FR-005, FR-009, FR-014; SC-001.

## Scenario 3 — an invalid token stays a refusal

For each, `authenticate()` must return `None`, never raise:

- a token with a bad signature and a numeric `sub`;
- an expired token with a missing session claim;
- a verified token with a wrong configured audience and a whitespace-only session claim;
- a token missing `exp`.

**Proves**: FR-006, FR-014; SC-002.

## Scenario 4 — values survive verbatim

A verified token with `{"sub": "alice", "sid": " Session-A "}` must yield `UserInfo(session_id=" Session-A ")` — spaces and case intact.

**Proves**: FR-008, FR-010; SC-003.

## Scenario 5 — two logins differ, one refresh does not

Sign three tokens for the same `sub`/roles: two with distinct `sid` values, two sharing one `sid` (a refresh). The aspect must see two distinct identifiers and one shared identifier.

**Proves**: FR-010; SC-004.

## Scenario 6 — a session-based access decision

An Action whose `@access_decide` declares `@context_requires(Ctx.User.session_id)` must be able to return different verdicts for different sessions with identical `sub` and roles, while a policy that does not depend on the session yields unchanged built-in verdicts.

**Proves**: FR-011; SC-005.

## Scenario 7 — the numeric-`sub` migration

The documentation and its runnable example show `{"sub": 12345}` → `AuthenticationContractError` and `{"sub": "12345"}` → accepted, with a future `exp` generated at run time.

**Proves**: FR-016; SC-006.

## Closing

`bash scripts/run_checks_with_log.sh` from the repository root, taken to zero, is the tail gate; the two accepted remarks (Vite chunk-size advisory, LangGraph pending-deprecation) stay and are not acted on.
