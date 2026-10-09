# Feature Specification: Entity specialization — one field, N extension tables, chosen by a classifier

**Feature Branch**: `feature/issue-199-entity-specialization`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/199 — entity specialization: one head field pointing at one of N extension tables, chosen by a classifier"

## Clarifications

### Session 2026-10-09

- Q: How is the field declared, and what does it hold? → A: **A container parameterised by the union, and the codes declared beside it as a `Literal`.** The maintainer settled the shape: the first argument of the field's type names the alternatives, and the marker beside it names the choosing field and the codes, so that a field and its variants never sit in one undifferentiated list. Measured consequences on real entity classes: subscripting the container produces a real class, a narrower parameterisation refuses the other alternatives, and a class outside the union is refused on assignment. The value carries the identifier, the variant and the hydrated row, so a link whose row is not loaded stays expressible. Two earlier designs are dropped: a wrapper value type of its own, and a bare union in the type position, which could not represent an un-loaded row at all.
- Q: How many specialization fields may one head carry? → A: **Several, one per axis.** A head may declare more than one field, each with its own classifier and its own codes. This is the point the maintainer settled directly: "the head may have several axes for extension".
- Q: May an extension participate in more than one specialization relation? → A: **No.** "Each extension has only one head" — one head class, and one partner field for every axis that head declares. A class that appears in the alternative list of two different heads is an error.
- Q: What follows for a head with several axes? → A: The two answers fix each other. An extension belongs to exactly one head and carries a partner field for every axis of it, so every axis of one head names **the same set of extension classes**; the axes differ in classifier and in codes, never in membership. A head whose second axis lists a different set of classes cannot be built: the classes it omits would hold no partner field for that axis, and the classes it adds would hold a partner field no declared axis accounts for.
- Q: Are the alternatives' codes shared between axes or declared per axis? → A: Declared per axis, on both sides, and compared per axis. Two axes of one head are two classifiers with two code vocabularies; the same extension carries one code per axis.
- Q: Is the cardinality of the relation declarable as mandatory? → A: No. Data completeness is a storage and transaction-boundary contract, not a model invariant, so the relation is optional (0..1) and no marker states otherwise.
- Decision carried over from the issue: no `Disjoint()` and no `Complete()` markers — data disjointness cannot be checked without loading the whole set, and completeness of the data is not checkable in the model.
- Decision carried over from the issue: this is a new relation **axis**, not a fourth ownership value. Ownership stays composition / aggregation / association; specialization is classification and identity.
- Decision carried over from the issue: the variant code stands next to the alternative on the head and on the extension alike; neither side is the authority, the match is.
- Decision carried over from the issue: an extension is a `BaseEntity` class reached through its own declaration, never a Python subclass of its head — otherwise Pydantic merges the fields and the head's field is duplicated onto the child.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One head field that points at one of N extension tables (Priority: P1)

A developer modelling events has a head table that holds the date and the event type, and a separate table per event type, each with its own structure. The developer declares the head's field once, naming the extension entities and the code each one is chosen by, and declares the reverse field on every extension. The model then says what the database will hold: one row of the head, and exactly one extension row, selected by the classifier value.

```python
@entity(description="Event", domain=EventsDomain)
class EventEntity(BaseEntity):
    id: str = Field(description="Event id")
    event_date: date = Field(description="When the event happened")
    event_type: str = Field(description="Classifier: which extension table holds the details")

    details: Annotated[
        Specialization[                      # ← one of these, and only these
            CreatedEventEntity | UpdatedEventEntity | DeletedEventEntity | MovedEventEntity | AssignedEventEntity,
        ],
        Classifier(                          # ← what selects, and which codes exist
            field="event_type",
            codes=Literal["created_event", "updated_event", "deleted_event", "moved_event", "assigned_event"],
        ),
        Inverse(field_name="event"),
    ] = Rel(description="Event details: one of the declared extensions, chosen by event_type")


@entity(description="Event created", domain=EventsDomain)
class CreatedEventEntity(BaseEntity):
    id: str = Field(description="Same id as the Event row")

    event: Annotated[
        Generalization[EventEntity],         # ← the way back
        Classifier("event", Literal["created_event"]),   # ← this class's own code
        Inverse(EventEntity, "details"),
    ] = Rel(description="Event this extension belongs to")
```

**Why this priority**: this is the whole value of the feature. Without it the continuation of a head row has no declaration at all: a single target type points at the wrong table, and a union of containers does not fail but silently keeps the first alternative — the model then lies about the database.

