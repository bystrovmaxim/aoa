# Phase 1 — Data model: a kind, its base class, its declaration and its row

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

The change adds one word per kind — derived, not stored — and one value on the wire. Nothing is persisted: the graph JSON is the transport, and Maxitor rebuilds its DuckDB tables from it on every load.

## Kind

| Kind base class | File | Suffix it requires | Wire word | What an instance represents | Domain identity |
| --- | --- | --- | --- | --- | --- |
| `BaseCoreEntity` | `core_entity.py` | `CoreEntity` | `core` | an independent domain object — an order, a contract, a supplier offer | the object's own identity |
| `BaseAssocEntity` | `assoc_entity.py` | `AssocEntity` | `assoc` | only the fact that participants are connected | the connection; a service id adds no business meaning |
| `BaseDetailEntity` | `detail_entity.py` | `DetailEntity` | `detail` | an identifiable part of one owner | owner identity plus a discriminator within that owner |
| `BaseSpecEntity` | `spec_entity.py` | `SpecEntity` | `spec` | variant-specific data of the same head object | exactly the head's identity |
| `BaseEnumEntity` | `enum_entity.py` | `EnumEntity` | `enum` | a shared reference value | a code within its dictionary |
| `BaseStateEntity` | `state_entity.py` | `StateEntity` | `state` | a state description within a process | a code within its lifecycle axis |

The suffix is the base class's name without `Base`; the word is that name without `Base` and without `Entity`, lower case. Both are derived from the six names, so there is no table to keep in sync — this one is documentation, not a declaration.

**Invariants**

1. Six kinds, one base class, one suffix and one word each, no overlap.
2. Exactly six classes in the repository inherit the entity base directly and override the subclass hook; a test pins the count.
3. For every one of the six, the word derived from its name is one of the six above; a test pins it.
4. The base class's own name is the only source of its suffix and its word: rename the class and both move together.

## Kind base class

| Property | Value |
| --- | --- |
| declaration | `class BaseCoreEntity(BaseEntity, ABC)` in its own file |
| recognition | it inherits the entity base directly **and** overrides `__init_subclass__` — no attribute, no registry, no decorator |
| name rule | `BaseEntity._require_kind_suffix(suffix)` — one check on the base, which takes the suffix as a parameter; each kind base class passes its literal (`"CoreEntity"`, `"AssocEntity"`, …); every descendant's name must end with it, otherwise `NamingSuffixError` naming the class and the suffix |
| fields | none beyond what the role implies — `BaseStateEntity` keeps `code` and `display_name` from #209 |
| graph presence | none: the entity base excludes a class it recognises as a kind base class |
| instantiation | refused: the entity base installs a `__new__` that raises `TypeError` for a kind base class |
| descendants | never excluded by inheritance: the flag is read from a class's own namespace, so the six kind base classes carry `@exclude_graph_model` themselves, and the state hook decorates each status type (as in #209) |

## Real entity

| Property | Value |
| --- | --- |
| declaration | a class descending from exactly one kind base class, usually decorated with `@entity(description=..., domain=...)` |
| name | ends with the base class's suffix |
| surface | unchanged — fields, relations, lifecycles, description, domain, classifier codes |
| row | `type: "Entity"`, `label` = class `__name__`, `id` = the class's qualified name, `properties = {description, entity_kind}` |
| graph presence | one `Entity` node, as today |

## Declaration rules (all at class-creation time)

| Shape | Outcome | Raised |
| --- | --- | --- |
| one kind base class in the chain, name carries that kind | accepted | — |
| no kind base class (direct inheritance from the entity base) | refused, naming the class and the six kind base classes | `DeclarationStructureError` |
| two kind base classes in the chain | refused, naming both | `DeclarationStructureError` |
| a descendant whose name lacks the kind suffix | refused, naming the expected suffix | `NamingSuffixError` |
| a descendant whose name carries another kind's suffix | refused as the wrong kind | `NamingSuffixError` |
| a name that does not end with `Entity` at all | refused by the generic invariant, which fires first | `NamingSuffixError` |
| an intermediate abstract descendant | accepted and held to the suffix, like any descendant | — |
| one kind base class plus ordinary mixins | accepted — only the six count | — |
| a status class without the `StateEntity` suffix | refused at its own creation | `NamingSuffixError` |
| a kind base class instantiated | refused | `TypeError` |
| a class carrying a kind base class and no `@entity` | accepted; the missing decorator stays a build-time error | — |

Every message names the class, what was found (the base classes, both of them, or their absence) and the suffix the kind requires.

## Graph entity row

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | `str` | yes | qualified class name (changed by the renames, not by this feature) |
| `type` | `"Entity"` | yes | node kind (unchanged) |
| `label` | `str` | yes | class `__name__` (changed by the renames) |
| `properties.description` | `str` | yes | the `@entity` description (unchanged) |
| `properties.entity_kind` | one of the six words | **yes, new** | the word derived from the kind base class of the class |

`additionalProperties` on an entity row's `properties` stays `false`, so the schema admits exactly these two keys and no other.

## Maxitor store

| Table | Change |
| --- | --- |
| `entity` | gains `entity_kind VARCHAR NOT NULL`; `_fill_table_entity` writes `row["properties"]["entity_kind"]` |
| node payload builder | the `entity` select adds `'entity_kind', entity_kind` to the rebuilt payload |

The store is rebuilt from graph JSON on every load; no stored file needs migrating. A hand-built fixture without the kind fails validation — that is the intended break and the phase asserts it.

## What the change does not model

- **Primary-key structure** — own PK, FK-composed, parent PK plus discriminator, PK equal to the head's PK: described by the class docstrings, not checked; `get_primary_key()` still returns `id` by convention.
- **Any renderer behaviour** — the kind is available; drawing a technical association differently is a later change.
- **Binary compatibility of names** — the old class names are removed, not aliased (spec FR-011).
