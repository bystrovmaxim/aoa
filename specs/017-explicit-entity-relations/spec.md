# Feature Specification: An entity-typed field is stated explicitly, a shared dictionary member is protected, and a relation's description is metadata

**Feature Branch**: `feature/issue-249-explicit-relations-and-dictionary-safety`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/249 — Make entity relations explicit and finish dictionary value safety, schemas and display. Six bounded parts: make entity-valued fields explicit, remove the redundant field name from `Classifier`, simplify dictionary cards, enforce dictionary immutability after custom validation, repair serialization schemas for `Enum` properties, and keep relation descriptions out of runtime defaults. Depends on #244; blocks 1–3 are proposed behaviour changes, blocks 4–5 repair confirmed defects, block 6 replaces an unsafe published declaration form. Tracked as six work items, not as commits."

## Context: what is true today, measured on 2026-10-23 at `2e70a30d`

- **An entity-typed field silently becomes a scalar.** A model declaring `showcase: ShowcaseCoreEntity = Field(description=...)` builds, the graph carries a `field` row named `showcase`, and no relation edge is drawn. Measured on the merged baseline: the model builds and `model_fields` holds `['id', 'showcase']`; the graph shows an ordinary column and an empty relation set. The type already says the field is a relation, so the declaration is accepted while meaning nothing.
- **`Classifier` restates the attribute it sits on.** `Classifier(field="user_event", variant=…)` names the very field of the annotation, and `entity_specialization_validator.py` compares the string with the derived name, so a typo is a refusal. The parameter predates #241, when the marker sat on a different field; after #241 moved the marker onto the reverse field, the value can only repeat what the annotation already says. Measured at the baseline: **165 `Classifier(field=…)` occurrences in 53 files** under `packages/`, `examples/` and `docs/`, and 112 matching lines in 39 notebooks (the issue's own baseline was 162 occurrences in 51 files plus 110 notebook cells; refresh both counts during implementation).
- **The dictionary card prints storage identity.** The enum kind supplies the `code` and `display_name` field rows, and every value row prints its code as the left cell, so the card shows `food-delivery | Prepared food delivery` plus a `code str` row above.
- **A dictionary member can be mutated after a custom validator replaces it with a list.** The declaration hook inspects the annotation only. Reproduced on `2e70a30d` with a `mode="after"` field validator returning `list(labels)`:

  ```text
  list ['original', 'changed']
  ```

  Attribute freezing does not protect a list's contents, and every consumer reads the same member through `by_code("item")`.
- **A validator can also change the shape silently.** Reproduced on `2e70a30d`: a `tuple[str, ...]` property whose after-validator returns a comma-joined string exports `'a'` with only a Pydantic serializer warning, while the published schema describes an array.
- **Serialization schemas of `Enum` properties lose their definitions.** Reproduced on `2e70a30d`: `to_reference()` succeeds with `{'grade': 'a'}`, while `model_json_schema(mode="serialization")` raises `KeyError '#/$defs/Grade'` because the property fragments are copied without the definitions they reference.
- **A relation's description is placed in the default slot.** Reproduced on `2e70a30d`:

  ```text
  Rel required: False
  Field required: True
  Omitted value type: Rel
  ```

  A `Rel(description=…)` default makes the field omittable and leaves a marker object in the entity, unvalidated. The corpus writes **262 `= Rel(description=…)` declarations** (issue baseline; refresh during implementation), two `_field_description_hint()` implementations read either a `Rel` default or `FieldInfo.description`, and the second path does not require nonblank text.
- **The schema hook and the description fallbacks are the code sites.** `BaseEnumEntity._emitted_reference_schema()` copies property fragments and drops their definitions; `entity_relation_intent_resolver.py` and `entity_specialization_intent_resolver.py` each carry a `_field_description_hint()`; `list_entities_action.py` builds the enum card's field list; `buildDotSource.ts` prints the code cell.
- **The baseline is `2e70a30d`.** All four confirmed defects (mutable member, exported-shape mismatch, dropped definitions, description object in the default slot) were reproduced at that commit before this specification was written.

## Clarifications

### Session 2026-10-23 — decisions carried from issue #249

