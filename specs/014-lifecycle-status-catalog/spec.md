# Feature Specification: Lifecycle statuses live on the state type, and the axis checks its whole vocabulary

**Feature Branch**: `feature/issue-237-state-catalog-and-lifecycle-checks`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/237 — The status objects of a lifecycle axis move from the axis class to the state type they belong to. The state type declares its own statuses in its own body as `DRAFT = OrderStateEntity(...)`; the axis becomes a generic `Lifecycle[OrderStateEntity]` and keeps only the transitions. The type then carries the catalogue (`members`, `codes()`, `by_code()`, `entity_type`) and the axis refuses two declaration mistakes at class creation: a status that is not a declared object of the type, and a declared status that the axis never uses. `StateVocabulary` is removed, the existing axis declarations migrate, and the entity field, the runtime and the graph do not change. The two obsolete negative examples and one test axis are removed; the final corpus is 49 axes and 64 state types."

## Context: what is true today, measured on 2026-10-22

- **One axis is one class.** Since #209 the status objects are class attributes of the axis, `_template` holds the transitions and the classification, and `StateVocabulary` is the mixin applied next to `Lifecycle`. The status type is a separate, module-level class that carries only the fields:

  ```python
  class OrderStateEntity(BaseStateEntity):
      sort_order: int = Field(description="Order within the state list")
      color: str = Field(default="#1565c0", description="State outline colour")

  class OrderLifecycle(Lifecycle, StateVocabulary):
      DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)
      PAID = OrderStateEntity(code="paid", display_name="Payment received", sort_order=1)
      _template = Lifecycle().state(DRAFT).to(PAID).initial().state(PAID).final()
  ```

- **The corpus.** 51 declarations of `(Lifecycle, StateVocabulary)` exist today: 32 in `packages/aoa-demo/src/aoa/demo/model/`, 16 in `examples/`, and 3 in the framework's tests. 63 classes descend directly from `BaseStateEntity`: 32 in the demo, 24 in the examples, 7 in the framework's tests. Two further snippets live in code docstrings (`domain/__init__.py`, `state_entity.py`, and the deleted `state_vocabulary.py`); they are documentation, not declarations, and are updated or removed with the modules. Four vocabulary axes and one state type are declared inside test functions to be refused, and five plain `Lifecycle` axes carry no vocabulary; none is a corpus declaration and none is counted.
- **The catalogue API lives on the axis.** `OrderLifecycle.members`, `codes()`, `by_code("paid")` and `entity_type` are axis attributes; the state type owns only its fields.
- **Two declaration mistakes pass silently.**
  1. **A declared status the axis never uses.** `members` can report `['draft', 'paid', 'cancelled']` while the machine has two states; nothing warns, and the diagram shows a machine narrower than the declared vocabulary.
  2. **Membership is compared by equality, not identity.** `state_vocabulary.py` uses `entity not in declared`, which for Pydantic objects compares fields. An equal-but-distinct instance is accepted although the template then holds that object, not the one `members` and `by_code` expose.
- **The coverage rule is safe for the current corpus.** Every one of the 32 demo axes already uses every status it declares; the new rule needs no status added or removed there.
- **The entity, the runtime and the graph are on the other side of the contract.** The entity field is `lifecycle: OrderLifecycle`, created as `OrderLifecycle(current_state="draft")`; the graph state row carries `status.model_dump()` as its attributes, and Maxitor reads that row. None of these may change.

## Clarifications

### Session 2026-10-22 — decisions carried from issue #237