**Independent Test**: declare one head with five named extensions and build the model. The head's field must yield five alternative targets with their codes, and one declared code must be reachable per alternative.

**Acceptance Scenarios**:

1. **Given** a head whose field names five extension entities with five distinct codes, **When** the model is built, **Then** the field yields exactly five alternative targets and the machine is created.
2. **Given** the same model, **When** the field is read on an instance, **Then** its value carries the identifier of the related row and which variant it is, and reaching into an un-hydrated variant fails explicitly rather than returning nothing.
3. **Given** a field declared as a union of two relation containers, **When** the model is built, **Then** it does not silently keep the first alternative: it is either refused, or reported as a specialization that must be declared as one.
4. **Given** a head carrying two axes over the same three extension entities, **When** the model is built, **Then** each extension is reachable from both classifiers — `created_event` on one axis and `web` on the other in the same class — and each axis yields its own three codes.

---

### User Story 2 - A broken declaration fails at build, naming the place (Priority: P2)

A developer writes an extension, forgets its partner field, or gives it a code that disagrees with the head's, and the model is built as part of ordinary work. The mistake surfaces at build with an error that names the class, the field and the rule — not later, as a field in the graph that quietly points at nothing.

**Why this priority**: every mistake in this declaration space either loses the edge from the graph or points it at the wrong table. A silent loss is worse than a failure, because nothing in the running system reports it.

**Independent Test**: for each declaration rule, break exactly that rule, build, and confirm the named error appears and no other; restore and confirm the build passes.

**Acceptance Scenarios**:

1. **Given** a head with at least one alternative, **When** an extension in that list carries no partner field, **Then** the build fails naming the extension and the missing field.
2. **Given** the same model, **When** an extension's code differs from the code assigned to it on the head, **Then** the build fails naming both codes and both sides.
3. **Given** the same model, **When** a class outside the head's alternative list declares a partner field pointing at the head's field, **Then** the build fails naming that class.
4. **Given** the same model, **When** the classifier names a field the head does not have, **Then** the build fails naming the classifier and the head.
5. **Given** the same model, **When** a class appears in the alternative lists of two different heads, **Then** the build fails naming both heads.
6. **Given** the same model, **When** an alternative is a Python subclass of the head, **Then** the build fails naming both classes.
7. **Given** a cycle between heads and extensions, **When** the model is built, **Then** the build fails naming the cycle.
8. **Given** each broken model above, **When** the single broken declaration is restored, **Then** the build passes with no other change.

---

### User Story 3 - The ERD and the graph show the variants (Priority: P3)

Whoever reads the ERD sees one row for the head's field, labelled with the classifier and listing the alternatives, and sees the generalization relation from every extension back to the head — instead of N foreign-key rows that suggest N independent links.

**Why this priority**: the diagram is how the model is reviewed by people who do not read the code, and a specialization that looks like N separate links misleads exactly the reader the diagram exists for.

**Independent Test**: build a system with a head and five extensions, read the ERD and the graph payload, and compare the field row and the relation edges with the declared model.

**Acceptance Scenarios**:

1. **Given** a built system with a head and N extensions, **When** the ERD is produced, **Then** the head's field appears as one row naming all N alternatives and the classifier, with no per-alternative duplicated row.
2. **Given** the same system, **When** the graph is read, **Then** each of the N extensions carries a generalization relation to the head, and every declared code is recoverable together with the extension class it selects.
3. **Given** an alternative whose class carries no graph node, **When** the model is built, **Then** the build fails instead of dropping the relation silently.

---

### User Story 4 - A row whose code is not declared is an explicit failure (Priority: P4)

Data arrives whose classifier value is not one of the declared codes. Nothing in the model can prevent that, but the framework must not answer "no relation" for it: the answer is an explicit failure naming the undeclared value.

**Why this priority**: a missing continuation and an undeclared one are different facts about the data. Collapsing them into an absent relation hides a data defect that an operator needs to see.

**Independent Test**: load a head row whose classifier value matches no declared code and confirm the failure names the value; load a row whose value is declared and confirm the variant is the declared one.

**Acceptance Scenarios**:

1. **Given** a declared code set, **When** a value outside it arrives, **Then** the failure names the value and the field, and no empty relation is produced in its place.
2. **Given** a value inside the declared set, **When** the row is hydrated, **Then** the variant is the one declared for that code.
3. **Given** a hydrated variant that does not match the declared alternative for the code, **Then** the failure is immediate rather than carried forward.

