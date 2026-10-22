# Feature Specification: Entity kinds — one base class per kind, and the kind in the name

**Feature Branch**: `feature/issue-210-entity-type-markers`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/210 — An entity is a subclass of one base today, and the base says nothing about what an instance represents. After this change there are six kind base classes: an independent domain object, a technical link, an identifiable part of one owner, the variant-specific data of the same object, a shared reference value, and a lifecycle state. The entity base refuses inheritance from itself; the six override that refusal and each one checks the name of its own descendants against its own kind. The kind is the class — there is no enum, no registry and no second declaration to keep in sync. `BaseStateEntity` came in #209; this change adds the other five, both rules, and the migration of the whole corpus — 476 classes — by meaning."

## Context: what is true today, measured on 2026-10-22

- **One base for every kind.** `BaseEntity` is the only base a real entity has: the classes representing an order, an order line and a currency are all written `class XxxEntity(BaseEntity)` — 476 of them. Since #209 one kind base class exists, `BaseStateEntity`, and 63 status classes inherit it. 540 classes therefore descend from the entity base — 476 real, 63 status and the base class itself; 470 of the 476 carry `@entity`.
- **The name rule today is one generic suffix.** `BaseEntity.__init_subclass__` refuses a name that does not end with `Entity`. Nothing distinguishes an order from an order line, or a technical link from a reference value: `OrderEntity`, `OrderLineEntity` and `CurrencyEntity` are three spellings of the same word.
- **The corpus.**

  | Area | Classes on `BaseEntity` |
  |---|---|
  | `packages/aoa-demo/src` | 209, in 17 bounded contexts (`store` 44, `assurance_portfolio` 28, `billing` 27, `analytics` 23, `messaging` 18, `catalog` 17, `clinical_supply` 14, `inventory` 12, `identity` 7, `support` 5, and 7 more) |
  | `examples/` | 145, in 43 scripts (`step_21_relations` 133) |
  | `packages/aoa-action-machine/tests` | 114, including `tests/support/domain_model/entities.py` |
  | `packages/aoa-ocel` | 2 in `src`, 3 in `tests` |
  | `packages/aoa-maxitor`, `packages/aoa-fastapi-adapter`, `packages/aoa-mcp-adapter` | 1 each |

- **The rename space is empty.** Of the 476, none ends with any of the six kind suffixes, and no class anywhere in the repository is already named `*CoreEntity`, `*AssocEntity`, `*DetailEntity`, `*SpecEntity` or `*EnumEntity`. Every rename lands on a free name.
- **The rename is visible outside Python.** 68 non-Python files that describe the repository as it is today mention an entity class name 1504 times: 43 notebooks (executed output interleaved with the code), 21 markdown pages — `README.md` and its Russian draft among them, 8 of the 21 being drafts a report links — the generated artefact trio of one example (`.dot`, `.json`, `.svg`), and one TypeScript check script. A further 25 files mention a name 205 times and are **history** — `docs/CHANGELOG.md`, the package changelogs and the earlier specifications under `specs/`; they record what was true when they were written and are not rewritten. Inside Python, 58 modules declare more than one entity, and two modules declare two classes with the same stem — `test_hydration.py` three `DummyEntity` and `test_entity_introspection.py` two `ChildEntity` — so a rename by kind must not collapse two distinct classes into one name.
- **The graph names an entity by its class name.** `EntityGraphNode` takes `full_qualname(cls)` as its node id and `cls.__name__` as its label, so a rename changes the interchange graph's labels and ids and every diagram drawn from it. Nothing stored holds a qualified id — 0 occurrences of a dotted entity id in the repository's JSON, markdown and Python — so nothing persisted becomes unreadable.

## Clarifications

### Session 2026-10-22 — decisions carried from the issue

