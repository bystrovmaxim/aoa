# Implementation Plan: the JWT authentication context carries a mandatory session id

**Branch**: `feature/issue-263-session-id` | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/023-session-id-context/spec.md`

## Summary

The authentication context today carries the caller (`sub`) and roles, but no session. A consumer that needs the login-session identifier either decodes the already-verified token a second time or glues a session key onto `sub`. The fix is a contract change in the JWT authentication pipeline, not an optional telemetry reading: `UserInfo` gains an optional `session_id`, `JwtAuthenticator` gains a mandatory `session_id_claim`, and both required identifiers — the configured `user_id_claim` (default `sub`) and `session_id_claim` — are held to one fail-fast contract.

The change has one shape, in five pieces:

1. **The context gains a field.** `UserInfo` gets `session_id: str | None = None` (frozen, `extra="forbid"` kept); `Ctx.User.session_id` resolves `"user.session_id"`. Module docs and AI-CORE blocks move with the field (Principles III–V).
2. **A dedicated contract error.** `AuthenticationContractError`, following the repository's `*ContractError` family, is raised at the claim boundary when a verified token violates the required-identifier contract — never for an invalid signature, malformed body or expired lifetime, which stay `None`.
3. **The authenticator enforces the contract.** `session_id_claim: str` is a required keyword-only parameter (no default, no disabled mode); a `None`/empty/non-string claim name is rejected at construction. After `jwt.decode`, both required claims must be non-blank strings, carried verbatim; the previous missing-`sub` `None` and the `str(...)` coercion are removed.
4. **The refusal path stops swallowing errors.** The broad `except Exception: return None` around JWT decoding and JWKS resolution is replaced with cause-aware handling: PyJWT's `InvalidSubjectError` (a numeric `sub`, raised even without `subject=`) is classified as a contract violation **before** the general `InvalidTokenError` refusal; identified verification/availability failures keep their `None`; unexpected implementation exceptions propagate.
5. **Every call site and document migrates.** Tests, examples, notebooks and docs supply `session_id_claim`; the login examples add `sid` to the tokens they sign; the numeric-`sub` migration and both failure modes are documented in English and Russian and shown in runnable examples.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"`); pydantic 2.x for `BaseSchema`.

**Primary Dependencies**: PyJWT 2.12.1 (with `crypto` extra) — the installed version whose `InvalidSubjectError`/verification ordering the contract pins. No new dependency.

**Storage**: none. The change introduces no session store, no state and no persistence; AOA stays stateless.

**Testing**: pytest; the closing `bash scripts/run_checks_with_log.sh`. Regression cases are exercised with real signed, unexpired tokens against the installed PyJWT; a run-time expiry is generated, not hardcoded.

**Target Platform**: the `aoa-action-machine` library package, consumed by the FastAPI/MCP adapters. The adapters are out of scope (clarification of 2026-10-25).

**Project Type**: library monorepo; this is a contract change inside one package plus its tests, examples and documentation.

**Performance Goals**: no new per-request cost beyond one dict lookup plus one `isinstance`/`isspace` check per required claim — O(1) on the decoded payload. The narrowing of the exception handling removes work, not adds it.

**Constraints**: fail-fast on configuration/programming/contract errors, ordinary refusal on verification failures (FR-005/FR-006/FR-012/FR-014); accepted values carried verbatim, no coercion/normalization (FR-008/FR-009); both required identifiers symmetric (FR-007); English throughout (Principle II); nothing committed without instruction (Principle I); adapters out of scope.