- **Six blocks, six work items.** The blocks are separately testable and separately implemented; keeping them in one issue provides one final documented contract, not one commit.
- **A bare structural-entity field is refused, and two equally legal forms replace it.** A relation wrapper, or the explicit embedded-value marker; a state entity has only the `Lifecycle[...]` form. The refusal names the owner, the field and the resolved entity type, and shows the forms that apply.
- **The refusal applies to Core, Assoc, Detail and Spec, and a state entity has no field form at all.** A `...StateEntity` type may be neither a relation nor a plain field: a state is described only by a `Lifecycle[...]` subclass carried on a field, as the corpus does today (`lifecycle: ClinicalSupplyLifecycle = Field(description="…")`). The refusal for a state-typed field therefore names that form, not the relation wrappers and not the embedded-value marker, and the marker does not apply to states. There is no authored bare state-entity field in the corpus to migrate. A dictionary reference (a `BaseEnumEntity` descendant, optionally `Optional`) stays a bare type, and a `BaseSchema` subclass stays out of the rule.
- **The embedded-value marker is `NoRelation("reason")`.** Positional reason, required and nonblank, on the same entity type of kind Core, Assoc, Detail or Spec. It is not `NoGraphEdge()`: hiding an existing relation edge and declaring that a field has no model relation are different meanings. It cannot be combined with a relation wrapper, and it does not infer storage, create a foreign key, or disable nested value validation.
- **The check has one boundary.** The rule is enforced during graph construction, before a usable graph is published, on the annotations Pydantic has already resolved. A class outside the graph is not judged. Unresolved names are not evidence of a scalar field, and no annotation string is evaluated with ad hoc `eval` nor a relation inferred from a name.
- **`Classifier` loses `field` and keeps every other check.** Head/alternative, inverse, dictionary-membership and variant/data consistency checks stay, including the head's comparison against the attribute name.
- **The dictionary card prints the label and the value's own properties, never the code; the code stays in the payload, in the graph, and in an SVG tooltip.** The two kind-supplied field rows (`code`, `display_name`) leave the payload's field list for the enum kind; the code remains in `properties.values` and as a `TOOLTIP` on the value row. Both decisions are presentation-only.
- **A dictionary member is checked after user validation, before it is published.** The annotation restriction stays, and the completed member is verified against the same immutable set; a mutable or unsupported runtime value is refused with the dictionary, the member, the property path and the actual type.
- **Schema definitions are preserved, not flattened.** References and definitions travel through Pydantic's schema generation; the fix is not limited to the `Enum` name and does not disable `Enum` support.
- **A relation's description is `FieldInfo.description` only.** No `Rel` object in a default slot or in `Annotated` metadata; no default other than an explicitly permitted `None`; no `default_factory`. The description fallbacks leave both intent resolvers.
- **`Rel` is removed in this change.** The symbol leaves the public surface together with its description-carrier role; a declaration still importing it fails immediately when the module is imported, which is the most direct statement that the form is gone. No deprecation window and no compatibility shim, and the field contract below is what guarantees that no object can occupy a relation slot even if a declaration defines a similarly shaped marker of its own.
- **This is a breaking declaration migration, not a warning-only deprecation.** Nullability and optional input stay separate choices, and each nullable field's omission semantics is decided deliberately rather than mechanically given `None`.

### Session 2026-10-23 — clarifications

- Q: Does requiring a relation forbid reading an entity partially, when every field except the primary key may or may not be read? → A: No. Requiredness binds the validating constructor and `build()` only; `partial()` keeps using `model_construct()` without required-field checks, and reading a field it did not receive raises the existing not-loaded error. The declaration describes what a complete entity is, not what every caller must read.
- Q: Which of the seven nullable relations become omittable after the migration? → A: Each one is decided by its actual full-construction call sites: where the code that builds the entity omits the field today, the field takes `default=None`; where it is always supplied, the field stays required but nullable.
- Q: Which values of an `Enum` property are supported by a dictionary member? → A: The enum member's own value obeys the same recursive immutable rule as any other property. Scalars, `Decimal`, dates, `UUID`, booleans and tuples of those are accepted; a list, mapping, set or model instance used as an enum value is refused at declaration, naming the dictionary, the member, the property path, the enum class and the value type.
- Q: What happens when an after-validator returns an immutable value of a different type than the annotation declares? → A: The declaration is refused: the runtime value must both match the declared annotation and be immutable, and the error names the property, the declared type and the actual type. Accepting it would publish a member whose export contradicts its own schema.
- Q: Where may the reason of an embedded-value marker be visible besides the declaration? → A: Nowhere. The graph, the payload and the card are unchanged, and the marker documents the absence of a relation in the source only.
- Q: Which field forms are supported for a structural entity, besides the exact type and a relation container? → A: None. A collection of a structural entity (`list`, `dict`, `set`, `tuple`) and a bare `X | None` are refused with a diagnostic naming the relation containers and the embedded-value marker, because treating them as relations would mean inferring intent from structure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A field whose type is an entity is never silently a scalar (Priority: P1)

A model author declares a field whose type is another entity. Either the field is a relation, and the annotation says so, or the framework refuses the model before a graph can be published, and the message shows the ways to say what was meant — two for a structural entity, one for a state. A field that is an ordinary scalar — a string, a number, a dictionary reference, a lifecycle — is declared exactly as it is today.

**Why this priority**: This is the defect the issue opened with: a declaration is accepted, a column appears, and no relation exists. A graph that quietly misdescribes the model is worse than a build that stops.

**Independent Test**: Declare an isolated model with one entity-typed field in the bare form; confirm the build is refused and the message names the owner, the field, the entity type and both legal forms. Repeat with a relation wrapper and with the embedded-value marker; confirm both build and that the graph shows the edge in the first case and no edge in the second.

**Acceptance Scenarios**:

