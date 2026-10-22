# Phase 0 — Research: six kind base classes, two rules, one renamed corpus

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

Every decision is taken against the code on the branch base, not against the issue's prose. The probes quoted here are reproducible.

## D1. The kind lives in the class, and nowhere else

**Decision**: six kind base classes, one file each in `domain/` — `core_entity.py`, `assoc_entity.py`, `detail_entity.py`, `spec_entity.py`, `enum_entity.py`, `state_entity.py` — each `class BaseXxxEntity(BaseEntity, ABC)`, each overriding `__init_subclass__` to check the names of its own descendants. No enum, no registry, no class attribute, no decorator.

**Rationale**: every alternative creates a second place that has to agree with the six classes — and each such place can drift:

| Alternative | Why not |
| --- | --- |
| `EntityKind(StrEnum)` with suffix and word | a second vocabulary next to the classes; the two must be kept in sync by hand |
| a registry of marker classes (`register_marker`, `markers()`) | process-wide state, an import order to maintain, and the same duplication |
| `_entity_kind: ClassVar[str]` on each class | a second declaration per kind: the class name says `CoreEntity`, the attribute says `core` |
| `@abstract_marker(EntityKind.CORE)` decorator | one more concept for the same information, and the declaration stops reading top-to-bottom |
| a marker list imported by `entity.py` | a proven import cycle: `BaseEntity` is defined in `entity.py`, so that module cannot import the classes that inherit it |

**Measured**: Pydantic accepts a class that only overrides `__init_subclass__`; nothing else is needed to declare a kind.

## D2. The suffix comes from the base class's own name

**Decision**: inside each kind base class's hook:

```python
suffix = BaseCoreEntity.__name__.removeprefix("Base")   # "CoreEntity"
if not cls.__name__.endswith(suffix):
    raise NamingSuffixError(...)
```

**Rationale**: the class name already says the suffix, so writing `"CoreEntity"` again would be the same duplication the design removes. All six names fit the convention (`BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity`, `BaseEnumEntity`, `BaseStateEntity`), and a rename that breaks it fails the six-class test immediately.

**Measured**: `BaseCoreEntity.__name__.removeprefix("Base")` → `CoreEntity`; `.removeprefix("Base").removesuffix("Entity").lower()` → `core`.

## D3. How the base recognises a kind base class: inheritance plus an overridden hook

**Decision**: `BaseEntity.__init_subclass__` treats a class as a kind base class when it inherits the entity base directly **and** defines `__init_subclass__` in its own body. Such a class is excluded from the model graph and gets a `__new__` that refuses construction. No attribute is involved.

**Rationale**: the base cannot import the six classes (cycle, D1), and the rules must not depend on a name convention (`Base*` would be a second grammar). "Inherits the base directly and overrides the hook" is exactly what a kind base class does and what a real entity does not — a real entity inherits one of the six and never defines the hook.

**Measured**:

```
_is_kind_base(BaseCoreEntity)      -> True
_is_kind_base(OrderCoreEntity)     -> False   (its base is BaseCoreEntity, not BaseEntity)
BaseCoreEntity()                   -> TypeError: BaseCoreEntity is the base class of a kind and cannot be instantiated.
```

**Alternative considered**: an attribute on each class (rejected in D1); checking `cls.__name__.startswith("Base")` (rejected: a name is not a declaration).

## D4. Where the two hierarchy rules live, and when they are switched on

**Decision**: the entity base refuses direct inheritance from itself (when the child neither overrides the hook nor is a kind base class) and refuses two kind base classes in one chain, with `DeclarationStructureError`. Both rules are implemented after the corpus migration.

**Rationale**: they are rules about the hierarchy, not about a kind, and they are the only ones that can catch a class that forgot its kind entirely. They fail at class creation, so switching them on before the migration would refuse the 476 classes that still inherit the base directly — the same ordering #209 used for the string form.

**Measured**: the refusal, once added, catches both faults:

```
class StrayEntity(BaseEntity)                       DeclarationStructureError: inherits the entity base directly
class BothEntity(BaseCoreEntity, BaseDetailEntity)  DeclarationStructureError: carries 2 kind base classes
```

## D5. Refusal types and messages

**Decision**: `DeclarationStructureError` for the hierarchy faults, `NamingSuffixError` for the naming faults, `TypeError` for constructing a kind base class. All three exist today. Every message names the class, what was found and the suffix the kind requires.

**Rationale**: the repository already has a typed exception per failure mode, and these three cover the axes exactly. A new type would duplicate them and force every existing `pytest.raises(NamingSuffixError)` to be rewritten.

## D6. The kind reaches Maxitor as data, and survives the store

**Decision**: `EntityGraphNode` writes `properties["entity_kind"]`, derived from the kind base class in the class's chain: its name without `Base` and without `Entity`, lower case. `graph_json_schema.py` makes the property **required** for an `Entity` row (`additionalProperties` stays `false`); the Maxitor DuckDB store gains `entity_kind VARCHAR NOT NULL`, fills it from the row, and includes it in the node payload the store rebuilds.

