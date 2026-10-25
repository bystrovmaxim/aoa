# Tasks: carry the authentication session id into the context

**Input**: Design documents from `specs/023-session-id-context/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/jwt-auth-contract.md

**Tests**: Required — the specification (FR-005/FR-006/FR-014) and the constitution's adversarial-verification rule make tests part of the change, not optional.

**Organization**: Tasks are grouped by user story (US1–US5 from spec.md) after a shared foundational phase. The three tail tasks (check run, documentation, changelog) are reserved and in that order per constitution VI.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no shared dependency)
- **[Story]**: maps the task to a user story (US1–US5)
- Every description carries an exact file path.

---

## Phase 1: Setup

**Purpose**: confirm the working branch and a green baseline; no new package or dependency is introduced.

- [x] T001 Confirm the feature branch `feature/issue-263-session-id` is checked out and run the existing JWT auth suite as a green baseline: `packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/` and `packages/aoa-action-machine/tests/action_machine/intents/context_requires/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared contract pieces every story builds on. No user story starts before this phase is complete.

**⚠️ CRITICAL**: these four tasks touch four different files and carry no dependency on one another.

- [x] T002 [P] Add `session_id: str | None = None` to `UserInfo` (keep `model_config = ConfigDict(frozen=True, extra="forbid")`) and update the module docstring and the AI-CORE `CONTRACT`/`INVARIANTS` to name the field, in `packages/aoa-action-machine/src/aoa/action_machine/context/user_info.py`.
- [x] T003 [P] Add `session_id: str = "user.session_id"` to `_UserFields` with its one-line docstring, and update the `Ctx.User` prose, in `packages/aoa-action-machine/src/aoa/action_machine/context/ctx_constants.py`.
- [x] T004 [P] Create `AuthenticationContractError` (one-line docstring; constructor carries the claim name and reason, never the token or the claim value) in `packages/aoa-action-machine/src/aoa/action_machine/exceptions/authentication_contract_error.py`, and export it from `packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py`.
- [x] T005 [P] Amend `Authenticator`'s AI-CORE `INVARIANTS` from "Return `None` for invalid credentials instead of exceptions" to the refusal-vs-contract split, in `packages/aoa-action-machine/src/aoa/action_machine/auth/authenticator.py`.

**Checkpoint**: the field, the path constant, the exception and the base invariant exist; user stories can start.

---

## Phase 3: User Story 1 - Read the session identifier inside an Action (Priority: P1) 🎯 MVP

**Goal**: a verified token with a session claim yields `UserInfo.session_id`, readable through `Ctx.User.session_id`.

**Independent Test**: sign a token with `sid`, run an Action with an aspect declaring `@context_requires(Ctx.User.session_id)`, assert `ctx.get(Ctx.User.session_id)` returns the exact value.

### Implementation for User Story 1

- [x] T006 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_authenticator.py`, add the required keyword-only `session_id_claim: str` (no default), validate the claim name at construction (`ValueError` for `None`/empty/non-string), and after `jwt.decode` populate `UserInfo(session_id=...)` from the claim's non-blank string value.
- [x] T007 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_auth_coordinator.py`, declare the same required `session_id_claim: str` and forward it to `JwtAuthenticator` with no validation of its own.
- [x] T008 [US1] Add tests: `UserInfo` serialisation contains `session_id` (in `packages/aoa-action-machine/tests/action_machine/intents/context_requires/test_user_info.py`), `Ctx.User.session_id` resolves (in `.../test_ctx_constants.py` / `.../test_context_view.py`), and an integration test where an aspect reads the exact session id (new `packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_session_id_in_aspect.py`). Two logins of one user must produce distinct values; refresh within one session must preserve it.

**Checkpoint**: the session id flows end to end; MVP value delivered.

---

## Phase 4: User Story 2 - Enforce the required identifier contract (Priority: P1)

**Goal**: a verified token that fails to carry a usable caller or session identifier fails loudly at the claim boundary, naming the claim and reason.

