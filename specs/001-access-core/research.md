# Phase 0 Research: Access decisions

Every decision below is either forced by the specification, settled in the clarification session (see `spec.md`, `## Clarifications`), or an engineering choice whose alternatives are named. No `NEEDS CLARIFICATION` item remains.

## D1. The three answers are a pydantic hierarchy discriminated by a `kind` word

- **Decision**: `Verdict` is a frozen `BaseSchema` with `kind: str` and no default, so the base cannot be built. `Allowed`, `Refused` and `Undecided` each pin `kind` with a `Literal`.
- **Rationale**: the answer travels as data (spec FR-003); `kind` is the word a caller branches on, and because it is a literal rather than a class name, renaming a class never changes the contract. A base that cannot be constructed means "an answer of no particular kind" is unrepresentable.
- **Alternatives considered**: a plain `Enum` (loses per-answer fields such as `gate` and `reason`); one exception type per outcome (exceptions are not data and cannot be returned by the question path); `dataclass` (drops the validation the rest of the engine's models rely on).

## D2. Gates are an ordered tuple of callables with one signature

- **Decision**: `GATES = (auth_gate, roles_gate, condition_gate, object_gate)`, in that order. A gate is `(Context, type[BaseAction], BaseParams | None, ToolsBox, dict[str, BaseResource]) -> Awaitable[Refused | Undecided | None]`. `None` means the call may continue; the first non-`None` answer ends the decision.
- **Rationale**: the order is part of the contract (spec FR-007), and it is the reason the identity and role gates can run before the parameters are examined (FR-008). One signature per gate keeps the cascade readable and the matrix testable.
- **Alternatives considered**: separate methods on the machine (order becomes implicit in the call sequence); a gate registry with priority numbers (more machinery than four fixed steps need); gates that raise (a gate that raises is a defect, not a decision — see D3).

## D3. A gate may answer "undecided" itself, and a gate that raises is turned into the same answer

- **Decision**: a gate that cannot tell returns `Undecided("EVALUATION_FAILED", cause=...)`; a gate that raises is caught by the cascade and becomes `Undecided("EVALUATION_FAILED", cause=exc)` — the same answer with the same fixed reason.
- **Rationale**: settled in `spec.md` (clarification Q2, FR-005). A gate that catches a store error inside its own logic must have a way to say so; forcing it to re-raise would make the developer invent an exception to express a normal outcome.
- **Alternatives considered**: only a raise produces undecided (two spellings for one outcome, and the developer must know to re-raise); a distinct answer for "gate crashed" versus "gate could not tell" (the caller can act on neither, and the difference is already in the event).

## D4. The reason vocabulary lives in one module; developer reasons are additive

- **Decision**: `reasons.py` holds the six fixed codes — `UNAUTHENTICATED`, `FORBIDDEN_ROLE`, `FORBIDDEN_GRANT`, `FORBIDDEN_GUARD`, `FORBIDDEN_OBJECT`, `EVALUATION_FAILED`. A declared `reason=` is any non-empty string, defaulted to the fixed code for that condition when the developer declares none.
- **Rationale**: spec FR-012 and FR-010. One list makes the framework's own vocabulary reviewable in one place; a default per condition means a developer who does not care still gets a reason the caller can branch on.
- **Alternatives considered**: an enum for all reasons (a developer could not add their own without editing the framework); free strings everywhere (the framework's own prose drifts between gates).

## D5. The object answer is one shared instance, decided in one branch

- **Decision**: `FORBIDDEN_OBJECT` is a single `Refused` instance used for both "no such object" and "someone else's object", and the developer answers both from one condition.
- **Rationale**: spec FR-011 and its acceptance scenario 2. Two branches drift, and the moment one becomes more specific the error channel starts telling a caller which object ids exist.
- **Alternatives considered**: a separate `NOT_FOUND` answer (leaks existence); two refusals with different reasons (the same leak, one refactor later).

## D6. Two new events; both carry the request identity the context already has

- **Decision**: `AccessDecidedEvent(action_name, verdict, check_only)` on every decision, and `AccessGateFailedEvent(action_name, exception_type)` when a gate fails. Both carry the request identity taken from the context when it is present, and never invent one. Both are additions to the plugin contract.
- **Rationale**: spec FR-013…FR-015 and the clarification on correlation. A decision event without correlation cannot be tied to the call that produced it, which is the whole point of publishing the failure separately.
- **Alternatives considered**: one event with a status flag (a failed gate and a refusal would be told apart by convention rather than by type); telemetry written by the core itself (the core stores nothing and knows no backend).

## D7. The execution path speaks through exceptions that carry the verdict; the question path returns it

- **Decision**: the execution path raises `AccessDenied(verdict)` or `AccessUndecided(verdict)`; the question path returns the verdict. `AuthorizationError` stops being raised by the core but stays in the tree, and the `except` clauses in `packages/aoa-fastapi-adapter` and `packages/aoa-mcp-adapter` switch to the new types.
- **Rationale**: the aspect pipeline is already running when the decision is enforced, so an exception is the only way to unwind it; the question path runs no aspect, so an answer is the natural result. The two adapter lines are the minimum that keeps a refusal leaving as a refusal — without them, existing adapter tests would see an unhandled error instead (this is the single out-of-package touch, and it was chosen explicitly).
- **Alternatives considered**: delete `AuthorizationError` now (its remaining consumers — the demo application, the examples and the tutorial — would break, and updating them is transport work); keep raising `AuthorizationError` and bolt the verdict onto it (keeps two exception shapes for one decision).

## D8. The core has no batch form of the question

- **Decision**: asking in advance is one call about one operation. Batching, endpoints, request limits and rate limiting are not modelled here.
- **Rationale**: settled in `spec.md` (scope note). The core answers about the call it is given; a batch is a shape of a request, and requests belong to the transport layer.
- **Alternatives considered**: keeping a batch API in the core (drags request shape into the engine and forces a bound to be specified here).

## D9. The cause of a failure stays in memory

- **Decision**: `Undecided` keeps the exception in a private attribute, which never appears in `model_dump()`, in an answer or in an event; the failed-gate event carries the failure's type only.
- **Rationale**: spec FR-005, FR-016 and SC-007. The text of a failure is diagnostic material for a log written where the crash happened, not part of a contract a caller reads.
- **Alternatives considered**: carrying the message in the answer (leaks internals, and a caller may cache it); dropping the cause entirely (the failure could not be logged where it happened).
