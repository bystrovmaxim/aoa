# Research: An entity tells the truth in Python

Every decision below was measured on `main` at `9e893a2cb`, Python 3.12, Pydantic 2.14.1. The probes live outside the repository; their outputs are quoted.

## R1. How a partial entity keeps only its loaded fields

**Decision**: a field of an entity is loaded exactly when the instance holds it in its own `__dict__`. `partial(**fields)` creates the instance without `model_construct` and puts only the given fields there; no flag records that the instance is partial.

**Rationale**: it is the only design that meets FR-006 to FR-009 together.

| Probe | Result |
| --- | --- |
| partial with every field `==` full entity | `True` — today's equality kept (FR-009) |
| `partial(id) == full` | `False` — as today |
| `'total' in partial(id).__dict__` | `False` |
| `partial(id).model_dump()` | `{'id': 'o1'}` — the unloaded field is absent (FR-007) |
| `model_copy(update={"total": 2.0})` | `total` in `__dict__`, `model_fields_set == {'id', 'total'}` (FR-008) |

A full entity always holds every field, because validation fills defaults; so "present in `__dict__`" also says "loaded" for it, and `BaseEntity.__getattr__` — which Python calls only for a missing attribute — raises `FieldNotLoadedError` for any missing declared field. `FieldNotLoadedError` subclasses `AttributeError`, so `hasattr`, `getattr(..., default)` and every caller that catches `AttributeError` behave as before.

The construction sets the four slots `model_construct` sets — `__dict__`, `__pydantic_fields_set__`, `__pydantic_extra__`, `__pydantic_private__` (the class's private defaults) — without filling defaults. A test pins this against Pydantic so that an upgrade that changes the slots fails loudly.

**Alternatives considered**:

- *`model_construct`, then remove the unloaded fields* — refused: the default factories have already run (case 2.3: `KeyError: 'id'` before anything can be removed).
- *`model_fields_set` plus a declared private flag `_partial`* (the wording #405 had) — refused: Pydantic compares private attributes in `__eq__`, so a partial entity with every field stops being equal to the full one (`private flag differs, same fields -> equal: False`), against FR-009. `model_fields_set` alone cannot tell "partial and not loaded" from "full and defaulted" either.
- *Keep `_partial_instance` and `_loaded_fields` in `__dict__`* (today) — refused: they live outside Pydantic, and `model_copy(update=...)` keeps the old set (case 2.2).

**Consequence for #405**: its phase 2 is reworded from "the loaded set is `model_fields_set`, the partial flag is a declared private attribute" to "a field is loaded when the instance holds it; no flag".

## R2. How relation containers stop pretending to be their entity

**Decision**:

1. `BaseRelationOne.__getattr__` raises `AttributeError` for a name that starts and ends with `__`, before it looks at the entity; every other name is forwarded as today.
2. `BaseRelationOne` and `BaseRelationMany` define `__reduce__`: it rebuilds the container through the constructor from the class, the id(s), the entity(ies) and the loaded state, so no copy and no unpickling assigns to a frozen slot. `copy.copy`, `copy.deepcopy` and `pickle` all use it (`deepcopy` deep-copies its arguments), so separate `__copy__` and `__deepcopy__` would repeat it.

**Rationale**: the defect has one cause — protocol lookups on the instance reach `__getattr__` — and two symptoms. Pydantic's serializer finds the entity's `__pydantic_serializer__` (cases 1.1–1.3), and `copy` finds the entity's `__deepcopy__` (case 1.4). Stopping dunder names cures both. Without a dunder fallback, `copy` and `pickle` use their default protocol, which assigns to the slots and meets the frozen `__setattr__` (case 1.5); `__reduce__` is the standard answer for an immutable slotted class, and it serves `copy`, `deepcopy` and `pickle` alike.

Prototype results: deep copy keeps the class and copies the entity; a shallow copy and a pickle round trip each give an equal container of the same class; an ordinary name is still forwarded; a dunder name raises `AttributeError`.

**Alternatives considered**: a list of the dunder names to refuse — refused, because any future protocol would leak again; making the containers Pydantic models — refused, out of scope and a change to their public shape (#407 gives them a JSON form instead).

## R3. What in the repository relies on the old behaviour

**Decision**: the change touches few places, and each is handled in the phase that changes its behaviour.

- `_partial_instance` and `_loaded_fields` exist only in `domain/entity.py`.
- `.partial(` is called in `examples/step_22_entity/03_partial.py` (no defaulted field: unchanged), `docs/tutorials/step-22-entity.md`, the docstring of `tests/support/domain_model/entities.py`, and three test files of `tests/action_machine/domain/` (`test_entity_introspection.py`, `test_entity_partial_getattr.py`, `test_specialization_container.py`); the matches in `aoa-langgraph` are `functools.partial`.
- `test_entity_partial_getattr.py` asserts that a declared field missing on a non-partial instance raises a generic `AttributeError`; after R1 it raises `FieldNotLoadedError`, which is an `AttributeError`, so the assertion is revisited, not weakened.
- No package source deep-copies or pickles an entity or a container (`deepcopy`, `model_copy(deep`, `pickle`: no match in `packages/*/src`).
- The how-to page on dictionary references already states that Python-mode `model_dump()` retains the wrappers; after phase 1 that statement becomes true, and the page gets an example that runs.