**Independent Test**: feed signed, unexpired tokens with a missing/empty/whitespace/non-string user-id or session claim and assert `AuthenticationContractError`, before any context assembly or Action execution.

### Implementation for User Story 2

- [x] T009 [US2] In `packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_authenticator.py`, enforce the symmetric required-identifier contract: after `jwt.decode`, both the configured `user_id_claim` (default `sub`) and `session_id_claim` must be a `str` that is non-empty and not `str.isspace()`-only, else raise `AuthenticationContractError` naming the claim; remove the `str(user_id)` coercion and the missing-`sub` `None` path. Update the module docstring and AI-CORE `CONTRACT`/`FAILURES`.
- [x] T010 [US2] Add tests in `packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py`: missing/null/empty/whitespace-only/non-string for both claims raise; numeric `sub` raises (no coercion); `" Session-A "` is preserved verbatim. Adversarially break each — drop the session projection, re-add `return None` for a missing claim, re-add `str(...)` — confirm the intended test fails and no unrelated test does, then restore.

**Checkpoint**: the contract is enforced and its breaks are caught.

---

## Phase 5: User Story 3 - Keep an invalid token a refusal, not an error (Priority: P1)

**Goal**: bad signature, malformed body, expired lifetime, wrong audience/issuer and missing `exp` stay `None`, even when the token also carries a broken identifier.

**Independent Test**: combine broken identifiers with each verification failure; each must yield `None` and none may raise the contract error prematurely.

### Implementation for User Story 3

- [x] T011 [US3] In `packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/jwt_authenticator.py`, replace the two broad `except Exception: return None` blocks with cause-aware classification: `InvalidSubjectError` → `AuthenticationContractError` naming `sub`, **before** the general `InvalidTokenError` → `None`; identified verification/availability failures → `None`; unexpected implementation exceptions propagate unchanged. Preserve PyJWT's verification precedence (signature → required → expiry → issuer → audience → subject), and do not set `verify_sub=False` for custom claims.
- [x] T012 [US3] Add regression tests in `packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py`: bad signature/expired/wrong-audience/wrong-issuer/missing-`exp` combined with bad claims → `None`; numeric `sub` via the PyJWT path → contract error; custom `user_id_claim` with a malformed registered `sub` → rejected naming `sub`; injected `RuntimeError` in JWT decoding and JWKS resolution propagates to the caller and no Action runs. Adversarially place a general `InvalidTokenError` handler ahead of the subject-specific one and confirm the numeric-`sub` test fails, then restore.

**Checkpoint**: the refusal path and the fail-fast path are separated and locked.

---

## Phase 6: User Story 4 - Base an access decision on the session (Priority: P2)

**Goal**: an application `@access_decide` may request and use `Ctx.User.session_id`; built-in role checks stay independent.

**Independent Test**: run an Action whose `@access_decide` keys on the session identifier and observe different verdicts for different sessions with identical `sub` and roles.

### Implementation for User Story 4

- [x] T013 [US4] Add a test under `packages/aoa-action-machine/tests/action_machine/intents/access_decide/` where `@access_decide` declares `@context_requires(Ctx.User.session_id)` and returns a session-dependent verdict, and a second assertion that an Action without a session-dependent policy yields unchanged built-in verdicts when only the session changes.

**Checkpoint**: session-based access is possible and the boundary is pinned.

---

## Phase 7: User Story 5 - Migrate the breaking changes (Priority: P3)

**Goal**: every JWT call site supplies the mandatory claim, and the tokens the examples sign carry it.

**Independent Test**: run every example and the full test suite; none fails with a missing `session_id_claim`.

### Implementation for User Story 5

- [x] T014 [US5] Add `session_id_claim="sid"` to every `JwtAuthCoordinator`/`JwtAuthenticator` construction and add `sid` to every signed token: `packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py`, `.../test_jwt_auth_coordinator.py`, `examples/step_03_authorization_and_roles/12_authentication.py`, `examples/step_13_fastapi/03_login_action.py`, `.../04_bearer_auth.py`, `.../05_cookie_auth.py`, `.../06_jwks_auth.py`, `examples/step_14_mcp/02_bearer_auth_limitation.py`, and each corresponding `.ipynb`.

