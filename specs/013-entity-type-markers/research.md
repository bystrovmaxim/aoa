# Phase 0 — Research: six markers, three refusals, one renamed corpus

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

Every decision below is taken against the code on the branch base, not against the issue's prose. The counts and probes are reproducible with the commands in this file.

## D1. How a marker is declared: `(BaseEntity, ABC)` plus one decorator

**Decision**: each of the six markers keeps the shape the issue names — `class BaseCoreEntity(BaseEntity, ABC)` — and carries one decorator, `@abstract_marker(EntityKind.CORE)`, which registers the class as a marker, marks it `exclude_graph_model`, and installs the instantiation guard.

**Rationale**: three things are needed at once, and only a decorator delivers all three without changing the bases: the registry must know the kind of each marker, the model graph must skip the marker (the entity inspector walks **every** loaded `BaseEntity` subclass and skips only those marked `exclude_graph_model` — `graph/core/base_graph_node_inspector.py:144`), and the marker must refuse instantiation.

**Alternatives considered**:

| Alternative | Why not |
| --- | --- |
| A common marker mixin as an extra base (`class BaseCoreEntity(_MarkerMixin, BaseEntity, ABC)`) | changes the base tuple the issue and the spec prescribe; makes `__bases__` reasoning harder for readers of the six declarations |
| `abc.abstractmethod` on each marker | forces every concrete entity to implement a dummy member; a marker states a role, not a protocol |
| `@model_validator(mode="before")` per marker | works, but costs a validator call per instantiation and still needs the registry to know which class is a marker; `__new__` receives `cls` natively |
| No exclusion of markers | measured: the entity inspector would emit six `Entity` nodes for the markers themselves |

**Probe used** (run on the branch base, `.venv` Python 3.12, Pydantic v2):

```python
class BaseProbeEntity(BaseEntity, ABC):
    def __new__(cls, *args, **kwargs):
        if cls in MARKERS:
            raise TypeError(f"{cls.__name__} is an abstract marker and cannot be instantiated.")
        return super().__new__(cls)
# → BaseProbeEntity(code="x")  → TypeError: BaseProbeEntity is an abstract marker …
# → ThingProbeEntity(code="x") → code='x'
```

## D2. Where the kind lives: a low-level registry module

**Decision**: `packages/aoa-action-machine/src/aoa/action_machine/domain/entity_kind.py` holds `EntityKind` and the registry. It imports nothing from the markers, so both `entity_markers.py` (five new markers) and the existing `state_entity.py` (`BaseStateEntity`) can register into it without a cycle. `EntityKind` is a `StrEnum` with the six members and two lookups on each: `suffix` (`CoreEntity` … `StateEntity`) and `word` (`core` … `state`, the wire value).

