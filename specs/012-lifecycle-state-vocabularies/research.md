# Phase 0 — Research: lifecycle states as objects

**Feature**: `specs/012-lifecycle-state-vocabularies` | **Date**: 2026-10-19

Every unknown in the plan's Technical Context is resolved below. Measurements were taken on this tree (branch `feature/issue-209-state-vocabularies`, from `main` at `17c6660f`) with runnable probes, not from the issue text; where the issue and the tree disagree, the tree is reported.

## R1 — Where the status type and the vocabulary are written

**Decision**: the axis class — `class SalesOrderLifecycle(Lifecycle, StateVocabulary)` with the statuses as class attributes of that class and the status type a module-level class beside it. No binding line, no generic parameter, no decorator, no nesting.

**Rationale**

1. The literal variant "status type *and* vocabulary inside the chain class" is impossible: a nested class body does not see the enclosing class namespace. Measured:
   `1) fully nested: NameError -> name 'SalesOrderStateEntity' is not defined`.
2. Variant B works and is the compact one: measured with a stub vocabulary, `L2.States.NEW` is the object and the chain builds.
3. Variant D (vocabulary inside the *entity* class, since statuses belong to the entity) is tolerated by pydantic — a nested plain class is not turned into a field, measured — but it creates an import cycle: the entity module already imports the chain for its lifecycle field, and the chain would import the entity for `.States`. The demo does not have that cycle today and this feature does not introduce it.
4. The axis class alone needs no link: the statuses and `_template` are in one body, so the check is structural. Measured: `members` are collected in declaration order, `by_code` works, the instance is a normal lifecycle (`current_state`, `can_transition`), and `_get_template()` finds the template. The measured leak — the mixin's dunders reach instances (`len(order.lifecycle) == 7`) — is why the API is plain methods only; the measured failure of a plain subclass (`ValueError: must declare at least one status`) is why a class with no members inherits them.

**Alternatives considered**

- **B, vocabulary nested in the chain class.** Workable; rejected as the default because every use outside the chain becomes `SalesOrderLifecycle.States.NEW`, and the chain class gains a second subject.
- **C, all three names at module level.** Workable; rejected because the "type belongs to the vocabulary" tie is then a convention rather than nesting.
- **D, vocabulary inside the entity class.** Rejected for the import cycle, not for the semantics.

## R2 — A plain class, not `enum.Enum`

**Decision**: `StateVocabulary` is a plain class with an `__init_subclass__` that collects status instances in declaration order, validates them, and builds the lookup.

**Rationale** — measured on the tree:

1. `class M(BaseStateEntity, Enum)` is impossible: `TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases`. So the enumeration cannot itself be the entity.
2. A nested class inside an `Enum` body becomes a member: measured members `[('Entity', ...), ('A', ...), ('B', ...)]`, with `DeprecationWarning: In 3.13 classes created inside an enum will not become a member`. "Declare the status type inside the enumeration" is exactly what the maintainer asked for, and `Enum` forbids it.
3. Members are reachable only as `.value`; the DSL and every external reader would need that indirection.
4. Two members with equal values collapse into an alias (`len == 1`), so duplicate-code detection and iteration would disagree in a corner the vocabulary must be able to explain.

**Alternatives considered**

- **`Enum` with the type outside.** Workable; rejected because it forbids the requested nesting and adds `.value` everywhere.
- **Module-level constants without a container.** Rejected: no iteration, no lookup, no duplicate check, and 32 flat namespaces.

## R3 — Exclusion from the model graph, automatic

**Decision**: `BaseStateEntity.__init_subclass__` marks every descendant with `exclude_graph_model`, so no status type can become an `EntityGraphNode`.

**Rationale**

1. Measured: an undecorated `BaseEntity` subclass fails graph node construction with `MissingEntityInfoError -> ProbeStateEntity has no usable @entity 'description'`. Because the base is loaded with the domain, a status type without exclusion breaks *every* graph build, not only the demo's.
2. The alternative — decorate each status type — is 32 chances to forget, and a forgotten one is a broken build.
3. The exclusion flag is read from the class's own namespace and is not inherited (measured); setting it in `__init_subclass__` gives exactly the "every status type, no exceptions" semantics without touching the inheritance rule.
4. A status type used as a field of another model remains a pydantic model and keeps serializing; only its appearance as a model-graph entity is prevented. The transport question is out of scope.

**Alternatives considered**

- **Per-class `@exclude_graph_model`.** Rejected: forgettable, and the failure is a build crash.
- **No exclusion, status entities become ERD nodes.** Rejected by the feature's decision 5: two representations of one thing, plus a synthetic `id` next to the code.

## R4 — All declared fields, under `properties.attributes`

**Decision**: the state row gains `properties.attributes` = `status.model_dump(mode="json")`, a nested object, and `GRAPH_JSON_SCHEMA` admits it as a free object inside the state row's otherwise strict envelope.

**Rationale**

1. Measured: `model_dump(mode="json")` returns all fields in declaration order, converts non-JSON types (`date` → ISO string), and honours `Field(exclude=True)` as an opt-out — so no field list is written by hand.
2. Nested, not spread: a status field may be named `state_key` or `lifecycle_class_id`, and spreading would silently overwrite the row's own fields. The envelope stays strict; the inside stays free, so a new domain field needs no schema change.
3. `code` and `display_name` are duplicated between the envelope and `attributes` on purpose: the rule is "all fields", without a special case.
4. A non-JSON-representable field fails at build time, in `mode="json"`, rather than producing a broken row.