**Rationale**: the kind is what lets the renderer later omit a technical association as a separate node without parsing the entity's own class name. The store is where the renderer reads from, so a kind the wire carries and the store drops would be data nobody can use. The DuckDB table is rebuilt from graph JSON on every load, so the column is not a persisted-data migration.

**Measured blast radius**: 12 hand-built `{"type": "Entity", …}` rows in 6 Maxitor test modules and 2 rows built with `type="Entity"` kwargs; one assertion compares an entity row's whole `properties` dict (`packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py:23`).

## D7. The wire value is the kind's word, derived once

**Decision**: `core`, `assoc`, `detail`, `spec`, `enum`, `state` — the kind base class's name without `Base` and `Entity`, lower case, so nothing is stored twice.

**Rationale**: one rule produces both the suffix a class must carry and the word the graph reports; a rename of a kind base class moves both together, which is the only way the two cannot disagree. The value matches the style of the existing row properties (`field_type`, `primary_key_hint`, `relation_type`).

**Measured**: `state` never appears on an entity row — every status type is excluded from the graph (#209) — so the schema's set of six is larger than the set a build can produce. Recorded as an edge case rather than removed: the schema is a contract about kinds, not about one build's contents.

## D8. Corpus migration: a mapping table first, then one AST codemod

**Decision**: two artifacts under `specs/013-entity-type-markers/evidence/` — `entity_kind_map.py` (module, old name, kind, new name, one-line reason) and `migrate_entity_kinds.py` (the codemod) — plus the same decisions rendered for review as `specs/013-entity-type-markers/entity-kind-map.md` **before** any rename is written.

**Rationale**: 476 renames cannot be reviewed as a diff. The map is where the judgement is reviewed; the codemod applies it mechanically, so the renames are reproducible and the "fields unchanged" claim can be checked against a baseline.

**How the codemod works**:

1. Build a symbol table: `(module, old class name) → (kind, new name)` for the 476.
2. Rename local class definitions; for names imported from a module in the table, rename to that module's new name; leave every name not in the table alone.
3. Fail loudly on ambiguity — 24 class names occur in more than one module, and 95 definitions share a name inside one module (mostly `Params`/`Result`; entities: three `DummyEntity`, two `ChildEntity`), so the codemod resolves by module, never globally.
4. Re-run the scan and assert 0 old names remain in `packages/` and `examples/`; notebooks and docs are handled by re-running the examples, not by the codemod.

**Classification rule for the judgement** (a default, overridden case by case in the map's reason column):

| Evidence in the class | Kind |
| --- | --- |
| declares `Generalization[...]` | `spec` |
| is a target of `CompositeOne`/`CompositeMany` | `detail` |
| its only fields are participant references, `id`, and service fields (`created_at`, `updated_at`, …) | `assoc` |
| carries a `code`-like field, no lifecycle, and is referred to by many | `enum` |
| everything else | `core` |
| already descends from `BaseStateEntity` | `state` (63 classes, names unchanged) |

**Measured**: the strong structural signals are sparse in the demo — `Generalization[` in 34 files, `Composite*` 1, `Classifier[` 0, `Association*` 256 — so most of the 476 are `core` by the rule and the rest need the reason column to be read. That is why the map is reviewed before the codemod runs.

## D9. `@entity` keeps its current latitude

**Decision**: `@entity` gains no new check. A plain class with `@entity` and no entity base remains accepted, as `tests/action_machine/domain/test_entity.py:75` states today, because the new rules are about the entity hierarchy, not about the decorator.

**Rationale**: the issue forbids direct inheritance from the base and requires one kind; a class outside the hierarchy is not an entity the graph will draw, and refusing it here would be a rule the issue does not ask for. The existing test stays as it is.

## D10. Intermediate abstract classes are not exempt

**Decision**: the suffix rule belongs to the kind base class and applies to every descendant, so an intermediate such as `BaseTransportCoreEntity` carries its kind like any other class.

**Rationale**: the exemption would need the rule to know whether a class is decorated with `@entity`, which is unknowable at class creation. The corpus has no intermediate class outside the framework, so dropping the exemption costs nothing and removes a branch from the rule.

**Measured**: `BaseTransportCoreEntity(BaseCoreEntity)` is accepted, and its child `TruckEntity` is refused with the same suffix message; a shared `AuditMixin` beside the base changes nothing.

## D11. What the migration must not touch

**Decision**: the baseline taken before the migration records, per entity class: the model field names, the relation field names with their relation type, the lifecycle field names, the `@entity` description, and the domain name. The comparison after the migration is the evidence for SC-005.

**Rationale**: a rename that also loses a field is invisible in a diff of 476 files and invisible to a test that only checks imports.

**Not persisted, not checked**: node ids and labels change by design; nothing stored holds a qualified id (0 measured), so there is no data migration.
