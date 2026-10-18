# Feature Specification: An aspect declaration's signature is an invariant, not a convention

**Feature Branch**: `feature/issue-193-aspect-decorator-signature-invariants`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/193 — the aspect decorators check only how many parameters a method declares. Its names, their order, the annotations, the types those annotations resolve to, and what a summary hands back are not invariants, while the sibling `@access_decide` treats all of them as ones."

## Context: what the engine asks of these methods today

Four decorators mark methods the engine calls itself, and all four check the arity alone:

| Declaration | Parameters the engine hands over |
| --- | --- |
| `@summary_aspect` | `self, params, state, box, connections` (+ trailing `ctx`) |
| `@regular_aspect` | the same |
| `@on_error` | the same, then `error` |
| `@compensate` | `self, params, state_before, state_after, box, connections, error` (+ trailing `ctx`) |

Measured on the tree as it stands, not assumed — a declaration that renames, reorders and leaves everything untyped is accepted, because five parameters is five parameters:

```python
@summary_aspect("S")
async def renamed_summary(self, reordered, ctx2, b, conn):   # every name wrong, nothing typed
    return MyAction.Result()
# accepted
```

`@access_decide` refuses exactly that shape, at two moments: at declaration for what needs no name resolution (count, names in order, an annotation on every parameter and on the return), and at assembly for the types, because `params` is annotated with the operation's own `Params`, a name that does not exist while the class body runs.

The documentation already promises the same of the aspects — "it is a declaration like `@summary_aspect`, and what the system requires of it is checked the same way" (`docs/reference/intents-and-invariants.md`) — and of a summary's answer: "it must return a typed `Result`". The second promise holds by convention alone, because the returned value is never compared with the operation's `Result`.

## Clarifications

### Session 2026-10-18 — decisions taken while writing this specification

- **All four decorators are in scope, not the two the table in the issue lists.** The issue names `@on_error` and `@compensate` among the siblings that "check the arity alone", and the argument that makes the check necessary is the same for them word for word: the engine calls the method, so the signature is a contract. Repairing two of four would leave the family split in the same way it is split today.
- **The two moments are the object check's two moments.** What needs no name resolution is refused where the method is written; what needs the operation's own names to exist is refused when the capability is assembled. A single moment would either refuse correct forward references or let a wrong type live until the first call.
- **The names are the engine's names as they are today.** No aliasing, no positional leniency, no short forms. `p, s, b, c` is exactly the style this change exists to refuse, and it is what eleven declarations in `examples/` use today.
- **A wrong declaration is refused, not warned about.** The framework cannot ship examples its own rules refuse, and the closing check run has to be green; a release with a warning window would mean two contracts, and the warning would outlive the release that introduced it. The repository's own corpus is migrated inside this change (see User Story 5).
- **A second summary is reported as a second summary, at assembly.** The same moment and the same shape as `DuplicateAccessDecideError`: the reader learns that the operation declares two exit points, and which two methods they are — not that an edge points at a node that does not exist.
- **The summary's answer is checked at both moments, as the last story.** At assembly, the declared return annotation is compared with the operation's `Result`, so `-> Any`, another operation's `Result` or an unresolvable name is refused before any call is served. At run time, the returned instance is compared with that same `Result`, so a method that contradicts its own annotation is refused too. That mechanism was the one genuinely open question in the issue, and it is settled here rather than in a follow-up, because dropping it would leave the documented invariant as a convention — and because `ActionResultTypeError` already exists in the vocabulary and is raised nowhere today.
- **The answer's rule takes the name it already has.** `ActionResultTypeError` is public, exported and raised nowhere today; a new class beside it would leave two names for one rule, and the dead one would stay dead. It becomes the error the answer rule raises. The two genuinely new names are therefore the signature's and the duplicate summary's, and the vocabulary grows by exactly two.
- **The error handler's result is not made checkable by this change, and the specification does not pretend it is.** The issue credits that path with a validation it does not have: `ActionResultTypeError` is imported and caught there, and raised nowhere in the package. Measured on the tree: a summary returning `{"not": "a result"}` answers with a `dict`; the same is true of a handler's result. This feature gives the summary the rule and the error name the handler path already mentions; unifying the two paths is a separate change, and pretending otherwise would make the family claim false.
- **Nothing else about an aspect changes.** The description requirement, the `async` requirement, the name suffixes, the order of the pipeline and the context contract stay exactly as they are. This work adds checks; it does not redesign aspects.

