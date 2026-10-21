# Phase 1 — Data model: a kind, its marker, its declaration and its row

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

The change adds one vocabulary — six kinds — and one value on the wire. Nothing is persisted: the graph JSON is the transport, and Maxitor rebuilds its DuckDB tables from it on every load.

## Kind (`EntityKind`)

| Member | Wire word | Suffix | Marker that carries it | What an instance represents | Domain identity |
| --- | --- | --- | --- | --- | --- |
| `CORE` | `core` | `CoreEntity` | `BaseCoreEntity` | an independent domain object — an order, a contract, a supplier offer | the object's own identity |
| `ASSOC` | `assoc` | `AssocEntity` | `BaseAssocEntity` | only the fact that participants are connected | the connection; a service id adds no business meaning |
| `DETAIL` | `detail` | `DetailEntity` | `BaseDetailEntity` | an identifiable part of one owner | owner identity plus a discriminator within that owner |
| `SPEC` | `spec` | `SpecEntity` | `BaseSpecEntity` | variant-specific data of the same head object | exactly the head's identity |
| `ENUM` | `enum` | `EnumEntity` | `BaseEnumEntity` | a shared reference value | a code within its dictionary |
| `STATE` | `state` | `StateEntity` | `BaseStateEntity` | a state description within a process | a code within its lifecycle axis |

`EntityKind` is a `StrEnum`; `suffix` and `word` are properties on the member. The registry exposes `register_marker(kind, cls)`, `kind_of(cls) -> EntityKind | None` (MRO walk, nearest marker wins) and `markers() -> tuple[type, ...]` in declaration order.

**Invariants**

1. Six members, one suffix and one word each; no member is added by this change's consumers.
2. A marker is registered exactly once; a second registration of the same class is refused at import.
3. `kind_of` walks the MRO, so an intermediate abstract descendant resolves to the marker its chain reaches; a class with two markers is a declaration fault, not a resolution, and is refused before `kind_of` is asked.
4. The registry imports no marker module; `entity_markers.py` and `state_entity.py` import it, never the other way.
5. `state` is a member although no entity row can carry it — every status type is excluded from the graph. The set is a contract about kinds, not about one build's contents.

## Marker

| Property | Value |
| --- | --- |
| declaration | `class BaseCoreEntity(BaseEntity, ABC)`, decorated with `@abstract_marker(EntityKind.CORE)` |
| effects of the decorator | registers the kind; marks the class `exclude_graph_model`; installs a `__new__` that refuses construction of the marker itself |
| fields | none beyond what the marker's role implies — `BaseStateEntity` keeps `code` and `display_name` from #209 |
| graph presence | none: the entity inspector walks every `BaseEntity` subclass and skips the excluded ones |
| `@entity` target | refused — a marker is not a real entity |
| intermediate abstract descendant | allowed; it inherits the marker, carries no `@entity`, is exempt from the suffix rule, and needs its own `exclude_graph_model` if it must stay out of the graph (the inspector's rule today) |

## Real entity

| Property | Value |
| --- | --- |
| declaration | `@entity(description=..., domain=...)` on a class whose MRO carries exactly one marker |
| name | ends with the marker's suffix; a wrong kind's suffix is refused |
| surface | unchanged — fields, relations, lifecycles, description, domain, classifier codes |
| row | `type: "Entity"`, `label` = class `__name__`, `id` = the class's qualified name, `properties = {description, entity_kind}` |
| graph presence | one `Entity` node, as today |

## Declaration rules (all at class-definition time)

| Shape | Outcome | Raised |
| --- | --- | --- |
| `@entity` class, exactly one marker in the MRO, name carries that kind | accepted | — |
| `@entity` class, no marker anywhere in the MRO (including a class that is not an entity at all) | refused | `DeclarationStructureError` |
| `@entity` class with two or more markers in the MRO | refused, naming both | `DeclarationStructureError` |
| a marker itself decorated with `@entity` | refused | `DeclarationStructureError` |
| `@entity` class whose name lacks the kind suffix | refused, naming the expected suffix | `NamingSuffixError` |
| `@entity` class whose name carries another kind's suffix | refused as the wrong kind | `NamingSuffixError` |
| intermediate abstract descendant without `@entity` | accepted, exempt from the suffix rule | — |
| one marker plus ordinary mixins | accepted — only the six markers count | — |
| status class without the `StateEntity` suffix | refused at its own declaration | `NamingSuffixError` |
| marker instantiated | refused | `TypeError` from the guard |

Every message names the class, what was found (the marker, both markers, or the absence of one) and the suffix the kind requires.

## Graph entity row

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | `str` | yes | qualified class name (unchanged by the feature, changed by the renames) |
| `type` | `"Entity"` | yes | node kind (unchanged) |
| `label` | `str` | yes | class `__name__` (changed by the renames) |
| `properties.description` | `str` | yes | the `@entity` description (unchanged) |
| `properties.entity_kind` | one of the six words | **yes, new** | the kind of the class's marker |

`additionalProperties` on an entity row's `properties` stays `false`, so the schema admits exactly these two keys and no other.

## Maxitor store

| Table | Change |
| --- | --- |
| `entity` | gains `entity_kind VARCHAR NOT NULL`; `_fill_table_entity` writes `row["properties"]["entity_kind"]` |
| node payload builder | the `entity` select adds `'entity_kind', entity_kind` to the rebuilt payload |

The store is rebuilt from graph JSON on every load; no stored file needs migrating. The row must be schema-valid, so a hand-built fixture without the kind fails validation — that is the intended break and the phase-2 test asserts it.

## What the change does not model

- **Primary-key structure** — own PK, FK-composed, parent PK plus discriminator, PK equal to the head's PK: described by the marker docstrings, not checked; `get_primary_key()` still returns `id` by convention.
- **Any renderer behaviour** — the kind is available; drawing a technical association differently is a later change.
- **Binary compatibility of names** — the old class names are removed, not aliased (spec FR-011).