1. **Given** a model whose field is annotated with a structural entity type and no marker, **When** the model graph is built, **Then** the build is refused and the message names the owner, the field, the resolved entity type, and both supported declaration forms.
2. **Given** the same field declared as a relation wrapper with its marker, **When** the model graph is built, **Then** a relation edge exists, the field appears as a foreign-key row rather than as a plain column, and the card draws the edge to the target entity.
3. **Given** the same field declared as an embedded value with a reason, **When** the model graph is built, **Then** the field remains an ordinary column, no relation edge is created, and the reason is discoverable from the declaration.
4. **Given** a field of a dictionary type, a `Lifecycle[...]` field, and ordinary scalar fields, **When** the model graph is built, **Then** every one of them is accepted exactly as today.
5. **Given** a model whose entity-typed field is inherited or carries a forward reference, **When** the model graph is built, **Then** the same rule applies after resolution, and an unsupported form produces an explicit diagnostic instead of bypassing the check.
6. **Given** a field whose type is a state entity, **When** the model graph is built, **Then** it is refused with a message naming the `Lifecycle[...]` form as the only way to describe a state, and neither a relation wrapper nor the embedded-value marker is offered for it.

---

### User Story 2 - A shared dictionary member cannot be changed after custom validation (Priority: P1)

A model author adds an after-validator to a dictionary property. Whatever the validator returns is checked before the member joins the catalogue: a mutable value is refused at declaration with a precise error, and a valid immutable result works as before. No consumer can reach a member whose contents are mutable, and editing an exported copy never changes the declared tuple.

**Why this priority**: A dictionary member is shared data every consumer reads through `by_code()`. A member whose list can be appended to after declaration changes behaviour everywhere at once; it is a correctness defect in the merged baseline.

**Independent Test**: Run the confirmed reproducer: a `tuple[str, ...]` property whose after-validator returns a list. Confirm the class creation fails with an error naming the dictionary, the member, the property path and `list`, and that neither `members` nor `by_code("item")` exposes the member. Then confirm a validator returning a valid tuple is accepted, that a state type with a list-valued status is untouched, and that editing an exported array leaves the declared tuple and a later export unchanged.

**Acceptance Scenarios**:

1. **Given** a dictionary whose after-validator replaces a declared tuple with a list, **When** the class is created, **Then** it is refused with an error naming the dictionary, the member, the property path and the actual type, and no invalid member becomes reachable through `members` or `by_code()`.
2. **Given** a model-level after-validator that mutates a nested value inside a tuple, **When** the class is created, **Then** the class is refused at the nested position, not only at the top level.
3. **Given** an `Enum` property whose value is itself mutable, **When** the class is created, **Then** the member is refused on the same rule, because accepting the annotation alone does not establish immutability.
4. **Given** a validator that returns a valid immutable value, **When** the class is created, **Then** the member is published and read exactly as before, inherited properties included.
5. **Given** an exported array of a member's property, **When** a consumer edits it, **Then** neither the declared tuple nor a later export changes.
6. **Given** the framework silently freezes a list into a tuple instead of refusing it, **When** the targeted regression test runs, **Then** the test fails, because silently changing a value is not the contract.
7. **Given** an after-validator that returns an immutable value of a different type than the property declares, **When** the class is created, **Then** the member is refused with the declared and the actual type named.
8. **Given** a state type whose status declares a list-valued property, **When** the class is created, **Then** it is published as it is today, because the rule binds dictionary members only.

---

### User Story 3 - A dictionary's serialization schema is self-contained (Priority: P2)

A consumer asks a dictionary — or a model containing one — for its serialization schema and gets a valid document: every reference resolves, an enum property is described by the shape the serializer emits, and the required list matches what is actually emitted. The input contract is untouched.

**Why this priority**: Construction and export already succeed while the schema path raises; a schema that cannot be generated blocks every consumer that generates clients or validates payloads, and it is a confirmed defect in the merged baseline.

**Independent Test**: Generate the serialization schema of a dictionary with an `Enum` property; validate the real JSON export against it; check that a disallowed enum value fails validation and that every local reference resolves. Repeat for a direct, optional and tuple-contained `Enum`, a dictionary inside a containing model, two definitions sharing a short class name, and a property with a custom serializer whose output type differs from its enum value.

**Acceptance Scenarios**:

1. **Given** a dictionary with an `Enum` property, **When** its serialization schema is generated, **Then** the document is produced without error and every local reference has a definition.
2. **Given** the real JSON export of that dictionary, **When** it is validated against the serialization schema, **Then** it validates, and a disallowed enum value is refused by the same schema.
3. **Given** a property whose custom serializer emits a different type from its enum value, **When** the schema is generated, **Then** the schema describes the emitted result, not the enum.
4. **Given** a field that is emitted with `null`, **When** the required list is read, **Then** the key is required but nullable; an intentionally excluded field is not required.
5. **Given** a code-only reference, **When** it is validated against the input schema, **Then** it still validates and resolves to the declared value, and the input and output contracts remain separate.

---