### Session 2026-10-18 — clarification

- Q: How should the framework refuse a `@summary_aspect` whose answer is not its declared `Result` — by checking the declared annotation at assembly, the returned instance at run time, both, or neither? → A: **Both moments.** The declared return annotation is compared with the operation's `Result` when the capability is assembled, so `-> Any` or another operation's `Result` never reaches a call; the returned instance is compared with the same `Result` after the method returns, so a method that contradicts its own annotation is refused as well. This follows the division the rest of the specification already uses: what can be read before a call is served is refused then, and what only exists during a call is refused there.
- Q: Should the three new refusals reuse the error classes the framework already raises, or does each rule get a name of its own? → A: **A named error per rule.** Each of the three rules is told apart by the error it raises, exported beside the existing ones, and the moment it was refused at (declaration or assembly) is stated in the message rather than in the class name. The signature rule keeps one name at both moments, because it is one rule broken once.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a developer writing an operation, a developer reading the refusal they just got, and the person who maintains the examples the documentation walks through.

### User Story 1 - A renamed or reordered parameter is refused where the method is written (Priority: P1)

A developer writes a summary aspect and calls the second parameter `p` because it is shorter, or writes the four parameters in the order they read best. Today the class is created, the operation assembles, and the method receives whatever the engine passed by position — which may well be the tool box under a name that says `conn`. The developer finds out later, somewhere else, or never.

After this change the class body itself refuses the declaration, and the refusal says what the engine hands over, in what order, and why the order is not negotiable.

**Why this priority**: this is the defect. Every other story is either a second kind of mistake or a consequence of the first; the renamed parameter is the one that runs silently and corrupts an answer.

**Independent Test**: declare one method per decorator with the right count and wrong names, and one with the right names in the wrong order; every one of them must fail while the class is being defined, without any operation being built and without any call being served.

**Acceptance Scenarios**:

1. **Given** a `@summary_aspect` method declaring `(self, p, state, box, connections)`, **When** the class body executes, **Then** it is refused with a message naming the method, the expected order and the actual order.
2. **Given** a `@regular_aspect` method declaring the right five names in the wrong order, **When** the class body executes, **Then** it is refused the same way.
3. **Given** an `@on_error` method whose `error` sits before `box`, **When** the class body executes, **Then** it is refused the same way.
4. **Given** a `@compensate` method whose two state parameters are swapped, **When** the class body executes, **Then** it is refused the same way.
5. **Given** a correct declaration with `@context_requires` under the declaration, **When** the class body executes, **Then** it is accepted and the trailing `ctx` is part of the expected order.
6. **Given** a declaration that takes `ctx` but carries no `@context_requires`, or one that carries `@context_requires` above the declaration so the declaration cannot see it, **When** the class body executes, **Then** it is refused, and the message says which of the two is the mistake and which decorator order is correct.
7. **Given** a declaration that receives its arguments as keyword-only parameters or through `*args`, **When** the class body executes, **Then** it is refused: the engine passes by position, so a signature that cannot receive positionally is not a signature the engine can call.

---

### User Story 2 - An untyped declaration is refused, and its types are checked at assembly (Priority: P2)

A developer declares an aspect with the right names and no annotations, or annotates `params` with `dict` because that is what it looks like. The annotations are how this framework states what a step hands over and what it reads back; a step that leaves them off is not a shorter declaration, it is an unstated contract.

