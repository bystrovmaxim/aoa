# Feature Specification: Lifecycle states as objects, read by the chain, the graph and the diagrams

**Feature Branch**: `feature/issue-209-state-vocabularies`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/209 — A lifecycle state is declared as two string literals, `.state("payment_pending", "Payment pending")`, and has no object behind it: its label never reaches the interchange graph, and there is nowhere to put anything a status knows about itself. After this change a status is an object with a code, a human label and arbitrary domain fields; the statuses of an axis are class attributes of the axis class, which also carries the links and the classification; the graph and the Maxitor diagrams are built from the objects, all the way to the labels, the order and the colours. The demo migrates completely and the string form disappears."

## Context: what the graph says about a state today, measured on 2026-10-19

The lifecycle template holds a `dict` of state keys to metadata, and the graph rebuilds each state row from the key:

- **The label never leaves the template.** `StateInfo` carries `display_name`, and the chain is declared with `.state("payment_pending", "Payment pending")`, but the graph state node's `label` is the key. Measured on the current code: a state node is `{"type": "StateIntermediate", "label": "payment_pending", "properties": {"lifecycle_class_id": ..., "state_key": "payment_pending"}}`.
- **The diagram therefore shows keys.** The FSM payload's `display_name` is read from the node label, so the wire answer says `{"key": "payment_pending", "display_name": "payment_pending", ...}` — a human label was declared one layer above and never arrived.
- **The order is alphabetical.** The FSM orders states "initial first, then by key", so a chain that thinks in `new → payment_pending → confirmed → …` is drawn `cancelled, confirmed, delivered, new, …`.
- **A status has no room for anything of its own.** There is no object, no type and no place for an order, a colour or any domain attribute: the pair of strings is the whole declaration.
- **The corpus.** 32 lifecycle declarations in 23 files under `packages/aoa-demo/src`: 28 named chains in 19 `*_lifecycle.py` files and 4 private cycle-sketch classes in the `*_stub.py` / `*_cycle_*.py` fixtures. 90 `.state(...)` calls and 65 `.to(...)` calls, measured by scanning `packages/aoa-demo/src`. Further call sites live in `packages/aoa-action-machine/tests`, `examples/` (including `examples/step_26_maxitor/`), the docstrings of the framework modules, and the rationale page `docs/explanation/architectural-constitution.md`; the string form is removed, so they move in the same change.

## Clarifications

### Session 2026-10-19 — decisions carried from the issue

- The status describes the status; the chain describes the links. Classification and transitions stay in the chain, and a status carries no `initial`/`final` flag. One and the same status may therefore be final in one chain and intermediate in another, which is lawful: classification belongs to the chain.
- One axis — one class: the statuses of an axis are class attributes of the axis class, and the same class carries the links and the classification. An entity with several axes has several such classes, one per lifecycle field.
- A status is never a model entity of the interchange graph: the ERD keeps its entity count, and the state row stays the state row. The object is the state row's description, not a second entity.
- Identity inside the machine stays the `code` string, so the state metadata shape, the runtime current-state API, transitions and serialization do not change.
- The string form is removed; no backward compatibility.
- Attributes travel to Maxitor: graph JSON, the diagram store, the FSM wire shape and the drawing.

### Session 2026-10-19 — placement, exclusion and rendering

- **Placement: the axis class.** The statuses of an axis are class attributes of the class that carries `_template`, and that class applies `StateVocabulary` as a mixin on the same declaration as `Lifecycle`. The status type is a module-level class next to the axis. There is no binding line, no generic parameter, no decorator and no nesting. This was chosen after measuring the alternatives — nesting the type in a vocabulary, nesting the vocabulary in the chain, a `states = …` binding or a class keyword, `Lifecycle[Vocabulary]`, and a decorator — because the axis class gives the same declaration-time check with none of their costs. An entity with several axes has several such classes, one per lifecycle field.
- **Exclusion: automatic.** The framework marks every status type out of the model graph; a per-class decorator would be forgotten in 32 files and its failure mode is a broken build, not a visible extra node.
- **Rendering depth: labels, order and colour.** The attribute payload reaches the store, the snapshot and the DOT source; the declared colour is applied with a fallback to the existing palette.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a model author writing a chain, a reader of the Maxitor diagrams, and the maintainer of the demo model whose chains are the examples the tutorials walk through.

### User Story 1 - A status is an object with fields of its own (Priority: P1)