**Scale/Scope**: 4 edited source files (`user_info.py`, `ctx_constants.py`, `jwt_authenticator.py`, `jwt_auth_coordinator.py`), 1 edited base contract (`authenticator.py`), 1 new exception module, 2 rewritten test files plus integration/regression additions, 5 example script+notebook pairs touched, `docs/extensions/jwt.md` + `jwt.ru_draft.md`, 2 changelogs, 1 version bump (`1.0.1a5` → `1.0.1a6`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | The branch exists on the maintainer's word. Each phase becomes a commit only on instruction; the tail is prepared, shown and left uncommitted. Nothing is pushed. |
| II. English in commits and code | Every message, comment, page and changelog in English | The new exception, every docstring/AI-CORE edit, the tests, the `jwt.md` page, the examples and both changelogs are English. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled sections | Every touched module keeps its header form; `user_info.py`, `jwt_authenticator.py` and `ctx_constants.py` update their purpose/architecture prose where the field enters the contract. |
| IV. AI-CORE blocks | `ROLE`/`CONTRACT`/`INVARIANTS` on public Python types | `UserInfo`'s `CONTRACT`/`INVARIANTS` gains the session field; `JwtAuthenticator`'s `CONTRACT`/`FAILURES` gains the required-claim contract and the raise-vs-`None` split; `Authenticator`'s `INVARIANTS` drops the "never raise" promise. |
| V. Short docstrings | One line with a period on every class, function, method | `AuthenticationContractError` carries a one-line docstring; every new/edited helper gets one. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | The tail is exactly three tasks, in that order, and no implementation task absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | The change has a runnable Python surface, so no exception is needed: the new session-aspect access, the numeric-`sub` migration and both failure modes get script+notebook pairs that are executed while written. |

**Violations requiring justification**: none.

**Re-checked after Phase 1 design**: unchanged. The design adds one field, one exception and one parameter; it narrows the refusal path rather than widening it, and the adapter boundary stays where it was.

## Project Structure

### Documentation (this feature)

```text
specs/023-session-id-context/
├── plan.md              # this file
├── spec.md              # the specification
├── research.md          # Phase 0: D1–D10, the PyJWT 2.12.1 facts, the rejected alternatives
├── data-model.md        # Phase 1: UserInfo, the required identifiers, the failure taxonomy
├── quickstart.md        # Phase 1: runnable proofs
├── contracts/
│   └── jwt-auth-contract.md   # verification → required claims → raise-vs-refuse, and the exception classification
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── context/user_info.py                        # + session_id field, docstring/AI-CORE
│   ├── context/ctx_constants.py                    # + Ctx.User.session_id
│   ├── auth/authenticator.py                       # INVARIANTS: None for refusal, raise for contract/config
│   ├── auth/jwt_auth/jwt_authenticator.py          # mandatory claim, symmetric contract, narrow except
│   ├── auth/jwt_auth/jwt_auth_coordinator.py       # forward session_id_claim
│   └── exceptions/authentication_contract_error.py # NEW: AuthenticationContractError
├── tests/action_machine/
│   ├── auth/jwt_auth/test_jwt_authenticator.py     # rewritten + regression cases
│   ├── auth/jwt_auth/test_jwt_auth_coordinator.py  # rewritten + propagation
│   ├── context/…                                   # UserInfo session_id serialisation
│   └── … (integration: aspect reads Ctx.User.session_id)
├── pyproject.toml                                  # version 1.0.1a5 → 1.0.1a6
└── CHANGELOG.md                                    # Unreleased entry (tail)

examples/
├── step_03_authorization_and_roles/12_authentication.py (+.ipynb)   # + session_id_claim
├── step_13_fastapi/03_login_action.py (+.ipynb)                     # + sid in the signed token
├── step_13_fastapi/04_bearer_auth.py (+.ipynb)                      # + session_id_claim
├── step_13_fastapi/05_cookie_auth.py (+.ipynb)                      # + session_id_claim
├── step_13_fastapi/06_jwks_auth.py (+.ipynb)                        # + session_id_claim
├── step_14_mcp/02_bearer_auth_limitation.py (+.ipynb)               # + session_id_claim
└── how_to/02_custom_auth_coordinator.py (+.ipynb)                   # checked, updated if it constructs JWT auth

docs/
├── extensions/jwt.md (+ jwt.ru_draft.md)          # parameter, field, failure modes, migration
├── tutorials/step-12-authentication.md            # any JwtAuthCoordinator signature line
└── CHANGELOG.md                                   # the article (tail)
```

**Structure Decision**: one package owns the change (`aoa-action-machine`), and the surrounding work is its tests, the example pairs that construct JWT auth, and the two documentation pages that name the constructor. No new module beyond the single exception file, no new package, no new dependency, no adapter change.

## Phases

Each phase is a commit only when the maintainer says so (Principle I); the numbers are the order of the work, not a claim to ship.

### Phase 1 — the context surface

- `context/user_info.py`: add `session_id: str | None = None`; update the module docstring and the AI-CORE `CONTRACT`/`INVARIANTS`.
- `context/ctx_constants.py`: add `session_id: str = "user.session_id"` to `_UserFields`; update the `Ctx.User` prose.

**Proves**: FR-001, FR-002.

### Phase 2 — the contract error

- `exceptions/authentication_contract_error.py`: new `AuthenticationContractError`, one-line docstring, constructor carrying the claim name and reason (never the value); export it from `exceptions/__init__.py`.

**Proves**: the exception surface used by FR-005/FR-012/FR-014.

### Phase 3 — the authenticator

- `jwt_authenticator.py`: add required keyword-only `session_id_claim: str`; validate the claim name at construction (`ValueError` for `None`/empty/non-string); after `jwt.decode`, enforce both required claims as non-blank strings and raise `AuthenticationContractError` on violation; drop `str(user_id)`; replace the two broad `except Exception` blocks with cause-aware classification (`InvalidSubjectError` → contract error, before `InvalidTokenError` → `None`; verification/availability → `None`; unexpected → propagate); update the module docstring and AI-CORE.
- `authenticator.py`: amend `INVARIANTS` from "return `None` for invalid credentials instead of exceptions" to the refusal-vs-contract split.

**Proves**: FR-003, FR-004, FR-005, FR-007, FR-008, FR-009, FR-012, FR-013, FR-014.

### Phase 4 — the coordinator

- `jwt_auth_coordinator.py`: declare the same required `session_id_claim: str`, forward it to `JwtAuthenticator`, no validation of its own.

**Proves**: FR-003, FR-007.

### Phase 5 — tests

- Rewrite `test_jwt_authenticator.py` and `test_jwt_auth_coordinator.py` for the new constructor; add the required user-id/session cases, the PyJWT exception-path regressions, verification precedence, custom-claim rejection, and the injected-`RuntimeError` fail-fast tests.
- Add the aspect integration test (an aspect declares `@context_requires(Ctx.User.session_id)` and reads the exact claim value) and the `@access_decide` session-based decision test.
- Run each adversarial break in isolation and restore: missing projection, incorrect path/forwarding, accidental normalization, whitespace-only acceptance, swallowed `InvalidSubjectError`, continuation after a contract failure, a general handler placed ahead of the subject-specific classification.

**Proves**: FR-004, FR-005, FR-006, FR-009, FR-010, FR-011, FR-014, FR-015; SC-001–SC-005.

### Phase 6 — migrate call sites and examples

- Add `session_id_claim="sid"` to every `JwtAuthCoordinator`/`JwtAuthenticator` construction in tests, examples and notebooks; add `sid` to the tokens `03_login_action.py` signs and to the JWT fixtures.

**Proves**: the breaking-constructor migration; SC-005.

### Tail task 1 — the closing check run

`bash scripts/run_checks_with_log.sh` from the repository root, taken to zero. The two accepted remarks — the Vite chunk-size advisory and the LangGraph pending-deprecation warning — stay and are not acted on. Any edit the run makes (ruff `--fix`) is reviewed as part of the change.

### Tail task 2 — the documentation

- `docs/extensions/jwt.md` (+ `jwt.ru_draft.md`): the required parameter, the field, both failure modes (refusal vs contract error), the numeric-`sub` migration, session semantics, and aspect/`@access_decide` access — with script+notebook pairs executed while written.
- `docs/tutorials/step-12-authentication.md`: any signature line that names `JwtAuthCoordinator`.

### Tail task 3 — the changelog

One article in `docs/CHANGELOG.md` about what the work created; one `Unreleased` entry in `packages/aoa-action-machine/CHANGELOG.md`.

## Requirement coverage

| Requirement | Where it is satisfied | Proof |
| --- | --- | --- |
| FR-001 `UserInfo.session_id` optional | Phase 1 | serialisation test shows `session_id`; `extra="forbid"` still holds |
| FR-002 `Ctx.User.session_id` | Phase 1 | `ContextView`/`resolve` test |
| FR-003 required `session_id_claim` | Phases 3–4 | `TypeError` on omission; `ValueError` on invalid name |
| FR-004 populated session on success | Phase 3 | "every success has non-empty session" test |
| FR-005 contract error at the claim boundary | Phases 2–3 | missing/null/empty/whitespace/non-string raise, before context assembly |
| FR-006 verification failures stay `None` | Phase 3 | precedence tests (bad sig/expired/wrong aud/iss + bad claims → `None`) |
| FR-007 symmetric required identifiers | Phase 3 | user-id and session tests are the same shape |
| FR-008 values carried verbatim | Phase 3 | `" Session-A "` and case preserved; no `str(...)` |
| FR-009 numeric `sub` not coerced | Phase 3 | numeric-`sub` regression raises, no coercion |
| FR-010 issuer owns lifecycle | Phase 5 (test only) | two logins distinct, refresh preserves; no store |
| FR-011 aspect/`@access_decide` access | Phase 5 | integration + access-decision tests |
| FR-012 config/programming errors propagate | Phase 3 | injected-`RuntimeError` reaches the caller |
| FR-013 broad except narrowed | Phase 3 | unexpected exceptions propagate; expected failures keep policy |
| FR-014 subject validation classified before refusal | Phase 3 | numeric-`sub` via PyJWT path raises contract error |
| FR-015 custom claim + malformed `sub` rejected, named `sub` | Phase 3 | custom-claim regression names `sub`, not the custom field |
| FR-016 docs/changelog/version ship | Tail 2–3 | `jwt.md` + `jwt.ru_draft.md`, changelogs, version bump |

## Complexity Tracking

No violations. The change adds one field, one exception and one parameter; it narrows the refusal path, keeps the adapters out of scope, and documents every new case with executed script+notebook pairs.