After this change every parameter except `self` carries an annotation, the return carries one, and the types those annotations resolve to are checked when the capability is assembled — `params`, the state, the tool box, the connections mapping, the context view, and the error a handler receives.

**Why this priority**: the names make the call correct; the types make it meaningful. It is second because a missing annotation never silently feeds the wrong object — it fails loudly at the first call anyway — while a renamed parameter does not.

**Independent Test**: declare one compliant-shaped method per decorator with a missing parameter annotation, and one with the return left bare; each must be refused at definition. Then declare one with every annotation present but `state` typed as `dict`, and confirm it refuses at assembly and not at the first call.

**Acceptance Scenarios**:

1. **Given** an aspect method whose `connections` parameter carries no annotation, **When** the class body executes, **Then** it is refused, naming the parameter.
2. **Given** an aspect method with no return annotation, **When** the class body executes, **Then** it is refused.
3. **Given** an aspect method annotated entirely with the wrong types, **When** the operation's capability is assembled, **Then** it is refused before any call is served, and the message names the parameter, what was declared and what the engine hands over.
4. **Given** an aspect method whose annotations are forward references that only resolve once the operation's own `Params` and `Result` exist, **When** the operation is assembled, **Then** the declaration is accepted.
5. **Given** an aspect method annotated with the operation's own `Params` subclass, **When** the operation is assembled, **Then** it is accepted: the operation's parameters are what the step receives.
6. **Given** `self` left unannotated, **When** the class body executes, **Then** it is accepted — the engine never passes `self`, and requiring an annotation on it would be a new rule rather than this one.
7. **Given** the four decorators with a correct parameter typing but a return that is not the contract's (`-> Any` on a summary, `-> str` on a regular aspect, `-> dict` on a compensator), **When** the capability is assembled, **Then** each is refused, naming its own return contract.

---

### User Story 3 - Two summaries are reported as two summaries (Priority: P2)

A developer declares two `@summary_aspect` methods, perhaps after renaming one while keeping the old one. Today assembly dies with `InvalidGraphError: Edge '@summary_aspect' from 'TwoSummariesAction' references missing target_node_id 'TwoSummariesAction:second_summary'` — which names a missing node and leaves the developer looking for a node they never wrote. The invariant the framework documents is "exactly one", and it is currently enforced by accident.

**Why this priority**: it is the cheapest part of the issue and the one a user meets most often, since a renamed method is a natural mistake; the refusal itself exists, it just does not say what went wrong.

**Independent Test**: declare two summary aspects on one operation, assemble it, and read the refusal; it must name both methods and say that an operation answers once.

**Acceptance Scenarios**:

1. **Given** an operation with two `@summary_aspect` methods, **When** the capability is assembled, **Then** the refusal names both methods and states that an operation has exactly one exit point.
2. **Given** an operation with one summary, **When** it is assembled, **Then** nothing about the refusal above appears in the run.
3. **Given** an operation with no summary at all, **When** it is assembled, **Then** the existing missing-summary refusal is unchanged — "no summary" and "two summaries" remain two different answers.

---

### User Story 4 - A summary's answer is the operation's Result (Priority: P3)

A developer annotates a summary `-> Any`, or returns an instance of a result type that is not the operation's, and the run hands it back as the operation's result — measured, not assumed: an operation declaring `ResultStub` whose summary returns `{"not": "a result"}` answers with a `dict`, and no layer objects. The cached path refuses exactly this with a typed error; the handler path names an `ActionResultTypeError` that nothing raises. The documented invariant — "exactly one `@summary_aspect`, and it must return a typed `Result`" — holds by convention alone.

**Why this priority**: it is the only part that touches the run-time path rather than the shape of a declaration, and the only part where the answer can be wrong in a way no static check can see. The declaration checks must not wait for it, but the invariant cannot be left as a convention either.