- **The statuses live on the type.** The state type declares its own statuses in its own body, and the axis names the type once: `class OrderLifecycle(Lifecycle[OrderStateEntity])`. The axis keeps only `_template`.
- **The surface is the class name.** A model author writes `DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)` inside `OrderStateEntity`; this is the only declaration form shown to authors. No `state(...)`, no `cast`, no `TYPE_CHECKING` block appears in model code.
- **The surface is a documented alias.** Inside a state type body, the type's own name resolves to the internal declaration factory `state(...)`. The alias is meaningful only in the call form; any other unknown name still raises `NameError`, and a self-referential field annotation stays a forward reference.
- **The conversion happens after the class exists.** The declaration factory returns a placeholder; a Pydantic hook converts every placeholder into a real instance after the model is built, so required fields, defaults, types and unknown keys are validated there — at class creation, before any graph is built.
- **Two refusals, two errors.** The axis refuses a status that is not a declared object of its type (`ForeignStateError`, with a distinct message for "code not declared" and "different instance, use `Type.STATUS`") and a declared status the axis never uses (`MissingStateError`, listing the missing codes). Both are declaration errors.
- **Coverage counts states only.** A member used only as a transition target is still missing: `.to(OrderStateEntity.CANCELLED)` does not declare `CANCELLED` as a state.
- **The catalogue moves to the type.** `members`, `codes()`, `by_code()`, `entity_type` become the state type's API. `by_code` raises `KeyError` for an unknown code. A subclass with no statuses inherits `members`; a subclass that declares statuses gets its own catalogue.
- **`StateVocabulary` is removed.** Its job splits between the state type's conversion hook and `Lifecycle.__init_subclass__`. There is no alias and no deprecation release: two vocabularies would be a second grammar.
- **The generic axis is the declared form.** The specification follows the issue's example, `Lifecycle[OrderStateEntity]`. The class-keyword alternative is recorded in Assumptions and is not part of this scope.
- **The migration is mechanical.** The status lines are copied unchanged from the axis to the type; no `state(...)`, no `cast`, no parentheses are rewritten. All 51 declarations migrate in this change.
- **Documentation is updated in place.** The entity, runtime, graph and Maxitor behaviour does not change, and no new user-facing case is introduced: only the declaration form changes. The existing pages and the example/notebook snippets that show the old declaration are updated point-wise; there is no new tutorial, no new example series and no wholesale notebook re-execution.

### Session 2026-10-22 — clarifications

- Q: Which axis form does the specification fix: the generic `Lifecycle[OrderStateEntity]`, or the class keyword `Lifecycle, state_type=OrderStateEntity`? → A: The generic form; `Lifecycle` becomes generic, every bare `Lifecycle` annotation and all 51 axes are parameterised, and the class-keyword alternative is out of scope.
- Q: Is `StateVocabulary` removed now, or kept as a deprecation alias for one release? → A: Removed now; one grammar, all 51 declarations migrate in this change, the old import fails, and the changelog records the break. No compatibility tests for the old form.
- Q: Must every axis list every status of its type, or may an axis use a subset? → A: Every status is mandatory. A type and its axis are one to one; two axes may share a type only if both list every status, and a narrowed specialized axis declares its own state type rather than skipping a status.
- Q: Is the declaration factory `state(...)` a public authoring surface, or internal to the framework? → A: Internal. The class name is the only documented surface, and the placeholder type appears in framework tests only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare a state type with its own statuses (Priority: P1)

A model author defines one class for a lifecycle status — its stable code, its human label and the presentation or domain fields the status needs — and declares every status of that type in the same class body. After the class is created, each declared name is a full instance of that type, all fields are initialised, and the type exposes the catalogue.

**Why this priority**: This is the new declaration surface; without it the rest of the feature has no object to work on, and the field-initialisation guarantee is what makes the surface usable at all.

**Independent Test**: Define a state type with several fields and several statuses, then check `OrderStateEntity.DRAFT` is an instance, `model_dump()` contains every field, `members` is in declaration order, `codes()` and `by_code()` answer, and a misspelled field fails at class creation.

**Acceptance Scenarios**:

1. **Given** a state type declaring `sort_order`, `color`, `fill_color` and `requires_receipt`, **When** it declares `DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)`, **Then** `OrderStateEntity.DRAFT` is an `OrderStateEntity`, its `sort_order` is `99`, and its omitted fields carry their declared defaults.
2. **Given** a status declaration that omits a required field or misspells an optional one, **When** the class is created, **Then** a `ValidationError` names the class and the field, and no partially initialised status exists.
3. **Given** a state type with no statuses, **When** it is created, **Then** it is a valid type with an empty catalogue.
4. **Given** a declared status with a duplicate code, **When** the state type is created, **Then** the duplicate is refused at class creation.

---

### User Story 2 - Refuse a foreign status and a missing status at the axis (Priority: P1)