### User Story 4 - A relation's description is metadata, never a runtime value (Priority: P2)

A model author documents a relation with `Field(description=…)`. The field's requiredness follows from its annotation and its explicit default, not from a description object: omitting a required relation is a validation error, omitting an explicitly optional one yields `None`, and no entity ever holds a description object in a relation slot. Descriptions reach the graph's edges unchanged.

**Why this priority**: The published form puts a description object in the field's default slot, so the field becomes omittable and an instance carries an object that was never validated. The corpus uses the form 262 times, and the change is a breaking declaration migration, so it must be planned as one.

**Independent Test**: Run the confirmed reproducer in its migrated form and confirm the omitted required relation is now a validation error, while the same field supplied explicitly validates; then exercise the four rows of the contract table independently, including hydration through `build()`. Refuse a prebuilt relation default and a factory, confirming the factory is not invoked. Supply a description through both supported `Field` syntaxes and confirm both the relation edge and the specialization edge carry it. Repeat the default and description checks for a relation field inherited from a base class and for one named through a forward reference.

**Acceptance Scenarios**:

1. **Given** a required relation declaring no default, **When** the entity is built without it, **Then** a missing-field error is raised; supplying `None` is also refused.
2. **Given** a nullable relation declaring no default, **When** the entity is built without it, **Then** a missing-field error is raised; supplying `None` is accepted.
3. **Given** a nullable relation declaring `default=None`, **When** the entity is built without it, **Then** the field is `None`.
4. **Given** a non-nullable relation declaring `default=None`, **When** the class is created, **Then** the declaration is refused.
5. **Given** a declaration that still imports and uses `Rel`, **When** its module is imported, **Then** it fails on the undefined name, because the symbol no longer exists.
6. **Given** a relation field whose default is any object other than an explicitly permitted `None`, **When** the model is validated, **Then** it is refused with a message naming the owner and the field, so no marker object can occupy a relation slot.
7. **Given** a relation field declaring a `default_factory`, **When** the model is validated, **Then** it is refused, and the factory is never executed.
8. **Given** a relation whose description is missing, empty or whitespace-only — including one whose edge is hidden, **When** the model is validated, **Then** it is refused.
9. **Given** hydration through `build()` for a required relation and for an omittable nullable one, **When** each is hydrated without the field, **Then** the outcomes match the rows above and no non-relation default appears in any relation slot.

---

### User Story 5 - A classifier names its variant and nothing else (Priority: P3)

A model author writes `Classifier(variant=…)` on a specialization's reverse field. The pair is carried by the container and the attribute name; the head's inverse check still compares against that attribute name; every other specialization check is unchanged. Passing the removed argument is refused rather than ignored.

**Why this priority**: The argument can only repeat the attribute name, so a value that can never add information is a place to make a mistake. It is small, bounded and independent of the other stories.

**Independent Test**: Migrate one specialization, pass a wrong `field=` value and confirm it is refused as an unexpected argument; then break each remaining check in turn — head/alternative, inverse, dictionary membership, variant/data consistency — and confirm each still refuses.

**Acceptance Scenarios**:

1. **Given** a specialization whose reverse field carries `Classifier(variant=…)` with no field name, **When** the model graph is built, **Then** the specialization group is identical to the one declared with the removed argument.
2. **Given** a declaration still passing `field="…"`, **When** the class is created, **Then** it is refused as an unsupported argument naming the marker.
3. **Given** a head whose reverse field name disagrees with the extension's attribute, **When** the model graph is built, **Then** the existing inverse check still refuses it.
4. **Given** an extension whose variant does not match the head's dictionary membership, **When** the model graph is built, **Then** the existing dictionary and consistency checks still refuse it.

---

### User Story 6 - A dictionary card shows labels, not storage codes (Priority: P3)

A reader of the ERD sees a dictionary card made of labels: no `code` field row, no `display_name` field row, and no code cell beside each value. The label identifies the value, the value's own properties appear underneath, and the code is available on hover and in the payload — never printed.

**Why this priority**: It is a display defect with a bounded blast radius, and it deliberately changes the card contract introduced by #244, so it ships after the model-side blocks settle.

**Independent Test**: Produce the server payload for a dictionary, validate it against the payload schema, render the DOT source and the SVG, and check the printed text, the tooltip and the payload separately. Confirm the graph JSON still carries the code and the label.

**Acceptance Scenarios**:

1. **Given** a dictionary with three values carrying properties, **When** the card is rendered, **Then** each value row prints its label and its properties, and no value row prints a code.
2. **Given** the same dictionary, **When** the payload is inspected, **Then** the enum kind's field list no longer contains `code` or `display_name`, the graph JSON and its schema still carry both, and each value's code is present in `properties.values`.
3. **Given** the same dictionary in the SVG, **When** a value row is hovered, **Then** its code is shown as a tooltip.
4. **Given** a dictionary value whose label contains `<`, `>` and `&`, **When** the card is rendered, **Then** the text is escaped and the SVG remains valid.
5. **Given** a non-dictionary entity, **When** the card is rendered, **Then** its field rows are unchanged.
6. **Given** a graph saved before this change, whose enum nodes still carry `code` and `display_name` field rows, **When** the card is rendered, **Then** it renders without a rebuild, neither row is printed, and nothing fails on their presence.