**Independent Test**: declare a summary annotated `-> Any` and confirm the operation refuses to assemble; then annotate it with its own `Result` and return a mapping, and confirm the run refuses the answer; then return its own `Result` and confirm the answer is unchanged.

**Acceptance Scenarios**:

1. **Given** an operation whose summary is annotated `-> Any`, or with another operation's `Result`, **When** the capability is assembled, **Then** the declaration is refused before any call is served, and the message names the operation, the declared `Result` and the annotation that was written.
2. **Given** an operation whose summary is annotated with its own `Result` but returns an instance of another operation's `Result`, **When** the operation runs, **Then** the answer is refused, naming the operation, the declared `Result` and what actually came back.
3. **Given** an operation whose summary is annotated with its own `Result` but returns something that is not a `Result` at all — a mapping, a string, `None` — **When** the operation runs, **Then** the answer is refused the same way.
4. **Given** an operation whose summary returns its own `Result`, **When** the operation runs, **Then** nothing changes: the same answer, the same logging, the same events.
5. **Given** a refusal above, **When** it is compared with the refusal a cached result gets, **Then** the two read as one family of "a step handed back the wrong answer" rather than two unrelated failures; the error handler's path, which mentions `ActionResultTypeError` without ever raising it, is out of this change and is not claimed to refuse anything.

---

### User Story 5 - The repository's own corpus complies (Priority: P3)

A developer copies an example, or reads a page, and gets a declaration the framework accepts. That is true today and stops being true the moment the checks land: 499 declarations in this repository do not meet the new contract — 243 in `.py` (163 under `examples/`, 80 under `packages/`), 158 in the example notebooks, 98 in the pages under `docs/` — and most of them are unannotated rather than misnamed. Nineteen of the 499 are wrong on purpose: they sit inside `pytest.raises` blocks and are the tests that prove the refusals fire, so they stay wrong and only their expected messages move.

**Why this priority**: it is a consequence of the change, not a feature, but it is not optional. The framework's examples are the documentation, and documentation the framework's own rules would refuse is worse than no documentation. It comes last because it can only be done once the rules are settled.

**Independent Test**: after the migration of `packages/`, `examples/` and the notebooks, re-run the corpus scan and execute every example; a single non-conforming site or a refusal at import time means a declaration was missed. The 98 documentation snippets are migrated in the same change but in its last step, after the check run, so they are verified there rather than here.

**Acceptance Scenarios**:

1. **Given** the migrated corpus, **When** every example is executed, **Then** none of them refuses a declaration.
2. **Given** the migrated corpus, **When** a reader compares an example before and after, **Then** the same operation does the same thing — only the names and the annotations of its aspect methods moved.
3. **Given** a declaration in the corpus that is wrong on purpose (a negative case demonstrating a refusal), **When** it is compared with one that is wrong by accident, **Then** the deliberate one still demonstrates the refusal it names, with its message updated if the message changed.

---

### Edge Cases

- **Decorator order with `@context_requires`.** The trailing `ctx` and the declaration that asks for it are two halves of one thing; the order decides which half the other sees. The refusal must explain the order, not merely restate the count.
- **A method that is both renamed and reordered.** One refusal, naming the first thing to fix, not two stacked errors.
- **`*args`, `**kwargs`, keyword-only parameters, and parameters with defaults.** The engine passes by position and fills nothing else, so a default on a parameter the engine always supplies is dead weight and is refused with the others.
- **A parameter annotated `Optional[...]`, `dict`, `Any`, or a string that never resolves.** Refused at the moment the type would be checked, with what was declared and what is handed over.
- **Inheritance.** An aspect is declared per operation and never inherited; a subclass that inherits a compliant method must not be refused for it, and a subclass that redeclares one must be checked on its own declaration.
- **`@compensate`'s target.** A compensator named for an aspect that does not exist is a different refusal, already made today; the signature check must come before or after it, never instead of it.
- **An operation with two summaries where one is inherited from a mixin.** Still two declarations; the refusal names both.
- **A refusal that happens at assembly must leave no half-built capability behind.** The next assembly of the same class — a second machine, a test fixture — must produce the same refusal, not a silently degraded graph.