A model author writes the axis as `Lifecycle[OrderStateEntity]` and lists the transitions. The axis accepts only the declared status objects of that type, by identity, and requires every declared status to appear as a state. A mistake is refused when the axis class is created, with an error naming the axis, the status and the allowed codes.

**Why this priority**: The two refusals are the correctness value of the feature; the declaration move alone would not prevent either mistake.

**Independent Test**: Declare one valid axis, one using a status of another type, one using an equal-but-distinct instance, and one omitting a declared status; the first builds, the other three raise the named errors.

**Acceptance Scenarios**:

1. **Given** an axis whose `.state()` or `.to()` names a status of another type, **When** the axis is created, **Then** `ForeignStateError` names the axis, the status code and type, and the allowed codes.
2. **Given** an axis that uses `twin = OrderStateEntity(...)` equal to `OrderStateEntity.DRAFT` but not the same object, **When** the axis is created, **Then** `ForeignStateError` says it is a different instance and names `OrderStateEntity.DRAFT`.
3. **Given** an axis that declares `CANCELLED` on the type and never lists it as a state, **When** the axis is created, **Then** `MissingStateError` lists `cancelled`.
4. **Given** a member used only as a transition target, **When** the axis is created, **Then** `MissingStateError` reports it as missing.
5. **Given** a plain `Lifecycle` subclass with a `_template`, **When** it is created, **Then** it behaves as today, unchecked.

---

### User Story 3 - Migrate the corpus without changing the entity, runtime or graph (Priority: P2)

The model author (or an agent) moves the status lines from each axis to its state type, drops `StateVocabulary`, parameterises the axis and qualifies the names in `_template`. The entity field, the runtime construction and the graph state rows stay as they are.

**Why this priority**: The feature is only real when the existing corpus is on the new form; the mechanical move is what keeps the migration safe.

**Independent Test**: Migrate the 51 declarations, import the 32 demo axes, run the lifecycle examples and the suite, and compare the graph state rows and the entity field types before and after.

**Acceptance Scenarios**:

1. **Given** an axis on today's form, **When** its status lines move to the state type and the axis becomes `Lifecycle[Type]`, **Then** the declaration builds with the same statuses and transitions and the same `current_state` behaviour.
2. **Given** the migrated corpus, **When** the demo graph is built, **Then** entity field types, state row attributes, labels and transitions are unchanged.
3. **Given** an axis that used `by_code` or `members` on the axis, **When** the corpus is migrated, **Then** the call site reads them from the state type.

---

### User Story 4 - The existing pages show the simple surface (Priority: P3)

An AI author writing on the engine sees one declaration form and no framework-specific factory: the status name is the class name, the fields are typed, and the errors are field-level or membership-level rather than a raw `NameError`.

**Why this priority**: The engine is AI-first; the surface must be the one an AI copies from the docs without a cast or a second concept.

**Independent Test**: From the updated snippets in the existing tutorial and reference, write a state type and axis; check that the code contains only `NAME = Type(...)`, that the checks fire as documented, and that the pages kept their structure (no new example series).

**Acceptance Scenarios**:

1. **Given** the tutorial and the reference page, **When** an author writes a state type and an axis, **Then** no `state(...)`, `cast` or `TYPE_CHECKING` appears in the authored code.
2. **Given** a typo in a status field or a forgotten status, **When** the module is imported, **Then** the error names the class and the field or the missing code.
3. **Given** the existing pages, **When** the declaration snippet is updated, **Then** the pages keep their structure and no new example series or tutorial is added.

---

### Edge Cases

