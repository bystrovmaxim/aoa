# Phase 0 Research: Access decisions

Every decision below is either forced by the specification, settled in the clarification session (see `spec.md`, `## Clarifications`), or an engineering choice whose alternatives are named. No `NEEDS CLARIFICATION` item remains.

## D1. The three answers are a pydantic hierarchy discriminated by a `kind` word

- **Decision**: `Verdict` is a frozen `BaseSchema` with `kind: str` and no default, so the base cannot be built. `Allowed`, `Refused` and `Undecided` each pin `kind` with a `Literal`.
- **Rationale**: the answer travels as data (spec FR-003); `kind` is the word a caller branches on, and because it is a literal rather than a class name, renaming a class never changes the contract. A base that cannot be constructed means "an answer of no particular kind" is unrepresentable.
- **Alternatives considered**: a plain `Enum` (loses per-answer fields such as `gate` and `reason`); one exception type per outcome (exceptions are not data and cannot be returned by the question path); `dataclass` (drops the validation the rest of the engine's models rely on).

## D2. Four steps with one signature, and five words for what refused

- **Decision**: `GATES = (auth_gate, roles_gate, guard_gate, object_gate)`, in that order. A step is `(Context, BaseAction, BaseParams | None, ToolsBox, dict[str, BaseResource]) -> Awaitable[Verdict | None]`; `None` means the call may continue, and the first non-`None` answer ends the decision. **Corrected while building it**: the step takes the action *instance*, not its class — the object check is an instance method and the cascade must call it as one, and both paths have an instance at decision time (the question path instantiates each item anyway). The class is still reachable through the instance, which is all the other steps need. The steps publish five words between them: `auth_gate` answers `AUTH_COORDINATOR`, `guard_gate` answers `GUARD`, `object_gate` answers `ACCESS_DECIDE`, and `roles_gate` answers **two** — `CHECK_ROLES` when the caller holds none of the roles the operation lists, `WHEN` when a listed role is held but the condition its grant declared refused.
- **Rationale**: the order is part of the contract (FR-007), and it is why the identity and roles steps run before the parameters are examined (FR-008) while `guard_gate` may read them. `when=` is evaluated *inside* the roles step rather than as a step of its own, because it takes part in choosing the role: a grant whose role matches but whose condition says no is skipped and another grant may still win, and a cascade that stops at the first refusal cannot express "try the next grant". The word can still be separate, because the step already knows which of the two happened — the existing code carries the same distinction as `level` 1 versus 2 (`role_matched` in `role_checker`). Separation of *names* costs nothing; separation of *steps* would change the rule. A step that fails outright names its own word, so a failure of the roles step names `CHECK_ROLES` even though that step can also answer `WHEN` — the word says which step could not tell, and the steps are four while the words are five.
- **Alternatives considered**: a step per condition (changes role matching, see above); one `WHEN_OR_GUARD` word carrying the difference in a second vocabulary (rejected in D4: it publishes a reason list that only restates what a word can say); separate methods on the machine (order becomes implicit in the call sequence); a registry with priority numbers (more machinery than four fixed steps need); steps that raise (a step that raises is a defect, not a decision — see D3).


## D3. A gate may answer "undecided" itself, and a gate that raises is turned into the same answer

- **Decision**: a gate that cannot tell returns `Undecided(gate=…, cause=...)`, naming itself; a gate that raises is caught by the cascade and becomes `Undecided(gate=…, cause=exc)` for the gate that raised — the same answer, differing only in which step it names.
- **Rationale**: settled in `spec.md` (clarification Q2, FR-005). A gate that catches a store error inside its own logic must have a way to say so; forcing it to re-raise would make the developer invent an exception to express a normal outcome. Naming the gate is what makes the answer actionable and costs nothing, because the gate is already a published word.
- **Alternatives considered**: only a raise produces undecided (two spellings for one outcome, and the developer must know to re-raise); a distinct answer for "gate crashed" versus "gate could not tell" (the caller can act on neither, and the difference is already in the failure event).


## D4. There is no reason vocabulary: the words are the gates

- **Decision**: the framework publishes five gate words and invents no reason text of its own. `reason` is the developer's: it carries whatever they declared beside their condition, and it is absent when they declared none.
- **Rationale**: an earlier draft kept a `reasons.py` with six codes beside the gates, and five of them restated a gate (`UNAUTHENTICATED` for `AUTH_COORDINATOR`, `FORBIDDEN_ROLE` for `CHECK_ROLES`, `FORBIDDEN_OBJECT` for `ACCESS_DECIDE`, `FORBIDDEN_GRANT`/`FORBIDDEN_GUARD` for the two conditions). The only information a reason carried beyond a gate was the `when=` versus `guard=` distinction, and a step name can carry that itself: `WHEN` and `GUARD` are separate words (D2), so nothing is left for a second vocabulary to say. Two lists that must stay in step are worse than one list that says everything.
- **Alternatives considered**: keeping all six codes in one module (duplication with a tidier address); making `reason` an enum (a developer could not add their own text); dropping `reason` entirely (a developer's own words are the most useful thing a refusal can carry, and FR-010 keeps them).


## D5. The object answer is one shared instance, decided in one branch

- **Decision**: `FORBIDDEN_OBJECT` is a single `Refused` instance used for both "no such object" and "someone else's object", and the developer answers both from one condition.
- **Rationale**: spec FR-011 and its acceptance scenario 2. Two branches drift, and the moment one becomes more specific the error channel starts telling a caller which object ids exist.
- **Alternatives considered**: a separate `NOT_FOUND` answer (leaks existence); two refusals with different reasons (the same leak, one refactor later).

## D6. One new event: a gate that cannot complete

- **Decision**: `AccessGateFailedEvent(action_name, exception_type)` is the only event this capability adds, published when a gate raises while a call executes, carrying the request identity the context already has and never inventing one. Asking in advance publishes nothing of the kind: a question is answered, not announced. A decision publishes nothing: it reaches the caller as an exception when executing and as the answer when asking.
- **Rationale**: a refusal is not a fact about the system that nobody else can observe — the caller receives it, and on the execution path the run already shows it (`GlobalStart` without `GlobalFinish`). What an operator genuinely cannot see otherwise is a gate that broke: the caller gets an undecided answer with no explanation, and the engine's own telemetry needs to say which step failed and with what kind of failure. Correlation on that event is what makes it actionable, which is why it carries the request identity.
- **Alternatives considered**: publishing every decision as its own event (dropped by the maintainer: it duplicates what the caller already has, and makes the question path — a question, not an action — produce a stream of facts nothing acts on); one event with a status flag for both a refusal and a failure (a policy decision and a broken dependency would be told apart by convention rather than by type); telemetry written by the core itself (the core stores nothing and knows no backend).

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
- **Rationale**: spec FR-005, FR-015 and SC-007. The text of a failure is diagnostic material for a log written where the crash happened, not part of a contract a caller reads.
- **Alternatives considered**: carrying the message in the answer (leaks internals, and a caller may cache it); dropping the cause entirely (the failure could not be logged where it happened).

## D10. The object check is a declaration, not an inherited method

- **Decision**: an operation's own answer about its object is declared — a decorator on a method whose name carries the enforced suffix — and it is optional, at most one, and never inherited. An operation that declares none has no object check. When it is declared, the step publishes its own before and after events, shaped like the compensator's, and the assembled capability carries the declaration so that introspection sees it.
- **Rationale**: the check is the only behaviour the machine reaches by method name rather than through the graph — nothing under `graph/` mentions `access_decide` at all — and it is inherited, with a default that allows everything. So nothing built on the graph can see it, and a subclass silently inherits its parent's decision. Every other behaviour of an operation is a declaration whose invariants are enforced while the capability is assembled; this makes the object check one of them, and its events come from machinery that already exists for the compensator.
- **Alternatives considered**: keeping the inherited method (invisible to the graph, silently inherited, and "at most one" unenforceable); making it required like the summary aspect (an operation without an object check is legitimate, and most have none); declaring it with an empty default (a declaration that says nothing is worse than no declaration).

## D11. The object check announces itself on both paths; nothing else is published, and no access decision reaches the failure handling

- **Decision**: the declared object check publishes its before and after events whenever it runs — executing or asking in advance — and a gate that cannot tell publishes the failed-gate event only while a call executes. No access decision enters the operation's own failure handling: a refusal and an inability to decide alike stop the call, as an exception while executing and as an answer when asked about.
- **Rationale**: the object check is the one access step that is a declared behaviour of the operation, so it is announced the way the other declared behaviours are, and asking in advance genuinely runs it — that is what makes the advance answer trustworthy rather than a guess. Everything else about a decision belongs to the caller: the answer, or the exception carrying it. Routing an access outcome into the failure handling would need a rule for what a handler may do with a denial — answering a call that was never authorized is the obvious hazard — and this capability deliberately builds no such rule.
- **Alternatives considered**: announcing the object check only while executing (the advance answer would come from a check that never announced itself, so the two paths would not be observably the same); publishing every decision as an event (dropped by the maintainer: it duplicates what the caller already has); letting a handler answer a denial (a handler would be able to serve a call the decision refused).
