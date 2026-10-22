# Feature Specification: A closed dictionary declares its variants, and specialization takes its codes from it

**Feature Branch**: `feature/issue-241-closed-dictionary-variants`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/241 — An `EnumEntity` is a closed dictionary: it declares every one of its values in its own class body, the way a state type declares its statuses, and it carries the catalogue (`members`, `codes()`, `by_code()`). A field that references a value is typed by the dictionary itself, accepts a declared value or its reference object, refuses a bare code, and serializes the value whole while the code stays authoritative on read. A specialization field names its dictionary as a type argument — `Specialization[Alternatives, Dictionary]` — so the head carries no classifier field; each extension names the field that points back and the declared value it is; the container holds the declared value and refuses one that disagrees with its hydrated row. The axis edge publishes the dictionary. The demo's currency references migrate and Maxitor shows the dictionary card, the reference and the axis label from the graph alone."

## Context: what is true today, measured on 2026-10-22

- **The dictionary kind declares nothing.** `BaseEnumEntity` adds no fields and no catalogue; its docstring says the role "is not … whether the dictionary is maintained in code or in storage", and the entity tutorial repeats that the marker "adds no fields automatically". A value is one instance a model constructs by hand:

  ```python
  class CurrencyEnumEntity(BaseEnumEntity):
      code: str = Field(description="Currency code")
      symbol: str = Field(description="Currency symbol")

  currency = CurrencyEnumEntity(code="EUR", symbol="€")
  ```

- **Exactly one dictionary class exists in the repository** — `examples/step_20_entity/07_enumeration.py`. `packages/aoa-demo` declares none: the demo's graph carries no `enum` entity at all. The marker's own docstring holds a second snippet, which is documentation, not a declaration.
- **A reference to a dictionary is a plain string.** In `packages/`, 25 fields carry a currency code as `str` (23 named `currency_iso`, plus `settlement_currency_iso` and `quote_currency_iso`), in 22 files. The same measurement shows 15 `*_iso` fields that are dates stored as strings and one `issuer_bin_country_iso`; they are not currency references and are not part of this feature's migration.
- **A specialization states its codes three times.** The head carries `Classifier(field=…, codes=Literal[…])`, and each extension carries `Classifier("field", Literal["one-code"])` on its `Generalization` field. The classifier field itself is a scalar `str`:

  ```python
  media: str = Field(description="Which pressing this is")
  pressing: Annotated[
      Specialization[FirstPressSpecEntity | RepressSpecEntity],
      Classifier(field="media", codes=Literal["first", "repress"]),
  ] = Rel(description="How this record was pressed")
  ```

- **The build compares the copies, and only the copies.** `entity_specialization_validator.py` runs once per graph build and checks the head's codes against the extensions' codes in both directions. Nothing compares either side with a declared vocabulary, because there is none; and nothing keeps a row's `str` value inside a set, because the field's type is `str`.
- **The corpus that carries this form** — measured on this tree: 86 class-body axis fields, 84 of them naming a classifier field, and 158 codes across them; 1 axis in `packages/aoa-demo` (3 `Classifier` declarations), 142 `Classifier(…, Literal[…])` declarations across the `examples/step_20_entity` and `examples/step_21_relations` series, and 105 in the framework's own tests. The negative example `examples/step_21_relations/41_error_codes_not_literal.py` asserts today's rule that codes must be a `Literal`; that rule is what this feature replaces, so the example is rewritten rather than kept.
- **The shape is already proven by the state kind.** Since #237 a state type declares its statuses in its own body (`DRAFT = OrderStateEntity(code="draft", display_name="Draft")`), the type exposes `members`, `codes()`, `by_code()` and `entity_type`, the conversion happens at class creation, duplicate codes are refused, the values are immutable and shared, and the axis refuses a status that is not a declared object of the type and a declared status the axis never uses.
- **The two kinds differ in one respect that must be kept.** A state type with no statuses inherits its parent's catalogue; the dictionary kind will not inherit values, for the reason given in the clarifications.
- **A storage column's name is a resource fact.** Entities are assembled from flat dictionaries (`build`, `partial`) and a resource writes its own SQL; nothing in the model knows a table or column name, which is why the code column of a variant can be called anything.
- **The entity kinds are open on the wire.** Since #239 the graph's `entity_kind` is a word taken from the kind base class and is not enumerated, so a future kind for a data-maintained dictionary needs no viewer change.

