# Feature Specification: A dictionary-typed field is a declared reference, and the graph carries it as an edge

**Feature Branch**: `feature/issue-256-dictionary-reference`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/256 — A dictionary-typed field declares a reference, and the graph carries it as an edge, not a silent column. #249 refuses a bare structural-entity field, but a `BaseEnumEntity` descendant is outside the rule: it passes unjudged, the graph gives it an `entity_field` row and no edge, and a collection does not even carry `reference_qualname`. Closes the dictionary gap left by #249, with the Enum kind entering the rule, the reference becoming an edge, the ERD drawing it, and three diagnostic texts corrected."

## Context: what is true today, measured on 2026-10-23 at `d1f28968`

- **The rule does not see the dictionary.** `_kind_of` classifies Core, Assoc, Detail, Spec and State only, so a field typed by a `BaseEnumEntity` descendant falls through and `_check_field` returns without a judgement. Measured on the merged baseline with a model holding `region: RegionEnumEntity` and `regions: tuple[RegionEnumEntity, ...]`:

  ```text
  validator: passed
  row id       type=str                               reference_qualname=None
  row region   type=RegionEnumEntity                  reference_qualname=RegionEnumEntity
  row regions  type=tuple[RegionEnumEntity, Ellipsis]  reference_qualname=None
  edges: ['domain', 'entity_field']
  ```

  The same bare shape for a structural entity is refused by #249. The existing tests codify the gap: `OrdinaryCoreEntity` is documented as "Keep every form the rule leaves alone" and carries `currency: CurrencyEnumEntity`, and `test_the_embedded_marker_is_refused_on_a_dictionary` refuses `NoRelation` on a dictionary, so today the bare type is the only form a dictionary field has.
- **The graph has no edge for the reference.** The output above lists `domain` and `entity_field` only. A consumer walking edges cannot find the dictionary the model declares, and the ERD prints the reference as text inside the column (`→ RegionEnumEntity`) rather than drawing a link to the dictionary card.
- **A collection of dictionary values loses even the reference property.** `declared_dictionary()` unwraps `Annotated` and `| None`, not a collection, so `regions` is a column that is not recognizable as a reference at all: no `reference_qualname`, no arrow, no distinct rendering.
- **An empty catalogue is refused only in the graph edge and only for two forms.** `EntityFieldGraphEdge._refuse_empty_dictionary` sees `D` and `D | None`, not a collection, and the refusal happens after the declaration boundary.
- **The affected corpus is measurable.** The reporting model has **9** dictionary-typed fields — `OfferCoreEntity.industry`, `OfferCoreEntity.barrier`, `OfferCoreEntity.regions` (`tuple`), `PlayerCoreEntity.gender` (`| None`), `ShowcaseCoreEntity.industries` (`tuple`), `GameCoreEntity.genre`, `UserEventLoginSpecEntity.platform`, `UserEventNewProfileSpecEntity.gender` (`| None`), `UserEventChangeProfileSpecEntity.gender` (`| None`). This repository has **60**: 26 in `packages/aoa-demo`, 23 in `examples/`, 11 in tests; every one is a bare type or `| None`, and no collection-of-dictionary field exists in the corpus. The counts are snapshots to refresh at the start of implementation.

## Clarifications

### Session 2026-10-23 — decisions carried from issue #256

