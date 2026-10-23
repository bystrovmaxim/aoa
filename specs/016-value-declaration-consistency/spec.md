# Feature Specification: A declared value is stated explicitly, protected where it is shared, and carried whole from the model to the ERD card

**Feature Branch**: `feature/issue-244-simplify-value-declarations`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/244 — Replace the hidden class-name alias with an explicit public `value(...)` declaration factory for dictionaries and statuses; remove the metaclass substitution. Then make the shared declared values actually immutable, serialize them through the field serializers their model declares, make the input and output JSON Schema describe what is accepted and what is emitted, carry the extra properties through to the ERD card (incorporating #242), and compose each specialization group label once. Tracked as six work items, not as commits."

## Context: what is true today, measured on 2026-10-23 at `e791ad28`

- **The declaration is hidden in the class's own name.** While the class body runs, `DeclaredValuesMeta` (a subclass of Pydantic's internal `ModelMetaclass`) supplies a `_DeclaredValuesNamespace` that answers the not-yet-existing class name with a factory; `USD = CurrencyEnumEntity(…)` therefore builds a placeholder object, not an instance. The factory itself — `value(**kwargs)` returning a `ValueSpec` — already exists in the same module, but it is not exported from `aoa.action_machine.domain` and no authored declaration uses it. The module docstring describes the alias as the form.
- **The form is everywhere.** 373 declarations in 116 files under `packages/` and `examples/` use the class-name syntax, for both dictionaries and statuses: 270 of them in 91 files outside the demo, and 103 in 25 files inside it.
- **The conversion after the class exists is deliberate.** `__pydantic_init_subclass__` turns each placeholder into a validated instance, computes the catalogue (`members`, `codes()`, `by_code()`, `entity_type`), refuses a duplicate code and fills the per-kind switches. That step is not the thing this change removes.
- **A declared value is not deeply immutable.** `to_reference()` copies the outer mapping but keeps the declared object's own nested property objects. Reproduced on the merged baseline:

  ```python
  ref = LabelsEnumEntity.ITEM.to_reference()
  ref["properties"]["labels"].append("changed")
  LabelsEnumEntity.by_code("item").labels   # ['original', 'changed']
  ```

  The frozen Pydantic model protects its own attributes, not the list inside one of them; `LabelsEnumEntity.ITEM.labels` is the same shared list.
- **Field serializers are bypassed.** `to_reference()` reads with `getattr`, so a `@field_serializer` on a declared field never runs; and the plain-model serializer is what a reference field serializes through. Reproduced:

  ```python
  DatedEnumEntity.ITEM.model_dump_json()
  # {"code":"item","display_name":"Item","properties":{"since":"2020-01-02"}}
  # a serializer asking for "%d/%m/%Y" printed nothing of the kind
  json.dumps(DatedEnumEntity.ITEM.to_reference())
  # TypeError: Object of type date is not JSON serializable
  ```

  Graph export takes the same path, so a graph document can carry a non-JSON leaf.
- **The published JSON Schema is an output shape used as an input shape.** `__get_pydantic_json_schema__` requires `code`, `display_name` and `properties`, while runtime validation accepts a code-only reference. Reproduced: `{"currency": {"code": "eur"}}` validates to the declared value, and the same payload raises `'display_name' is a required property` and `'properties' is a required property` against `model_json_schema(mode="validation")`; validation mode and serialization mode return the identical shape.
- **The card carrier already exists.** PR #243 merged a strict-schema-compatible carrier: `ListEntitiesAction` converts the graph's property mapping into a list of `{name, value}` objects, the payload schema describes those objects, and `buildDotSource.ts` escapes and renders them. This feature preserves and verifies that path; it does not replace it, and the older `properties_json` string carrier proposed in #242 is superseded.
- **The two representations differ on purpose.** The graph reference is `{code, display_name, properties: {...}}`; the ERD display payload is `{code, display_name, properties: [{name, value}, …]}`.
- **The group label is composed twice.** The server SQL writes `field (by COALESCE(classifier_field, dictionary_label))` and the client appends ` (${dictionary_label})` again, so a group renders as `kind (by EditionKindEnumEntity) (EditionKindEnumEntity)`.
- **The baseline is `e791ad28`.** The four defects above were first observed at `5b5aa4fd`; the basic property display requested by #242 is already merged by #243.

## Clarifications

### Session 2026-10-23 — decisions carried from issue #244