## Clarifications

### Session 2026-10-22 — decisions carried from issue #241

- **The dictionary is closed by definition.** `BaseEnumEntity` means a dictionary whose values are declared in code; a dictionary maintained in data is a different kind, not this one. Today's docstring claims the opposite and is rewritten.
- **The declaration surface is the class body.** A model author writes `USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")` inside `CurrencyEnumEntity`, exactly as a status is written inside its state type. No second factory appears in authored code.
- **The marker supplies `code` and `display_name`.** Both are required and non-blank; the model declares only the additional fields the value needs. The state marker already proves this split.
- **Values are not inherited, like aspects.** An aspect resolves through own-class declarations only; a dictionary descendant starts with no values and declares its own set. A subclass of a concrete dictionary is therefore a different dictionary, not "the parent's values plus one".
- **A concrete dictionary cannot be empty.** Every `@entity` dictionary declares at least one value; an undecorated intermediate may be empty, exactly as a base class is not a dictionary.
- **The field's type is the dictionary.** `currency: CurrencyEnumEntity`, not `str`, not `Literal`, not a marker. The type is where assignment is checked, which is the gap #203 measured: today `currency_iso="bootleg"` enters the model.
- **The value travels whole, and the code is authoritative.** A field serializes as `{"code": …, "display_name": …, "properties": {…}}`, additional declared fields under `properties`, so a row stays readable by a consumer that does not hold the model. On read the code resolves to the declared instance; the payload's other fields are neither used nor compared, so a renamed label never changes behaviour and a stale copy never overrides a declaration.
- **An undeclared code is an error and there is no fallback.** The set is reserved by the declaration; a placeholder such as `UNKNOWN` would make "a value nobody declared" a legitimate domain value, writable back to storage, and would hide a mismatch between producer and model. Isolating a bad row belongs to whoever reads it.
- **The axis names the dictionary once, as a type argument.** The head declares `kind: Specialization[FirstPressSpecEntity | RepressSpecEntity, EditionKindEnumEntity]` and nothing else; the extension writes `Classifier(field="record", variant=EditionKindEnumEntity.FIRST)`. There is no classifier field, so a `Literal`, a restated code set and a head-side `Classifier` are all refused.
- **Coverage is full.** Every declared value of the dictionary has exactly one alternative, and every alternative's code is a declared value of that dictionary — the same two-sided rule the lifecycle applies to statuses.
- **The extension must use the declared value, not a copy.** An equal-but-distinct instance is refused and the error names `Type.VALUE` to use; this mirrors the lifecycle's "different instance" refusal.
- **`Literal` leaves specialization.** It remains for closed sets that are not a domain dictionary (a one-member tag, role modes, edge relationships), which #203 lists and this feature does not touch.
- **One dictionary may classify several axes.** A dictionary is an entity of its own; each axis proves full coverage separately. An existing rule already keeps one class in one head; the rules about a classifier field disappear with the field.
- **The axis edge publishes the dictionary.** `dictionary_qualname` and `dictionary_label` join the edge's properties, so the graph answers why an axis has these codes, and Maxitor can label the axis and point at the card.
- **The values are not graph nodes.** A value has no identity outside its dictionary, no domain of its own, no lifecycle and no relationships. The dictionary node carries its values in `properties.values`; a node per value would claim identity the value does not have and would need a domain edge invented for it.
- **The check lives at graph build.** The dictionary, the head and the extensions are separate classes, and the head's annotation is a forward reference until Pydantic resolves it; no class-creation hook sees all three. The pass in `entity_specialization_validator.py` is where the whole model is visible.
- **Maxitor learns no names.** The card, the value rows and the axis label come from the graph; the rule #239 set for kinds applies unchanged to dictionaries and values.

### Session 2026-10-22 — clarifications