- A status of another type is named in `.state()` or `.to()`: `ForeignStateError` names the axis, the status code and type, and the allowed codes.
- An equal-but-distinct instance of a declared status is used: `ForeignStateError` says it is a different instance and names `Type.STATUS`.
- A declared status is never listed as a state: `MissingStateError` lists its code.
- A declared status is used only as a transition target: it is still reported missing.
- A misspelled field, a missing required field, or a wrong type in the status declaration: `ValidationError` at class creation, naming the class and the field.
- A coercible value (`sort_order="42"`): accepted and stored by Pydantic's rules, not treated as an error.
- A state type with no statuses: valid, empty catalogue.
- A subclass with no statuses: inherits the parent's catalogue; with statuses: its own catalogue.
- Two declared statuses share a code: refused at class creation.
- A subclass with its own template omits one of its declared statuses: `MissingStateError`.
- A plain `Lifecycle` subclass with no type parameter: behaves as today, unchecked.
- Two axes share one state type: each must list every status; a narrowed axis is refused with `MissingStateError` and declares its own type.
- The type's own name is used as a value in its body, not as a call: it yields the declaration factory, not the class.
- A global with the same name as the state type is referenced inside its body: the alias shadows it.
- A field annotation refers to the type itself: it must be a forward reference.
- The exclusion of the status placeholders from model fields is removed: class creation fails with a Pydantic error.
- `by_code` is asked for an unknown code: `KeyError`.
- `StateVocabulary` is imported after the change: the name no longer exists.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A state type MUST be able to declare its statuses as class attributes of its own body, in the call form `NAME = <TheType>(...)`.
- **FR-002**: After the class is created, each status attribute MUST be an instance of the declaring type; the catalogue (`members`) MUST preserve declaration order; codes MUST be unique within the type.
- **FR-003**: The state type MUST expose the catalogue as `members`, `codes()`, `by_code(code)` and `entity_type`; `by_code` MUST raise `KeyError` for an unknown code; `entity_type` MUST be the type itself.
- **FR-004**: A subclass with no statuses MUST inherit the parent's catalogue; a subclass that declares statuses MUST get its own; a type with no statuses MUST be valid with an empty catalogue.
- **FR-005**: Every declared field of a status MUST be initialised when the class is created; fields not passed explicitly MUST take their declared defaults; a misspelled field, a missing required field or a wrong type MUST raise a `ValidationError` at class creation.
- **FR-006**: Inside a state type body, the type's own name MUST resolve to the declaration factory only in the call form; any other unknown name MUST still raise `NameError`; a self-referential field annotation MUST remain a forward reference.
- **FR-007**: The axis MUST be declared as `Lifecycle[StateType]` over the state type and MUST keep only `_template`; the catalogue MUST NOT remain on the axis.
- **FR-008**: When the axis has its own template, every status in `.state()` and `.to()` MUST be one of the type's declared objects by identity, otherwise `ForeignStateError` MUST be raised naming the axis, the status code and type, and the allowed codes.
- **FR-009**: The "different instance" form of the foreign refusal MUST say so explicitly and name the declared attribute to use (`Type.STATUS`).
- **FR-010**: Every declared status of the type MUST appear as a state in the axis; a missing one MUST raise `MissingStateError` listing the missing codes. A status used only as a transition target MUST NOT count as a state.
- **FR-011**: Both refusals MUST run at class creation (import time), before any graph is built, and MUST cost nothing at runtime.
- **FR-012**: A plain `Lifecycle` subclass with no type parameter MUST keep today's behaviour and MUST NOT be checked.
- **FR-013**: `StateVocabulary` MUST be removed from the public API; every remaining declaration (49 axes, 64 state types) MUST migrate to the new form; no deprecation alias MUST remain.
- **FR-014**: The entity field type (`lifecycle: OrderLifecycle`), the runtime construction (`OrderLifecycle(current_state=...)`), the graph state row (`status.model_dump()`) and the Maxitor payload MUST NOT change.
- **FR-015**: The authored code MUST type-check without `cast` or a `TYPE_CHECKING` block; a status attribute MUST be typed as the state type, including its domain fields; `mypy --strict` MUST be clean.
- **FR-016**: The declaration factory MUST be internal to the framework; the class name MUST be the only documented surface, and the placeholder type MUST appear in framework tests only.
- **FR-017**: The status placeholders MUST be excluded from the model's fields, and removing that exclusion MUST fail class creation with a Pydantic error.
- **FR-018**: The existing declaration rules — the state-kind name suffix, the exclusion from the model graph, duplicate-code refusal, the eight template build rules — MUST keep their behaviour and their error types.

### Key Entities