A model author writes a chain for one entity. Instead of two strings per state, they declare the statuses of that chain once — code, human label, and whatever the status knows about itself (an order, a colour, a domain attribute) — and then declare the links between those objects.

**Why this priority**: it is the feature. Everything else reads what this story creates; without the object there is nothing for the graph or the diagram to read.

**Independent Test**: declare one vocabulary with three statuses carrying a code, a label and one domain field, build a chain from them, and confirm that the chain reports the same state keys, labels, classifications and transitions as the equivalent string declaration did, and that the objects are reachable from the chain by code.

**Acceptance Scenarios**:

1. **Given** a vocabulary with statuses `new`, `payment_pending`, `cancelled` carrying labels and a domain field, **When** the chain is built from those objects, **Then** the chain's states, initial/final classification and transitions are exactly those of the equivalent string chain, and the labels come from the objects.
2. **Given** a chain built from objects, **When** its current state is set to a status code and a transition is requested, **Then** the runtime behaves as today: the current state is the code string, allowed transitions are the declared ones, a forbidden transition is refused.
3. **Given** a status object, **When** its code is read, **Then** it is the same string the chain uses as the state key.
4. **Given** a vocabulary, **When** it is iterated, **Then** statuses come in declaration order, and any status can be found by its code.
5. **Given** a vocabulary with two statuses carrying the same code, **When** the vocabulary is declared, **Then** it is refused at declaration, naming the duplicate code.
6. **Given** a status whose code or label is empty or whitespace-only, **When** the status is created, **Then** it is refused at creation, naming the field.

---

### User Story 2 - The chain refuses what does not belong to it (Priority: P2)

A model author builds a second chain for another entity. Both chains have a `cancelled` status — different objects, possibly different fields. A state object of one chain must not be usable in the other, and the string form must not be usable at all, so a mistake is refused where it is written rather than surfacing later as a state node carrying a stranger's fields.

**Why this priority**: the object form creates the possibility of mixing axes, and the point of an object is that it carries fields — a status of another axis would silently bring foreign fields into a diagram.

**Independent Test**: build two axis classes with a status of the same code but different fields, use one class's status in the other class's `_template`, and confirm the refusal names the status and the class and happens at class definition; then pass a string to the same calls and confirm the same kind of refusal.

**Acceptance Scenarios**:

1. **Given** two axis classes with their own statuses, **When** `_template` in the first names a status of the second, **Then** the class definition is refused, naming the status and the class.
2. **Given** a chain declaration, **When** `.state("new", "New")` or `.to("cancelled")` is written, **Then** it is refused at declaration with a type error — the string form no longer exists.
3. **Given** a forward reference — a transition to a status declared later in the chain — **When** the chain is built, **Then** it is accepted, as today.
4. **Given** the same status code in two chains with different classifications, **When** both chains are built, **Then** both are accepted and each keeps its own classification.
5. **Given** an axis class, **When** a subclass declares no statuses of its own, **Then** it inherits the parent's members and builds.

---

### User Story 3 - The diagrams tell the truth (Priority: P3)

A reader opens a chain's FSM diagram in Maxitor. The states are drawn with the human labels the author wrote, in the order the author declared, with the colour the status carries. Hovering or inspecting a state shows the fields the status declares.

**Why this priority**: it is the observable value of the object. The graph could carry objects and the diagram still show keys — that is today's state.

**Independent Test**: build a graph from a chain whose statuses carry labels, order and colour; load it into the diagram store; ask for the FSM snapshot; confirm the labels are the human labels, the order is initial first then the declared order, the payload carries the fields, and the drawing uses the colour when present and today's palette when absent.

**Acceptance Scenarios**:

1. **Given** a state with the code `payment_pending` and the label `Payment pending`, **When** the FSM snapshot is produced, **Then** its `display_name` is `Payment pending`, not the code.
2. **Given** a chain whose statuses declare an order, **When** the FSM snapshot is produced, **Then** the initial state comes first and the rest follow the declared order; when no order is declared, the order is today's.
3. **Given** a chain whose statuses declare a colour, **When** the diagram source is built, **Then** the state is drawn with that colour; when no colour is declared, the existing per-type palette is used and the drawing is unchanged.
4. **Given** a state object with domain fields, **When** the graph state row and the FSM snapshot are read, **Then** all the fields are present with their values.
5. **Given** a graph with state rows, **When** the model graph is assembled, **Then** no state type appears as an entity of the model graph — the entity count is the one the model had before.

---

### User Story 4 - The demo moves without changing a single code (Priority: P4)