- Q: Where does the code set of a specialization axis come from now? → A: From a closed dictionary type, named as the second type argument of the head's specialization field. `Literal` is refused, and each extension names the declared value it is.
- Q: Where does the head name the dictionary, now that there is no classifier field? → A: In the head field's type argument, `Specialization[Alternatives, Dictionary]`. A head-side `Classifier`, a separate classifier field or a `Literal` is refused.
- Q: What does the container's `variant` accept? → A: A declared value or its reference object; a bare code is refused, because the resource resolves it before the model is built.
- Q: What does a field serialize to? → A: The whole value, with additional declared fields under `properties`; on read the code is authoritative and the rest is cargo.
- Q: What happens on a code that the dictionary does not declare? → A: An error naming the field, the code and the declared set. No fallback value exists.
- Q: Are dictionary values inherited by a subclass? → A: No; own-class declarations only, as with aspects.
- Q: May one dictionary classify two axes? → A: Yes; each axis proves full coverage.

### Session 2026-10-22 — the axis carries no classifier field

- **One fact, one place.** The head's specialization field names the dictionary as its second type argument; a separate classifier field is removed from the model, so the code and the container cannot drift.
- **The container holds the declared value.** `variant` accepts a declared value or its reference object, never a bare code; the resource resolves the stored code before the model is built and refuses an undeclared one with the row, the field, the code and the declared set.
- **The container checks the pair.** A value whose hydrated entity class declares another value is refused; the extension exposes the value its own declaration names, derived, never typed by hand.
- **The extension names its field and its value.** `Classifier(field="record", variant=EditionKindEnumEntity.FIRST)`; the head's `Inverse`, when present, names the same field and is checked against it.
- **Storage keeps a column with the code.** Its name is not fixed: the resource maps it to the field, and the model is not told the column name.
- **The order of variants is the dictionary's declaration order**, because a union has no order of its own.

- Q: Must the head keep a classifier field? → A: No. The dictionary is the second type argument of the head's field; a head-side `Classifier`, a separate field or a `Literal` is refused.
- Q: Does the extension keep naming a field? → A: Yes. `Classifier(field="record", variant=…)`; without the field name the pairing would be implicit, and neither a human nor an agent could read it from the declaration.
- Q: Does the container accept a bare code? → A: No. A declared value or its reference object only.
- Q: Who turns the stored code into a value? → A: The resource, with a local domain error naming the row, the field, the code and the declared set.
- Q: Does the container check that the hydrated class matches the value? → A: Yes; the extension exposes its declared value and the container compares them.
- Q: Where is the code stored? → A: In a column of the resource's choosing; the model never names it.
- Q: In what order do variants appear in the graph? → A: The dictionary's declaration order.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare a closed dictionary with its values (Priority: P1)

A model author defines one class for a reference value — the fields every value needs — and declares every value of that dictionary in the same class body. After the class is created, each declared name is an instance of that type, the catalogue reports the values in declaration order, and a duplicate code or an empty concrete dictionary is refused.

**Why this priority**: This is the block that stands alone: without it there is no dictionary for an axis to borrow, and none of the other three blocks has an object to work on.

**Independent Test**: Declare a dictionary with three values and two extra fields, then check `codes()`, `by_code()`, `members` and `entity_type`; declare a duplicate code, an empty concrete dictionary and a subclass with no values, and check each refusal.

**Acceptance Scenarios**:

1. **Given** a dictionary declaring `USD`, `EUR` and `RUB`, **When** the class is created, **Then** `codes()` is `["usd", "eur", "rub"]`, `by_code("eur")` is the declared `EUR` instance, `members` is those three values, and `entity_type` is the dictionary type itself.
2. **Given** a dictionary declaring the same code twice, **When** the class is created, **Then** the class is refused and the message names the duplicated code.
3. **Given** an `@entity` dictionary with no declared values, **When** the class is created, **Then** it is refused; **Given** an undecorated intermediate class with no values, **When** it is created, **Then** it is accepted as a base.
4. **Given** a concrete dictionary, **When** a subclass declares its own value, **Then** the subclass's catalogue holds only that value and nothing from the parent.
5. **Given** a value declaration that omits `code` or `display_name`, or gives a blank one, **When** the class is created, **Then** a validation error names the class and the field.