- **D-1 — The bare dictionary type stays the declared reference form.** #241 decided it: "The type of a field that references a value? The dictionary type itself: `currency: CurrencyEnumEntity`. Not `str`, not `Literal`, not a marker." The rule therefore judges the field and accepts the bare form; it does not ask the author to wrap a type that already says what the field is. A wrapper such as `Reference[D]` would restate the type and migrate 60 declarations without adding information. If the maintainer chooses the explicit container instead, only the legal-form table and the migration count change; the graph, ERD and diagnostic work is identical.
- **D-2 — A collection of dictionary values has no declared form and is refused.** A column cannot hold many codes, and a many-reference would silently invent a join table the model does not declare. The reporting model's `regions` and `industries` are the two fields that change; the corpus has none.
- **D-3 — The reference is carried as a typed edge, not only as a column property.** #249's defect is precisely "the graph gets a `field` row and no relation edge". A property on a column is not a relation, so the reference must be reachable by walking edges.
- **D-4 — `NoRelation` stays refused on a dictionary, with a corrected message.** The marker declares an embedded structural entity; a dictionary reference is already declared by its type, so the refusal must say that instead of implying the marker belongs to another kind.
- **D-5 — A relation container around a dictionary type is refused.** A shared value is not an association target; `AssociationOne[CurrencyEnumEntity]` must not become a second way to say what the bare type says.
- **D-6 — The empty catalogue is refused at the declaration boundary in every form.** The graph edge keeps no copy of the rule.
- **D-7 — The reference edge coexists with the field row.** The code column exists in storage, so the `entity_field` row stays; the edge is added. The same reference is not printed twice on the card.
- **D-8 — A reference to a dictionary outside the graph is refused at the declaration boundary.** A dictionary marked `@exclude_graph_model` has no node, so the edge would have a dangling target and the coordinator would fail referential integrity; the declaration boundary must name the field and the dictionary instead.
- **D-9 — The state kind is untouched.** A state entity keeps its own refusal and the `Lifecycle[...]` form; this change adds one kind to the rule and does not reshape the existing three form sets.
- **D-10 — The three diagnostic defects found in the same pass are fixed in text only.** A union of two structural entities, a heterogeneous collection and a mapping already refuse; only the wording is wrong, and no behaviour is added.
- **D-11 — The edge name and its properties are proposals.** The spec fixes the meaning; the plan fixes `entity_reference`, the cardinality property and the payload field names.

### Session 2026-10-23 — clarifications

- Q: Does the rule require a wrapper for a dictionary reference, as it does for a structural entity? → A: No. The structural bare type is ambiguous — it may be a relation or an embedded value — so #249 refuses it and asks which one. A dictionary bare type is not ambiguous: #241 makes it the reference. The rule judges the field, accepts the reference, and refuses only the forms that declare nothing (a collection) or declare the wrong thing (a relation container).
- Q: Does the reference edge replace the field row in the ERD? → A: No. A relation replaces the column because the column is not the relation; a dictionary reference is stored as a code column, so the row stays and the edge is added. The card must not print the same reference twice: the row keeps its type text, and the edge draws the link to the dictionary card.
- Q: What happens to a field whose dictionary lives in another domain? → A: The reference is still a reference. The ERD slice must include the referenced dictionary when a neighbour is requested, or the reference must be visibly unresolved; a slice must not draw an arrow to a card it did not include.
- Q: Is `reference_qualname` kept now that an edge exists? → A: Yes. It is the row-level identity that the payload, the schema and the renderer already consume, and the edge is additional evidence, not a replacement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A dictionary-typed field is judged by the entity-field rule (Priority: P1)

A model author declares a field whose type is a dictionary. The bare type and the optional type are accepted as the declared reference, exactly as #241 says. A collection of dictionary values, a relation container around a dictionary, and a dictionary with no catalogue are refused before a graph is published, and the message shows the form that works. A `NoRelation` on a dictionary is refused with a message that says the bare type already declares the reference.

**Why this priority**: This is the gap the issue opened with. Today every dictionary shape passes unjudged, including the two collection fields in the reporting model, which no longer carry even the reference property. The rule must see the kind before any graph work can be trusted.

**Independent Test**: Declare a model with one field per row of the form table — bare, optional, `tuple`, `Sequence`, `frozenset`, `dict`, each relation container, `NoRelation`, an empty catalogue, an inherited field and a forward reference. Confirm each row is accepted or refused exactly as the table says, and that every refusal names the owner, the field, the resolved dictionary and the legal form.

**Acceptance Scenarios**:

1. **Given** a field annotated with a concrete dictionary type, **When** the model graph is built, **Then** the field is accepted as a reference and no refusal is raised.
2. **Given** the same field written `D | None`, **When** the model graph is built, **Then** it is accepted on the same terms.
3. **Given** a field annotated `tuple[D, ...]`, `list[D]`, `Sequence[D]`, `set[D]`, `frozenset[D]` or `dict[str, D]`, **When** the model graph is built, **Then** it is refused, and the message names the field, the dictionary and the two accepted forms, and does not offer a relation container.
4. **Given** a field annotated with any of the eight relation containers whose type argument is a dictionary, **When** the model graph is built, **Then** it is refused with a message stating that a dictionary value is a shared reference, not an association target.
5. **Given** a field annotated `Annotated[D, NoRelation("reason")]`, **When** the model graph is built, **Then** it is refused, and the message says the bare dictionary type already declares the reference.
6. **Given** a field typed by a dictionary that declares no values, in any of the accepted or refused forms, **When** the model graph is built, **Then** it is refused at the declaration boundary with a message naming the field and the dictionary.
7. **Given** a dictionary-typed field inherited from a base class or named through a forward reference, **When** the graph is built, **Then** the same judgement applies after resolution.
8. **Given** a class outside the graph, **When** the graph is built, **Then** it is not judged, exactly as #249 decided.

---

### User Story 2 - The graph carries the reference as an edge (Priority: P1)

A consumer walks the published graph and finds the dictionary a field references: a typed edge from the host entity to the dictionary entity, named by the field. The field row stays and keeps `reference_qualname`. The graph's JSON schema declares the edge, and a slice that asks for neighbours includes the referenced dictionary.

**Why this priority**: A column property is not a relation. #249 exists because the graph described a column where the model declared an entity field; the dictionary case is the same defect and must be closed the same way.

**Independent Test**: Build the graph for the reproducer model, walk the edges, and confirm the reference edge exists with the field name and the dictionary as its target; validate the graph document against its schema; read `reference_qualname` on the row; then repeat for an inherited field, a forward reference and a dictionary in another domain.

**Acceptance Scenarios**:

1. **Given** a model with a dictionary reference, **When** the graph is published, **Then** an edge from the host entity to the dictionary entity exists and carries the field name.
2. **Given** every accepted form, **When** the graph is published, **Then** the field row carries `reference_qualname` naming the same dictionary the edge targets.
3. **Given** the graph document, **When** it is validated against the graph JSON schema, **Then** the reference edge and its properties are declared, and the document validates.
4. **Given** a dictionary-typed field inherited from a base class or named through a forward reference, **When** the graph is published, **Then** the reference edge exists for it exactly as for a field declared on the class itself.
5. **Given** a dictionary marked outside the graph, **When** a field references it, **Then** the declaration is refused with a message naming the field and the dictionary, and the build never reaches referential integrity with a dangling target.
6. **Given** a dictionary that also classifies a specialization axis, **When** the graph is published, **Then** both the reference edge and the axis edge exist and neither is mistaken for the other.
7. **Given** two dictionaries with the same short class name in one graph, **When** the graph is published, **Then** each reference edge targets its own dictionary and the payload does not confuse them.

---

### User Story 3 - The ERD shows the reference (Priority: P2)

A reader of the ERD sees the dictionary card and a link from the field to it. The field row stays with its type and its reference, the dictionary card keeps the #249 behaviour — labels, no code, the code in a tooltip — and a non-dictionary entity's rows are unchanged.

**Why this priority**: The display follows the model. It is bounded and can ship after the rule and the graph, but it is what the maintainer actually looks at, so it is in this change rather than a later one.

**Independent Test**: Produce the payload for a domain containing a host and its dictionary, validate it against the payload schema, render the DOT source and the SVG, and check the printed text, the tooltip and the payload separately; then repeat with the dictionary in another domain and with `include_neighbors` on and off.

**Acceptance Scenarios**:

1. **Given** a dictionary reference in the graph, **When** the payload is produced, **Then** the reference is present in the payload and the field row keeps its `reference_qualname`.
2. **Given** the rendered card, **When** the reader looks at the field row, **Then** the reference is visible and printed once, not twice.
3. **Given** the dictionary card, **When** it is rendered, **Then** the #249 behaviour is unchanged: no `code` row, no `display_name` row, no code cell in a value row, and the code on hover.
4. **Given** a non-dictionary entity, **When** it is rendered, **Then** its rows are unchanged.
5. **Given** a dictionary in another domain and a slice that includes neighbours, **When** the payload is produced, **Then** the dictionary card is included and the reference resolves; with neighbours off, the reference is visibly unresolved rather than pointing at an absent card.
6. **Given** a graph saved before this change, **When** it is rendered, **Then** it still renders, and a reference that the old graph carries only as `reference_qualname` does not break the card.

---

### User Story 4 - A refusal names the shape that is wrong (Priority: P3)

A model author who writes a union of two structural entities, a heterogeneous collection or a mapping gets a message about that shape, not a message that calls every one of them a collection and offers a many-relation.

**Why this priority**: No behaviour is wrong today — these forms already refuse — but the message sends the author to a form that does not fit. It is cheap, in the same validator, and independent of the dictionary work.

**Independent Test**: Declare `A | B` for two structural entities, `tuple[A, B]`, and `dict[str, A]`; confirm each is refused and that each message names the actual shape and the form that applies.

**Acceptance Scenarios**:

1. **Given** `A | B` for two structural entities, **When** the graph is built, **Then** the refusal names both entities and asks for two fields, and does not describe the union as a collection.
2. **Given** `tuple[A, B]` for two different structural entities, **When** the graph is built, **Then** the refusal names the collection and both entity types, and does not offer a many-relation to a single one of them.
3. **Given** `dict[str, A]`, **When** the graph is built, **Then** the refusal describes a mapping and offers a form that fits.
4. **Given** the three shapes above, **When** the change is applied, **Then** none of them becomes accepted.

### Edge Cases

- A dictionary reference in an entity excluded from the graph: the class is not judged, exactly as #249 decided, and no edge is published for it.
- A field referencing a dictionary excluded from the graph: refused at the declaration boundary (D-8), never a dangling edge.
- A dictionary reference inside a `Spec`, `Assoc` or `Detail` host: judged and carried exactly as on a Core host.
- A dictionary reference on a class whose graph build is triggered before the dictionary class is loaded: the unresolved name is not treated as a scalar, and the judgement happens after resolution.
- Two dictionaries with the same short class name, referenced from one or two hosts: each edge and each `reference_qualname` names its own qualified type.
- A dictionary that is also the vocabulary of a specialization axis: the reference edge and the axis edge coexist.
- A dictionary reference with `default=None` on a nullable field and one without a default: both are the reference form; the default rules of #249 bind relation containers, not dictionary references, and the spec does not add new default rules for them.
- A dictionary reference on a field annotated through `Annotated` metadata that is not a relation marker: the reference is judged on the resolved inner type, and unrelated metadata is ignored.
- A dictionary whose catalogue is empty, referenced twice from one host: both fields are refused, and the message names the dictionary once per field.
- A dictionary reference in a graph slice that requests neighbours: the dictionary is included; without neighbours, the reference is present in the data but the card is absent, and the renderer must not invent it.
- A field whose type is a dictionary and whose name suggests another meaning (`currency_iso`): the rule reads the type, never the name.
- A dictionary reference in a legacy graph saved before the change, present only as `reference_qualname`: the card renders without a rebuild.
- A union of two structural entities, a heterogeneous collection and a mapping: refused by shape, with a message that names the shape.

## Requirements *(mandatory)*

### Functional Requirements

**The dictionary kind enters the rule**

