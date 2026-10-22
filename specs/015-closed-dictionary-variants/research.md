# Research: a closed dictionary declares its variants

**Feature**: `specs/015-closed-dictionary-variants` | **Date**: 2026-10-22 | **Plan**: [plan.md](./plan.md)

Every decision below was measured against the tree at `70980156` and against the neighbouring feature `014-lifecycle-status-catalog`, which built the state kind's catalogue. Where the specification already fixed a decision, the research records the implementation choice that follows from it.

## D1 — The declaration machinery is shared as a mixin and a metaclass, never as a common ancestor

**Decision**: extract the state kind's machinery — the namespace that answers the class's own name with a factory, the placeholder, the post-model conversion hook, the catalogue and the duplicate refusal — into a kind-neutral module (`domain/declared_values.py`): a `_DeclaredValues` mixin that does **not** inherit `BaseEntity`, a `DeclaredValuesMeta(ModelMetaclass)`, a `ValueSpec` placeholder and a `value(**kwargs)` factory. `BaseStateEntity` and `BaseEnumEntity` each keep their own `__init_subclass__` (their suffix and, for the state, the graph exclusion) and inherit the mixin.

**Rationale**: `BaseEntity.__init_subclass__` recognises a kind base structurally — `BaseEntity in cls.__bases__` plus a local `__init_subclass__` — and refuses a class with two kind bases in one MRO. A shared ancestor that inherits `BaseEntity` directly would therefore be read as a seventh kind base and would break the single-kind rule from #210. A mixin plus a metaclass carries the same code without inheriting the entity base.

**Alternatives considered**: copying the machinery into `enum_entity.py` (two copies drift, and the specification asks for one mechanism); a shared `BaseVocabularyEntity(BaseEntity)` (breaks `_is_kind_base`, see above); a helper function called from each marker's hook (keeps the metaclass duplicated, since `__prepare__` cannot be shared by a function).

## D2 — Values are not inherited because the catalogue is built from `cls.__dict__` only

**Decision**: the conversion hook reads the placeholders declared in the class's own `__dict__` and builds `members` from them; a dictionary with no placeholders of its own gets an empty catalogue and, if decorated, is refused. `BaseStateEntity` keeps its present behaviour in the same hook by inheriting the parent's catalogue when it declares none — the difference is one conditional in the shared mixin, configured by the marker.

**Rationale**: aspects resolve through own-class declarations only; the specification requires the same for values. Building from `__dict__` is exactly the own-class rule, while `members` and `_by_code` remain `ClassVar`s, so a subclass starts empty instead of inheriting.

**Alternatives considered**: a `_inherit_values: ClassVar[bool]` flag read by one hook (chosen — one hook, two configured behaviours); two separate hooks (duplicated conversion); refusing any subclass of a dictionary (contradicts the decision recorded in the specification: a subclass is a different dictionary, not a forbidden one).

## D3 — The dictionary type is a Pydantic core schema that accepts a code or a declared instance

**Decision**: `BaseEnumEntity.__get_pydantic_core_schema__` returns a plain validator plus a serializer: the validator accepts a declared instance (identity-checked against `members`) and its reference object `{code, display_name, properties}`, which it resolves by `code`; it refuses an unknown code, a constructed copy and a bare code string. The serializer emits the same reference object, `properties` holding the extra declared fields. `__get_pydantic_json_schema__` publishes that object shape so OpenAPI and the graph agree.

**Rationale**: the field's type must be the dictionary (FR-008), and the wire carries the value whole (FR-010) while the code is authoritative on read (FR-011). A core schema is the only place where a type can both accept two input shapes and emit one output shape; a per-field validator would have to be repeated on every referencing field and would not cover the graph.