**Checkpoint**: the migration compiles and runs; the documented token contract matches.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: the three reserved tail steps, in this order (constitution VI).

- [x] T015 Run `bash scripts/run_checks_with_log.sh` from the repository root and take every remark to zero. The two accepted remarks — the Vite chunk-size advisory and the LangGraph pending-deprecation warning — stay and are not acted on; any ruff `--fix` edit the run makes is reviewed as part of the change.
- [x] T016 Write the documentation: `docs/extensions/jwt.md` and its `jwt.ru_draft.md` companion state the mandatory `session_id_claim`, the `session_id` field, both failure modes (ordinary refusal vs `AuthenticationContractError`), the numeric-`sub` migration (`{"sub": 12345}` → contract error, `{"sub": "12345"}` → accepted), session semantics, and aspect/`@access_decide` access. Add the runnable script + notebook pair for the session-aspect and the numeric-`sub` migration under `examples/`, and execute every example with the repository's own environment (a future `exp` generated at run time). Amend `docs/tutorials/step-12-authentication.md` where it names the constructor.
- [x] T017 Write the changelog as one article in `docs/CHANGELOG.md`, add the `Unreleased` entry in `packages/aoa-action-machine/CHANGELOG.md`, and bump the version `1.0.1a5` → `1.0.1a6` in `packages/aoa-action-machine/pyproject.toml`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks every user story.
- **US1 (Phase 3)**: depends on Foundational (T002/T003) and on T004/T005 for the exception; no dependency on US2/US3.
- **US2 (Phase 4)**: depends on Foundational; builds on T006's constructor and T004's exception.
- **US3 (Phase 5)**: depends on Foundational; builds on T009's validation and T011's classification.
- **US4 (Phase 6)**: depends on US1 (the field and the filled context).
- **US5 (Phase 7)**: depends on US1–US3 (the constructor is final by then).
- **Polish (Phase 8)**: depends on all stories.

### User Story Dependencies

- US1, US2 and US3 are independently testable and share one file (`jwt_authenticator.py`); within that file they are ordered T006 → T009 → T011.
- US4 depends on US1.
- US5 depends on US1–US3.

### Parallel Opportunities

- Foundational T002–T005 are four different files and run in parallel.
- US1's test task T008 can be written once T006/T007 land.
- US2's and US3's test tasks (T010, T012) touch the same test file, so they run sequentially within it, but US4's T013 is a different directory and can run in parallel with them.

### Within Each User Story

- Tests are written and shown to fail before the implementation that makes them pass.
- The authenticator edits are applied in the order T006 → T009 → T011.
- Each adversarial break is applied in isolation, confirmed to fail the intended test, then restored.

---

## Parallel Example: Foundational phase

```text
Task T002: context/user_info.py            (session_id field)
Task T003: context/ctx_constants.py        (Ctx.User.session_id)
Task T004: exceptions/authentication_contract_error.py
Task T005: auth/authenticator.py           (INVARIANTS)
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (baseline) and Phase 2 (foundational).
2. Complete Phase 3 (US1): the session id flows into an aspect.
3. **STOP and VALIDATE**: run T008's integration test independently; the value is delivered.

### Incremental Delivery

1. Foundational → the field and the error exist.
2. US1 → session id reaches the context (MVP).
3. US2 → broken identifiers raise loudly.
4. US3 → invalid tokens stay refusals.
5. US4 → session-based access is possible.
6. US5 → every call site migrates.
7. Tail → check run to zero, documentation, changelog.

### Notes

- [P] tasks = different files, no shared dependency.
- The three tail tasks are reserved and must not be absorbed by any story.
- `jwt_authenticator.py` is the one file all of US1–US3 edit; apply T006 → T009 → T011 in that order.
- Verify each adversarial break fails before restoring; never leave a break in place.