---

### Edge Cases

- A specialization field with no alternatives at all: an error, not an empty relation.
- A single alternative: a legal but degenerate specialization, and it must build.
- Two alternatives declared with the same code: an error, because two tables would be indistinguishable by code.
- A code that is empty or whitespace-only: an error.
- A code whose value cannot belong to the classifier field's type: an error at build.
- The classifier naming a relation field, a class-level constant, or a property instead of a scalar field: an error.
- The classifier being the specialization field itself: an error.
- A field that parameterises the container with a class that is not a declared entity: refused at build, because it carries no graph node.
- A field left empty although its classifier field holds a declared code: the field reads as nothing, and the framework substitutes no type for a value it was not given.
- An object of a class outside the parameterised union: refused when the value is assigned.
- A head naming codes in one order and declaring the classes in another: allowed — the check is by membership, so reordering alone never breaks a model.
- A class named by the union whose own reverse declaration states a code the head does not list, and a code the head lists that no class declares: both fail, each naming what is missing.
- One alternative being a subclass of another alternative, or a Python subclass of the head: an error, because "exactly one variant" would then be provably false.
- An extension carrying no partner field, or a partner field whose target is an ancestor of the head rather than the head itself: an error.
- An extension holding a partner field for an axis the head never declared: an error.
- A head with several axes where one axis lists a different set of extension classes than another: an error, because the classes it omits would hold no partner field for that axis while the classes it adds would hold two.
- A head with several axes where an extension declares a partner field for one axis and not for another: an error, since every axis of one head names the same set of classes.
- Two axes of one head carrying the same code for one extension: allowed but pointless — the codes of different axes are separate vocabularies and are never compared with each other.
- A class that appears in the alternative list of two different heads: an error.
- A specialization without a reverse side, and a reverse side without a specialization: both are errors — there is no one-way form of this relation.
- A chain where an extension is itself the head of another specialization: allowed, provided no cycle is created.
- A classifier value present in the data but not declared: an explicit runtime failure, never an empty relation.
- An extension class that is not a declared entity: an error at build, because the relation would otherwise be lost with no node to carry it.
- A link whose row was not loaded: the identifier and the variant stay readable, and the row reads as absent rather than as an invented one.
- A head row whose classifier field is empty or absent: nothing selects a variant, and the framework must not invent one.

## Requirements *(mandatory)*

### Functional Requirements

**The declaration on the head**

- **FR-001**: A head MUST be able to declare one field by parameterising a container with the union of its alternative targets, and to name beside it the classifier field whose value selects among them together with the codes those alternatives answer to. The container's type argument is what the model enforces: a class the union does not list MUST be refused, and a narrower parameterisation MUST refuse the other alternatives. A head MAY carry several such fields, one per axis, each with its own classifier and its own codes.
- **FR-002**: A specialization field MUST declare at least one alternative; a field with no alternatives MUST be refused at build.
- **FR-003**: Every alternative MUST name a declared entity; a class without an entity declaration MUST be refused at build, because it carries no graph node and the relation would be lost silently.
- **FR-004**: The same class MUST NOT be declared twice within one alternative list.
- **FR-005**: The codes within one axis MUST be non-empty and pairwise distinct.
- **FR-006**: Every code MUST be compatible with the type of its axis's classifier field, so that a value the field can hold can select the variant it names.
- **FR-007**: No alternative MAY be a subclass of another alternative, or a Python subclass of the head.
- **FR-008**: Each extension class MUST have exactly one head: a class MUST NOT appear in the alternative lists of two different heads.
- **FR-009**: Every axis of one head MUST name the same set of extension classes, because each extension has exactly one head (FR-008) and carries one partner field per axis of it (FR-012). Two axes of one head differ in classifier and in codes, never in membership.

**The classifier**

- **FR-010**: Every specialization field MUST name its classifier; a field without one MUST be refused at build.
- **FR-011**: The classifier MUST name an existing scalar field of the head — not a relation, not a class-level constant, not a property — and MUST NOT be the specialization field itself.

**The reverse side**