- **A kind base class states a role, not a table shape.** Six roles: an independent object, a technical link, an owner's part, variant-specific data of the same object, a shared reference value, a lifecycle state. The number of foreign keys, the presence of an `id` column or the shape of a table does not decide the kind; what the instance represents does. An order line with its own UUID is still a detail.
- **The class is the declaration.** There is no enum, no registry of classes, no attribute on the class and no decorator: the six base classes are the only place a kind exists, and each one derives its own suffix and its own word from its own name.
- **Two rules, each owning its half.** The entity base refuses inheritance from itself; the six override that refusal and each checks the name of its own descendants.
- **Six kind base classes, no more.** `BaseStateEntity` arrived in #209; this change adds five and gives all six the same shape.
- **Primary-key introspection is out of scope.** The class docstrings describe identity (own PK, FK-composed, parent PK plus discriminator, PK equal to the head's PK), but the check needs an identity subsystem that does not exist — `get_primary_key()` still returns `id` by convention.

### Session 2026-10-22 — clarifications

- Q: Do all 476 classes migrate in one change, or is part of the corpus moved to a separate task? → A: All 476 migrate in one branch and one pull request; no part of the corpus is deferred, and no temporary allowance is introduced.
- Q: Are the old entity names kept as deprecated aliases after the rename? → A: No — the rename is a hard break with no alias, and the changelog says so.
- Q: Which exception type do the declaration refusals raise? → A: `DeclarationStructureError` for a structural fault (inheriting the base directly, two kinds in one chain) and `NamingSuffixError` for a naming fault (missing or foreign kind suffix); no new exception type is introduced.
- Q: Does the kind travel into the interchange graph as data, or only in the class name? → A: As data — every entity row carries `properties.entity_kind` with the kind's word (`core`, `assoc`, `detail`, `spec`, `enum`, `state`), and the word is derived from the kind base class's own name, so the graph adds no second declaration.
- Q: Where does the kind live — an enum, a registry, an attribute, or the classes themselves? → A: In the classes themselves. The base recognises a kind base class by inheritance and an overridden hook; each kind base class takes its suffix from its own name; the wire word is that same suffix without `Base` and `Entity`. One place, no types to maintain.

### Session 2026-10-22 — corrections found by the cross-artifact analysis

- **The rename ripple was miscounted.** The first measurement said 81 files and 1510 mentions. Re-measured with `.dot` and `.svg` in scope and with history separated: 68 current-state files carry a name 1504 times, and 25 historical files carry it 205 times. Context, FR-013 and SC-008 now state the split.
- **History is not rewritten.** The changelogs and the earlier specifications under `specs/` describe what was true when they were written; the rename does not reach into them. A requirement to make the old name absent "anywhere in the repository" would have edited history to hide a rename that did happen.
- **The corpus denominator was inconsistent.** 540 counts the state base class itself; 539 counts the classes the rule is about. SC-003 uses 539 and names the exemption.
- **The refusal criterion stopped one requirement short.** SC-004 covered the structural and naming requirements but not the error types and messages; it now covers both.

### Session 2026-10-22 — scope decisions taken in this specification

- **The issue's split allowance is not used.** The issue permits moving other packages to a separate task "if the volume is large". Measured, that volume is 8 classes (`aoa-ocel` 5, `aoa-maxitor` 1, `aoa-fastapi-adapter` 1, `aoa-mcp-adapter` 1) against 468 in the demo, the examples and the framework's own tests, which the issue keeps in scope. Eight classes do not justify a second issue, and the rule fails at class creation, so splitting them would leave those packages' suites red for the length of the split. All 476 migrate here.
- **No legacy allowlist.** The rule fails when the class is created, so a legacy allowance would be a second, quieter grammar. The delivered state has one form: every entity carries exactly one kind base class and the kind in its name.
- **Intermediate abstract classes are not exempt.** The suffix rule belongs to the kind base class and applies to every descendant, so a base such as `BaseTransportCoreEntity` carries its kind like any other class. The corpus has no intermediate class outside the framework, so this costs nothing today and removes an exception from the rule.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a model author declaring an entity, a reader of a diff or of the Maxitor diagrams who has to tell an order from an order line, and the maintainer of the demo model, whose 209 entities are the corpus the tutorials walk through.

### User Story 1 - A declaration says what kind of thing it is (Priority: P1)

A model author writes a new entity. They choose one of the six kind base classes — an independent object, a technical link, an owner's part, variant data of the same object, a reference value, a lifecycle state — and write the class as `XxxCoreEntity`, `XxxAssocEntity`, `XxxDetailEntity`, `XxxSpecEntity`, `XxxEnumEntity` or `XxxStateEntity`. The choice is the `class` line, not a note in a docstring.

**Why this priority**: it is the feature. Everything else — the rules, the migration, the documentation — reads what this story creates.

**Independent Test**: declare one entity of each of the six kinds from its own kind base class, import the module, and confirm all six exist with exactly one kind in their inheritance chain and a name carrying that kind (quickstart §1 and §2).

**Acceptance Scenarios**:

1. **Given** the six kind base classes, **When** a module imports them, **Then** each is an abstract class derived from the entity base, is exportable from the framework's domain package, and is kept out of the model graph.
2. **Given** a class `OrderCoreEntity` declared `@entity` on `BaseCoreEntity`, **When** the module is imported, **Then** the declaration is accepted.
3. **Given** one entity of each kind, **When** the model graph is built, **Then** every one of them appears as an entity node exactly as an `XxxEntity` did before, and no kind base class appears as an entity.
4. **Given** a kind base class, **When** it is instantiated, **Then** it is refused: a kind base class states a role and is not a real entity.
5. **Given** a class that inherits the entity base directly, **When** it is created, **Then** it is refused, because an entity inherits one of the six.

---

### User Story 2 - A misdeclaration is refused where it is written (Priority: P2)

A model author writes a class that inherits the base directly, or names an order line `OrderSpecEntity`, or adds two kind base classes "just in case". The mistake is refused at class creation with a message that names the class, what was found and the suffix the kind requires.

**Why this priority**: an unchecked kind base class is a comment. The value of the six kinds is that one of them is always present and correct; a rule enforced later — at graph build or at review — is the state this change removes.

**Independent Test**: declare each forbidden shape in its own module, import it, and confirm a creation-time error naming the class and the expected kind; then declare the lawful shapes — an intermediate descendant of a kind base class, one kind base class beside an ordinary mixin — and confirm they import (quickstart §2).

**Acceptance Scenarios**:

1. **Given** a class inheriting the entity base directly, **When** it is created, **Then** it is refused with `DeclarationStructureError`: an entity inherits one of the six kind base classes.
2. **Given** a class that inherits two kind base classes, **When** it is created, **Then** it is refused with `DeclarationStructureError`, naming both.
3. **Given** a class inheriting one kind base class, **When** its name does not end with that kind's suffix, **Then** it is refused at class creation with `NamingSuffixError`, naming the expected suffix.
4. **Given** a class inheriting `BaseDetailEntity`, **When** its name ends with `CoreEntity`, **Then** it is refused as the wrong kind — the suffix must be the base class's own.
5. **Given** an intermediate abstract class `BaseTransportCoreEntity(BaseCoreEntity, ABC)`, **When** it and a concrete `TruckCoreEntity` are declared, **Then** neither is refused: an intermediate carries its kind like any other descendant.
6. **Given** a class that inherits one kind base class and one ordinary mixin, **When** it is created, **Then** it is accepted: only the six count towards the rule.
7. **Given** a status class, **When** its name does not end with `StateEntity`, **Then** it is refused at its own creation.
8. **Given** a class that carries a kind base class and no `@entity`, **When** it is created, **Then** it is accepted — the three teaching examples and the framework's negative fixtures keep working, and the missing decorator stays a build-time error of the entity and specialization inspectors.
9. **Given** a class whose name does not end with `Entity` at all, **When** it is created, **Then** the generic naming refusal fires first, naming the `Entity` suffix.

---

### User Story 3 - The corpus says what it means (Priority: P3)

The maintainer of the demo model reclassifies its 209 entities by meaning: the order stays a core entity, the order line becomes a detail, the currency dictionary becomes an enumeration, a line-item relationship that carries only the fact of the connection becomes an association. The framework's fixtures, the examples and the other packages follow.

**Why this priority**: it is the proof that the six kinds are usable on a real model, and the acceptance criterion of the issue. It is P3 because it is mechanical once the kind base classes exist — and because a corpus migrated before them would drift back.

**Independent Test**: for every migrated class, compare the declared model fields, relations and lifecycle names before and after the change; then run every package's tests and every example script (quickstart §4–§6).

**Acceptance Scenarios**:

1. **Given** the 476 classes that inherit the base directly, **When** the migration is complete, **Then** each carries exactly one kind base class and a name carrying that kind, and it is the object's meaning — not its table shape — that chose the kind.
2. **Given** a migrated class, **When** its model fields, relation fields, lifecycle fields and `@entity` description are compared with the class before the change, **Then** they are identical: the base class and the name changed, nothing else did.
3. **Given** the 145 classes in `examples/` in 43 scripts, **When** they are renamed, **Then** each script and its notebook still describe the same case and the recorded output reflects the new names.
4. **Given** the demo's 17 bounded contexts, **When** the store is loaded and the model graph is built, **Then** the graph has the same number of entities, fields, relations and lifecycles as before the change; only the labels and ids differ, and each entity row gains its kind.
5. **Given** the whole repository, **When** it is searched for a class inheriting the base directly, **Then** the only matches are the six kind base classes.
6. **Given** two classes in one module that shared a stem before — three `DummyEntity`, two `ChildEntity` — **When** they are renamed by kind, **Then** they remain distinct names in that module.

---

### User Story 4 - The reader of the model sees the kind, and the documentation says how (Priority: P4)

A reader opens a diagram or a diff and sees `SalesOrderLineDetailEntity` next to `SalesOrderCoreEntity`; a reader of the reference page finds the six kinds, what each one represents, both rules and the word each kind reports. The tutorial that teaches the name suffix no longer teaches the old one.

**Why this priority**: the name is the only part of the classification visible without reading the class; and a rule that is not documented is rediscovered by every author.

**Independent Test**: read the reference page and the tutorial as someone who has not seen the change; run the new example and confirm its printed output matches the notebook (quickstart §7 and §9).

**Acceptance Scenarios**:

1. **Given** the reference page for intents and invariants, **When** it is read, **Then** it carries all six kinds with their identity, their suffix and their wire word, and both rules with the refusal each produces.
2. **Given** the tutorial that declares an entity, **When** it is read and run, **Then** the class it teaches derives from a kind base class and is named with its kind, and the run prints what the page shows.
3. **Given** the documentation pages written by this change, **When** it is reported, **Then** each page has its Russian draft beside it and both links are given.
4. **Given** the changelog, **When** it is read by someone who has not followed the work, **Then** it says what a model author can now do — choose a kind and have the framework hold them to it — without a per-file account of the renames.

---

### Edge Cases

- A class inheriting the entity base directly and overriding `__init_subclass__` but not being one of the six: it is treated as a kind base class — excluded from the graph and not instantiable. A test pins that exactly six such classes exist, so a seventh is a deliberate act, not an accident.
- A kind base class that forgets to override the hook: the base refuses it as a direct inheritor, and the six-class test fails earlier.
- A class inheriting a kind base class and an abstract intermediate that also descends from it: allowed; one kind in the chain is one kind.
- A name that ends with a kind suffix but whose base class is a different kind: refused, naming both.
- A name that ends with a second, unrelated suffix (`…CoreEntityRow`): refused by the generic `Entity` rule, naming the expected `Entity` ending.
- A class inheriting the base directly and never decorated: refused — the rule is about the hierarchy, not about the decorator. The three teaching examples keep working because they inherit kind base classes after the migration.
- A module that declares two entities with the same stem (`DummyEntity` × 3, `ChildEntity` × 2): the rename keeps them distinct; a rename that would collide in one module is a mistake in the migration, not a lawful outcome.
- An entity whose meaning is genuinely arguable — a supplier offer that looks like a join table, a relationship that has acquired its own process: decided by what the instance represents, recorded in the plan's mapping table so the maintainer reviews the judgement rather than rediscovering it in a diff.
- An entity that is a technical link but also carries a lifecycle: not an association; a link that is approved or terminated is a domain object.
- A status class that is a subclass of another status class: still `…StateEntity`; the rule belongs to the base class and is inherited.
- A notebook whose recorded output shows a renamed class: re-run rather than edited, so what the reader sees is what the code prints.
- A generated artefact (`.dot`, `.json`, `.svg`) carrying the old label: regenerated by its example, not patched by hand.
- The kind `state` in `properties.entity_kind`: no entity row carries it, because every status type is excluded from the graph; the word is in the schema's set for completeness, and a row that claimed it would be a defect.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The framework MUST provide the five missing kind base classes — `BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity`, `BaseEnumEntity` — as abstract classes derived directly from the entity base, one file each beside the existing `BaseStateEntity`, each carrying the role, contract and invariants stated in the issue, and each exportable from the framework's domain package.
- **FR-002**: A kind base class MUST be abstract in three senses at once: it is never instantiated, it is never a node of the model graph, and the entity base MUST recognise it as a kind base class without any enum, registry, class attribute or decorator — by inheriting the base directly and overriding the subclass hook.
- **FR-003**: Every class descending from a kind base class MUST be named with that kind's suffix, and the suffix MUST be taken from the kind base class's own name (its name without the `Base` prefix), so the class name is the only declaration of the kind.
- **FR-004**: The entity base MUST refuse inheritance from itself: a class that inherits it directly without being a kind base class is refused with `DeclarationStructureError`, and a class carrying two kind base classes is refused with `DeclarationStructureError` naming both.
- **FR-005**: The name refusals MUST be `NamingSuffixError` naming the class and the expected suffix; every refusal in FR-003 and FR-004 MUST name the offending class, what was found and the suffix the kind requires.
- **FR-006**: The existing generic `*Entity` naming invariant MUST stay in force and MUST fire before the kind rules; an ordinary mixin inherited beside a kind base class MUST NOT count towards the rule; the six kind base classes themselves MUST be exempt from the kind-suffix rule.
- **FR-007**: `BaseStateEntity` MUST be the sixth kind base class with the same shape: its descendants are named `…StateEntity`, are refused otherwise, and stay out of the model graph as they do today.
- **FR-008**: Every refusal in FR-003 to FR-007 MUST happen when the class is created, before any graph is built or any instance exists, and MUST NOT be a warning or a deferred build error. A structural fault MUST be a `DeclarationStructureError`; a naming fault MUST be a `NamingSuffixError`; instantiating a kind base class MUST be a `TypeError`.
- **FR-009**: A class carrying a kind base class and no `@entity` MUST NOT be refused by these rules; the existing build-time refusal of an undeclared entity MUST stay unchanged, and `@entity` MUST gain no new check.
- **FR-010**: Each of the 476 classes that inherit the entity base directly MUST be given exactly one kind base class chosen by what an instance represents, and MUST be renamed so that its name ends with that kind — with the choice recorded as a mapping the maintainer can review before the renames are made.
- **FR-011**: A migrated class MUST keep its model fields, relation declarations, lifecycle declarations, `@entity` description, domain and classifier codes unchanged; the base class and the name are the only changes. Two classes in one module that shared a stem before MUST remain distinct after the rename. The old name MUST NOT survive as an alias, a re-export or a shim.
- **FR-012**: The migration MUST cover the whole repository: the demo's 209 entities in 17 bounded contexts, the 145 entities of the 43 example scripts, the 114 in the framework's tests including its shared fixture model, and the 8 in the other packages — no split into a second issue and no temporary allowance for a class that has not been migrated.
- **FR-013**: Every non-Python reference to a renamed class in a file that describes the repository as it is today MUST be updated in the same change — 43 notebooks (re-executed, not edited), 21 markdown pages including `README.md` and its Russian draft, the generated artefact trio of the affected example (regenerated by the example), and the one TypeScript check script — so that no old name remains in the current state of the repository. Historical records MUST NOT be rewritten: the changelogs and the earlier specifications under `specs/` keep the names they were written with.
- **FR-014**: The reference documentation MUST gain the six kinds with what each one represents, its identity, its suffix and its wire word, and both rules with the refusal each produces; the tutorial that declares an entity MUST teach the new naming rule; every page written here MUST have its Russian draft beside it.
- **FR-015**: The changelog MUST be one article about what this work created, in plain words, with the nuances a model author needs — that a technical association may be omitted from the diagram as a separate node while its participants' connection stays, that a relationship which has acquired its own process is no longer an association, and that an existing entity's old name is gone rather than aliased — and without a per-file account of the renames.
- **FR-016**: Every entity row of the interchange graph MUST carry its kind as `properties.entity_kind`, with the word derived from the kind base class's own name (without `Base` and without `Entity`, lower case); the graph's JSON schema MUST admit the property as required, and the drawing MUST NOT change.
- **FR-017**: The closing check run MUST be taken to zero, and the documentation and the changelog MUST follow it, in that order.

### Key Entities

- **Kind base class**: one of the six abstract classes a real entity inherits from. States what an instance represents, derives its suffix and its wire word from its own name, and holds its descendants to that suffix. Carries no fields of its own, except the state one's `code` and `display_name` from #209.
- **Kind**: the role a base class states, the suffix every class descending from it carries, and the word the graph reports. Six kinds, one base class, one suffix and one word each, no overlap.
- **Real entity**: a class descending from exactly one kind base class, named with that kind, usually decorated with `@entity`.
- **Corpus**: the 476 classes that inherit the base directly today, plus the 63 status classes that already carry their kind; the population the rules must hold for.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 classes in the repository inherit the entity base directly except the six kind base classes; before the change there are 476.
- **SC-002**: 476 of 476 classes are reclassified and renamed; 100% of their names end with the kind of their base class; 0 keep a name that ends with another kind's suffix.
- **SC-003**: 0 classes that descend from a kind base class lack that kind's suffix: the 476 reclassified classes carry theirs, the 63 status classes already carry `StateEntity`, and a class a test adds carries its kind like any other. The six kind base classes are the only classes exempt from the rule, and their own names carry their kind anyway.
- **SC-004**: Every refusal in FR-003 to FR-008 has a test that measures it at class creation — the error type and the names it carries included — and each test fails when the rule is broken and no other test does.
- **SC-005**: For 476 of 476 migrated classes the set of model field names, relation field names and lifecycle field names is identical before and after; 0 classes gain or lose a field, a relation or a lifecycle.
- **SC-006**: The model graph of the demo keeps its entity count, its field count, its relation count and its lifecycle count; 0 kind base classes appear as entity nodes.
- **SC-007**: 100% of entity rows carry `properties.entity_kind`, its value is the word derived from the class's kind base class, and the graph's JSON schema validates every row with it present; 0 rows carry a word outside the six.
- **SC-008**: 0 references to an old class name remain in the 68 current-state non-Python files, and 0 remain in Python; the 25 historical files keep theirs.
- **SC-009**: All package test suites and all 43 example scripts pass.
- **SC-010**: Exactly six classes in the repository inherit the entity base directly and override the subclass hook, and for each of them the word derived from its name is one of the six kinds.
- **SC-011**: The full check run is zero, apart from the two accepted remarks.

## Assumptions

- **The class is the only place the kind exists.** No enum, no registry, no attribute, no decorator. A kind base class is a class that inherits the entity base directly and overrides the subclass hook; its suffix and its word come from its own name.
- **The rules are split by their data.** The kind base class owns its name rule, because it owns the suffix; the entity base owns the hierarchy rules — no direct inheritance, one kind — because they are about the base and know no kind.
- **The whole corpus migrates in one change.** The rule fails when the class is created, so a repository whose packages are partly migrated does not import: their test suites, demo and framework alike, go red at collection. The examples are not in that gate — lint, typecheck and pylint read `packages/`, not `examples/` — but a tutorial that no longer runs is a broken deliverable, not a deferred one.
- **The rules and the wire land after the migration.** The refusals and the `entity_kind` row land in the phases that follow the corpus, because a repository with 476 direct inheritors cannot import once the refusal is on. This is the same ordering #209 used for the string form; the delivered branch has one state.
- **The issue's split allowance is not exercised.** It was offered for a large volume in the smaller packages; measured, that volume is 8 classes, and splitting them would leave their suites red for the duration.
- **Names come from meaning, and meaning is reviewed.** The mapping from each of the 476 classes to one of six kinds is a judgement about the domain, made against the base classes' descriptions and the demo's business data. It is written down as a table before the renames, because a wrong kind is invisible in a diff of 476 files.
- **A class without `@entity` stays lawful.** The framework's negative fixtures and the three example scripts that show a declaration mistake depend on it, and the missing decorator remains a build-time error rather than a creation-time one.
- **The rename is a visible change, and that is the point.** Entity labels and node ids in the interchange graph are the class names, so every diagram draws the new names. Nothing stored holds a qualified id, so nothing persisted breaks.
- **Primary-key structure is not checked.** A class docstring describes the identity its kind implies; verifying it needs an identity subsystem that does not exist, and it is out of scope here.
- **A renderer change is not part of this work.** The association kind gives Maxitor a reliable basis for omitting a technical link as a separate node while keeping the connection between its participants; the kind reaches it as `properties.entity_kind`, and the drawing change that uses it is a separate task.
- **History keeps its names.** A changelog entry or an earlier specification that quoted `OrderEntity` stays as written: the old name is gone from the code and from the pages that describe today, not from the record of what was.

## Measured context and deliberate naming

The specification names the six kind base classes, the suffix each one derives and the wire word, because they are the contract a model author writes and a requirement that cannot name the type it introduces cannot be tested. The counts — 476 classes on the base, 539 real classes in the corpus (540 with the state base class), 145 in the examples, 209 in the demo, 68 current-state non-Python files carrying a name — are measured on the branch base, and the plan and tasks use them rather than re-deriving them from the issue's prose. No module path of the migration, no function name and no framework internals appear outside this context section.

Two places where the measurement corrects the issue are recorded rather than smoothed over:

- The issue speaks of reclassifying "every existing `class XxxEntity(BaseEntity)`" and names demo and the framework's fixtures. It does not mention `examples/`, which holds 145 of the 476 — 30 % of the corpus, in 43 scripts with notebooks beside them. They cannot be left behind, although the check run never touches them (`lint` covers `packages/`, `tests/`, `scripts/`; typecheck and pylint cover `packages/`): the examples are the runnable half of the tutorials, so the rule fails the first time a reader runs one.
- The issue offers to move the other packages to a separate task if the volume is large. The measured volume there is 8 classes, so the allowance is not used; the volume that is actually large — demo and examples — is the part the issue keeps in scope.
