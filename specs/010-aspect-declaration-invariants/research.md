# Phase 0 — Research: an aspect declaration's signature is an invariant, not a convention

**Feature**: `specs/010-aspect-declaration-invariants` | **Date**: 2026-10-18

Every unknown in the plan's Technical Context is resolved below. The measurements were taken on the tree at `main` (`c61bdfe6`) with a syntax-tree scan of the repository and with runnable probes, not from the issue's text; where the issue and the tree disagree, the tree is reported.

## R1 — Where the shared contract lives

**Decision**: one new module, `packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py`, holding a public `AspectContract` (name, parameter order, the type each parameter must resolve to, and the rule for the return) and four module-level validators: `validate_names`, `validate_annotated`, `validate_types`, `validate_callable_with_position`.

**Rationale**

1. The four decorators need one message shape and one order rule. Four copies of "must declare its parameters as (self, params, state, box, connections)" drift within a release.
2. The refusal text is this feature's only user-visible output; keeping it in one module is what makes SC-002 ("a reader fixes the declaration from the message alone") testable once rather than four times.
3. `access_decide/access_decide_signature.py` is the precedent and is imported by exactly two places (the decorator and the graph node); this module will be imported by eight (four decorators, four nodes), which makes a shared home more valuable, not less.

**Alternatives considered**

- **Reuse `access_decide_signature.py`.** Rejected: its contract is the object check's four parameters, its return must be a `Verdict`, and it has no `state`, `error` or `state_after`. Generalising it would rewrite a committed, working module for no benefit and would put the object check's tests at risk.
- **Add the checks to each decorator.** Rejected: four copies of the type table (`BaseState`, `ToolsBox`, `dict[str, BaseResource]`, `ContextView`) and four copies of the "why the order is fixed" sentence.
- **A base class and four subclasses.** Rejected: the difference between the four is data, not behaviour — a table is enough.

## R2 — The four contracts, exactly

Measured from the call sites, not from the documentation:

| Declaration | Parameters, in order | Types each must resolve to |
| --- | --- | --- |
| `@summary_aspect` | `self, params, state, box, connections` (+ `ctx`) | `params`: `BaseParams` or a subclass; `state`: `BaseState`; `box`: `ToolsBox`; `connections`: `dict[str, BaseResource]`; `ctx`: `ContextView` |
| `@regular_aspect` | the same | the same |
| `@on_error` | the same, then `error` | the same, `error`: `Exception` |
| `@compensate` | `self, params, state_before, state_after, box, connections, error` (+ `ctx`) | `params`/`box`/`connections`/`ctx` as above; `state_before`: `BaseState`; `state_after`: `BaseState \| None`; `error`: `Exception` |

The returns:

| Declaration | Return contract | Where the engine reads it |
| --- | --- | --- |
| `@summary_aspect` | the operation's `Result` | `AspectExecutor.execute_summary` (`aspect_executor.py:187`) |
| `@regular_aspect` | a state fragment: `dict[str, Any]` | `execute_regular` already refuses a non-dict with `TypeError` (`aspect_executor.py:157`) |
| `@on_error` | the operation's `Result` | `ErrorHandlerExecutor.handle` (`error_handler_executor.py:136-149`), unchecked today |
| `@compensate` | `None` | `SagaCoordinator` awaits the call and ignores the value (`saga_coordinator.py:161-182`) |

**Evidence for `state_after: BaseState | None`**: `SagaFrame.state_after` is typed `object | None` with the comment "BaseState | None" (`runtime/saga_frame.py:71`), and the frame is replaced with `state_after=state` only after the aspect succeeds (`action_product_machine.py:461-467`). A compensator for an aspect that failed therefore receives `None`. Requiring `BaseState` there would be a rule the engine breaks.

**Evidence for `error: Exception`**: the handler is called with the caught exception (`error_handler_executor.py:62`), and any exception can arrive; a narrower annotation would be a promise the framework cannot keep.

## R3 — Resolving annotations of operations declared inside a function

**Decision**: `validate_types` calls `get_type_hints(func, localns=...)` with a `localns` built from the operation class itself — `{action_cls.__name__: action_cls, action_cls.__qualname__.rpartition(".")[2]: action_cls} | dict(vars(action_cls))` — and the operation's module globals stay the `globalns`.

**Rationale**

1. Under `from __future__ import annotations`, every annotation is a string, so resolution is mandatory; the repository's modules use that import widely.
2. 48 of the 506 aspect declarations in `.py` sit **inside a function** (mostly tests and `packages/aoa-*/tests/support`). There, `-> MyAction.Result` cannot be resolved from `func.__globals__` alone: `MyAction` is a local name. Adding the class itself to `localns` makes `MyAction.Result` resolve, and `vars(action_cls)` makes a bare `Result` resolve too.
3. This is strictly more capable than `access_decide_signature.validate_types`, which needs no such trick because its return contract is a module-level `Verdict`. Copying its implementation without the `localns` would refuse correct declarations in the repository's own tests.