**Alternatives considered**: a `CodeOf[...]` marker (the specification's Assumptions record it as unnecessary once the dictionary is the type); `model_validator` on every entity (repeated, forgettable); accepting only instances (a JSON payload carries a code, and every adapter would have to resolve it).

## D4 — The container names the dictionary, and the head carries no classifier field

**Decision**: `Specialization[T, D]` takes the dictionary as its second type argument; the head declares `kind: Specialization[FirstPressSpecEntity | RepressSpecEntity, EditionKindEnumEntity]` and carries neither a classifier field nor a head-side `Classifier`. The build reads `D` from `__pydantic_generic_metadata__["args"][1]`, unwrapping `Optional`. Each extension writes `Classifier(field="record", variant=EditionKindEnumEntity.FIRST)`.

**Rationale**: the classifier field and the container's `variant` were two statements of one fact — which variant a row is — and nothing kept them together. With the dictionary as a type argument the fact has one home, the head's field list loses a column that was a selector rather than an attribute, and the axis's code set is visible in the head's annotation. The extension still names its field and its value, because a reader — human or agent — must see both in the declaration itself.

**Alternatives considered**: the separate classifier field typed by the dictionary (`kind_code: EditionKindEnumEntity`, `Classifier(field="kind_code")`) — the form the earlier draft carried; it keeps the two-homes defect and adds a column to every card. A head-side `Classifier` without a field — refused, because it hides which field is the axis. A bare code on the container — refused, because the code is a storage fact, not a model one.

## D5 — The graph carries values on the dictionary node and a reference on the field

**Decision**: the `Entity` node's `properties` gains `values` (an array of `{code, display_name, properties}`), required when `entity_kind` is `enum` via an `if/then` branch in `GRAPH_JSON_SCHEMA`. The `EntityField` node's properties gain an optional `reference_qualname` — the dictionary's interchange id — set when the field's annotation is a `BaseEnumEntity` descendant, so a consumer can draw the field as a reference instead of a scalar column.

**Rationale**: values are the dictionary's declaration data, not vertices (FR-015); the ERD needs a machine-readable way to recognise a reference (FR-016), and reusing the existing `EntityField` row keeps the `entity_field` edge model unchanged. A new node type per value, or a relation edge for a reference, would claim identity or ownership the value does not have.

**Alternatives considered**: graph nodes per value (rejected in the specification and in #241); a relation edge `reference` to the dictionary node (would imply ownership and add edges that the domain ERD would have to filter); a naming convention on `field_type` (`"EditionKindEnumEntity"`) only (fragile: a scalar field could name a model class for a JSON blob).

## D6 — The specialization checks join the existing per-axis pass, vocabulary first

**Decision**: `_validate_axis_vocabulary(axis)` runs first in `_validate_axis` and refuses a head field whose second type argument is not a decorated, non-empty dictionary; a `Literal` or a restated code set on the head; an extension whose `variant` is not a declared value of that dictionary or is a copy; and an extension whose `field` is not a `Generalization[…]` field of that head. `_validate_codes_match` then compares the catalogue with the alternatives two-sided, in the declaration order of the dictionary. The classifier-field rules (`_validate_classifier_field`, `_validate_one_axis_per_classifier`, `_validate_codes_fit_classifier`) are deleted with the field.

**Rationale**: the vocabulary rules are the causes of the symptoms the later rules would report, so they run first. The pass already runs once per build in `NodeGraphCoordinator.build()`, and a model with no axis returns without touching anything. Deleting the classifier rules is not a loss of rigour: the facts they checked (the field exists, is scalar, is not the axis, fits the codes) no longer exist.

**Alternatives considered**: a new validator module (a second walk, and two places to keep in step); a class-creation check (impossible: the head is declared before its extensions, and the annotation is a forward reference until Pydantic resolves it — recorded in the specification).

## D7 — The corpus migrates by codemod that derives each dictionary from the axis's existing `Literal`s

**Decision**: one AST codemod rewrites `.py` files and the code cells of `.ipynb` files. For each axis it reads the head's `codes=Literal[...]` and each extension's single code, generates one `<Head>KindEnumEntity` class above the head with one value per code (`display_name` derived from the code by title-casing and replacing underscores), deletes the head's classifier field, adds the dictionary as the second type argument of the head's specialization field, drops the head's `Classifier`, and replaces each extension's `Classifier("field", Literal["code"])` with `Classifier(field="field", variant=<Class>.<VALUE>)`. Constructions and payloads that set the deleted field move the code inside the container. The generated class is placed beside the head in the same module and carries `@entity` with the module's domain. The negative examples that assert the replaced rules are rewritten by hand.

**Rationale**: 110 axes across 45 files and 38 notebooks cannot be migrated by hand without drift, and the codes already exist in the `Literal`s, so the dictionary is derivable rather than invented. Deleting the field is mechanical because the head's construction sites are few per axis and the codemod reports every one it cannot rewrite.

**Alternatives considered**: hand migration (drift, and the diff cannot be reviewed); a shared `examples` fixture module holding every dictionary (each example is a standalone runnable script and stops being one); leaving the examples on `Literal` (the new rule refuses them, so the tree would not be green).

## D8 — The demo gets one dictionary in its own domain, and keeps its field names

**Decision**: add `packages/aoa-demo/src/aoa/demo/model/dictionaries/` with `DictionariesDomain` and `CurrencyEnumEntity` declaring `USD`, `EUR`, `RUB` (lowercase codes `usd`, `eur`, `rub`). The 25 currency fields keep their present names (`currency_iso`, `settlement_currency_iso`, `quote_currency_iso`) and change only their type and default (`sales_core.py`: `default=CurrencyEnumEntity.USD`).

**Rationale**: keeping the field names keeps the graph's field names, Maxitor's columns and the demo's screens stable; the change is about the type, not the naming. A dedicated domain says a shared dictionary is not owned by one business domain, which is the point of the kind; the sidebar gains one domain node, which is the honest picture.

**Alternatives considered**: putting the dictionary in `billing` (implies ownership and makes the other domains look like guests); renaming the fields to `currency` (a gratuitous wire change, and Maxitor columns would move for no reason); the 15 `*_iso` date fields and `issuer_bin_country_iso` (not currency references — recorded in the specification).

## D9 — Maxitor reads the dictionary from the payload it already receives

**Decision**: `ListEntitiesAction` selects `entity_kind`, the node's `values` and each field's `reference_qualname` into the existing slice payload; the client's `ErdEntity` gains `values` and `ErdField` gains `reference_qualname`; the ERD card renders the value rows, the field renders as a reference, and the specialization container label uses `dictionary_label` from the edge. No endpoint, no table and no column is added.

**Rationale**: the payload is one round trip and already carries the entities of the selected domains; the values belong to the dictionary's node, so they arrive with it. Nothing in the rendering names a dictionary, a kind or a value.

**Alternatives considered**: a new `list-dictionary-values` endpoint (a second request per card); storing values in a DuckDB table of their own (a table for rows that never change); rendering values as nodes (rejected in the specification).

## D10 — Codes are free-form, compared exactly, and the demo writes them lowercase

**Decision**: `code` is a non-blank string with no pattern beyond non-emptiness; comparison and lookup are exact. The demo's codes are lowercase (`usd`), matching the wire style of `entity_kind`; the existing example's `code="EUR"` becomes `eur`.

**Rationale**: the state kind imposes no pattern beyond non-emptiness, and a pattern would be a second contract for the same kind of value. Lowercase in the demo keeps codes readable in the graph and in the ERD's value rows.

**Alternatives considered**: a lowercase pattern on every code (refuses legitimate codes such as ISO-4217 uppercase `EUR`); case-insensitive lookup (two codes could differ only by case, so uniqueness would become ambiguous).

## D11 — Evidence is a scan and a before/after graph, as in `014`

**Decision**: add `specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py` (counts: dictionaries, values, currency fields, `Classifier(…, Literal[…])` per area, axes per area) and `baseline.before.json` / `baseline.after.json` holding the demo graph's `enum` node, its values, the reference fields and the axis edges; `compare_baselines.py` reports a named difference or identity, as `014` did for its state rows.

**Rationale**: the specification's success criteria are counts and graph facts; the evidence script makes both assertable and makes an accidental graph change visible in review.

**Alternatives considered**: asserting only through tests (a missing reference field would be invisible when no test covers the domain); a manual diff of the JSON (unreviewable at this size).

## D12 — The documentation and the examples are part of the delivered change, with notebooks

**Decision**: the dictionary case and the reference case are shown in the existing `examples/step_20_entity/07_enumeration.py` and its notebook, rewritten in place; the axis case is shown by the migrated `step_20_entity/06_specialization.py` and `step_21_relations` series, whose notebooks are rewritten by the same codemod and executed after the migration. No new example series is added; one new script+notebook pair is not created, because the three cases live in pages that already exist.

**Rationale**: the constitution requires each case twice, and the cases here replace the content of pages that already exist rather than introducing a new subject; rewriting in place keeps the reader's path and the `examples` index stable. The affected notebooks are executed, because a notebook that was only edited is a claim.

**Alternatives considered**: a new `step_20_entity/07a_closed_dictionary` pair (a second page for the same subject, and the old page would still show the replaced contract).

## D13 — The container holds a value, and checks the pair

**Decision**: `Specialization[T, D]` is a frozen Pydantic model whose `variant: D` accepts a declared value or its reference object `{code, display_name, properties}`; a bare string is refused by the dictionary's core schema, which only builds the reference form. A model validator compares `type(entity).declared_variant` with `variant` when `entity` is not `None` and refuses a mismatch. `BaseSpecEntity` exposes `declared_variant`, derived in its Pydantic init hook from its own `Generalization[…]` + `Classifier(variant=…)` declaration.

**Rationale**: the container is the one place where the value and the hydrated row meet, so it is the one place where they can disagree; one comparison closes it. Deriving `declared_variant` reads the existing declaration instead of introducing a second one, and keeps the check in the domain layer, away from the graph's validator.

**Alternatives considered**: validating in the resource (the rule then lives in every resource and is absent from hand-built objects); not validating (a mismatch surfaces far from its cause); a hand-written `variant` class attribute on each extension (a second copy of the code, exactly what the feature removes).

## D14 — The stored code is read by the resource, never by the model

**Decision**: storage keeps a column holding the code; its name is not fixed and the resource maps it to the entity field explicitly (`build` with a mapper). The resource resolves the code with `by_code`, wraps `KeyError` into a domain error naming the row, the field, the code and the declared set, picks the extension class whose declaration carries that code, and passes the declared value into the container.

**Rationale**: the model must not accept a code (D4, and Q3 of the design conversation), and the catalogue's `by_code` already raises; the wrapper is three explicit lines in the resource, which is where data meets the model — no new framework abstraction, and the message still names everything a reader needs.

**Alternatives considered**: a framework-level `resolve_declared_value(...)` helper (one implementation, but a new public concept for three lines); letting the container accept a code and resolve it (rejected: the code would reach the model); trusting the resource to raise `KeyError` raw (a message that names neither the row nor the field).
