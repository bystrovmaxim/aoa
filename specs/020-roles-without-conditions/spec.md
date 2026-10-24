# Feature Specification: Roles Without Conditions

**Feature Branch**: `feature/issue-248-check-roles-without-grant-guard`

**Created**: 2026-10-24

**Status**: Draft — clarification complete; ready for planning; implementation not started

**Input**: Maintainer instruction to run `/speckit-specify` for [issue #248](https://github.com/bystrovmaxim/aoa/issues/248): remove `grant`/`guard` from `@check_roles`, keep roles in `@check_roles`, move conditional authorization into `@access_decide`.

## Clarifications

### Session 2026-10-24

- Q: The demo package carries three actions that use the words being removed (`cancel_order`, `when_refusal_shape_action`, `guard_refusal_shape_action`) and it is part of the closing check run. What happens to them? → A: Rewrite all three on `@access_decide`. `cancel_order` shows the object rule in `@access_decide`; the two shape actions become the refusal shapes an object rule produces; their test modules are rewritten with them. The demo keeps teaching the same refusal shapes, with fewer words.
- Q: Four example pages exist to teach the removed mechanism (`02_grant`, `03_guard`, `17_grant_fallback`, `22_reason_required`), and two more teach the five words (`07_three_answers`, `13_cascade`). What happens to them? → A: Rewrite them in place and keep their numbers. The same pages and notebooks remain — numbers 01 to 23, with 17 still carrying two pages — teaching the new content: a condition on one role becomes a branch of one object rule, "another grant after a refusal" becomes the branch order inside that rule, the shared condition becomes the object rule itself, and a missing refusal reason becomes a `Refused("REASON")` branch. Page numbers do not move. The four suffixes that name the removed mechanism do move, because a page called `17_grant_fallback` that teaches branch order keeps the removed word in the tree; the tutorial links are rewritten in the same phase, so nothing is left pointing at a name that no longer exists.
- Q: How are `grant`, `Grant`, `guard=`, `guard_reason=`, `Gate.WHEN` and `Gate.GUARD` taken away? → A: Full removal, with a migration message where a declaration can still be written. The names disappear (importing them fails as an absent symbol); `@check_roles` refuses the `guard=`/`guard_reason=` keywords at class definition with a message that names `@access_decide` and shows the replacement, so a migrating author is told where the condition goes instead of reading a bare `TypeError`.
- Q: A condition could inspect the caller's roles — "a sales manager, and only for the eu region". `@check_roles` cannot express the whole fact and the specification forbids role matching inside `@access_decide`. Where does such a condition go? → A: Anywhere the object rule needs it. The ban is not "the object rule may not see roles": it is "the object rule must not repeat the role check that `@check_roles` already performs". An object rule may declare `user.roles` with `@context_requires` and reason about the caller's roles for the part the declaration cannot express; what it must not do is re-match the declared role, filter by role mode, or introduce a role helper that turns the role layer into two.
- Q: `@check_roles(GuestRole, CustomerRole)` is accepted today but lets nobody through, because a sentinel never appears among a caller's roles. What should a sentinel declared beside ordinary roles mean? → A: The same thing it means alone. A declaration is an OR over its alternatives, and every element of it is an alternative: `GuestRole` among roles makes the whole declaration open, `AnyRole` among roles requires the caller to hold at least one role that is not silenced. The declaration is not an error; it says what it appears to say.

### Decisions taken without a question

These follow from the issue text and are recorded here so planning does not re-open them.

- **No new graph marker.** Maxitor already models `AccessDecide` as its own node type with its own table and edges, so the presence of that node is the graph's statement that an object rule exists. No `authorization="access_decide"` property is added to the action node.
- **The words disappear from the vocabulary, not just from emission.** `Gate` publishes three words after this change. Deprecated members that are never emitted are explicitly rejected: a stored answer naming `WHEN` or `GUARD` is refused as an unknown gate rather than silently accepted.
- **The refusal moves inside the run.** A former `guard=` answered before the run existed; an object rule answers after connection validation. The refusal stays a refusal — it is still not a failure — but it is now an answer about a run that has started. This is documented as part of the change rather than hidden.
- **A role named twice is one role.** Without per-role conditions, two identical edges carry no information; the declaration stays valid and the graph carries one edge per distinct role.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare who may call, and nothing else (Priority: P1)

An action author writes the role requirement of an operation as one declaration: a role, a tuple of alternative roles, `GuestRole` or `AnyRole`. The declaration cannot carry a condition, so an author reading it learns exactly one thing — who may enter the gate.

**Why this priority**: This is the decision the issue records. A role layer that also evaluates conditions is two mechanisms under one name, and the condition half is the one that keeps growing.

**Independent Test**: Declare an action for each accepted form, build the machine and read the graph. Then attempt every removed form — `grant(role)`, `guard=`, `guard_reason=`, a leftover condition object, an empty declaration — and confirm each is refused where it is written, with a message that names the replacement wherever a declaration can still be written.

**Acceptance Scenarios**:

1. **Given** `@check_roles(CustomerRole)`, `@check_roles((CustomerRole, AdminRole))`, `@check_roles(GuestRole)` and `@check_roles(AnyRole)`, **When** the machine is built, **Then** each declaration is accepted and the role graph carries one `Action → Role` edge per distinct declared role.
2. **Given** `@check_roles(grant(CustomerRole))` in a module, **When** the module is imported, **Then** the import fails because `grant` is not a name the framework publishes, and the migration is stated in the documentation rather than in a stack trace.
3. **Given** `@check_roles(CustomerRole, guard=..., guard_reason=...)`, **When** the class is defined, **Then** the declaration is refused with a message naming `@access_decide` and showing what the condition becomes.
4. **Given** a role named twice in one declaration, **When** the graph is built, **Then** one edge is produced and no duplicate-node or duplicate-edge failure occurs.
5. **Given** `@check_roles(GuestRole, CustomerRole)`, **When** a caller with no roles and a caller holding `CustomerRole` are both decided, **Then** both are allowed — the open alternative satisfies the choice — and the same declaration with `AnyRole` instead of `GuestRole` requires at least one role that is not silenced.
6. **Given** an action with no `@check_roles` at all, **When** the machine runs it, **Then** the existing mandatory-role refusal still fires.

### User Story 2 - Put the object rule where the object is (Priority: P1)

An author whose access rule depends on the order, the caller, or configuration writes it as one async `@access_decide` method that answers `Allowed`, `Refused("REASON")` or `Undecided`, declares the user or request fields it reads with `@context_requires`, and gets a typed verdict instead of a boolean.

**Why this priority**: The conditions being removed were already too narrow: they received a user and maybe the parameters, returned a bare `bool`, and had nowhere to declare what they read. `@access_decide` already has the shape real rules need.

**Independent Test**: Migrate the `cancel_order` example — a locked order and another customer's order — into one `@access_decide` method, and confirm both refusals arrive with `Gate.ACCESS_DECIDE`, the framework's `FORBIDDEN_OBJECT` where the object rule says so, and the developer's own reason where the author declared one.

**Acceptance Scenarios**:

1. **Given** a locked order, **When** the call is decided, **Then** the answer is `Refused("ORDER_LOCKED")` with gate `ACCESS_DECIDE`.
2. **Given** an order owned by another caller, **When** the call is decided, **Then** the answer is the shared `FORBIDDEN_OBJECT` refusal with gate `ACCESS_DECIDE`.
3. **Given** an author calling `machine.check_access_decide(...)` before running, **When** the object rule refuses, **Then** the same answer comes back as from `machine.run`.
4. **Given** an object rule that declares `@context_requires("user.user_id")`, **When** the graph is built, **Then** the `AccessDecide` node carries its required-context companions and Maxitor can list them.
5. **Given** an object rule that returns a plain `bool`, `None` or a string, **When** the call is decided, **Then** the answer is `Undecided` naming `ACCESS_DECIDE` with the mistake kept as its cause — never `Allowed`.
6. **Given** an object rule that repeats the role check the declaration already performs — matching the declared role with `issubclass`, filtering by role mode, or going through a role helper — **When** the change is reviewed and searched, **Then** the duplication is found and removed: the declaration keeps the gate, and the object rule keeps only what the declaration cannot express.

### User Story 3 - Read one vocabulary of answers, three words long (Priority: P1)

A transport author, a plugin and a reader of stored decisions branch on the word that refused. After the change there are three: who is calling, the roles they hold, the object they touch. A fourth condition word never arrives, and a stored answer that claims one is refused rather than trusted.

**Why this priority**: The words are published contract. Leaving two of them in the enum — never emitted, still valid — keeps every consumer branching on states the framework can no longer produce.

**Independent Test**: Ask a decision for each of the three words and read the event; then rebuild an answer from stored data that names `WHEN` or `GUARD` and confirm the rebuild is refused.

**Acceptance Scenarios**:

1. **Given** any operation in the repository, **When** a decision is produced on any path, **Then** the word is one of `AUTH_COORDINATOR`, `CHECK_ROLES`, `ACCESS_DECIDE`.
2. **Given** stored decision data naming `WHEN` or `GUARD`, **When** it is rebuilt as an answer, **Then** validation fails as an unknown gate.
3. **Given** the ordered steps of a decision, **When** the order is read, **Then** the pre-run phase is two steps — who is calling, which roles are held — and the in-run phase is the object rule, and nothing was renumbered to hide the removal.
4. **Given** a decision where the roles step cannot read its declaration, **When** the answer is produced, **Then** it is `Undecided` naming `CHECK_ROLES` — there is no second word left for a condition that failed.

### User Story 4 - See in the graph what the operation decides (Priority: P2)

A reader of the interchange graph and of Maxitor sees who may enter an operation — the role edges — and, when the operation has one, a separate node standing for the object rule and the context fields that rule reads. Nothing on the graph claims to hold a condition any more.

**Why this priority**: A graph that carries runtime callables it never exports tells a reader two different stories. Today the role edge and the action node hold conditions that never leave the process.

**Independent Test**: Build an action with a role and an object rule, export the graph, and read it in Maxitor. Repeat with an action that has a role and no object rule.

**Acceptance Scenarios**:

1. **Given** an action with `@check_roles` and `@access_decide`, **When** the graph is exported, **Then** the role edge carries the role and its mode, the `AccessDecide` node carries its description and required-context companions, and no condition data appears on either.
2. **Given** an action with roles only, **When** the graph is exported, **Then** it carries no `AccessDecide` node, and the absence is the statement that the object rule does not exist.
3. **Given** an action whose role is `RoleMode.SILENCED`, **When** the graph is read, **Then** the mode is present and the runtime still refuses the caller.

### User Story 5 - Migrate a repository, not a strawman (Priority: P2)

The repository's own declarations move: the demo's three actions and two test modules, the action-machine's condition, gate and graph tests, the six authorization pages and notebooks, the tutorial, the reference and the changelog. Every migrated page executes, and the pages that taught `grant`/`guard` teach the object rule in the same place and under the same number.

**Why this priority**: A removal that leaves the teaching material describing the removed mechanism is not a removal; and the closing check run covers the demo package, so a half-migrated repository cannot be green.

**Independent Test**: Run the closing check run; execute every rewritten script and notebook and compare recorded output; take each documented before/after pair and confirm the old form fails while the new one passes.

**Acceptance Scenarios**:

1. **Given** the migrated `cancel_order` demo action, **When** a locked order and a foreign order are decided, **Then** the refusals come back with gate `ACCESS_DECIDE` and the reasons the action declares.
2. **Given** the rewrite of `02_grant`/`03_guard`/`17_grant_fallback`/`22_reason_required` under their existing numbers, **When** each script and notebook is executed, **Then** it completes and prints what the page records.
3. **Given** the tutorial's ABAC sections, **When** they are read after the rewrite, **Then** they teach the object rule and never the removed declarations, and every link they carry resolves.
4. **Given** the reference that states five words are published, **When** it is read after the change, **Then** it states three and names what replaced the condition words.
5. **Given** the changelog, **When** it is read by someone who did not follow the work, **Then** one article says what they can now do and the nuances that changed for them.

### Edge Cases

- `@check_roles()` with no argument, an empty tuple or list, a string role name, a non-role object, a leftover condition object passed positionally — refused where it is written, as today, with the migration added to the message.
- A declaration that names the same role twice is accepted as one role, not as an error.
- `GuestRole` and `AnyRole` keep their meanings — open, and "at least one role that is not silenced" — whether declared alone or as one alternative among ordinary roles. A declaration is a choice between its alternatives, so the weakest alternative decides: an open alternative makes the whole declaration open.
- An operation with `@check_roles(GuestRole)` and no object rule is valid and open, and adding an object rule to the same operation makes the object gate answer.
- An author who relied on a condition refusing *before* the run now gets the refusal inside the run: connection validation happens first, and the run's start and refusal are published. A rule that must prevent any side effect cannot be expressed by an object rule and does not get a new pre-run hook in this change.
- A condition that read only the parameters becomes a branch; one that read the user becomes a branch reading a declared context key; one with a reason becomes `Refused("THAT_REASON")`; several grants for the same role collapse into the branches of that one method, in the order they were declared.
- A condition that chose between roles — "a sales manager, and only for the eu region" — becomes a branch that declares `user.roles` and reasons about the part `@check_roles` cannot say. It does not re-check the declared role: that is the duplication the rule forbids.
- `RoleMode.UNUSED` is still refused at declaration and `DEPRECATED` still warns; `SILENCED` still grants nothing; an `AnyRole` operation whose caller holds only silenced roles is still refused.
- Inherited `@check_roles` keeps its current behaviour; an object rule is still never inherited.
- A failing object rule — an exception, a wrong return type — is `Undecided`, never `Allowed`, and is never read as a refusal.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `@check_roles` MUST accept one or more role arguments — each a `BaseRole` subclass, a sentinel included — and, as the only argument, a non-empty tuple or list of `BaseRole` subclasses. Several positional roles and a tuple of roles MUST mean the same thing, because both forms are in use today. It MUST NOT accept a condition, a grant, a string, an empty collection, or an object that is not a role.
- **FR-002**: `grant`, the `Grant` type, the `guard=` and `guard_reason=` keywords, `Gate.WHEN` and `Gate.GUARD` MUST be absent from the public surface, from the graph and from the wire form. An import of `grant` or `Grant` MUST fail as an absent symbol; a declaration that still passes `guard=`/`guard_reason=` or a condition-bearing object MUST fail at class definition with a message that names `@access_decide` and states the replacement shape. No deprecated member, no warning-only window and no silently ignored keyword MAY remain.
- **FR-003**: The role step MUST answer `CHECK_ROLES` or nothing at all. It MUST NOT evaluate any condition, MUST NOT produce the removed words, and MUST keep today's matching rule — `issubclass` over the caller's role types, silenced roles ignored, `AnyRole` requiring at least one active role, `GuestRole` restricting nothing.
- **FR-004**: `Gate` MUST publish exactly `AUTH_COORDINATOR`, `CHECK_ROLES` and `ACCESS_DECIDE`. An answer rebuilt from stored data that names a removed word MUST be refused as an unknown gate, and no path MAY coerce such data into a valid answer.
- **FR-005**: The decision's ordered steps MUST become two before the run — who is calling, which roles are held — and one inside it, the object rule. `WHEN` and `GUARD` MUST NOT appear as steps, as words, as map keys, or as documentation of the order; the seam between the two phases MUST stay where it is. Every place that states a count — "four steps", "five words" — in a module header, a test, the tutorial, the reference or an example MUST state the new one.
- **FR-006**: The shared-condition step and the role-condition branch MUST be removed, including the resolver entry points that read them, so that no code path can reach a condition that is no longer declared. Code that loses its last user MUST be removed with it, and the repository's dead-code check MUST stay clean.
- **FR-007**: Conditional authorization MUST be expressible in full through `@access_decide`: one async method per operation, named with the `_access_decide` suffix, returning `Allowed`, `Refused` with an optional reason, or `Undecided`; reachable with `@context_requires` and a restricted context view; never inherited; at most one per operation. Every refusal it produces MUST carry `ACCESS_DECIDE`.
- **FR-008**: `@access_decide` MUST NOT repeat the role check that `@check_roles` already performs: it MUST NOT re-match the declared role, MUST NOT filter by role mode, and no new public role helper MAY be introduced. It MAY declare `user.roles` with `@context_requires` and reason about the caller's roles for whatever the single declaration cannot express — the ban protects the role layer from a second copy of itself, not the object rule from knowing who is calling. This MUST be verifiable by search over the migrated declarations and by review.
- **FR-009**: `@access_decide` MUST remain optional. An operation with `@check_roles(GuestRole)` and no object rule MUST build and be open; adding an object rule to that operation MUST make the object gate answer on the run path and on the ask-in-advance path alike.
- **FR-010**: The graph MUST carry one `Action → Role` edge per distinct declared role, with the role's mode and no condition data on the edge or on the action node. Declaring the same role twice MUST yield one edge and no duplicate failure. No new graph property MAY be introduced to say where authorization lives: the `AccessDecide` node, when present, is that statement.
- **FR-011**: The `AccessDecide` node MUST keep its description and its required-context companions, so a graph reader can list which user or request fields an operation's decision reads.
- **FR-012**: Role behaviour that is not a condition MUST be preserved exactly: bare roles, tuples, `GuestRole`, `AnyRole`, `RoleMode.ALIVE`/`DEPRECATED`/`SILENCED`/`UNUSED` handling, the mandatory-declaration refusal, and inherited `@check_roles` — with the single deliberate exception of FR-013, where a sentinel declared among ordinary roles stops being an unsatisfiable alternative.
- **FR-013**: A sentinel declared as one alternative among ordinary roles MUST mean what it means alone: a declaration containing `GuestRole` is open, and a declaration containing `AnyRole` requires at least one role that is not silenced. A sentinel MUST NOT be an alternative that can never be satisfied, and mixing it with ordinary roles MUST NOT be an error.
- **FR-014**: Every declaration of the removed mechanism in the repository MUST be migrated: the demo package and its tests, the action-machine tests, the examples and their notebooks. Every migrated page MUST keep its number and its file name, and MUST execute with the repository's own environment.
- **FR-015**: The documentation MUST be rewritten for the new mechanism: the tutorial's condition sections, the reference that states the words and the invariants, the glossary, and any page that named the removed declarations. Every case the change introduces — each accepted declaration, each refusal, each migration before/after, each mode — MUST appear as a named case; each case MUST appear twice, as a script and as a notebook; and a Russian draft page MUST sit beside each documentation page written in this change, outside the commit.
- **FR-016**: The migration MUST be stated for an author, not for a diff: `@check_roles(grant(Role))` becomes `@check_roles(Role)`; a tuple of grants becomes a tuple of roles; `guard=` and `when=` become branches of one `@access_decide`; a condition with a reason becomes `Refused("REASON")`; a condition that read the user becomes a branch reading a declared context key; a condition that chose between roles becomes a branch reading `user.roles`, with the declared role left to `@check_roles`.
- **FR-017**: The change MUST state, where an author will look, that a migrated condition now refuses inside the run rather than before it, and what that means for an operation whose side effects must not start first. No pre-run hook MAY be reintroduced to preserve the old timing.
- **FR-018**: Verification MUST include adversarial checks, each paired with a valid neighbouring control: a leftover `grant(...)` or `guard=` declaration; an operation with its `@check_roles` removed; a silenced role still refused by the role gate; a `GuestRole` operation open without an object rule and refusing with it; an object rule that reads a module-level value. The last of these belongs to the code-isolation check of issue #247, which is not in the tree yet: until it lands, the same mutation is verified by review and a recorded search over the migrated declarations, and the feature MUST state which of the two verifications produced the result rather than claiming a check that does not exist.
- **FR-019**: Planning MUST reserve exactly three closing tasks in this order and no other task may absorb them: the scoped check run taken to zero, the documentation with its examples, and the changelog as one article.
- **FR-020**: The scope of this feature MUST exclude replacing the declared role gate with a check inside `@access_decide`, adding a role helper, removing `@check_roles`, reworking role-mode semantics, introducing a new authorization declaration beyond `@access_decide`, and runtime sandboxing.

### Key Entities

- **Role declaration**: The single fact `@check_roles` carries — one role, or a choice between alternatives any of which may be a role or a sentinel — read by the role step and by the graph.
- **Object rule**: The optional `@access_decide` method of an operation: its description, the context keys it declares, the order of its branches, and the verdict each branch returns.
- **Verdict**: `Allowed`, `Refused` with a gate and an optional reason, or `Undecided` with a gate and a private cause. The gate is one of the three published words.
- **Published word**: `AUTH_COORDINATOR`, `CHECK_ROLES`, `ACCESS_DECIDE` — the value a consumer branches on, and the whole vocabulary after this change.
- **Decision order**: Two pre-run steps and one in-run step, with the seam between them unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search of the source, tests, examples and documentation finds zero occurrences of `grant(`, `Grant`, `guard=`, `guard_reason=`, `Gate.WHEN`, `Gate.GUARD`, and of the words `WHEN`/`GUARD` as gate values. The only pages allowed to name them are the migration material — the tutorial's migration section and `docs/CHANGELOG.md` — where each appears once as the removed form, and the search result is recorded rather than asserted.
- **SC-002**: Every accepted declaration form has a passing case and every refused form has a failing case with a message naming the replacement; the count of refused forms matches the number the spec enumerates.
- **SC-003**: Every role test that existed before this change keeps its outcome, with two named exceptions: the tests whose subject is the removed words, replaced by tests of the object rule and of the migration message, and any test that pinned a sentinel declared among ordinary roles as unsatisfiable, replaced by the open and at-least-one-role outcomes of FR-013.
- **SC-004**: No decision produced anywhere in the repository or its examples carries a gate outside the three published words; a stored answer naming a removed word is refused in every case tried.
- **SC-005**: Each of the three demo actions, the six rewritten pages and their notebooks executes and prints the output the page records; the tutorial, reference and glossary contain no instruction that names a removed declaration.
- **SC-006**: Each required adversarial mutation is caught by its targeted check while its valid neighbouring control passes; and a search of the migrated declarations finds no object rule that repeats the role check its own declaration already performs.
- **SC-007**: `bash scripts/run_checks_with_log.sh` is green, with only the two accepted remarks the constitution names, and it covers the demo package among the others.
- **SC-008**: An author who follows only the migration section can convert each of the four shapes — bare grant, conditioned grant, shared guard, reason-bearing condition — without reading the implementation.

## Assumptions

- Issue #248 is the feature source and its decision section governs: `@check_roles` stays the only role layer, and the conditional half moves to `@access_decide`. It supersedes the `when`/`guard` part of issue #247; #247 continues to apply to action methods and to `@access_decide` itself, but its code-isolation check is **not implemented yet** (a search of `graph/validators/` finds only the entity validators), so FR-018 treats that one adversarial mutation as a recorded review until #247 lands.
- Public declaration syntax, the graph's role edges and the published gate words are product contracts in this specification, so they are named explicitly despite the generic template's preference for omitting implementation detail. No module layout, no algorithm and no internal naming is prescribed.
- The maintainer answers recorded in Clarifications govern scope: the demo is rewritten, the examples are rewritten in place under their existing numbers, removal is full with a migration message where a declaration can still be written, the object rule may reason about roles it declares but must not repeat the declared gate, and a sentinel declared among ordinary roles keeps its own meaning.
- One deliberate change to role behaviour is accepted: a sentinel written beside ordinary roles stops being an alternative that can never be satisfied. No other role outcome changes, and no declaration that works today stops working.
- The timing change is accepted as part of the decision to move conditions: a refusal that used to precede the run now answers inside it, and this is documented rather than preserved by a new hook.
- The closing check run's two known remarks — the Vite chunk-size advisory and LangGraph's pending-deprecation warning — remain accepted and are not acted on.
- This phase writes the specification and its quality checklist only. It does not claim implementation, executed examples or a passing check run.
- The constitution, the maintainer's existing changes and the staging area remain untouched. Commits, pushes, pull requests and merges require a separate explicit instruction.
