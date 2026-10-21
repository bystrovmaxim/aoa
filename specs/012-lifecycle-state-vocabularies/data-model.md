# Phase 1 — Data model: a status, its vocabulary, its row and its diagram

**Feature**: `specs/012-lifecycle-state-vocabularies` | **Date**: 2026-10-19

The feature adds one object and two carriers of data derived from it: the graph state row and the FSM snapshot. Nothing is persisted; the lifecycle template is import-time metadata, and the DuckDB store is rebuilt from graph JSON on every load.

## Status (`BaseStateEntity`)

| Field | Type | Required | Meaning | Where it goes |
| --- | --- | --- | --- | --- |
| `code` | `str` | yes | identity of the state inside the chain | the state key, the state row id, the FSM `key`, the transition source/target |
| `display_name` | `str` | yes | human label | the state row `label`, the FSM `display_name`, the diagram node title |
| domain fields | any JSON-representable pydantic field | no | order, colour, anything the domain needs | `properties.attributes` in the graph, `attributes` in the FSM payload |

**Invariants**

1. Immutable (`frozen`), `extra="forbid"` inherited from the entity base.
2. `code` and `display_name` are non-empty and not whitespace-only; refused at construction.
3. No `id` of its own and no `initial`/`final` flag; the code is the identity and the chain classifies.
4. Every instance of a status type is excluded from the model graph; the type never becomes an `EntityGraphNode`.
5. `model_dump(mode="json")` is the single serialization used by the graph; `Field(exclude=True)` is the opt-out.

## Axis class (`Lifecycle` + `StateVocabulary`)

| Member | Type | Meaning |
| --- | --- | --- |
| the status type | module-level `BaseStateEntity` subclass | inferred from the members, exposed as `entity_type` |
| the members | status instances, class attributes in declaration order | the statuses of the axis |
| the lookup | plain methods on the class | `by_code(code)`, `codes()`, `members` |
| the template check | `_template` in the same class body | every status in it is one of the members |

**Invariants**

1. A class that declares statuses declares at least one; a class that declares neither statuses nor its own `_template` is a specialization and inherits the members.
2. All members are instances of one status type; a member of another type is refused at class creation.
3. Codes are unique in the class; a duplicate is refused at class creation, naming the code.
4. Declaration order is the member order and the order the diagram falls back to.
5. The vocabulary API is plain methods, never dunders, so lifecycle instances do not inherit it.
6. `StateVocabulary` applied without `Lifecycle` is refused; one axis is one class.

## Chain state metadata (`StateInfo`, unchanged)

| Field | Type | Source |
| --- | --- | --- |
| `key` | `str` | `status.code` |
| `display_name` | `str` | `status.display_name` |
| `state_type` | `StateType` | `.initial()` / `.intermediate()` / `.final()` |
| `transitions` | `frozenset[str]` | `.to(...)` targets, unwrapped to codes |

**Invariants**

1. The dataclass, the `dict[str, StateInfo]` and every accessor keep their shape.
2. `transition(target)` and `can_transition(target)` keep taking the code string.
3. The eight build rules are unchanged and keep owning reachability, finality and target existence.
4. The chain additionally holds `_state_entities: dict[str, BaseStateEntity]`, copied to instances, exposed by `get_state_entity(code)`.
5. The statuses and the template are declared in one class body; every status object in `_template` is one of that class's attributes, checked at class creation.

## Runtime current status

A specialized lifecycle accepts a code, validates it against the template and stores `_current_status` as a reference to the declared object in `_state_entities`. There is no `_current_state` field. `current_status` returns that same object; `current_state` reads its `code`.

`transition(code)` checks the permitted edge and creates a new instance of the same lifecycle class, referring to the declared destination object. It does not construct a status or alter the original lifecycle. `current_state_info` continues to read the template's `StateInfo` by code. A template has no current status, so runtime properties raise `RuntimeError`; repr, equality and hashing still support templates. Instance equality and hashing use the concrete lifecycle class and code, not status fields.

## Graph state row

| Field | Value | Source |
| --- | --- | --- |
| `id` | `<lifecycle node id>:<code>` | unchanged |
| `type` | `StateInitial` / `StateIntermediate` / `StateFinal` | unchanged, from the chain |
| `label` | `display_name` | the status |
| `properties.lifecycle_class_id` | the chain's qualified name | unchanged |
| `properties.state_key` | `code` | unchanged |
| `properties.attributes` | `{field: value, …}` | the status, all fields |

**Invariants**

1. The row is still validated by `GRAPH_JSON_SCHEMA`; the envelope stays strict, `attributes` is a free object.
2. A transition edge still targets `<lifecycle node id>:<to_code>`; nothing about edges changes.
3. With a chain declared with the string form during phases 1–4, the row is exactly today's row.

## DuckDB `state` table

| Column | Type | Source |
| --- | --- | --- |
| `id` | `VARCHAR` | the row id |
| `label` | `VARCHAR` | the row label (now the human label) |
| `kind` | `VARCHAR` | the row type |
| `lifecycle_class_id` | `VARCHAR` | the row property |
| `state_key` | `VARCHAR` | the row property |
| `attributes` | `JSON` | the row property, new |

**Invariants**

1. Both insert paths fill `attributes` (the per-table path and the by-type path).
2. The `nodes` view exposes it; the `lifecycle` and `state_edges` queries do not change.
3. A graph loaded from JSON without `attributes` yields an empty object, not `NULL` in the payload.

## FSM snapshot state item

| Field | Type | Source |
| --- | --- | --- |
| `key` | `str` | `state_key` |
| `display_name` | `str` | `label` |
| `state_type` | `str` | `kind` → `initial` / `intermediate` / `final` |
| `transitions` | `list[str]` | the transition edges |
| `attributes` | closed object, optional | the presentation attributes of the `attributes` column (`code`, `display_name`, `sort_order`, `color`, `fill_color`); other fields stay in the graph row |

**Invariants**

1. Nothing becomes required; an old payload without attributes stays valid.
2. Order: initial first, then `attributes.sort_order` when present (default `0`), then `key`.
3. The diagram source uses `attributes.color` for the stroke and `attributes.fill_color` for the fill when present; otherwise the per-type palette, unchanged.