---

### User Story 2 - Reference a value from a field (Priority: P1)

A model author types a field by the dictionary. The field accepts a declared code or the declared instance; it refuses an undeclared code and a fabricated copy; and when the row is serialized the value travels whole with its extra fields under `properties`, while reading is driven by the code alone.

**Why this priority**: This is what makes the dictionary reach an object at all; without it a dictionary is a list nobody can use, and the "any string fits" defect #203 measured stays.

**Independent Test**: Build one entity with a dictionary-typed field, assign a declared instance, a declared code, an undeclared code and a fabricated instance; then serialise and re-read a payload whose copy carries a stale label.

**Acceptance Scenarios**:

1. **Given** `currency: CurrencyEnumEntity`, **When** a row is built with `CurrencyEnumEntity.USD` or with `{"code": "usd", "display_name": "US dollar", "properties": {"symbol": "$"}}`, **Then** the row is built and its field is the declared `USD` instance.
2. **Given** the same field, **When** a row is built with a bare `"bootleg"` or with a reference object whose `code` is `"bootleg"`, **Then** the row is refused with a message naming the field, the code and the declared codes.
3. **Given** the same field, **When** a row is built with `CurrencyEnumEntity(code="usd", display_name="Copy")`, **Then** the row is refused because a copy is not a declared value.
4. **Given** a row whose serialized value carries a label different from the declaration, **When** the payload is read, **Then** the field is the declared instance and behaviour is unchanged by the payload's label.
5. **Given** an optional field typed by the dictionary, **When** the payload carries no value, **Then** the field is `None`, which is distinct from an unknown code.

---

### User Story 3 - Move a specialization axis onto a dictionary (Priority: P1)

A model author removes the head's classifier field and both `Literal`s: the head's specialization field names the dictionary as its second type argument, and each extension names the field that points back and the declared value it is. The build refuses a `Literal`, a value with no alternative, an alternative with no declared value, a copy of a value and a field that does not point back; the axis edge names the dictionary, and a container refuses a value that does not match the class it carries.

**Why this priority**: This is the correctness value of the feature: one set instead of three copies, one declaration of the variant instead of a field and a container that can drift, and a membership rule that a typo cannot bypass.

**Independent Test**: Declare one complete axis, then five broken ones — a head that keeps a classifier field or a `Literal`, a missing alternative, an extension naming a foreign value, an extension naming a copy, and an extension naming a field that does not point back — and check each message; then build the same dictionary into a second axis covering it fully and one covering it partially.

**Acceptance Scenarios**:

1. **Given** a head that keeps a separate classifier field or states its codes as a `Literal`, **When** the graph is built, **Then** the axis is refused with a message naming the single declaration form.
2. **Given** a dictionary of three values and an axis of two alternatives, **When** the graph is built, **Then** the axis is refused and the message names the uncovered value.
3. **Given** an extension whose `Classifier` names a value of another dictionary, **When** the graph is built, **Then** the axis is refused.
4. **Given** an extension that constructs its own equal-but-distinct value instead of naming the declared one, **When** the graph is built, **Then** the axis is refused and the message names the declared value to use.
5. **Given** one dictionary and two axes that each cover it fully, **When** the graph is built, **Then** both axes are accepted.
6. **Given** an accepted axis, **When** its edge is read, **Then** it carries `field_name`, `classifier_value`, `dictionary_qualname` and `dictionary_label`, and it carries no `classifier_field`.
7. **Given** a container carrying a declared value and an entity whose class declares a different one, **When** the container is built, **Then** it is refused with a message naming both values.
8. **Given** a container built with a bare code string, **When** it is built, **Then** it is refused, because the code is resolved before the model sees it.

9. **Given** a stored row whose column carries `"first"`, **When** the resource reads it, **Then** the field holds the declared value and its entity class is the one that declares that value; **Given** a column carrying `"bootleg"`, **When** the resource reads it, **Then** the read fails before the model is built, naming the row, the field, the code and the declared set.

---

### User Story 4 - Adapt the demo, the examples and Maxitor (Priority: P2)