- **The declaration is one public factory.** `value(code=…, display_name=…, …)` is the authored form for both kinds, imported from `aoa.action_machine.domain`.
- **The class-name alias leaves and is not kept as a compatibility path.** No hidden substitution remains, no fallback form, no deprecation window; every in-scope declaration migrates in this change.
- **The post-class conversion stays.** A specification is turned into a validated instance after the model is built; this is the one automatic step that remains, and it is documented plainly rather than removed.
- **The value's supported properties are decided at declaration, and the answer is refusal.** A declared property is limited to immutable types — `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `UUID` and tuples of those — and a `list`, `dict`, `set` or any other mutable container is refused when the class is created, with a message naming the field and the type. The rule applies recursively, so a tuple holding a list is refused exactly as a top-level list is. No shallow or deep copy is used as a substitute for the rule, and an exported payload cannot reach the declared object's data because it holds no mutable data at all.
- **Python mode and JSON mode are stated explicitly.** If they differ — a serializer present or absent, a non-primitive leaf — the difference is a documented contract, not an accident of `getattr` versus `model_dump`.
- **Input and output schema are two contracts.** The input schema accepts a code-only reference and a supported full reference; the output schema describes the complete emitted reference. Runtime acceptance is unchanged: a missing, blank or unknown code is still refused.
- **The card carrier is preserved, not rewritten.** Graph shape stays `{code, display_name, properties}`; the ERD payload stays a typed list whose items declare `name` and `value` as strings with no additional properties.
- **Display is text, determinism is the backend's job.** A string property is display text; a supported non-string property reaches the card as deterministic JSON text, produced consistently with the serializer contract.
- **No domain vocabulary in Maxitor.** The renderer names no dictionary and no field; `symbol` and `note` are examples in this document, never code.
- **The group label has one owner.** The dictionary name appears once, and the server's payload driven through the client renderer is the proof, not two layer-local assertions.
- **Values stay rows, not nodes.** Nothing in this change gives a value an identity of its own in the graph.
- **Historical planning notes are reconciled, not rewritten into history.** `specs/015-closed-dictionary-variants/contracts/dictionary-declaration.md` and the stale ERD-payload risk in `specs/015-closed-dictionary-variants/plan.md` identify what was resolved; the old limitation is not described as current behaviour.

### Session 2026-10-23 — clarifications