- **FR-012**: Every alternative MUST carry exactly one partner field per axis of its head, and each such field MUST point at the head and at the axis's own field. On the extension the partner field is declared with the marker as it stands; on the head the same marker names **only** the partner field name, because the entities are already named by the field's own type — a second form of an existing declaration, added by this capability.
- **FR-013**: The reverse side MUST be present and MUST NOT be declared absent: the one-way form does not exist for this relation — not on the extension, where it would leave the alternative unnamed, and not on the head, where it would leave the alternatives with no way back.
- **FR-014**: The codes MUST be declared on **both** sides — the whole set beside the head's field, and each class's own code beside that class's reverse declaration — and the build MUST compare them in **both directions**: every class in the union MUST declare exactly one code, every declared code MUST belong to a class in the union, the two sets MUST be equal, and their sizes MUST agree. A class with no code, a code no class declares, a class declaring more than one, and a repeated code MUST each fail the build naming the class and the code. Neither side is the authority: the match is.
- **FR-015**: Mutuality MUST hold: the set of classes declared in one axis's alternative list MUST equal the set of classes whose partner field points at that axis's field.
- **FR-016**: Closure MUST hold: no class outside an axis's alternative list MAY point at that axis's field, and no extension MAY carry a partner field for an axis its head does not declare.
- **FR-017**: The partner field's target MUST be exactly the head class, not an ancestor of it and not a protocol.
- **FR-018**: A head-to-extension cycle MUST be refused at build.

**The shape of the hierarchy**

- **FR-019**: Each extension MUST have exactly one head and one partner field per axis of that head. It MUST NOT reach a second head, and it MUST NOT carry a partner field for an axis its head does not declare (FR-016).
- **FR-020**: The alternatives of one head MUST cover that head exactly: every declared alternative MUST be a variant of that head and of no other, and every class that is a variant of the head MUST be declared in its alternative list.
- **FR-021**: An extension MAY itself be the head of another specialization, provided no cycle results (FR-018).

**The graph, the diagram and the interchange**

- **FR-022**: The model MUST publish, for every alternative, the variant code and the extension class it selects, so that a consumer can tie a code to a table without re-deriving it from a class name.
- **FR-023**: The relation from an extension to its head MUST reach the graph as a generalization relation, directed from the extension to the head, for every declared alternative.
- **FR-024**: The head's specialization field MUST appear in the diagram as one field entry naming all alternatives and the classifier, never as one foreign-key entry per alternative.
- **FR-025**: A model that declares no specialization MUST produce exactly the graph it produces today: this feature adds a relation axis and changes no existing declaration.

**Runtime behaviour**

- **FR-026**: The value of a specialization field MUST carry the identifier of the related row, **which variant** it is, and the hydrated row when one was loaded. The variant MUST be stored rather than derived: with an un-hydrated row the identifier says which row but not which of the N tables holds its continuation. The field therefore has three states — a loaded row, a link whose row is not loaded, and nothing — and reading it MUST return exactly what was assigned, with no conversion and no substituted type.
- **FR-027**: A classifier code arriving from data MUST be declared for its axis; an undeclared code MUST produce an explicit failure naming the value, and MUST NOT be reported as an absent relation. Resolving a code to the class it selects MUST be the caller's own explicit step, against the declared mapping — the framework MUST NOT resolve, guess or coerce a variant on the developer's behalf.
- **FR-028**: A row placed in the container MUST be of a class the type argument lists; any other class MUST be refused when the value is assigned, and MUST NOT be carried forward. The container MUST be immutable after construction.
- **FR-029**: The framework MUST NOT substitute a type for a value it was not given: a field left empty stays empty, a link whose row was not loaded keeps its identifier and variant readable and reports the row as absent rather than inventing one, and an object of another class is refused rather than coerced into one of the alternatives.

**Diagnostics**

- **FR-030**: Every declaration rule above MUST be checked when the model is built, and a violation MUST be reported as a named error identifying the class, the field and the rule; no violation MAY result in a silently dropped or silently redirected relation.

### Key Entities *(include if feature involves data)*

- **Head**: an entity that carries at least one classifier and its specialization field. It may declare several axes; it is a head for exactly the set of extension classes its axes list, and that set is the same for every axis.
- **Extension**: an entity that holds the continuation of a head row, has exactly one head, and carries one partner field per axis of that head. It participates in no second specialization.
- **Axis**: one specialization field on a head, with its own classifier field and its own code vocabulary. Several axes of one head share their membership and differ in classifier and codes.
- **Classifier**: a scalar field of the head whose value selects which extension table holds the continuation of the row. It is mandatory and declared explicitly.
- **Variant code**: the code-like string declared beside an alternative on the head and beside the partner field on the extension; the two must match. It is the only thing that ties a code to an extension, and what a consumer ties to a table.
- **Specialization field**: one axis of the head — the field naming the alternatives, their codes, the classifier and the partner field name. Its value carries an identifier and a variant.
- **Generalization relation**: the edge from an extension to its head, which is where the reverse direction of the relation is read.