The maintainer migrates the demo's 32 declarations (28 chains and 4 private cycle sketches) to vocabularies. The codes stay 1:1: every state key the demo had is the code it has, so nothing that stores, queries or serializes a state key changes.

**Why this priority**: it proves the feature on the corpus, and a changed code would be a silent migration bug in stored data.

**Independent Test**: collect the set of state keys per chain before and after the migration and compare; then run the demo tests and examples.

**Acceptance Scenarios**:

1. **Given** the 32 demo declarations, **When** they are migrated, **Then** each one's set of state codes and transition pairs is identical to before.
2. **Given** the migration is complete, **When** the demo, the framework tests and the examples are scanned, **Then** no `.state("…"` and no `.to("…"` remains.
3. **Given** the migrated demo, **When** the graph is built, **Then** it builds, its state nodes keep their ids and kinds, and the demo tests and examples pass.

---

### Edge Cases

- A vocabulary with zero statuses: refused at declaration.
- Two statuses with the same code but different fields: refused at declaration (they are not the same status).
- The same code in two different vocabularies: allowed — different statuses of different chains.
- A status classified final in one chain and intermediate in another: allowed, and each chain keeps its own classification.
- A status type used as a field of something else (a result, another entity): out of scope here; the object is exposed by the chain only.
- A declared field that cannot be represented as JSON: the graph build refuses rather than emitting a broken row.
- A chain with no initial or no final state: refused by the existing build rules, which do not move.
- A status object with no extra fields: allowed; the label and code still reach the graph and the diagram.
- A diagram with no attributes at all (all chains before the migration completes): the drawing is unchanged.
- A subclass of an axis that declares no statuses: allowed; it inherits the members.
- A status object of another axis used in `_template`: refused at class definition, naming the status.
- A class that applies `StateVocabulary` without `Lifecycle`: refused at class definition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The framework MUST provide a base type for a lifecycle status, directly derived from the entity base, carrying a required code, a required human label, and no other required field.
- **FR-002**: A status MUST be immutable, MUST refuse an empty or whitespace-only code or label at creation, and MUST be named with the entity suffix, on a par with every other entity type.
- **FR-003**: The framework MUST provide a `StateVocabulary` mixin that a model author applies on the same class declaration as `Lifecycle`; it MUST collect the class's status objects in declaration order, infer and expose their single type, expose lookup by code, and refuse at class creation a duplicate code, a mix of status types, an axis class with no statuses, and a `StateVocabulary` applied to a class that is not a `Lifecycle`. A subclass of an axis that declares no statuses MUST inherit them.
- **FR-004**: A lifecycle class MUST accept status objects in its template and transitions, MUST take the label from the object, and MUST refuse a string argument. When the template is declared in the same class, it MUST refuse a status object that is not one of that class's status attributes, naming the status and the class.
- **FR-005**: A chain MUST keep the links and the classification: whether a state is initial, intermediate or final, and which transitions exist, MUST remain declared in the chain and MUST NOT be derived from the status object.
- **FR-006**: A status MUST carry no initial/final flag; the same status MAY be classified differently by two chains.
- **FR-007**: The state key inside the machine MUST remain the code string; state metadata, the current-state API, transition checking and serialization MUST keep their current shape and behaviour.
- **FR-008**: A chain MUST expose its status objects by code, so that code outside the chain can read the object of the current state.
- **FR-009**: The graph state row MUST keep its identity and its kind, MUST take its label from the status object, and MUST carry every declared field of the status object with its value.
- **FR-010**: A status object MUST NOT appear as an entity of the model graph; the graph builds with no added entities and no failure for the status type.
- **FR-011**: The interchange graph schema MUST admit the status fields and MUST keep validating every state row.
- **FR-012**: The diagram store MUST retain the status fields, and the FSM snapshot MUST expose them per state.
- **FR-013**: The FSM snapshot MUST report the human label as the state's display name, MUST order states as initial first and then the declared order, and MUST fall back to today's order when no order is declared.
- **FR-014**: The diagram source MUST use a status's declared colour when present and MUST fall back to the existing per-type palette otherwise; with no attributes anywhere, the drawing MUST be identical to today's.
- **FR-015**: The demo's 32 declarations (28 chains and 4 private cycle sketches) MUST be migrated with codes and transition pairs kept 1:1, and the string form MUST be removed from the framework tests, examples and documentation examples in the same change.
- **FR-016**: Every refusal named in this feature MUST happen at declaration, before any graph is built or any call is served, and MUST name the offending value, class or code.