- Q: Is the class-name alias kept as a deprecated second form? → A: No. It is removed with its namespace and metaclass, and every declaration migrates in this change, the demo's included.
- Q: Does `value(...)` replace the conversion hook? → A: No. It replaces only the way a declaration is written; the conversion after class creation stays and is documented.
- Q: Which kind does the immutable-property rule bind? → A: The dictionary kind only. A dictionary value's extra fields are limited to the supported immutable set; a state type keeps its present freedom, because the corpus's only `list[str]` property and its only non-JSON property are statuses asserted as deliberate lifecycle scenarios.
- Q: What happens to a mutable property? → A: It is refused at declaration with a message naming the class, the field and the type. The supported set is `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `UUID` and tuples of those, applied recursively; no copy is used in place of the rule.
- Q: Does the card's property list change shape? → A: No. `{name, value}` items remain, because that is what [PR #243](https://github.com/bystrovmaxim/aoa/pull/243) merged and what the strict payload schema accepts.
- Q: Is the reference form JSON or Python? → A: JSON. `to_reference()` applies field serializers and emits JSON-compatible leaves only; the model's Python-mode dump may differ and that difference is documented.
- Q: How detailed is the output schema for a value's properties? → A: Each declared property appears by name with its JSON type and format, and additional members are refused; the input side keeps `properties` open, because runtime validation ignores its contents.
- Q: Which layer composes the group label? → A: The server. The payload carries the composed `field (by Dictionary)` label, the client renders it as received, `dictionary_label` leaves the group shape, and a test drives the server payload through the client renderer.
- Q: Does removing the class-name alias leave the demo broken? → A: No. The demo's 103 declarations in 25 files migrate mechanically, because its modules are imported by the demo's tests and the check run would otherwise fail; its demonstration code and behaviour stay outside the work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare a value with `value(...)` (Priority: P1)

A model author declares a dictionary entry or a lifecycle status by writing `value(code=…, display_name=…, …)` inside the class body, importing `value` from the domain package. The class is created, each declared name is an instance of the declaring type, and the catalogue behaves as it does today.

**Why this priority**: This is the declaration form every other story is written in, and it is the change that removes an undocumented trick from the public surface. Nothing else can be documented or tested honestly until the authored form is the one the framework shows.

**Independent Test**: Declare a dictionary with two extra fields and three values, and a state type with two statuses, using only `value(...)`; then check attribute access, `members`, `codes()`, `by_code()`, `entity_type` and declaration order. Declare a duplicate code, a blank `code`, an unknown field and an empty concrete dictionary, and check each refusal.

**Acceptance Scenarios**:

1. **Given** a dictionary whose body writes `EUR = value(code="eur", display_name="Euro", symbol="€")`, **When** the class is created, **Then** `CurrencyEnumEntity.EUR` is an instance of `CurrencyEnumEntity`, `by_code("eur")` is that same object, and `.symbol` is `"€"`.
2. **Given** a state type whose body writes `NEW = value(code="new", display_name="New", requires_receipt=False)`, **When** the class is created, **Then** the status is a `BaseStateEntity` descendant with its declared fields, and the lifecycle resolves it as it does today.
3. **Given** a class body that still writes `EUR = CurrencyEnumEntity(…)`, **When** the class body executes, **Then** it fails on the undefined class name, because the only declaration form is `value(...)`.

---

### User Story 2 - A shared value cannot be changed by a consumer (Priority: P1)

A consumer receives a value's reference form and tries to modify it — a list under `properties`, a nested mapping, or the declared attribute itself. Nothing it does reaches the declared object every other consumer shares.

**Why this priority**: A declared value is the dictionary's data, and silent mutation of it changes behaviour everywhere at once. It is a correctness defect in the merged baseline, not a refinement.

**Independent Test**: Build a dictionary value carrying a list and a nested mapping; call `to_reference()`; append to the list, insert into the mapping and assign a new element; then read the declared value and `by_code(...)` again and compare.

**Acceptance Scenarios**:

1. **Given** a dictionary value declaring `labels: list[str]`, **When** the class is created, **Then** it is refused, the message names the class, the field and `list`, and the supported property types are documented.
2. **Given** a declared field of type `tuple[str, ...]` or a date, **When** a consumer reads `to_reference()["properties"]`, **Then** the value holds no mutable container and no operation on the exported form can change the declared object.
3. **Given** a tuple that itself holds a list, **When** the class is created, **Then** it is refused at the nested position, not only at the top level.
4. **Given** a declared value, **When** a consumer assigns to one of its attributes, **Then** the frozen model refuses, as it does today.

---

### User Story 3 - A reference serializes through its own field serializers (Priority: P2)

A model author puts a `@field_serializer` on a declared field, or uses a standard non-primitive type such as a date. Whatever the framework exports — the model's JSON, the reference form, the graph document — carries the serializer's output, not a raw Python object.

**Why this priority**: The value travels to storage and to viewers; an object that cannot be serialized breaks the export path, and an ignored serializer makes a documented contract a lie.

**Independent Test**: Declare a value with a date field and a custom serializer; serialize the model, the reference and an actual graph document; parse the results as JSON.

**Acceptance Scenarios**:

1. **Given** a declared field with `@field_serializer` formatting a date, **When** the value is dumped to JSON, **Then** the serializer's string appears.
2. **Given** a declared field of type `date` with no custom serializer, **When** the value is exported to a graph document, **Then** the emitted leaf is JSON-compatible.
3. **Given** a plain-model dump and a JSON-mode dump of the same value, **When** they differ, **Then** the difference is a documented part of the contract and every supported property type is covered by a test.

---

### User Story 4 - Input and output schemas describe their own contracts (Priority: P2)

A consumer generates a JSON Schema from a model that references a dictionary. Against the input schema a code-only reference validates; against the output schema the complete emitted reference does. A missing, blank or unknown code is still refused at runtime.

**Why this priority**: A schema that rejects payloads the runtime accepts misleads every generated client and every integration test. It follows the serialization story because the output shape is only settled once serialization is.

**Independent Test**: Validate a code-only payload and a full-reference payload against the input schema; validate an emitted reference against the output schema; validate a blank code and supply an unknown code at runtime.

**Acceptance Scenarios**:

1. **Given** a model with a dictionary-typed field, **When** a code-only payload is checked against the input schema, **Then** it validates, and `model_validate` returns the declared instance.
2. **Given** the same model, **When** an emitted reference is checked against the output schema, **Then** it validates, and each supported property type appears in the shape the serializer produces.
3. **Given** a payload with a missing, blank or undeclared code, **When** it is validated at runtime, **Then** it is refused exactly as it is today.
4. **Given** the same model, **When** both modes are compared, **Then** they are not required to be identical, and where they differ the difference is documented.

---

### User Story 5 - A dictionary's properties reach the ERD card (Priority: P3, verification)

A reader of the ERD sees each declared value's code, label and extra properties on the dictionary card. A property present in the saved graph does not disappear between the graph, the storage, the payload and the rendered diagram.

**Why this priority**: The carrier is already merged by #243. The value of this story is proof that the fixes of stories 1–4 did not break it, and that the last unsupported leaf now arrives too.

**Independent Test**: Take a graph with a dictionary whose values carry extra properties, including one containing `<`, `>` and `&`; run the payload action; validate the payload against its schema; render the DOT and the SVG; compare the visible rows with the declared values. Repeat for a value with no extra properties and for a model with no dictionaries.

**Acceptance Scenarios**:

1. **Given** a dictionary value with two extra properties, **When** the full path runs, **Then** both appear as rows inside the value's row, with names and values escaped.
2. **Given** a property whose value contains `<`, `>` and `&`, **When** the diagram is rendered, **Then** the text is displayed literally and the output is still valid SVG.
3. **Given** a value with no extra properties, **When** it is rendered, **Then** it shows code and label and no empty row.
4. **Given** a supported non-string property, **When** it is displayed, **Then** it appears as deterministic JSON text, consistent with the serializer contract of story 3.
5. **Given** a model with no dictionaries, **When** the ERD is built, **Then** it renders as it does today.

---

### User Story 6 - A specialization group label is composed once (Priority: P3)

A reader of the ERD sees a group labelled `kind (by EditionKindEnumEntity)` — the dictionary named exactly once, escaped as before.

**Why this priority**: It is a display defect with a small blast radius, and it is fixed in the same display path as story 5, where the label and the value rows already share an owner.

**Independent Test**: Produce the server payload for a group with both members present, feed that payload to the client renderer, and assert the resulting DOT label.

**Acceptance Scenarios**:

1. **Given** a group whose payload carries the composed label `kind (by EditionKindEnumEntity)`, **When** the client renders it, **Then** the DOT label is that text and the dictionary name appears once.
2. **Given** a group payload that still carries `dictionary_label`, **When** the client renders it, **Then** the field is not appended a second time.
3. **Given** a dictionary name containing a character needing HTML escaping, **When** the label is rendered, **Then** it is escaped exactly once.

### Edge Cases

- A declaration writes `value(...)` with no `code`, a blank `code`, a blank `display_name`, or a field the type does not declare: each is refused at class creation, naming the class and the field.
- Two values of the same dictionary declare the same code: refused as today; two dictionaries declare the same code: allowed.
- An undecorated intermediate class declares nothing: accepted as a base; a decorated concrete dictionary declares nothing: refused.
- A subclass of a concrete dictionary declares its own values: its catalogue has only those; it inherits none.
- A state type declares no statuses: it keeps inheriting its parent's catalogue.
- A value's property is a list, a nested mapping or a set: refused at declaration with a message naming the field and the type. A tuple of supported types, a `date`, a `Decimal` and a `UUID`: accepted and immutable in the exported form. A model of the framework's own: refused, because it is mutable through its own containers.
- A field serializer raises on a value: the error surfaces with the field's name rather than being swallowed or replaced by a raw-object error.
- A field serializer for one field affects another: it must not — no serializer recursion and no cross-field bleed.
- An optional dictionary field is absent: `None`, distinct from an unknown code; a payload omits `code` but carries a label: refused as malformed.
- A reference object given at construction carries a stale `display_name` or stale `properties`: the code wins, and the rest is ignored.
- A property value is `None`, an empty string or an empty tuple: still displayed as a row with a deterministic text form, or explicitly documented as omitted.
- A group has a classifier field and another has only a dictionary label: both labels are composed the same way, and neither degrades to `(by )`.
- A payload reaches the client without a label: the renderer falls back to the group id or omits the text, and never draws an empty `(by )`.
- A graph saved before this change already holds the properties: it displays without a rebuild.
- A property is dropped between the graph and the card: the payload lists one item per property in the graph's mapping, so a missing item is a failing assertion rather than a silent gap.

## Requirements *(mandatory)*

### Functional Requirements

**The declaration form**

- **FR-001**: `value(**fields)` MUST be a supported public import from `aoa.action_machine.domain`, usable in the class body of both a dictionary and a state type, and the only declaration form for both kinds.
- **FR-002**: `value(...)` MUST return a declaration placeholder that the class creation converts into a validated instance of the declaring type; the conversion MUST stay automatic and MUST be documented plainly.
- **FR-003**: The hidden class-name substitution MUST be removed together with the namespace and metaclass that implement it, including the direct dependency on Pydantic's internal metaclass; no compatibility form MAY remain.
- **FR-004**: Each declared name MUST remain an attribute of the declaring type, hold a validated instance, and be the same object every consumer receives; `members`, `codes()`, `by_code()` and declaration order MUST be preserved.
- **FR-005**: Duplicate codes, blank `code` or `display_name`, unknown fields and invalid field data MUST still be refused at class creation.
- **FR-006**: Each kind's existing catalogue rules MUST be preserved: a dictionary does not inherit values and a concrete dictionary may not be empty; a state type without statuses inherits its parent's catalogue.
- **FR-007**: Every declaration, test, fixture and executable example MUST migrate to `value(...)`, and undefined-name suppressions that existed only for the class-name trick MUST be removed. The demo's declarations migrate mechanically in the same change, because removing the alias would otherwise break its imports and the check run; its demonstration code, scenarios and behaviour remain outside the work.
- **FR-008**: The migration MUST be documented as the one-line change plus the import, without claiming that this item alone fixes immutability, serialization, schema or every Pydantic integration detail.

**Immutability of a declared value**

- **FR-009**: A declared value MUST NOT be changed through any form exported to a consumer — the reference form, its `properties` mapping, or a nested container inside one of its fields.
- **FR-010**: The supported property types of a **dictionary** value MUST be the immutable ones: `str`, `int`, `float`, `bool`, `Decimal`, `date`, `datetime`, `time`, `UUID`, an `Enum` subclass, `Literal[...]`, `Optional[X]` where `X` is supported, and tuples of supported types. A `list`, `dict`, `set`, `frozenset`, a nested model, `Any` or any other mutable container MUST be refused when the class is created, with a message naming the class, the field and the refused type, and the supported set MUST be documented.
- **FR-011**: The refusal MUST be recursive within a dictionary value: a mutable container nested inside an otherwise supported one — a tuple holding a list, a mapping inside a tuple — MUST be refused as a top-level list is. A copy MUST NOT be used in place of this rule.
- **FR-012**: Direct mutation of a declared value's own attribute MUST be refused as it is today, the value MUST remain frozen, and no new mutation path MAY be opened by the serialization changes. The property-type rule binds the dictionary kind only: a state type keeps its present freedom, because a status may carry data that need not be hashable and a value with no JSON form, both of which are existing lifecycle scenarios.

**Serialization**

- **FR-013**: A supported field serializer declared on a value's model MUST be honoured when the value is exported, in both the model's JSON and the reference form, and MUST NOT recurse.
- **FR-014**: The reference form MUST always be JSON-compatible: every leaf it carries MUST be a JSON value, and a standard non-primitive type such as a date MUST be emitted as the JSON mode emits it, never as a raw Python object. There is no Python-native variant of the reference form.
- **FR-015**: The reference form MUST be defined as the value's JSON-mode export, and the model's Python-mode dump, where it differs, MUST be documented as such and covered by tests.
- **FR-016**: Graph export MUST produce JSON-compatible data not only through the model's dump but through the actual graph document path, so a value that survives one path cannot break the other.

**Schemas**

- **FR-017**: The input JSON Schema of a dictionary-typed field MUST accept a code-only reference and a supported full reference, and MUST NOT require fields the runtime does not require. Its `properties` member MUST remain unconstrained in content, because runtime validation ignores what a payload carries there.
- **FR-018**: The output JSON Schema MUST describe the complete reference the framework emits: `code` and `display_name` as non-blank strings, and `properties` as an object that declares each of the dictionary's declared property names with its JSON type and format, refusing additional members. The asymmetry between the two schemas MUST be documented as intentional: input describes what is accepted, output describes what is emitted.
- **FR-019**: Runtime validation MUST keep refusing a missing, blank or undeclared code, and MUST keep ignoring a stale label or stale properties in a reference object.
- **FR-020**: Real inputs and real outputs MUST be validated against their respective schemas in tests, not merely inspected.

**The ERD card**

- **FR-021**: The graph's reference shape MUST remain `{code, display_name, properties}` and the ERD payload's property list MUST remain a list of objects declaring `name` and `value` as strings with no additional properties; the whole payload MUST satisfy the schema type it declares.
- **FR-022**: The full path — declared value, graph JSON, storage, payload action, validated payload, diagram source, rendered SVG — MUST be covered by a test that fails when a property disappears at any layer.
- **FR-023**: A string property MUST display as text, and a supported non-string property MUST display as deterministic JSON text produced consistently with FR-013.
- **FR-024**: The renderer MUST escape property names and values, MUST render them inside the existing value row, and MUST remain independent of domain vocabulary — no dictionary name and no fixed field list.
- **FR-025**: A value with no extra properties, a model with no dictionaries, and a property containing `<`, `>` and `&` MUST each be covered.
- **FR-026**: Documentation that describes the old limitation as current behaviour MUST be reconciled — the dictionary-declaration contract, the stale ERD-payload risk in the earlier plan, the Maxitor tutorial and the component README — identifying what was resolved rather than rewriting the history.

**The specialization group label**

- **FR-027**: The server MUST compose the complete group label `field (by Dictionary)` and the client MUST render that label as received, appending nothing; `dictionary_label` MUST leave the group's payload shape, so no second consumer can compose the name again.
- **FR-028**: Escaping MUST be preserved where it already happens, and a name needing HTML escaping MUST be escaped exactly once between the payload and the DOT text.
- **FR-029**: A test MUST drive the server-produced payload through the client renderer, so that two independently correct-looking layer tests cannot hide the duplication.

**Governance**

- **FR-030**: Each corrected defect MUST be reintroduced in isolation, its targeted test confirmed to fail, unrelated tests in the run confirmed to pass, and the implementation restored; the drop-an-extra-property case MUST be among them, not only malformed input.
- **FR-031**: Declared-value identity, reference resolution by code, catalogue order, each kind's inheritance rules, lifecycle behaviour and specialization pairing MUST be preserved.
- **FR-032**: The change MUST NOT introduce a separate Python `Enum`, an additional generic parameter, a new resolver cleanup, or a change to specialization declaration syntax.
- **FR-033**: The two accepted remarks of the check run — the build's chunk-size advisory and the pending-deprecation warning — MUST NOT be acted on.

### Key Entities

- **Declaration**: one authored line `NAME = value(...)` inside a kind's class body, carrying the fields the value needs; it becomes an instance of the declaring type after class creation.
- **Placeholder**: what `value(...)` returns before the class exists; internal to the framework and never stored, returned or compared by a consumer.
- **Declared value**: a validated, shared, immutable instance of a dictionary or a state type, identified by its `code` and labelled by its `display_name`.
- **Reference form**: `{code, display_name, properties}` — what the framework emits for a value; the only form `to_reference()` produces, and JSON-compatible by contract.
- **Reference object**: `{code, display_name, properties}` as it arrives from a payload; the runtime resolves it by `code` and ignores the rest. The same members as a reference form, but an input, not an output.
- **ERD property item**: `{name, value}` — one property as the diagram payload carries it; both members are display strings.
- **Input schema** and **output schema**: two contracts for the same field, one describing what is accepted, one describing what is emitted.
- **Group label**: the text on a specialization group in the diagram, naming the axis field and the dictionary once.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 declarations using the class-name form remain in `packages/` and `examples/`, the demo included; the 373 declarations in 116 files measured on `e791ad28` are all on `value(...)`, every migrated example keeps its scenario, and the demo's own behaviour is unchanged.
- **SC-002**: 0 references to the removed namespace or metaclass remain in `src/`, `tests/` or `examples/`; the only Pydantic internal the declaration machinery touches is gone.
- **SC-003**: A declaration written with `value(...)` creates the same catalogue as the class-name form did: attribute access, `members`, `codes()`, `by_code()`, declaration order and `entity_type` are equal in 100 % of the migrated cases.
- **SC-004**: The four reproduced defects each have a dedicated test that passes, and the same test fails when the defect is reintroduced: a mutable property type accepted at declaration, a bypassed field serializer, a non-serializable export, and an input schema that rejects a code-only reference.
- **SC-005**: A property present in a saved graph appears in the rendered diagram for 100 % of the covered cases, including a value with a tuple property, a supported non-string property, a property whose value is `None` or an empty string, and a property containing `<`, `>` and `&`.
- **SC-006**: A group label contains the dictionary name exactly once, proven by a test that consumes the server payload.
- **SC-007**: The closing check run reports only the two accepted remarks, and the documentation pages named in Dependencies are reconciled in place, with no new tutorial series and no Russian draft.

## Assumptions

- **Two kinds, one factory.** Dictionaries and statuses keep sharing the declaration machinery; the difference between them — inherited catalogue, requirement to declare at least one value, the noun used in messages — is unchanged.
- **The placeholder is not public.** `value(...)` returns something the class consumes; a consumer never holds one, and no API promises its shape. It is documented as internal because the class-creation step is the only reader.
- **The migration count is a snapshot.** 270 declarations in 91 files outside the demo, and 103 in 25 demo files, were measured on `e791ad28`; declarations added before implementation change the count, not the rule.
- **The conversion hook stays.** Removing Pydantic's internals from the declaration mechanism does not mean removing the post-class conversion; the two are separable, and only the alias is removed.
- **Reference data is scalar by nature.** A declared value carries a code, a label and descriptive scalars; a dictionary of labels or a nested structure is reference data of another shape. Refusing mutable containers at declaration keeps the value immutable everywhere without a copy, and no dictionary in the measured corpus declares a `list` or `dict` property.
- **The reference form is JSON mode.** `to_reference()` produces what the value's JSON export produces, so the graph, the model's JSON output and any consumer of the reference share one shape. The model's Python-mode dump may keep a native value such as a date, and the pages say so; a caller that needs native values reads the instance, not the reference.
- **The card carrier is fixed.** PR #243's `{name, value}` list is the shape; this change verifies and completes it, and does not reintroduce the older `properties_json` string.
- **No rebuild is needed for display.** Properties already saved in a graph appear without a storage migration or a graph rebuild.
- **Maxitor learns no names.** As after #239 and #241, the card, the rows and the label come from the graph; no dictionary, kind or field name of AOA's enters the renderer.
- **The demo's behaviour is out of scope; its declarations are not.** The 103 declarations in 25 demo files migrate mechanically, because the alias cannot leave otherwise; the demo's demonstration code, scenarios and behaviour are neither investigated nor changed.
- **The check run is the arbiter.** The closing run is taken to zero, and the two accepted remarks remain the only exceptions, because they come from tools rather than from this repository's code.

## Dependencies

- The merged baseline `e791ad28`, and the declaration machinery in `declared_values.py`, `enum_entity.py` and `state_entity.py`.
- The reference validator, the model serializer and the JSON-schema hook on `BaseEnumEntity`.
- The graph export path that publishes a reference, and `packages/aoa-maxitor`'s payload action and DOT renderer.
- `specs/015-closed-dictionary-variants/contracts/dictionary-declaration.md` and the risk recorded in `specs/015-closed-dictionary-variants/plan.md`.
- The documentation that states the old contract: `docs/tutorials/step-20-entity.md`, `docs/tutorials/step-26-maxitor.md`, `docs/reference/glossary.md`, `docs/reference/intents-and-invariants.md`, `packages/aoa-maxitor/README.md`, the Maxitor component README and the changelog articles of `aoa-action-machine` and `aoa-maxitor`.

## Out of scope

- The demo's demonstration code, scenarios and behaviour; only its value declarations migrate, mechanically.
- A separate Python `Enum`, a new generic parameter, or any change to specialization declaration syntax.
- The `properties_json` string carrier proposed in #242, superseded by the merged `{name, value}` list.
- A storage migration or a graph rebuild for properties already saved.
- A broader resolver cleanup, and the other closed sets #203 lists.
- Russian drafts of any page written here.

## Deliberate exceptions to "no implementation detail"

The specification names `value`, `BaseEnumEntity`, `BaseStateEntity`, `to_reference()`, `members`, `codes()`, `by_code()`, `entity_type`, `properties`, `name`, `value`, `classifier_field` and `dictionary_label` because they are the names a model author writes, the fields a consumer reads and the names a test asserts. It also names module paths, file paths and measured counts in the Context, Dependencies and Out of scope sections, because the scope rests on them. No other module path, function name or framework internal appears in the requirements.