### What is deliberately not a model invariant

- **Data completeness** — that every head row has an extension row. This is a storage and transaction-boundary contract, so the relation is optional and no declaration states otherwise.
- **Data disjointness** — that one row does not live in two extension tables. It cannot be checked without loading the whole set, and for a single-valued field "not two variants at once" already follows from the field's own cardinality.
- **Matching the data's codes to the declared ones** — only a storage-level check can enforce this.

### Out of scope

- **Generating storage from the model.** The model states which code selects which extension class; it defines no table, no column and no constraint. Turning the published mapping into a table-level check is a graph consumer's work.
- **Closing the gap between the documented relation rules and the implemented ones.** The ownership matrix, the mandatory reverse side and the mandatory relation description are documented today and not yet enforced; bringing them into code is a predecessor of its own and is not part of this capability.
- **Incomplete and overlapping alternative sets.** Markers that would state "one of these always holds" or "these may overlap" are deliberately not introduced (Clarifications).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A model in which one head declares five extensions builds, and the head's field yields exactly five alternative targets with five codes; a field with zero alternatives fails the build in 100% of attempts.
- **SC-002**: Each of the declaration rules above is covered by a break-and-restore check: the break fails the build with a named error pointing at the offending class and field, and the restore passes with no other change. Zero rules silently pass while broken.
- **SC-003**: In 100% of built models, the set of classes reaching a head through a partner field equals the set of classes the head's axes declare — measured in both directions, so neither an unlisted class nor a missing alternative passes.
- **SC-004**: In 100% of cases where a class joined two heads, where one axis of a head listed a different set of classes than another axis, or where a cycle exists, the build fails naming the classes involved.
- **SC-005**: A model that declares no specialization produces a graph identical to the one the same model produces today, and a model that declares one exercises zero changed behaviour in the existing relation kinds.
- **SC-006**: For a system with one head and five extensions, the diagram shows exactly one field entry for the head's field — naming five alternatives and the classifier — and exactly five generalization relations, one per extension, with zero per-alternative foreign-key entries.
- **SC-007**: For 100% of alternatives, the variant code and the extension class it selects are recoverable from what the model publishes; measured on a model whose class names bear no resemblance to their codes.
- **SC-008**: In 100 runs where a data value falls outside the declared codes, every outcome is an explicit failure naming the value, and zero are reported as an absent relation.
- **SC-009**: In 100% of cases where a hydrated entity does not match the variant declared for its code, the failure is raised at the point of hydration rather than carried forward.

## Assumptions

- The readers of this capability are developers modelling a domain and the consumers of the resulting graph — the diagram, the interchange payload and storage generation — not end customers.
- Specialization is a separate relation axis beside ownership, not a fourth ownership value: ownership stays composition / aggregation / association, and the two are never mixed in one relation.
- The variant code is a plain code-like string, declared as a member of a `Literal`. The classifier field stays an ordinary field of the head with whatever type it already has.
- The reverse direction is where the relation is read as generalization; the direction of the edge follows the semantics of the relation, not the side that declares the field.
- An extension is an ordinary entity in every other respect: it may carry its own fields, relations and lifecycle, and it may itself be the head of another specialization.
- An extension is a separate entity reached through its declaration, never a Python subclass of its head: subclassing would merge the head's fields into the child.
- Data completeness and data disjointness are storage and transaction-boundary contracts, which is why no marker states either of them and why the relation is optional.
- What a storage generator does with the published code-to-extension mapping — a table-level check, a constraint, nothing at all — is outside this capability; the mapping itself is published so that a consumer can act on it.
- Entities stay storage-agnostic: this capability defines no table, no column and no constraint of its own.
- Existing relations keep their behaviour and their declarations: what this feature adds is a new axis and its checks, not a change to composition, aggregation or association.
- The default of the relation is optional (0..1): nothing in the model promises that a head row has an extension row.
- A specialization field holds a container of its own kind, and is **not** a related object for process mining: the head row is the object, and the walk that materializes related objects keeps ignoring this field. The framework's other relation containers are unchanged by it.
- The project constitution applies: English in commits, in git and in code; module headers; one-line docstrings; documentation written with the change; and the full check run taken to zero as the last step of the work.