**Rationale**: `BaseStateEntity` already exists in `state_entity.py` with its fields and validators (#209). Moving it would churn 54 importing files for no gain; a registry that both modules can import keeps `(BaseEntity, ABC)` and the file layout intact. The registry is also the single place a reader sees the six kinds, their suffixes and their wire words side by side.

**Alternatives considered**: one module holding all six markers (moving `BaseStateEntity` — rejected: 54 files, no behavioural gain); deriving the kind from the class name (`*CoreEntity` → core — rejected: a name is what the rule checks, not what the rule reads; a missing suffix would make the kind unreadable); deriving the kind from the MRO at each call site (duplicated in the decorator, the node, the store).

## D3. Where the rules run, and what they read

**Decision**: the single-marker and suffix rules run inside the `@entity` decorator, reading `issubclass(cls, marker)` over the whole MRO. The status suffix rule runs in `BaseStateEntity.__init_subclass__`, because status classes carry no `@entity`.

**Rationale**: the spec's FR-003 requires the chain, not `cls.__bases__`, so an intermediate abstract descendant stays lawful. The decorator is the one place every real entity passes through, and it already owns the target check and the metadata write — the refusal belongs beside them. Status classes never reach the decorator (#209 declares them as class attributes of a vocabulary), so their own base is the only declaration-time hook they have.

**Measured**: 476 classes sit directly on `BaseEntity`; 470 of them carry `@entity`, 6 do not (three negative fixtures in the framework's tests, three teaching examples). 63 status classes sit on `BaseStateEntity` and carry no `@entity`. No class anywhere inherits another entity class (0 measured), so no entity chain exists that would bypass the decorator.

**Alternatives considered**: `BaseEntity.__init_subclass__` (rejected: it would refuse the three negative fixtures and the three teaching examples, whose whole point is a class that is not declared as an entity); a runtime check at graph build (rejected by the spec — the refusal must happen where the class is written).

## D4. Refusal types and messages

**Decision**: `DeclarationStructureError` for the structural faults (no marker, two markers, a marker as the decorator target) and `NamingSuffixError` for the naming faults (missing suffix, foreign suffix, wrong kind). Both exist today (`exceptions/declaration_structure_error.py:7`, `exceptions/naming_suffix_error.py:5`, both `TypeError`). No new exception type. Every message names the class, the marker found (or the absence of one) and the suffix the kind requires.

**Rationale**: the repository already has a typed exception per failure mode, and these two cover the two axes exactly — the decorator "was accepted, the class was not" for structure, and the existing naming invariant for the name. A new `EntityDeclarationError` would duplicate both and force every existing `pytest.raises(NamingSuffixError)` to be rewritten.

**Alternative considered**: separate narrow types per fault (three new classes — rejected: three names where the reader only needs to know whether the fault is structural or nominal).

## D5. The kind reaches Maxitor as data, and survives the store

**Decision**: `EntityGraphNode` writes `properties["entity_kind"] = kind.word`; `graph_json_schema.py` makes it a **required** property of an `Entity` row (and `additionalProperties` stays `false`); the Maxitor DuckDB store gains `entity_kind VARCHAR NOT NULL` in the `entity` table, fills it from the row, and includes it in the node payload the store rebuilds.

**Rationale**: the kind is what lets the renderer later omit a technical association as a separate node without parsing a class name. The store is where the renderer reads from, so a kind that the wire carries and the store drops would be data nobody can use. The DuckDB table is rebuilt from graph JSON on every load, so the column is not a persisted-data migration.

**Measured blast radius**: 12 hand-built `{"type": "Entity", …}` rows in 6 Maxitor test modules and 2 rows built with `type="Entity"` kwargs; one assertion compares an entity row's whole `properties` dict (`packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py:23`). All are updated in the same phase.

**Alternatives considered**: optional property (rejected: a missing kind would pass the schema and the renderer would be back to guessing); kind as a top-level node field (rejected in the clarification — the `properties` object is where a row's own data lives); kind out of the store (rejected: unusable by the renderer).

## D6. The wire value is the kind's word

**Decision**: `core`, `assoc`, `detail`, `spec`, `enum`, `state`.

**Rationale**: the suffix is a naming convention for Python readers; the renderer needs a stable token, not a spelling rule. Lower-case words also match the style of existing row properties (`field_type`, `primary_key_hint`, `relation_type`).

**Measured**: `state` never appears on an entity row — every status type is excluded from the graph (#209), so the schema's set of six is larger than the set a build can produce. That is recorded as an edge case rather than removed, because the schema is a contract about kinds, not about one build's contents.

## D7. Corpus migration: a mapping table first, then one AST codemod

**Decision**: two artifacts under `specs/013-entity-type-markers/evidence/` — `entity_kind_map.py` (the decision per class: module, class, kind, one-line reason, and the migration's new name) and `migrate_entity_markers.py` (the codemod that applies it) — plus the mapping rendered for review as `specs/013-entity-type-markers/entity-kind-map.md` before any rename is made.

**Rationale**: 476 renames cannot be reviewed as a diff. The map is where the judgement is reviewed; the codemod is where it is applied mechanically, so the renames are reproducible and the "fields unchanged" claim can be checked against a baseline taken before the migration.

**How the codemod works**:

1. Build a symbol table: `(module, old class name) → (kind, new name)` for the 476.
2. For each Python file under `packages/` and `examples/`: rename local class definitions from the table; for names imported from a module in the table, rename to that module's new name; rename remaining occurrences only when the name resolves to the table entry for that file or for the imported module. A name that is not in the table is left alone.
3. Fail loudly when a name is ambiguous — 24 class names occur in more than one module, and 95 class definitions share a name inside one module (mostly `Params`/`Result`, none of them entities in the same module except three `DummyEntity` and two `ChildEntity`), so the codemod resolves by module, never globally.
4. Re-run the scan and assert 0 old names remain in `packages/` and `examples/`; the notebooks and the docs are handled by hand and by re-running the examples, not by the codemod.

**Classification rule for the judgement** (a default to be overridden case by case, recorded in the map's reason column):

| Evidence in the class | Kind |
| --- | --- |
| declares `Generalization[...]` | `spec` |
| is a target of `CompositeOne`/`CompositeMany` | `detail` |
| its only fields are participant references, `id`, and service fields (`created_at`, `updated_at`, …) | `assoc` |
| carries a `code`-like field, no lifecycle, and is referred to by many | `enum` |
| everything else | `core` |
| already inherits `BaseStateEntity` | `state` (63 classes, unchanged names) |

**Measured**: the strong structural signals are sparse in the demo — `Generalization[` appears in 34 files, `Composite*` in 1, `Classifier[` in 0, `Association*` in 256 — so most of the 476 are `core` by the rule and the rest need the reason column to be read. That is exactly why the map is reviewed before the codemod runs.

**Alternatives considered**: renaming without a map (rejected: 476 unreviewable decisions); a global search-and-replace by class name (rejected: 24 names live in more than one module); aliasing old names to keep imports working (rejected in the clarification).

## D8. `@entity` on a plain class becomes a refusal

**Decision**: the refusal covers a class decorated with `@entity` that has no marker in its MRO, including a class that is not a `BaseEntity` subclass at all.

**Rationale**: today the decorator accepts `@entity(description="Test")` on a bare class — `tests/action_machine/domain/test_entity.py:75` states it as a feature ("`@entity` does not require `BaseEntity`"). With six markers, "an entity is a class with exactly one marker" is the definition, so that shape is a misdeclaration. The existing test inverts into the test of the new refusal; the inspector-side behaviour for an undeclared entity is untouched.

**Alternative considered**: keep accepting a markerless `@entity` (rejected: it would leave a declared entity with no kind, which is the state this change removes).

## D9. The rule lands last on the branch

**Decision**: markers, the registry, the graph property and the migration land first; the refusals are switched on in the phase that follows the migration. Every commit on the branch leaves the tree green.

**Rationale**: the refusal fails at class definition, so switching it on before the corpus moves breaks every import. The spec's FR-012 forbids a temporary allowance, so the ordering is the only way to keep "one phase = one commit" true without an exception list. This is the same ordering #209 used for the string form.

## D10. Intermediate abstract classes

**Decision**: an intermediate abstract descendant of a marker is a class that inherits a marker and carries no `@entity`. It is exempt from the suffix rule by construction (the rule reads the decorator's target), and it needs its own `exclude_graph_model` if it must stay out of the graph — the inspector's rule today, unchanged. No intermediate abstract class exists in the corpus at the branch base (0 measured outside the framework's `BaseStateEntity`), so this decision adds no work; it is recorded so the rules do not have to be guessed at.

**Measured**: 0 classes inherit another entity class; the only marker descendant that is not a real entity is `BaseStateEntity` itself.

## D11. What the migration must not touch

**Decision**: the baseline taken before the migration records, per entity class: the model field names, the relation field names with their relation type, the lifecycle field names, the `@entity` description, and the domain name. The comparison after the migration is the evidence for SC-005.

**Rationale**: a rename that also loses a field is invisible in a diff of 476 files and invisible to a test that only checks imports. The baseline is cheap to take (`__pydantic_fields__`, `get_foreign_keys` markers) and turns FR-011 into a measurement instead of a promise.

**Not persisted, not checked**: node ids and labels change by design (the graph names an entity by its class); nothing stored holds a qualified id (0 measured), so there is no data migration.