The demo's currency references become dictionary references, the one dictionary class in the examples becomes a real closed dictionary, the specialization examples move onto the new declaration, and Maxitor shows the dictionary card with its value rows, the reference to it, and the axis container labelled with the dictionary — from the graph alone.

**Why this priority**: The feature is invisible until the graph it feeds carries a dictionary; the demo is the graph Maxitor loads, and the examples are what an author copies.

**Independent Test**: Import the demo, build its graph, load it in Maxitor, toggle the `enum` kind, and check the card, the rows, the reference and the axis label; run the migration counters for the demo and the examples.

**Acceptance Scenarios**:

1. **Given** the migrated demo, **When** the graph is built, **Then** no `currency_iso: str` remains in `packages/aoa-demo`, every currency field references the dictionary, and every code the demo uses is declared.
2. **Given** the migrated examples, **When** the specialization series is imported, **Then** no `Classifier(…, Literal[…])` remains, and the series keeps its scenario per file, including the rewritten negative example.
3. **Given** the demo graph in Maxitor, **When** the ERD is opened, **Then** the dictionary is one card with its values as rows, a referring entity draws a reference to that card, and the specialization container names the dictionary.
4. **Given** Maxitor's source, **When** it is searched for AOA's dictionary, kind or value names, **Then** none appears in the rendering path.

---

### Edge Cases

- A dictionary declares one value: valid; a concrete dictionary declares none: refused.
- A dictionary declares the same code twice: refused at class creation, naming the code.
- A subclass of a concrete dictionary declares its own values: it has its own catalogue and none of the parent's values.
- A subclass of a concrete dictionary declares nothing and is decorated: refused as an empty dictionary.
- A field is assigned a value of a *different* dictionary with the same code: refused; identity is per dictionary.
- A field is assigned an equal-but-distinct copy of a declared value: refused, and the message names `Type.VALUE`.
- A payload omits `code` but carries a label: refused as a malformed payload, not treated as an absent value.
- A payload carries an undeclared code: refused, naming the field, the code and the declared set.
- A payload carries a stale `display_name`: ignored; the declared instance is used.
- An optional dictionary field with no value: `None`, distinct from an unknown code.
- A head keeps a separate classifier field or a `Literal`: refused, naming the single declaration form.
- A container is built with a bare code string: refused, because the resource resolves the code before the model is constructed.
- A container carries a value whose hydrated class declares another value: refused, naming both values.
- A head row has no variant: the field is `None`, and the container is not built.
- A stored column carries an undeclared code: the read fails before the model is built, naming the row, the field, the code and the declared set.
- A dictionary value has no alternative, or an alternative names no declared value: both refused, naming the axis field.
- One dictionary used by two axes, one covering it fully and one partially: the partial one is refused on its own field.
- The same code exists in two dictionaries: allowed; each dictionary is its own set.
- A dictionary referenced from a field of a `str` type elsewhere: the string field keeps working and is not a reference; the migration is per field, not global.
- A dictionary is asked to be a `Composite` target or to carry a lifecycle: this feature neither adds nor removes such a check; a dictionary obeys whatever model-wide rule every kind obeys today.
- A graph exported before this feature carries no `values` on an `enum` entity: the graph document is rebuilt, as it was for `entity_kind`; no reader is expected to accept both shapes.

## Requirements *(mandatory)*

### Functional Requirements

**The dictionary kind**

- **FR-001**: An `@entity` descendant of the dictionary kind MUST declare at least one value in its own class body; a concrete dictionary with no values MUST be refused at class creation, and an undecorated intermediate class with no values MUST be accepted.
- **FR-002**: The kind MUST supply `code` and `display_name` as required, non-blank fields, and MUST NOT require the model to redeclare them.
- **FR-003**: Each declared name MUST become an instance of the declaring type at class creation; its declared fields MUST be initialised, with defaults applied and unknown keys refused.
- **FR-004**: The type MUST expose the catalogue as `members` (declaration order), `codes()`, `by_code(code)` and `entity_type`; `by_code` MUST raise `KeyError` for an unknown code.
- **FR-005**: Duplicate codes inside one dictionary MUST be refused at class creation, naming the duplicate.
- **FR-006**: Values MUST NOT be inherited: a subclass's catalogue MUST contain only the values it declares, and a subclass that declares none and is not decorated MUST hold an empty catalogue.
- **FR-007**: The declaration mechanism MUST be the one the state kind uses, not a second mechanism; the conversion, duplicate refusal and catalogue MUST behave the same way, and the state kind's inheritance of its parent's catalogue MUST NOT change.