- **FR-001**: A field whose resolved type is a `BaseEnumEntity` descendant MUST be judged by the entity-field rule on the same boundary as the structural kinds — bare, optional, under `Annotated`, and inside a collection. It MUST NOT pass unjudged as it does today.
- **FR-002**: The bare form `D` and the optional form `D | None` MUST be accepted as the declared reference form, in line with #241, and MUST NOT be refused; the framework MUST NOT require a wrapper that restates the type.
- **FR-003**: A collection of dictionary values — `tuple[D, ...]`, `list[D]`, `Sequence[D]`, `set[D]`, `frozenset[D]`, `dict[K, D]` — MUST be refused with a message naming the owner, the field, the resolved dictionary and the two accepted forms, and MUST NOT offer a relation container.
- **FR-004**: A relation container of the existing eight (`AssociationOne`/`AssociationMany`, `CompositeOne`/`CompositeMany`, `AggregateOne`/`AggregateMany`, `Specialization`, `Generalization`) whose target is a dictionary type MUST be refused with a message naming the field and stating that a dictionary value is a shared reference, not an association target.
- **FR-005**: `NoRelation("reason")` on a dictionary MUST stay refused, and the message MUST say that the bare dictionary type already declares the reference, rather than implying the marker belongs to another kind.
- **FR-006**: A field typed by a dictionary with no declared values MUST be refused at the declaration boundary in every form — accepted or refused — with a message naming the field and the dictionary. The graph edge MUST NOT keep its own copy of that rule. When a dictionary is both empty and outside the graph, the empty-catalogue refusal is the one reported, because it names the cause the author can fix.
- **FR-007**: The judgement MUST apply after resolution, to inherited fields, forward references and `Annotated` forms, and MUST NOT judge a class outside the graph, exactly as #249 decided.
- **FR-008**: The rule MUST read the resolved type only. No annotation string may be evaluated, and no relation or reference may be inferred from a field's name.
- **FR-009**: The dictionary kind MUST be distinguishable from Core, Assoc, Detail, Spec and State in the classification the rule uses, so a future kind is added in one place and a dictionary is never silently treated as one of the existing kinds.

**The graph carries the reference**

- **FR-010**: Every accepted dictionary reference MUST produce a typed edge from the host entity to the dictionary entity in the published graph, carrying the field name. Walking the published edges MUST find the reference; a property on a column alone MUST NOT be treated as the carrier.
- **FR-011**: Every accepted dictionary reference MUST carry `reference_qualname` on its field row, naming the same dictionary the edge targets.
- **FR-012**: The field row MUST remain beside the edge, because the code column exists; the edge MUST NOT replace the row or remove the reference property.
- **FR-013**: The graph JSON schema MUST declare the reference edge and its properties, and a published graph carrying a dictionary reference MUST validate against it.
- **FR-014**: The reference edge's target MUST be a node of the published graph. A dictionary marked outside the graph MUST be refused at the declaration boundary with a message naming the field and the dictionary, and MUST NOT surface as a referential-integrity failure of a dangling target.
- **FR-015**: The reference edge MUST remain distinct from a specialization axis edge that names a dictionary; a graph carrying both MUST keep both, each resolved to its own target.
- **FR-016**: The reference MUST be visible in the graph regardless of the host's kind, the dictionary's domain, or whether the field is inherited or reached through a forward reference.

**The ERD shows the reference**

- **FR-017**: The ERD payload MUST expose the reference so the card can draw the link between the field and the dictionary card, and MUST keep `reference_qualname` on the field row for existing consumers.
- **FR-018**: The rendered card MUST keep the field row, which prints the dictionary name once as the reference, and the reference edge MUST be labelled with the field name; the same text MUST NOT be printed twice. The dictionary card MUST show exactly one link from the field to the dictionary.
- **FR-019**: The dictionary card's #249 behaviour MUST be unchanged — no `code` and no `display_name` field rows for the enum kind, no code cell in a value row, and the code available as a tooltip.
- **FR-020**: A non-dictionary entity's rows MUST be unchanged, and a legacy graph that carries the reference only as `reference_qualname` MUST render without a rebuild.
- **FR-021**: A graph slice that requests neighbours MUST include a referenced dictionary from another domain; without neighbours, the reference MUST remain unresolved rather than point at a card the slice did not include.
- **FR-022**: The payload schema, the payload tests and the renderer checks MUST be updated to the final behaviour, and the graph document MUST keep carrying the reference.