## Requirements *(mandatory)*

### Declaration shape

- **FR-001**: The four declaration decorators — summary, regular, on-error and compensate — MUST refuse a method whose parameters are renamed or reordered, at the moment the method is declared, and the refusal MUST name the method, the order the engine uses and the order that was written.
- **FR-002**: The refusal MUST state why the order is fixed — the engine calls the method and binds by position — so that a reader can tell this apart from a style rule.
- **FR-003**: The parameter count check that exists today MUST remain, and MUST agree with the name check rather than duplicate it: one refusal per mistake, phrased once.
- **FR-004**: The trailing `ctx` MUST be expected exactly when the declaration asks for context, and a mismatch in either direction MUST be refused with a message naming the correct decorator order.
- **FR-005**: A signature the engine cannot call positionally — keyword-only parameters, `*args`, `**kwargs` — MUST be refused as a signature, not merely as a wrong count.
- **FR-006**: Every parameter except `self` MUST carry an annotation, and so MUST the return; a missing one MUST be refused at declaration. `self` stays exempt.
- **FR-007**: The types those annotations resolve to MUST be checked when the capability is assembled, before any call is served — the parameters (the operation's `Params`, the state, the tool box, `dict[str, BaseResource]` for the connections, the context view for an asked-for `ctx`, `Exception` for an error, `BaseState | None` for a compensator's `state_after`) and the return (the operation's `Result` for a summary and an on-error handler, `dict[str, Any]` for a regular aspect, `None` for a compensator).
- **FR-008**: An annotation that cannot be resolved at assembly MUST be refused with the reason — an unimportable forward reference is a contract that cannot be read, not a declaration that passes.

### The single summary

- **FR-009**: An operation declaring two summary aspects MUST be refused at assembly with a refusal that names both methods and says the operation has exactly one exit point. It MUST NOT surface as a missing graph node.
- **FR-010**: An operation with no summary MUST keep the refusal it has today, and that refusal MUST remain distinguishable from the duplicate one.
- **FR-011**: A summary's answer MUST be the operation's declared `Result` at both moments: a return annotation naming anything else — including `Any` and another operation's `Result` — MUST be refused when the capability is assembled, and an instance of anything else returned by the method MUST be refused after it returns.
- **FR-012**: Both refusals MUST name the operation, the declared `Result` and, at run time, what actually came back; and both MUST read as one family with the refusal a cached result already gets, in the shape of the message and the kind of error.

### The repository's own declarations

- **FR-013**: Every declaration in `examples/`, under `packages/` and in the pages under `docs/` MUST meet the contract this change introduces, except the declarations that exist to demonstrate a refusal. The 480 sites that do not meet it today and are not such demonstrations are migrated inside this change, not after it.
- **FR-014**: A migrated declaration MUST keep its behaviour: the operation, its descriptions, its suffixes and what it does to the state are unchanged; only the names and the annotations of its aspect methods move.
- **FR-015**: The declarations that exist in the corpus to demonstrate a refusal MUST keep demonstrating it, with their expected messages updated where the message changed.
- **FR-016**: The documentation that states these invariants MUST be updated in the same change, so that no page describes a rule the framework does not keep.

### Invariance

- **FR-017**: An operation whose declarations already comply MUST behave identically: the same answer, the same order of steps, the same events, the same logs, and the same assembly result.
- **FR-018**: Nothing about the description requirement, the `async` requirement, the name suffixes, the context contract or the pipeline order may change as a side effect.

### The refusals themselves

- **FR-019**: Each of the three rules this feature introduces MUST be identified by a named error of its own, exported in the public exception namespace and documented beside the existing ones: the signature contract (names, order, annotations and the types they resolve to), the duplicate summary, and the summary's answer. Two of the three are new names; the answer's rule raises `ActionResultTypeError`, which already names it, is already public, and is raised nowhere today. Existing declaration errors that name a different rule keep their names.
- **FR-020**: The signature rule MUST raise the same error at both of its moments, and the message MUST say which moment it was — refused while the method was declared, or refused while the capability was assembled — because a reader facing the second needs to know that the class body was already executed.
- **FR-021**: Each new error MUST remain catchable by the exception type its family already uses, so that a caller whose handler relies on catching the family does not start missing these refusals.
- **FR-022**: A refusal for a rule not covered by this feature MUST NOT be renamed or re-typed: a wrong description, a synchronous method, a wrong name suffix and a missing summary keep the refusals they have today.

### Key Entities

- **Declaration**: a method an operation marks with one of the four decorators, together with its description, its name and its signature. It is the unit this feature judges, and its signature is the contract.
- **Operation**: the class that owns declarations. It has exactly one exit point, and its `Params` and `Result` are the two types every declaration is checked against.
- **Refusal**: the answer to a declaration that does not meet the contract. It names the rule, the declaration and the correction, and it is the feature's only user-visible output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A declaration that renames, reorders, leaves something untyped or mistypes a parameter is refused before any call is served, in all four decorators, in 100 % of the cases listed as acceptance scenarios.
- **SC-002**: Each refusal names the method, the expected signature and the correction; a reader who has never seen the rule can fix the declaration from the message alone.
- **SC-003**: Zero declarations in `examples/`, under `packages/` and in `docs/` are refused by the new rules *except* the ones that exist to demonstrate a refusal: the count of non-conforming sites falls from 499 to the 19 deliberate ones, each named with the test that asserts its refusal, and the closing check run is green.
- **SC-004**: Every example runs and prints what it printed before, apart from the renamed and annotated declarations themselves.
- **SC-005**: An operation that assembled and ran before this change assembles and runs with the same answer, the same events and the same logs after it, unless its declarations were among the non-conforming ones.
- **SC-006**: Two summaries produce a refusal that names both methods, and the phrase naming a missing target node appears nowhere in it.
- **SC-007**: A summary that returns something other than its operation's `Result` is refused in the same shape as a cached result's wrong answer, and the two messages read as one family — while the error handler's path is left exactly as unchecked as it is today, and no claim is made that it refuses anything.

## Assumptions

- The four decorators' parameter orders are the ones the engine uses today, verified in the code rather than taken from the issue: summary and regular `(self, params, state, box, connections)`, on-error the same plus `error`, compensate `(self, params, state_before, state_after, box, connections, error)`; `ctx` is appended last in every case.
- The object check's two moments are the right model for the aspects: that implementation is the reference, and no new moment is invented.
- The corpus migration is mechanical but large: 480 sites, measured across the four decorators and the three carriers of declarations — 224 in `.py`, 158 in notebook cells, 98 in documentation snippets — plus 19 declarations that are wrong on purpose and stay wrong. The figures first written here (523 non-conforming, 211 in `.py`) came from a scan that judged only two of the four decorators and compared every declaration against the summary's name list; the measurement in `evidence/corpus-baseline.md` supersedes them, and the plan's research records the correction. A migration done by hand at that size will contain mistakes, so the closing check run — plus a run of every example — is the gate rather than a spot check.
- Declarations in the corpus that are wrong on purpose are expected to keep failing for the reason they demonstrate, and their demonstration is updated rather than deleted.
- Two new public errors appear — the signature's and the duplicate summary's — with the answer's rule reviving `ActionResultTypeError` rather than duplicating it; no other public vocabulary changes: no new decorator option, no new parameter, no renamed existing error.
- No documentation page is written in this feature — only the pages that state the invariants this change makes true are updated, per the repository's rule that documentation ships with the change it describes.