**References to a value**

- **FR-008**: A field that references a dictionary value MUST be typed by the dictionary type; a declared instance or its reference object `{code, display_name, properties}` MUST be accepted, and the field MUST hold the declared instance. A bare code string MUST be refused.
- **FR-009**: A reference object whose `code` is undeclared MUST be refused at construction, and the message MUST name the field, the code and the declared codes; a constructed copy of a declared value MUST be refused, and the message MUST name the declared value to use.
- **FR-010**: Serialization MUST carry the value whole — `code`, `display_name` and the extra declared fields under `properties`.
- **FR-011**: On read, the code MUST be authoritative: it MUST resolve to the declared instance, and the payload's `display_name` and `properties` MUST NOT affect behaviour or be compared with the declaration.
- **FR-012**: A payload without `code` MUST be refused as malformed, and an absent value MUST be representable only as `None`, only where the field is optional.
- **FR-013**: A dictionary MUST remain an ordinary entity: it carries the kind's name suffix, a domain, its declared fields, its marker stays abstract and unconstructible, and the class stays in the entity graph. Nothing about its lifecycle, ownership or composability changes, and no rule the other five kinds already have changes.

**The graph**

- **FR-014**: The dictionary's entity node MUST carry its values in `properties.values`, each entry with `code`, `display_name` and the extra fields under `properties`.
- **FR-015**: Values MUST NOT become graph nodes and MUST NOT require domain edges of their own.
- **FR-016**: A field that references a dictionary MUST be recognizable in the graph as a reference to that dictionary, so an ERD can draw it as a reference rather than as a scalar column.

**Specialization**

- **FR-017**: A head's specialization field MUST be `Specialization[Alternatives, Dictionary]`, the dictionary named as its second type argument; the head MUST NOT carry a separate classifier field and MUST NOT use `Classifier`. A `Literal` or a restated code set MUST be refused with a message naming the single declaration form.
- **FR-018**: A container's `variant` MUST accept only a declared value of that dictionary or its reference object `{code, display_name, properties}`; a bare code string, a value of another dictionary and a constructed copy MUST each be refused, and the copy's message MUST name the declared value to use.
- **FR-019**: A container MUST refuse a `variant` that does not match the class of its hydrated `entity`; every extension class MUST expose the value its own declaration names, so the comparison needs no second source.
- **FR-020**: An extension's `Classifier` MUST name the field that points back and the declared value (`Classifier(field=…, variant=…)`); a code string, a foreign value, a copy, or a field that is not a `Generalization[…]` of that head MUST each be refused. An `Inverse` on the head, when present, MUST name the same field.
- **FR-021**: Every declared value of the dictionary MUST have exactly one alternative, and every alternative MUST declare a declared value of that dictionary; both directions MUST be refused with a message naming the axis field and the offending code.
- **FR-022**: The checks of FR-017 to FR-021 MUST run in the existing whole-model build pass, before any graph is published, and MUST cost nothing at runtime.
- **FR-023**: One dictionary MAY classify several axes; each axis MUST be checked for full coverage on its own.
- **FR-024**: The axis edge MUST carry `field_name`, `classifier_value`, `dictionary_qualname` and `dictionary_label`, and MUST NOT carry `classifier_field`.
- **FR-025**: A `Literal` MUST remain usable for closed sets that are not a domain dictionary, and no other declaration form of the framework MUST change.
- **FR-026**: The existing specialization rules MUST keep their behaviour and error types — alternatives are declared entities, one class in one head, no cycles — and the rules about a classifier field MUST be removed with the field.
- **FR-027**: The corpus MUST migrate in the same change: every classifier field is removed, every head's field gains the dictionary argument, every extension's marker gains `variant=`, and every construction and payload moves the code inside the container.

**The corpus**

