# Data model: lifecycle statuses on the state type

**Feature**: `specs/014-lifecycle-status-catalog` | **Date**: 2026-10-22 | **Plan**: [plan.md](./plan.md)

## Overview

```
State type  ──declares──►  Status objects        (one instance per declared name)
     │                          │
     │ owns                     │ is a state of
     ▼                          ▼
Catalogue  ◄──checked against──  Axis (Lifecycle[StateType])
     ▲                          │
     │                          │ owns
     └── members, codes,        ▼
         by_code, entity_type   Template (states, transitions, classification)
                                     │
                                     ▼
                                State row in the graph (status.model_dump())
```

The type owns the statuses and the catalogue; the axis owns the machine and checks its template against the catalogue. The entity field and the graph row are downstream of the axis and do not change.

## State type

The class that declares one status shape and, in its own body, every status of that shape.

| Aspect | Rule |
| --- | --- |
| Base | A direct subclass of `BaseStateEntity` (the state kind). The name ends with `StateEntity` (the kind rule from #210). |
| Fields | `code` and `display_name` from `BaseStateEntity`, plus any domain or presentation fields the status needs (`sort_order`, `color`, `fill_color`, `requires_receipt`, …). |
| Status declarations | `NAME = <TheType>(...)` in the class body; the name is the declaration factory only in the call form. |
| Result | After class creation, each `NAME` is an instance of the type; the placeholder is gone. |
| Catalogue | `members`, `codes()`, `by_code()`, `entity_type`; filled by the conversion hook. |
| Empty type | Valid; `members` stays `()`. |
| Inheritance | A subclass with no statuses inherits the parent's `members`; a subclass that declares statuses gets its own tuple, not an extension. |
| Config | `BaseStateEntity.model_config` merges the entity config with `ignored_types=(StateSpec,)`. |
| Graph | Excluded from the model graph (`exclude_graph_model`), as today. |

## Status object

One immutable instance of a state type.

| Field | Type | Rule |
| --- | --- | --- |
| `code` | `str` | Required; non-empty after strip; identity inside the lifecycle; unique within the type. |
| `display_name` | `str` | Required; non-empty after strip; the label the diagram shows. |
| Domain fields | whatever the type declares | Required or defaulted per the field declaration; validated by Pydantic when the class is created. |
| Extra fields | — | Refused (`extra="forbid"`). |
| Mutability | — | Frozen by `BaseEntity`. |

## Catalogue

The ordered collection of a state type's declared statuses.

| Aspect | Rule |
| --- | --- |
| `members` | `tuple` in declaration order; the instances themselves, not wrappers. |
| `codes()` | `list[str]` in declaration order. |
| `by_code(code)` | The declared instance; `KeyError` for an unknown code. |
| `entity_type` | The state type itself. |
| Uniqueness | Two statuses with the same code are refused at class creation (`ValueError`). |
| Same type | Every entry is an instance of the declaring type by construction; an instance assigned by hand is not a member and is refused by the axis as foreign. |

## Axis

The machine of one lifecycle field.

| Aspect | Rule |
| --- | --- |
| Declaration | `class OrderLifecycle(Lifecycle[OrderStateEntity])`. |
| Owns | `_template` (the transition graph) and `_state_type` (resolved from the generic parameter). |
| `_state_type` | Resolved in `Lifecycle.__init_subclass__` from `__orig_bases__`; inherited by subclasses that do not redeclare a parameter. |
| Catalogue | **Not** on the axis: `by_code`, `members`, `codes()`, `entity_type` live on the state type. |
| Plain form | A `Lifecycle` subclass without a parameter keeps today's behaviour and is unchecked. |
| Runtime | `OrderLifecycle(current_state="draft")`; `current_state`, `current_status`, `transition`, `available_transitions` unchanged. |
| Entity field | `lifecycle: OrderLifecycle` unchanged. |

## Template

The transition graph of one axis, built by the fluent DSL.

| Aspect | Rule |
| --- | --- |
| States | `get_state_entities()`: the status objects declared with `.state(...)`. |
| Targets | `get_transition_entities()`: the status objects named in `.to(...)`. |
| Classification | `initial` / `intermediate` / `final`, unchanged. |
| The eight build rules | Unchanged: classification, reachability, finality, target existence, and the rest. |
| The two new refusals | Every state and target is a member of the axis's catalogue by identity; every member appears as a state. |

## State row in the interchange graph

| Aspect | Rule |
| --- | --- |
| Attributes | `status.model_dump()` — code, display name and every declared domain field. |
| Label | `status.display_name`. |
| Transitions | The template's edges, unchanged. |
| Maxitor payload | The same five presentation keys (`code`, `display_name`, `sort_order`, `color`, `fill_color`), unchanged. |

## Declaration errors

| Error | Base | Raised when | Message carries |
| --- | --- | --- | --- |
| `ForeignStateError` | `TypeError` | A template state or target is not a declared object of the axis's type; or the type has no statuses | The axis, the status code and type, the allowed codes; or "a different instance, use `Type.STATUS`" |
| `MissingStateError` | `ValueError` | A declared status does not appear among the template's states | The axis, the state type, the missing codes |

Both are raised in `Lifecycle.__init_subclass__`, at class creation (import time), before any graph is built.

## Validation rules

| Rule | Where | Requirement |
| --- | --- | --- |
| Status fields validated, defaults applied | Conversion hook, `cls(**spec.kwargs)` | FR-005 |
| Unique codes | Conversion hook | FR-002 |
| Catalogue in declaration order | Conversion hook | FR-002 |
| `by_code` raises `KeyError` | Catalogue | FR-003 |
| Subclass inheritance | Conversion hook / MRO | FR-004 |
| Alias only in the call form | `__prepare__` / docs | FR-006 |
| Foreign status refused by identity | `Lifecycle.__init_subclass__` | FR-008, FR-009 |
| Coverage of every status | `Lifecycle.__init_subclass__` | FR-010 |
| Checks at class creation | `Lifecycle.__init_subclass__` | FR-011 |
| Plain `Lifecycle` unchecked | `Lifecycle.__init_subclass__` | FR-012 |
| Placeholders excluded from fields | `model_config["ignored_types"]` | FR-017 |
| Existing kind/name/template rules | Unchanged | FR-018 |

## State transitions of the change itself

1. The class body stores a `StateSpec` for each status name.
2. Pydantic builds the model, ignoring the placeholders.
3. `__pydantic_init_subclass__` replaces each placeholder with `cls(**kwargs)`; the fields are validated and the catalogue is filled.
4. The axis class body builds `_template` from the real instances.
5. `Lifecycle.__init_subclass__` resolves the type, checks identity and coverage, and stores `_state_type`.
6. The graph and the runtime read the same objects as before.