- **State type**: the class that declares the fields of one status and, in its own body, the statuses themselves; it owns the catalogue.
- **Status object**: one immutable instance of a state type, carrying `code`, `display_name` and the declared domain fields.
- **Catalogue**: the ordered tuple of a state type's declared statuses, with lookup by code and the shared type.
- **Axis**: the `Lifecycle[StateType]` class that holds the transitions and the classification; it no longer holds the catalogue.
- **Template**: the transition graph of one axis, whose states and targets must be declared objects of the type.
- **Declaration error**: `ForeignStateError` (a status that is not a declared object) and `MissingStateError` (a declared status absent from the axis).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new state type with three statuses and six fields is declared, created and used without any framework factory appearing in the authored code; 100 % of its fields are present in `model_dump()`.
- **SC-002**: All remaining declarations (49 axes — 32 demo, 14 examples, 3 framework tests; 64 state types — 32/21/11) are on the new form; 0 occurrences of `StateVocabulary` remain in `packages/` and `examples/`; all 32 demo axes import.
- **SC-003**: The three refusal cases (foreign type, equal-but-distinct instance, missing status) each raise their named error in a dedicated test, and no other test fails.
- **SC-004**: A misspelled status field, a missing required field and a wrong type each fail at class creation with a message naming the class and the field; a coercible value is accepted and stored by Pydantic's rules.
- **SC-005**: The demo graph before and after the change reports the same entity field types, state row attributes, labels and transitions for every axis.
- **SC-006**: `mypy --strict` is clean across the eight packages, no new `# type: ignore` is introduced, and the closing check run reports only the two accepted remarks (Vite chunk-size, LangGraph deprecation).
- **SC-007**: The existing pages and the example/notebook snippets that show the old declaration are updated point-wise: the declaration, the fields and defaults, the refusals and the plain `Lifecycle` escape appear where they already appeared. No new tutorial, no new example series and no wholesale notebook re-execution.

## Assumptions

- **The generic form is chosen.** The axis is `Lifecycle[StateType]`, as the issue's example shows. The class-keyword alternative (`Lifecycle, state_type=Type`) is recorded in the issue as an open decision; it is not in this scope.
- **One state type serves one full axis.** The coverage rule has no subset opt-out: two axes may share a type only if both list every status, and a narrowed or specialized axis declares its own state type.
- **`StateVocabulary` is removed hard.** No deprecation release and no alias; the changelog records the break, as #209 did for the string form.
- **The declaration factory is internal.** `state()` and the placeholder type are framework implementation; the class name is the only documented surface.
- **The alias shadows a same-named global.** A state type body that references a global with the same name as the class receives the declaration factory instead. This is the documented diagnostic cost of the surface and is covered by a test.
- **Field names in the call are checked at class creation, not by mypy.** Pydantic validates the arguments; the `pydantic.mypy` plugin would check them statically and is out of scope.
- **The generic migration is part of this change.** `mypy --strict` with `disallow_any_generics` requires every bare `Lifecycle` annotation to be parameterised; the 51 axes and the core annotations migrate together.
- **The corpus count is a snapshot.** 51 declarations and 63 state types were measured on `main` after #210 (PR #238); new axes declared before implementation increase the migration count.
- **The dependency is closed.** #210 is merged; the branch is based on `545b5c43`, and the demo and the examples are already on the `Entity` naming convention.
- **Pydantic supports the conversion hook.** The installed Pydantic version provides the post-model hook and the ignored-types configuration used by the conversion; no version change is planned.

## Dependencies

- #209 and #210, merged; the state entities and the kind name rule are in place.
- The Pydantic model base and its validation behaviour, including `extra="forbid"`.
- `mypy --strict`, ruff and the repository's check run.
- The demo corpus, the examples and the notebooks, which are both the migration target and the evidence.

## Out of scope

- The graph, Maxitor, persistence and the entity projection: no change.
- The eight template build rules: unchanged.
- The placement of the status fields (`sort_order`, `color`, `fill_color`): unchanged.
- The `state_type=` class-keyword alternative, the `pydantic.mypy` plugin, and a deprecation alias for `StateVocabulary`.
- The `state()` factory as a public authoring surface.

## Deliberate exceptions to "no implementation detail"

The specification names `BaseStateEntity`, `Lifecycle`, `StateVocabulary`, `members`, `codes()`, `by_code()`, `entity_type`, `ForeignStateError`, `MissingStateError` and the hook names because they are the contract a model author writes and the names a test asserts. It also names module paths and measured counts in the Context section because the issue's scope rests on them. No other module path, function name or framework internal appears in the requirements.