**Evidence**

Measured with an AST scan that tracks whether a declaration is nested inside a function: 48 of 506 `.py` declarations are function-local; the large majority of them are in test modules. A probe over the current `access_decide` test pattern (a class declared inside a test function, parameters annotated with imported base types) confirms the resolution works where every name is module-level, and fails where the annotation names the class hosting it — hence the `localns`.

**Alternatives considered**

- **Require module-level annotations only.** Rejected: it would refuse the repository's own test fixtures and force 48 hoists for no user-facing reason.
- **Skip unresolvable annotations silently.** Rejected: FR-008 requires a refusal — an unreadable contract is not a passing one, and silence is exactly the failure mode this feature exists to end.
- **Evaluate annotations with `eval` by hand.** Rejected: `get_type_hints` already handles `Optional`, string forward references and `Annotated`; reimplementing it is how subtle bugs arrive.

## R4 — What a summary's return annotation may be

**Decision**: the annotation must be a **supertype of the operation's declared `Result`** — `issubclass(declared_result_type, annotation)`. `-> MyAction.Result` passes, `-> BaseResult` passes, `-> Any` and `-> OtherAction.Result` are refused at assembly.

**Rationale**

1. The engine hands back an instance of the operation's `Result`; an annotation that is a supertype of it is a true promise, and `BaseResult` is the shorthand a generic action uses.
2. `access_decide` already accepts the family rather than the exact leaf: `_validate_return` accepts `Verdict` and its subclasses, not only a specific verdict.
3. `Any` is not a type: `issubclass(X, Any)` raises, so the check must reject `Any` (and anything that is not a class) explicitly. That is the case the issue measured and the demo in the spec reproduced.

**Alternatives considered**

- **Exact type only (`annotation is declared_result_type`).** Rejected: it would refuse `-> BaseResult`, which promises nothing false, and would diverge from the object check's rule for no benefit.
- **Annotation-only check, no run-time check.** Rejected in the clarification: a method that contradicts its own annotation is invisible to it.

## R5 — Where the duplicate summary is refused

**Decision**: `SummaryAspectIntentResolver.resolve_summary_aspects(action_cls)` raises `DuplicateSummaryAspectError` when the collected list holds more than one, naming both methods in the operation's own order, mirroring `AccessDecideIntentResolver.resolve_check`.

**Rationale**

1. It is the first thing the edge builder calls (`summary_aspect_graph_edge.py:68`), so the confusing `InvalidGraphError: ... references missing target_node_id 'TwoSummariesAction:second_summary'` is never reached.
2. The resolver is the natural owner: the same class already owns "which summary does this operation declare", and `ActionGraphNode.get_summary_aspect_graph_node` reads `self.summary_aspect[0]` on the edges the resolver produced — with at most one, the `[0]` is no longer a silent truncation.
3. `resolve_summary_aspects` has exactly two callers (`summary_aspect_graph_edge.py`, `tests/.../test_aspect_intent_resolver.py`), so raising cannot surprise a third party.

**Alternative considered**: checking in `SummaryAspectGraphEdge.get_summary_aspect_edges`. Rejected: the refusal belongs to resolution, not to edge construction, and the resolver is what the tests already call.

## R6 — Where the summary's answer is checked at run time

**Decision**: in `AspectExecutor.execute_summary`, after the call returns: resolve the operation's `Result` once, compare `raw` with `isinstance`, raise `ActionResultTypeError` naming the operation, the declared `Result` and the actual type; on success, return the value as today.

**Rationale**