### Edge Cases

- An entity-typed field declared as a collection or as a bare `X | None`: refused, and the diagnostic names the relation containers and the embedded-value marker.
- An entity-typed field carried by an inherited base or a forward reference: the rule applies to the resolved type, and an unsupported form produces an explicit diagnostic rather than bypassing the check.
- An optional embedded value written as `Annotated[X, NoRelation("reason")] | None`: accepted, because the marker states the intent the bare form lacks.
- An entity-typed field whose forward reference never resolves: the build fails on the unresolved name, and the failure is not reported as "scalar field".
- The embedded-value marker with a blank reason, combined with a relation wrapper, or carrying a reason but no entity type: each is refused at declaration.
- A field whose type is a state entity, written bare, inside a relation wrapper, or with the embedded-value marker: each is refused, and the message names the `Lifecycle[...]` form.
- A dictionary reference written with the embedded-value marker, or a `Lifecycle[...]` field: both are ordinary declarations, and the marker is redundant there rather than silently accepted.
- A dictionary member whose runtime value is a tuple containing a dictionary, a set, or a model instance: refused, and the error names the property path and the actual type.
- A member's property is an `Enum` whose declared value is a list or a mapping: refused on the same rule, not accepted because the annotation is an `Enum`.
- A member's after-validator returns the same value, an equal tuple, or a new valid tuple: accepted, and the catalogue keeps one published member identified by its code.
- A member's after-validator returns an immutable value of another type — a comma-joined string for a declared `tuple[str, ...]`: refused, naming the declared and the actual type, instead of exporting a shape the schema does not describe.
- A serialization schema is generated twice for the same dictionary and once inside a containing model: each result is self-contained, and two definitions sharing a short class name do not collide.
- A dictionary declares no `Enum` property, or declares no properties at all: the schema path is unchanged.
- A relation field is declared with both the inner and the outer `Field` description: the merged `FieldInfo` applies, and the description on the edge matches what Pydantic reports.
- A relation field's edge is hidden by `NoGraphEdge()`: the hidden edge still obeys the default and description rules, and no edge is published.
- A relation field's type is a forward reference: the rules are checked after resolution, so a class body that names a not-yet-defined type still executes.
- A relation field is inherited from a base class or declared only through an annotation on a resolved forward reference: the default and description rules apply to it exactly as to a field declared on the class itself.
- A module still imports `Rel`: the import fails immediately, before any class is created.
- A relation is hydrated with a `None` the annotation does not permit: refused by validation with the field's name.
- A relation is omitted from a partial instance: construction succeeds, the field is reported as not loaded on access, and no required-field check runs.
- A relation field is read through `build()` with the field absent: the declared default rule applies, and a required relation is refused.
- A legacy graph saved before the display change still carries the enum's `code` and `display_name` fields: the card neither prints them nor fails on their presence.
- A dictionary card and a non-dictionary card are rendered in one diagram: only the dictionary's rows change.

## Requirements *(mandatory)*

### Functional Requirements

**An entity-typed field is declared explicitly**

- **FR-001**: A field whose resolved type is a structural entity of kind Core, Assoc, Detail, Spec or State MUST NOT be built as a scalar column; the model MUST be refused before a usable graph is published.
- **FR-002**: The refusal MUST name the owner, the field and the resolved entity type, and MUST show both supported declaration forms; for a state entity it MUST show the single `Lifecycle[...]` form instead.
- **FR-003**: Exactly two forms satisfy the rule for Core, Assoc, Detail and Spec: a relation wrapper of the existing eight containers (`AssociationOne`/`AssociationMany`, `CompositeOne`/`CompositeMany`, `AggregateOne`/`AggregateMany`, `Specialization`, `Generalization`), or the explicit embedded-value marker `NoRelation("reason")` on the same entity type. Either form MAY be written with `| None` to make the relation or the embedded value optional. A collection of a structural entity (`list`, `dict`, `set`, `tuple`) MUST be refused with a diagnostic naming the relation containers, because no form infers a relation from a container. A state entity satisfies neither form: its only form is a `Lifecycle[...]` subclass carried on a field, and the refusal for a state-typed field MUST name that form.
- **FR-004**: The embedded-value marker MUST require a nonblank reason, MUST be accepted only on a structural entity of kind Core, Assoc, Detail or Spec, MUST NOT be combinable with a relation wrapper or unrelated relation markers, MUST NOT infer storage, create a foreign key or disable nested value validation, MUST NOT change the graph, the payload or the card, and MUST be distinguishable from `NoGraphEdge()`, which hides an edge of an existing relation.
- **FR-005**: The check MUST run at one boundary — during graph construction, before a usable graph is published — on the annotations Pydantic has already resolved, and it MUST see inherited fields, forward references, unions and containers that hold structural entities and refuse each unsupported form with an explicit diagnostic. A class outside the graph MUST NOT be judged. No annotation string may be evaluated with ad hoc `eval`, and no relation may be inferred from a field's name.
- **FR-006**: A field of a dictionary type (a `BaseEnumEntity` descendant, optionally `Optional`), a `Lifecycle[...]` field, a `BaseSchema` subclass and every ordinary scalar field MUST be accepted exactly as today.
- **FR-007**: The affected corpus MUST be re-measured during implementation: the issue baseline reported 0 bare entity-typed fields among 2,793 entity fields, 730 of them inside relation containers. The measurement is a baseline, not a permanent guarantee.