**A refusal names the shape that is wrong**

- **FR-023**: A union of two structural entities MUST be refused with a message naming both entities and asking for separate fields, and the message MUST NOT describe the union as a collection.
- **FR-024**: A heterogeneous collection of structural entities MUST be refused with a message naming the collection and every entity it holds, and MUST NOT offer a many-relation to one of them as the only form.
- **FR-025**: A mapping whose value is a structural entity MUST be refused with a message that describes a mapping, and MUST NOT offer a many-relation as the form.
- **FR-026**: These three corrections MUST change text only: none of the shapes becomes accepted, and every other refusal keeps its current behaviour.

**Verification and delivery**

- **FR-027**: Each corrected defect and each new refusal MUST be reintroduced in isolation, its targeted test confirmed to fail while an unrelated control test in the same run passes, and the implementation restored.
- **FR-028**: The reproducer's shapes MUST become a checked regression in the repository's own suite — the same model the quickstart uses: `region` accepted with a reference edge, `regions` refused with the collection message, and no dictionary-typed field passing the rule without a judgement.
- **FR-029**: The repository check run MUST be taken to zero, and the two accepted remarks — the build's chunk-size advisory and the pending-deprecation warning — MUST NOT be acted on.
- **FR-030**: English documentation MUST be reconciled in the same change — at least `docs/how-to/explicit-entity-fields.md`, whose boundaries paragraph says "Dictionary references ... retain their own forms", and `docs/reference/intents-and-invariants.md`, whose dictionary graph row says "references carry `reference_qualname`; values are not separate nodes" — together with the dictionary tutorial, the ERD example and each affected package's changelog article.
- **FR-031**: The corpus MUST be re-measured at the start of the phase and recorded in the plan: the repository's 49 non-test dictionary fields (26 in `packages/aoa-demo`, 23 in `examples/`) plus 11 in tests, and the reporting model's 9. Under D-1 no corpus declaration changes; under the alternative in D-1 all of them do.
- **FR-032**: The change MUST NOT add a new default rule, requiredness rule or description rule for dictionary references; the reference is judged on its type, and the #249 relation-field contract does not extend to it.

### Key Entities

- **Dictionary reference**: a field whose resolved type is a `BaseEnumEntity` descendant, optionally nullable; the declaration of a field that holds a declared value of that dictionary.
- **Reference edge**: the typed graph edge from the host entity to the dictionary entity, carrying the field name, published beside the field row.
- **Field row**: the `entity_field` row that represents the stored code column, carrying the field's type and its `reference_qualname`.
- **Field form table**: the accepted and refused shapes of a dictionary-typed field — bare, optional, collection, relation container, embedded-value marker, empty catalogue.
- **Diagnostic**: the refusal text, which must name the owner, the field, the resolved type and the form that applies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of the forms in the field-form table are judged — accepted or refused — and 0 dictionary-typed fields pass the rule without a judgement. Measured by a table-driven test with one case per row.
- **SC-002**: 0 of the 49 non-test dictionary fields in `packages/aoa-demo` and `examples/` produces a field row without a reference edge, and 0 test fields do either. The counts are re-measured at the start of the phase and recorded.
- **SC-003**: The repository's checked regression covers one accepted reference, one refused collection, one refused container, one refused marker and one refused empty catalogue, and each answer matches `quickstart.md`; the reporting model's 9 fields are the acceptance its owner runs against this build and are not claimed by the closing check run.
- **SC-004**: A graph document containing a dictionary reference validates against the graph JSON schema, and the edge count for the reproducer is the count the model declares.
- **SC-005**: The ERD payload and the rendered SVG show the reference once per field, the dictionary card keeps the #249 behaviour, and the payload, the graph document and the rendered text are checked separately.
- **SC-006**: 100 % of the three diagnostic cases (union, heterogeneous collection, mapping) name the actual shape, and none of them becomes accepted, confirmed by the same tests that refused them before.
- **SC-007**: Reintroducing the enum exclusion makes the targeted regression fail while a structural-entity control passes; the same holds for each diagnostic correction and for the dangling-target refusal.
- **SC-008**: The closing check run reports only the two accepted remarks, the named documentation pages are reconciled, each affected package's changelog has its article, and the refreshed corpus counts are recorded.