### Key Entities

- **Status**: one state of one chain. Carries a code (its identity), a human label, and arbitrary domain fields (order, colour, and whatever the domain needs). Immutable. Adds nothing else.
- **Vocabulary**: the status attributes of one axis, collected by the `StateVocabulary` mixin on the axis class itself. Infers the status type, keeps the members in declaration order, and guarantees unique codes.
- **Axis class**: one class that is both `Lifecycle` and `StateVocabulary` — its attributes are the statuses, its `_template` holds the transitions and the classification. One axis is one chain.
- **Graph state row**: the chain's status as the interchange graph sees it — a stable id, a kind from the chain, a label and the fields from the status.
- **FSM snapshot**: what the diagram reads — per state a key, a display name, a kind, its transitions and its fields.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 32 demo declarations are migrated; the set of state codes and the set of transition pairs are identical before and after for every chain (100% of chains, 0 changed codes).
- **SC-002**: After the change, 0 string state declarations remain in the demo, the framework tests, the examples and the documentation examples.
- **SC-003**: 100% of states in the FSM snapshots report the declared human label as their display name; 0 report the code.
- **SC-004**: 100% of FSM snapshots order the initial state first and then follow the declared order where one is declared; where none is declared the order equals today's.
- **SC-005**: 100% of declared status fields that are not opted out with `Field(exclude=True)` appear, with their values, in the graph state row and in the FSM snapshot.
- **SC-006**: The model graph's entity count is unchanged by the change; 0 state types appear as entities.
- **SC-007**: Every refusal in FR-002, FR-003 and FR-004 is covered by a test, and each is measured at declaration time.
- **SC-008**: The full check run is zero, apart from the two accepted remarks.

## Assumptions

- **Placement: the axis class.** The statuses and the links are declared in one class body, the class applies `StateVocabulary` as a mixin next to `Lifecycle`, and the status type is module-level beside it. No binding, generic, decorator or nesting. Nesting a status type inside the same class as a nested vocabulary does not work — a nested class body does not see the enclosing class namespace — which is one more reason the axis class keeps the type at module level.
- **Exclusion is automatic.** Every status type is kept out of the model graph by the framework, not by a decorator the author must remember; a forgotten decorator would either break every graph build or double the entities.
- **No second identity.** A status has no id of its own; the code is the identity, and the graph's usual synthetic `id` column does not apply to state rows.
- **Attributes are JSON-representable.** A declared status field is expected to have a JSON form; a field that does not is refused at build rather than silently dropped.
- **Codes and labels are duplicated in the attributes payload.** The state row already carries the code and the label; they appear again among the fields on purpose, because the rule is "all declared fields", without a special case.
- **Ordering.** Initial first, then the declared order, then the code as a tiebreak; no declared order degrades to today's ordering.
- **Colour.** The declared colour applies to the state's outline; a declared fill colour, when present, applies to its fill; otherwise the per-type palette is used.
- **Transport is out of scope.** A status object is not made a field of an operation result or of another entity here; the chain exposes the object by code, and the transport question — raw object or a wire projection — is a separate task.
- **Persistence is out of scope.** The current state stays a code string; no status object is stored or hydrated.
- **The demo is the corpus.** The 32 declarations are migrated here; a shared vocabulary across chains is not introduced.
- **Two forms on the branch.** The delivered state has one form. On the branch the string form stays accepted until the corpus has moved, so that every commit stays importable; its removal is its own commit, and the delivered behaviour is the single form.

## Measured context and deliberate naming

The specification names two public type names, `BaseStateEntity` and `StateVocabulary`, because they are the contract a model author writes, and names the interchange concepts (state row, FSM snapshot, model graph) because the feature is about what those layers carry. This is the same deliberate exception the previous specification records: a requirement that cannot name the type it introduces cannot be tested. No module path, no function name and no framework internals appear outside the measured context above.

Two corrections against the issue are recorded rather than smoothed over:

- The issue speaks of "28 lifecycle classes"; the scan finds 32 declarations in 23 files — 28 named chains in 19 files plus 4 private cycle-sketch classes that also declare states with the string form and therefore move in the same change. The plan budgets for 32, not 28.
- The issue's example `OrderStateEntity(code="new", display_name="New")` has no domain field; the fields the diagrams need (`sort_order`, `color`) are introduced by this specification, so the plan budgets for them rather than discovering them mid-migration.