- **FR-028**: The demo MUST declare its currency dictionary, reference it from every field that carries a currency code (25 declarations in 22 files), and declare every code those fields use.
- **FR-029**: The example that declares a dictionary MUST declare its values in the body, and the specialization examples MUST move onto a dictionary, including the negative example that today asserts `Literal`-only codes.
- **FR-030**: The framework's own fixtures MUST move onto the new form; no test MAY assert the replaced rule.
- **FR-031**: No `currency_iso: str` declaration MUST remain in `packages/aoa-demo`, and the date-like `*_iso` string fields MUST remain unchanged, because they are not dictionary references.

**Maxitor**

- **FR-032**: The ERD MUST show a dictionary as a card with its values as rows, read from `properties.values`.
- **FR-033**: A referencing entity MUST draw a reference to the dictionary card; the specialization container's label MUST name the dictionary.
- **FR-034**: Maxitor's rendering MUST contain no dictionary, kind or value name of AOA's: the card, the rows and the label MUST come from the graph.

**Governance**

- **FR-035**: Every refusal introduced here MUST be a declaration or build error with a message naming the class, the field, the code and the allowed values. The storage read path — resolve the code, refuse an undeclared one before the model is constructed — MUST be documented in the contract, because this repository has no storage-backed adapter to test it against.
- **FR-036**: The two accepted remarks of the check run MUST survive: the Vite chunk-size advisory and LangGraph's pending-deprecation warning MUST NOT be acted on.
- **FR-037**: Documentation MUST ship with the change, and the changelog MUST be one article per package whose visible behaviour changes.

### Key Entities

- **Dictionary**: a closed set of reference values declared in one class body; an entity of its own, with a domain and declared fields; it owns the set.
- **Value**: one immutable instance of a dictionary, identified inside it by `code`, labelled by `display_name`, carrying the dictionary's extra fields.
- **Catalogue**: the ordered tuple of a dictionary's declared values, with lookup by code and the shared type; not inherited.
- **Reference**: a field typed by a dictionary; it holds a declared value, serializes the value whole, and is read by its code.
- **Container**: `Specialization[Alternatives, Dictionary]`, the head's field; it carries the declared `variant`, the extension row id, the hydrated row when loaded, and refuses a value that disagrees with that row's class.
- **Axis**: a head's `Specialization[Alternatives, Dictionary]` field plus, per extension, a `Generalization[…]` field whose `Classifier` names that field and the declared value the extension is; there is no separate classifier field.
- **Axis edge**: the graph row that names the axis field, the code of each alternative and the dictionary the codes come from; it names no classifier field, because the head has none.
- **Declared value of an extension**: the value its `Classifier(variant=…)` names and its class exposes, used by the container to check that the hydrated row and the value agree.
- **Declaration error**: the refusals of an empty dictionary, a duplicate code, an undeclared code, a copied value, a missing alternative and an uncovered dictionary value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A dictionary with three values and two extra fields is declared, created and used with zero framework factories in the authored code; 100 % of each value's declared fields are present when it is serialized.
- **SC-002**: 0 `@entity` dictionaries without declared values and 0 duplicate codes remain in `packages/` and `examples/`; the one dictionary class in `examples/` and the demo's new dictionary both build.
- **SC-003**: 0 occurrences of `Classifier(…, Literal[…])` remain in `packages/aoa-demo`, `examples/` and the framework's tests: the 3 demo declarations, the 142 example declarations and the 105 test declarations are all on the dictionary form, and every migrated example keeps its scenario.
- **SC-004**: 0 declarations of `currency_iso: str` remain in `packages/aoa-demo`; the 25 currency fields in 22 files reference the dictionary, and the 16 other `*_iso` string fields are untouched.
- **SC-005**: The eight refusal cases — empty dictionary, duplicate code, undeclared code, copied value, a head that keeps a classifier field or a `Literal`, uncovered dictionary value, a bare code on a container, a container whose value and entity class disagree — each raise their named error in a dedicated test, and no other test fails.
- **SC-006**: The demo graph reports the dictionary node with all its values, one reference per currency field, and one axis edge carrying the dictionary's qualname and label; Maxitor renders the card, the rows, the reference and the axis label from that graph with no AOA name in the rendering path.
- **SC-007**: The closing check run reports only the two accepted remarks, and the documentation listed in Dependencies is updated in place, with no new tutorial and no new example series.