**A shared dictionary member is protected after validation**

- **FR-008**: The existing declaration-time annotation restriction MUST stay, and the completed declared member MUST additionally be verified after user validation and before it is published in the catalogue.
- **FR-009**: Mutable or unsupported runtime contents MUST be refused with an error naming the dictionary, the member, the property path and the actual type. A member whose runtime value does not match its declared annotation MUST be refused on the same boundary, with the declared and the actual type named, even when the value is immutable.
- **FR-010**: The verification MUST be recursive within a member's properties and MUST cover nested tuples and `Enum` values. Accepting an `Enum` annotation MUST NOT be treated as establishing that its value is immutable: the member's own value MUST satisfy the same immutable set recursively, and an enum whose value is a list, mapping, set or model instance MUST be refused at declaration with the enum class and the value type named.
- **FR-011**: The framework MUST NOT silently freeze a list into a tuple, coerce the value, or change the field's declared type; a validator returning a valid immutable value MUST continue to work.
- **FR-012**: An invalid member MUST NOT be reachable through `members`, `codes()` or `by_code()`, and the rule MUST bind dictionary members only — `BaseStateEntity` is not restricted by this change.
- **FR-013**: A JSON export MUST remain independent of the declared data: editing an exported array MUST NOT change the declared tuple or a later export.
- **FR-014**: Reintroducing annotation-only checking MUST make the targeted regression test fail.

**Serialization schemas preserve definitions**

- **FR-015**: The serialization schema of a dictionary MUST be valid and self-contained for every supported property, both when it is generated on the dictionary and when the dictionary is embedded in a containing model.
- **FR-016**: References and definitions MUST be preserved through Pydantic's schema-generation mechanism; the fix MUST NOT be limited to one `Enum` name, MUST NOT flatten properties into an untyped object, and MUST NOT disable `Enum` support. Field serializers MUST still determine the emitted property shape.
- **FR-017**: The nested `properties.required` list MUST agree with the emitted form: a field emitted with `null` is present and required but nullable, and requiredness MUST be derived from actual serialization behaviour, including intentionally excluded fields, rather than marking every Python field required.
- **FR-018**: The actual JSON export MUST validate against the generated schema; a disallowed enum value MUST fail that validation; every local reference MUST resolve.
- **FR-019**: The input schema MUST keep accepting a code-only reference, and this fix MUST NOT merge the input and output contracts.
- **FR-020**: Tests MUST cover a direct `Enum` property, optional and tuple-contained `Enum`s, a dictionary field inside a containing model, two definitions with the same short class name, and a property whose custom serializer emits a type different from its enum value.
- **FR-021**: Reintroducing the dropped definitions MUST make the targeted regression test fail.

**A relation's description is metadata**

- **FR-022**: A relation field MUST carry a runtime relation value supplied by its caller, or an explicitly declared absence; its description MUST belong to `FieldInfo.description` and never to an object in the default slot or in `Annotated` metadata.
- **FR-023**: The default contract MUST be: no default, or `None` only when the resolved annotation permits it. When a complete entity is constructed — through the validating constructor or `build()` — a required relation fails on omitted input and on explicit `None`; a nullable relation without a default fails on omitted input and accepts `None`; a nullable relation with `default=None` yields `None`; a non-nullable relation with `default=None` MUST be refused at declaration. A partial instance is a separate path: it MUST remain constructible from any subset of non-key fields without these checks and MUST keep reporting an unloaded field on access.
- **FR-024**: Every other default MUST be refused, including a prebuilt relation container and any description-shaped object; `default_factory` MUST be refused on relation fields even when it would return `None`, and the factory MUST NOT be executed to inspect its result.
- **FR-025**: A relation's description MUST be a nonblank string, and the refusal MUST name the owner and the field and show the `Field(description=…)` replacement.
- **FR-026**: The rules MUST apply to all eight containers, to inherited fields, and to forward references after resolution, and MUST hold when `NoGraphEdge()` hides a relation's edge.
- **FR-027**: The relation and specialization intent resolvers MUST use one description rule that reads `FieldInfo.description` only; the two `Rel`-default fallback branches MUST be removed, and the marker and container docstrings and the claim that both ends must carry `Rel` MUST be corrected.
- **FR-028**: A single `Field` inside `Annotated` MUST be supported under the same description and default rules, because Pydantic consumes it into `FieldInfo`; both supported syntaxes MUST produce the same canonical `FieldInfo`, and the merge precedence MUST be documented rather than described as the inner declaration being ignored.
- **FR-029**: The declaration migration MUST cover declarations, hydration callers, tests, documentation and notebooks together, and each nullable field's omission semantics MUST be decided deliberately rather than mechanically: a nullable relation is given `default=None` only where the code that builds a complete entity omits it today, and stays required but nullable where the field is always supplied.
- **FR-030**: Description text, relation targets, inverse matching, classifier mappings and graph edge semantics MUST remain unchanged; the migration changes field defaults and missing-input behaviour and is not a spelling replacement.
- **FR-031**: The `Rel` symbol and its role as a description carrier MUST be removed from the public surface in this change, with no deprecation window and no compatibility path; a declaration still importing it MUST fail when its module is imported.
- **FR-032**: A successfully validated entity or hydration result MUST NOT contain any description object in a relation slot, and enabling a validation mode alone MUST NOT be treated as a substitute for these declaration checks.