**Alternatives considered**

- **Flat properties.** Rejected for collisions and per-field schema churn.
- **Only a curated list of fields.** Rejected: the maintainer asked for all pydantic fields, and a curated list drifts from the type.

## R5 — The state row keeps its identity, takes its label

**Decision**: the state row keeps its `id` (`<lifecycle node id>:<code>`) and its `node_type` (`StateInitial`/`StateIntermediate`/`StateFinal`), takes `label` from `status.display_name`, and gains `attributes`. `StateInfo` is untouched.

**Rationale**

1. Measured today: the row is `{"type": "StateIntermediate", "label": "payment_pending", "properties": {... "state_key": "payment_pending"}}` — the label is the key, although the chain declared `"Payment pending"`.
2. The FSM payload reads `display_name` from that label, so the diagram shows the key. Fixing the label fixes the diagram without touching the FSM's field names.
3. The kind comes from the chain (`initial`/`intermediate`/`final`); a status has no classification, and the same status may be classified differently by two chains.

**Alternatives considered**

- **Put the attributes in `label`.** Rejected: a label is a string; the diagram needs a word.
- **Change `StateInfo` to hold the object.** Rejected: the state metadata is a snapshot the graph and the runtime rely on; the chain already keeps the objects.

## R6 — Maxitor: store, payload, order, colour

**Decision**: `state.attributes JSON` in DuckDB (both insert paths and the `nodes` view), `attributes` per state in the FSM payload and its schema (optional), order by initial-first → `attributes.sort_order` → `key`, and the DOT builder uses `attributes.color` for the stroke and `attributes.fill_color` for the fill, falling back to the existing per-type palette.

**Rationale**

1. The diagram is served from the already-loaded DuckDB graph, and the design is explicit that this path must not import the service's classes — so the attributes must be in the store, not fetched from Python.
2. Order: measured today is `(state_type != "initial", key)`; a chain that thinks `new → payment_pending → confirmed` is drawn alphabetically. `initial` first is a drawing invariant; `sort_order` is a status property; the key is the tiebreak that reproduces today's order when nothing is declared.
3. The DOT builder already parametrises fill/stroke by state type (`paletteForStateType`); the declared colour is one lookup with a fallback, and with no attributes the source is byte-identical.
4. The FSM state item carries a **closed** attribute object. Measured: `JsonSchemaValue` requires an object branch to declare `properties` and `additionalProperties: false`, so a free-form `{"type": "object"}` is refused at import (`ValueError: ... must declare 'properties' as an object`). The wire therefore carries the presentation attributes only; the store keeps every field and the graph row exposes them whole.

**Alternatives considered**

- **Sort in the client.** Rejected: the payload already carries the attributes; the order is part of the answer, and two clients would each implement it.
- **Colour only in the payload, not in the drawing.** Rejected: the maintainer asked for the attributes to reach Maxitor, and a colour that does not colour anything is not reaching it.

## R7 — The DSL and the import cycle

**Decision**: `.state(status)` and `.to(*statuses)` accept status objects; the string form is accepted until phase 5 and then removed; `Lifecycle` keeps `_state_entities` and exposes `get_state_entity`/`get_state_entities`; the mixin checks every status in `_template` against the class's attributes; the DSL itself only unwraps a status to its code; `lifecycle.py` imports `BaseStateEntity` lazily inside the DSL methods.

**Rationale**

1. `entity.py` imports `Lifecycle` at module level (`entity.py:119`); a module-level import back from `lifecycle.py` would be a cycle. The lazy import sits on the declaration path only, not on `get_lifecycle_fields`, which is walked per field.
2. `mypy --strict` requires overloads for the two accepted forms; after phase 5 the overload set collapses to one.
3. Forward references stay allowed (a transition may name a status declared later), so the guard checks only the *type*, never that the target was already declared — the build rules own existence.
4. The mixin's template check catches the cross-axis mistake that the code identity alone cannot: two chains may share the code `cancelled`, so a foreign object would otherwise pass as a state key while carrying another chain's fields.

**Alternatives considered**

- **Validate target existence at declaration.** Rejected: it would forbid forward references, which the DSL has always allowed and the eight build rules already cover.
- **Infer the vocabulary from the lifecycle class name.** Rejected: a naming convention is not a type check.

## R8 — The corpus and the branch's sequence

**Decision**: 32 lifecycle declarations in 23 files under `packages/aoa-demo/src` — 28 named chains in 19 `*_lifecycle.py` files and 4 private cycle-sketch classes in the `*_stub.py` / `*_cycle_*.py` fixtures — with 98 `.state(...)` and 65 `.to(...)` calls, 68 transition pairs once the templates are read. All 32 move, because they all use the string form. The string form is kept until phase 5 so every phase leaves the tree green.

**Rationale**

1. Measured: `grep -rn "^class .*Lifecycle" packages/aoa-demo/src` → 32; `grep -rn "\.state(" packages/aoa-demo/src` → 90; `.to(` → 65.
2. The four private sketches are not chains anybody draws, but they declare states with the string form, so removing the form breaks them like the rest.
3. Ordering the work as "types and DSL (both forms) → state row → Maxitor → migration → removal" keeps every commit importable. A reviewer can judge the framework change without the 32-file migration in the same diff.

**Alternatives considered**

- **Remove the string form first.** Rejected: every commit before the migration would fail to import the demo, its tests and the examples.
- **One big commit with the removal and the migration.** Rejected: it mixes a framework change with a mechanical migration and hides a wrong code inside the noise.