## Assumptions

- **"Closed" means declared in code.** `BaseEnumEntity` is the closed dictionary; a dictionary maintained in data is a different kind, recorded in the issue as future work. Until it exists, such a table is modelled as a `BaseCoreEntity` with a unique code.
- **Full coverage, no subset.** An axis covers its dictionary completely; a dictionary wider than an axis is not a subset relation and would need a projection feature that is out of scope.
- **One mechanism, two kinds.** The state kind's declaration machinery is shared, but the kinds stay siblings: the state kind keeps its lifecycle role, its exclusion from the entity graph and its inherited catalogue; the dictionary keeps its ordinary-entity role and its non-inherited values.
- **The dictionary is a type argument of the container.** `Specialization[Alternatives, Dictionary]` names it; the `CodeOf`-style marker and the head-side `Classifier` considered earlier are unnecessary once the dictionary itself is the closed type, and neither is introduced.
- **Storage keeps a code column.** Its name is not fixed and is chosen by the resource; the model never sees the column name. The resource resolves the code into a declared value and fails before the model is constructed when the code is undeclared.
- **The container accepts values, not codes.** The model refuses a bare code string; only a declared value or its reference object enters.
- **The values are not nodes.** A value is the dictionary's declaration data, carried on its node; the condition for revisiting this is stated in the issue (per-value identity, audit or filtering).
- **The demo's timestamps are not references.** The 15 `*_iso` string fields are dates, not dictionary values, and the single `issuer_bin_country_iso` stays a string until a country dictionary exists.
- **The graph document is rebuilt, not versioned.** A graph exported before this feature lacks `values`; readers are not required to accept both shapes, as was the case for `entity_kind`.
- **The corpus count is a snapshot.** 25 currency fields in 22 files, 3 demo `Classifier` declarations, 142 example declarations and 105 test declarations were measured on `main` at `70980156`; declarations added before implementation change the migration count.
- **The dependencies are closed.** #210, #237 and #239 are merged; the branch `feature/issue-241-closed-dictionary-variants` is based on `70980156`.

## Dependencies

- #203 as the notion this feature realises for the dictionary case; #210, #237 and #239 as merged work.
- The state kind's declaration machinery in `state_entity.py` and its Pydantic conversion hook.
- The whole-model build pass in `entity_specialization_validator.py` and `NodeGraphCoordinator.build()`.
- The interchange schema and the graph traversal that publishes node properties.
- Maxitor's ERD payload and card rendering.
- The documentation pages that state the old contract: `docs/tutorials/step-20-entity.md`, `docs/tutorials/step-26-maxitor.md`, `docs/reference/glossary.md`, `docs/reference/intents-and-invariants.md`, `docs/how-to/specialization-declaration-fails.md`, `packages/aoa-maxitor/README.md`, the marker's own docstring and the changelog articles.

## Out of scope

- A data-maintained dictionary as a separate kind.
- Generating storage DDL from a declaration (a `CHECK`, a lookup table).
- Graph nodes per value, filtering by value, editing dictionaries in Maxitor, per-value audit or provenance.
- The other closed sets #203 lists — role modes, edge relationships, cascade answers — which keep their `Literal`/`Enum` forms.
- A projection feature for a dictionary wider than an axis.
- Any change to the five other kinds, to the state kind's catalogue inheritance, or to the model-wide kind rules tracked in #212.

## Deliberate exceptions to "no implementation detail"

The specification names `BaseEnumEntity`, `BaseStateEntity`, `Classifier`, `Specialization`, `Generalization`, `codes()`, `by_code()`, `members`, `entity_type`, `entity_kind`, `properties.values`, `dictionary_qualname`, `dictionary_label`, `entity_specialization_validator.py` and `NodeGraphCoordinator.build()` because they are the contract a model author writes, the graph fields a consumer reads, and the names a test asserts. It also names module paths and measured counts in the Context section because the scope rests on them. No other module path, function name or framework internal appears in the requirements.