1. `execute_summary` is the only place a summary's return value reaches the machine (`action_product_machine.py:503` is the single call site).
2. The method already calls `resolve_result_type(action_cls)` and discards the answer (`aspect_executor.py:215`); the change keeps the value and uses it, so the per-call cost is one `isinstance`.
3. `ActionResultTypeError` already exists, is exported, and is raised nowhere — the check makes it real instead of leaving a dead public name (see the spec's Clarifications).

**Evidence that the path is unchecked today**: a probe action declaring `ResultStub` whose summary returns `{"not": "a result"}` answers with a `dict` and no refusal (`answer type: dict`, `is ResultStub: False`).

## R7 — The error vocabulary and what stays catchable

**Decision**

- `AspectSignatureError(SignatureContractError)` — the shape and the types at both moments; the message says which moment it was.
- `DuplicateSummaryAspectError(TypeError)` — a second summary, mirroring `DuplicateAccessDecideError`.
- `ActionResultTypeError` — revived for the answer rule; not re-created.
- Both new names exported in `exceptions/__init__.py` (import + `__all__`), beside the existing ones.

**Rationale**

1. Subclassing `SignatureContractError` keeps every existing `except SignatureContractError` and `except TypeError` working, which is what FR-021 asks for, while giving the rule a name of its own (FR-019).
2. Mirroring `DuplicateAccessDecideError` keeps the two "you declared it twice" refusals reading the same way.
3. The four decorators today raise `SignatureContractError` for the arity; the new class replaces it there, so the old name never disappears from a traceback.

**Note on the existing `__all__`**: `exceptions/__init__.py` lists several names twice (`"DuplicateAccessDecideError"` appears twice). This plan adds two names once each and does not clean the list — that is a separate change.

## R8 — The corpus migration: how large, and how it is done

**Decision**: migrate mechanically with a throwaway codemod that is **not committed**, review the diff by tree, and treat the closing check run and a full run of every example as the gate.

**Measured size** (AST scan of every declaration of the four decorators, 2026-10-18):

| Tree | Declarations | Non-conforming | Of which |
| --- | --- | --- | --- |
| `.py` under `packages/` | 343 | 104 | 104 need names and/or annotations |
| `.py` under `examples/` | 163 | 163 | every one |
| example notebooks (`examples/**/*.ipynb`) | 158 | 158 | every one |
| `docs/**/*.md` code blocks | 99 | 98 | 97 unannotated, 6 misnamed (some both) |
| **total** | **763** | **523** | |

**Correction to the specification**: the spec's figure of 211 counted only the two decorators the issue's table names (summary, regular) and only `.py` files. Counting all four decorators and the two other carriers of declarations gives 523. The specification is updated to the measured total in the same pass as this research.

**Why a codemod, and why it is not committed**

1. 523 sites across 200+ files is past the size where hand-editing is safe, and the transformation is regular: parameter names are known, and the annotation to insert is known from the parameter's role.
2. A script that rewrites declarations is not part of the framework's surface; committing it would add a tool nobody runs again. Its evidence is the diff and the check run.
3. The codemod must not guess: where a site is ambiguous (a declaration annotated with the operation's own `Params` that the codemod cannot name), it leaves the line untouched and reports it, and the migration fixes those by hand.

**What the codemod cannot do, and the hand work it leaves**

- **The summary's return annotation.** The operation's `Result` class is per operation; in `packages/` and `examples/` it is usually `${Operation}.Result` or a module-level `…Result` — resolvable per file, so the codemod derives the name from the class body's `BaseAction[...]` arguments when they are literals.
- **The docs' return annotations.** A snippet's operation may not define a `Result` at all (early tutorials use `ResultStub`); those are read one by one.
- **Notebooks.** The same transformation over cell sources, with JSON re-serialised so that the diff stays cell-by-cell; a notebook whose `.py` twin exists must end identical in the shared cells.

**Order**: `packages/` first (the suite does not run without it), then `examples/*.py`, then notebooks, then `docs/`.

## R9 — How the change is proven

**Decision**: three independent proofs, none of which is a screenshot or a claim.

1. **Adversarial tests**, per `AGENTS.md`: for each rule, the test is written first, the check is disabled in the code, the test is confirmed to fail **alone**, and the code is restored. The rules and their tests:

   | Rule | Test |
   | --- | --- |
   | names and order, four decorators | a declaration per decorator, renamed and reordered, refused at class creation |
   | keyword-only / `*args` | a declaration the engine cannot call positionally |
   | annotations present | one missing parameter annotation, one missing return, per decorator |
   | types at assembly | a `box: str`, a `connections: dict[str, Any]`, a `state: dict`, a bare `error` |
   | `@context_requires` order | takes `ctx` without declaring it, and declares it above the decorator |
   | a second summary | two declarations, refusal naming both, and the graph error gone |
   | the answer's annotation | `-> Any`, `-> Other.Result`, `-> BaseResult` (accepted), `-> MyAction.Result` |
   | the answer's instance | a mapping, a foreign `Result`, and the operation's own `Result` |
   | invariance | an already-compliant operation: same answer, same events, same logs |

2. **The corpus runs.** Every example `.py` is executed with the repository's environment (`uv run python examples/...`) and its output compared with the recorded output; notebooks are executed cell-by-cell for the ones the migration touched. The closing check run does not execute examples, so this is a separate, deliberate pass.

3. **The check run.** `bash scripts/run_checks_with_log.sh` to zero, with the two known remarks (`archive/logs/check-all.txt`) left as they are: the Vite chunk-size advisory and LangGraph's pending-deprecation warning.

**Not a proof**: a passing suite whose fixtures were all rewritten to comply — that would show the checks accept correct code, not that they refuse incorrect code. Which is why item 1 exists and is done first.