**`Classifier` states only the variant**

- **FR-033**: `Classifier` MUST take the variant and no field name; the pair MUST be carried by the container and the attribute name, and the head's inverse check MUST still compare against that attribute name.
- **FR-034**: Only the check for the removed `Classifier.field` MAY be deleted; head/alternative, inverse, dictionary-membership and variant/data consistency checks MUST be retained.
- **FR-035**: A declaration still passing the removed argument MUST be refused with a message that names the marker, instead of being silently ignored.
- **FR-036**: Every in-scope occurrence MUST migrate, including documentation, script and notebook examples; the baseline measured at `2e70a30d` is 165 occurrences in 53 files plus 112 notebook matches, and it MUST be refreshed again at the start of the migration.

**A dictionary card shows labels**

- **FR-037**: For the enum kind, the card payload MUST omit `code` and `display_name` from its field list; the graph document and its schema MUST keep both.
- **FR-038**: The value row MUST print the label and the value's own properties, MUST NOT print the code, and MUST expose the code as a tooltip on the row; the code MUST remain in the payload's `properties.values`.
- **FR-039**: Rendering MUST remain domain-agnostic — no dictionary name, kind name or fixed field list in the renderer — and escaping MUST be preserved.
- **FR-040**: A non-dictionary entity's rows MUST be unchanged, and a graph saved before the change MUST render without a rebuild.
- **FR-041**: The card's payload check, the payload test and the dictionary-card contract MUST be updated to the final behaviour, and the contract introduced by #244 MUST be reconciled rather than contradicted.

**Verification and delivery**

- **FR-042**: Each corrected defect MUST be reintroduced in isolation, its targeted test confirmed to fail while an unrelated control test in the same run passes, and the implementation restored.
- **FR-043**: Each block MUST keep separate implementation and migration steps and separate regression evidence, even though all six ship in one issue.
- **FR-044**: The repository check run MUST be taken to zero, and the two accepted remarks — the build's chunk-size advisory and the pending-deprecation warning — MUST NOT be acted on.
- **FR-045**: English documentation, script and notebook examples MUST be updated in the same change, and each affected package's changelog MUST gain a concise article; a documented limitation MUST be replaced only once its regression check passes. No Russian drafts are created for these pages; the task list keeps its own `tasks.ru_draft.md`, as it did for #244.

### Key Entities

- **Structural entity**: an entity of kind Core, Assoc, Detail, Spec or State; a field whose resolved type is one of the first four is a relation by nature, and a state entity is described only through a `Lifecycle[...]` field.
- **Relation container**: the existing wrapper of a relation field (`AssociationOne`/`Many`, `CompositeOne`/`Many`, `AggregateOne`/`Many`, `Specialization`, `Generalization`); it carries cardinality and ownership.
- **Embedded-value marker**: `NoRelation("reason")` — the declaration that a structural entity is stored as a value of the owning model, with no model relation and no foreign key.
- **Field description**: the human text on a field, carried by `FieldInfo.description` and read once by every consumer, including the graph's edges.
- **Dictionary member**: a declared and validated value shared by every consumer, identified by its code and published in the catalogue.
- **Serialization schema**: the document describing what the framework emits for a dictionary field, self-contained in its definitions and consistent with the actual export.
- **Card field row and value row**: the two shapes on an ERD dictionary card — a field name with its type, and a value's label with the value's own properties.
- **Classifier**: the marker that pairs a specialization's reverse field with the head's variant; it names the variant and nothing else.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 fields with a bare structural-entity type remain in `packages/` and `examples/` after the change; the baseline reported 0, and the count measured at the start of the phase is recorded in the plan.
- **SC-002**: 100 % of the six refusal classes — bare entity, bare `X | None`, a collection of an entity, a state-typed field, a blank marker reason and a container combined with the marker — produce a message naming the owner and the field; a structural-entity case additionally names the resolved type and both legal forms, and a state-entity case names the `Lifecycle[...]` form.
- **SC-003**: Each of the four confirmed behaviours reproduced at `2e70a30d` has a dedicated test: a mutable member published through `by_code()`, a member whose exported shape contradicts its annotation, a `KeyError` from the serialization schema, and a description object left in a relation slot. Each test passes after the fix, and each fails when the defect is reintroduced while an unrelated control test keeps passing.
- **SC-004**: 0 declarations import or pass `Rel`, whose symbol is gone; the 262 declarations measured at the baseline are migrated, and the refreshed count is zero against the new contract.
- **SC-005**: 0 fields whose resolved type is a state entity remain in `packages/` and `examples/`; the corpus already carries none, and every state is described by a `Lifecycle[...]` field.
- **SC-006**: 0 declarations passing a field name to `Classifier` remain in `packages/`, `examples/` and `docs/`; the baseline of 165 occurrences in 53 files plus 112 notebook matches is refreshed and driven to zero.
- **SC-007**: A dictionary card prints the label and the value's properties for 100 % of covered cases, prints no code in the SVG text, and exposes the code in a tooltip; the payload, the graph document and its schema are checked separately from the rendered text.
- **SC-008**: The closing check run reports only the two accepted remarks, the affected documentation pages are reconciled in place, each affected package's changelog has its article, and no Russian draft is created for those pages — the task list's own `tasks.ru_draft.md` is the one exception, as in #244.