## Assumptions

- **D-1 holds: the bare dictionary type is the reference.** The 60 corpus declarations keep their annotations and their graphs gain an edge. If the maintainer chooses an explicit container instead, the legal-form table, the migration step and SC-002's count change; the graph, ERD and diagnostic work does not.
- **A collection of dictionary values is refused.** The two reporting-model fields are the only members of the corpus class; no corpus declaration is a collection of dictionaries.
- **The reference edge is additional, not a replacement.** The code column and `reference_qualname` stay, because storage and the payload already depend on the row.
- **The rule reads types, not names.** A field named `currency_iso` typed `str` stays a scalar; nothing here infers a reference from a name.
- **The state and structural form sets do not change.** The change adds one kind to the rule; it does not reshape what #249 decided for Core, Assoc, Detail, Spec and State.
- **The dictionary card is presentation from #249.** Its field list, value rows and tooltip are not part of this change except that they must keep working.
- **The two accepted check remarks are tool noise**, not findings of this repository, and are not acted on.
- **Naming is provisional.** `entity_reference`, the cardinality property and the payload field names are proposals for the plan; the requirements fix the meaning, not the spelling.

## Dependencies

- The merged #249 change (PR #251) and its boundary: `entity_field_validator.py`, `entity_field_graph_node.py`, `entity_field_graph_edge.py`, `entity_graph_node.py`, `graph_json_schema.py`, and the two intent resolvers.
- #241's decision that a field references a dictionary value by naming the dictionary type, and #244's reference, schema and card contracts that #249 finished.
- `packages/aoa-maxitor`'s `list_entities_action.py`, its payload schema, `buildDotSource.ts` and the client checks, together with `tests/test_list_entities_payload_dictionary.py` and `test_demo_dictionary_graph.py`.
- The documentation and examples that state the old behaviour: `docs/how-to/explicit-entity-fields.md`, `docs/reference/intents-and-invariants.md`, `docs/tutorials/step-20-dictionaries.md`, `examples/step_20_dictionaries/09_erd.py`, and the changelog articles of `aoa-action-machine` and `aoa-maxitor`.
- Issue [#256](https://github.com/bystrovmaxim/aoa/issues/256) and issue [#249](https://github.com/bystrovmaxim/aoa/issues/249).

## Out of scope

- The storage schema: the code column, its type and its foreign key are the resource's business.
- A many-reference form for a collection of dictionary values: refused here, and a later issue decides the shape if one is wanted.
- Dictionary provenance (`sourced_from="gender_codes"`).
- `BaseStateEntity` and the lifecycle machinery.
- A dictionary maintained in data: a different entity kind.
- Redesigning relation cardinality, ownership, inverse or specialization-consistency rules.
- Russian drafts of any page written here.

## Deliberate exceptions to "no implementation detail"

The specification names `BaseEnumEntity`, `NoRelation`, `AssociationOne`/`Many`, `CompositeOne`/`Many`, `AggregateOne`/`Many`, `Specialization`, `Generalization`, `Annotated`, `Lifecycle`, `reference_qualname`, `entity_field`, `entity_reference`, `@exclude_graph_model`, the eight relation containers and the cardinality property, because they are names a model author writes, values a consumer reads, or names a test asserts. It also names module, file and check paths and measured counts in the Context, Dependencies and Out of scope sections, because the scope rests on them. No other internal function, private attribute or framework detail appears in the requirements.