## Assumptions

- **The six blocks stay in one issue but not in one commit.** They touch related model boundaries and need separate regression evidence; planning keeps them as separate work items.
- **#244's contract is the starting point.** The explicit `value(...)` declaration, the immutable-property rule, the input/output schema split and the `{name, value}` card carrier all exist; this change finishes them rather than replacing them.
- **The rule reads types, not names.** A storage identifier that hides an external foreign key is not detectable and is out of scope; the check binds the declared type only.
- **The corpus counts are snapshots.** 0 bare entity fields, 262 `Rel` declarations, 165 `Classifier(field=…)` occurrences in 53 files and 112 notebook matches were measured at `2e70a30d`; declarations added before implementation change the counts, not the rules.
- **The embedded-value marker is not `NoGraphEdge()`.** Hiding an edge and declaring that no model relation exists are separate statements, and the two markers must not be interchangeable.
- **State entities are included, with one form only.** A state is neither a relation nor a plain field, so a state-typed field is refused and the message names the `Lifecycle[...]` form. The corpus has no authored bare state-entity field, so no existing declaration changes.
- **Presentation only for the card.** The graph, storage and payload keep the code and the label; the change is the card's field list, the printed rows and the tooltip.
- **`Rel` is gone, not deprecated.** The symbol is removed with its role, so a stale declaration fails when its module is imported; the field contract covers the case of a declaration that defines a similarly shaped object of its own.
- **Nullability is a domain decision.** Each nullable field is decided deliberately during migration; the mechanical application of `default=None` is rejected because it would change what the model requires.
- **The check run is the arbiter.** It is taken to zero, and only the two accepted tool remarks remain.

## Dependencies

- The merged baseline `2e70a30d`, and the declaration and relation machinery in `relation_markers.py`, `enum_entity.py`, `entity_specialization_validator.py`, and the two intent resolvers.
- The model-graph publishing boundary where a resolved field can be validated, and the hydration path `build()`.
- `packages/aoa-maxitor`'s `list_entities_action.py`, its payload schema, `buildDotSource.ts` and the client checks (`check-erd-dictionary-values.ts`).
- `specs/016-value-declaration-consistency/contracts/dictionary-card.md` and the specification it belongs to, which state the card contract introduced by #244.
- The documentation and examples that show the old forms: the relation and specialization chapters of `docs/`, the tutorials that declare relations, notebooks under `examples/`, and the changelog articles of `aoa-action-machine` and `aoa-maxitor`.
- Issue [#244](https://github.com/bystrovmaxim/aoa/issues/244) and its merged change, whose contract this specification completes.

## Out of scope

- The storage-coverage audit: a `str` identifier that hides an external foreign key is a false scalar, and only a storage schema or a checked-in relation manifest can catch it.
- Dictionary provenance (`sourced_from="gender_codes"`).
- Redesigning relation cardinality, ownership, inverse or specialization-consistency rules.
- Restricting `BaseStateEntity` properties by the dictionary immutability rule.
- Russian drafts of any page written here.

## Deliberate exceptions to "no implementation detail"

The specification names `NoRelation`, `NoGraphEdge`, `Classifier`, `Rel`, `Field`, the eight relation containers, `FieldInfo.description`, `Lifecycle`, `BaseEnumEntity`, `BaseStateEntity`, `BaseSchema`, `to_reference`, `members`, `codes()`, `by_code()`, `properties.values`, `TOOLTIP` and `build()`, because they are the names a model author writes, the values a consumer reads, and the names a test asserts. It also names module, file and check paths and measured counts in the Context, Dependencies and Out of scope sections, because the scope rests on them. No other internal function, private attribute or framework detail appears in the requirements.
