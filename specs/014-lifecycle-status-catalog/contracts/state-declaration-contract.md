# Contract: the state type declares its statuses

**Feature**: `specs/014-lifecycle-status-catalog` | **Date**: 2026-10-22

This is the contract a model author writes. It covers the surface, the fields, the catalogue, the inheritance and the typing. The axis contract is [lifecycle-axis-contract.md](./lifecycle-axis-contract.md).

## 1. The surface

```python
class OrderStateEntity(BaseStateEntity):
    sort_order: int = Field(description="Order within the state list")
    color: str = Field(default="#1565c0", description="State outline colour")
    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")

    DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)
    PAID = OrderStateEntity(code="paid", display_name="Payment received", sort_order=1, requires_receipt=True)
    CANCELLED = OrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=2)
```

- The statuses are class attributes of the type's own body.
- The call is the type's own name. No `state(...)`, no `cast`, no `TYPE_CHECKING`.
- The names are ordinary class attributes after the class is created.

## 2. The alias rule

Inside a state type body, the type's own name resolves to an internal declaration factory.

| Use in the body | Result |
| --- | --- |
| `DRAFT = OrderStateEntity(code=..., display_name=...)` | A placeholder that becomes an `OrderStateEntity` when the class is created. |
| `x = OrderStateEntity` (not a call) | The factory function, not the class. |
| `parent: OrderStateEntity` (a field annotation) | Must be a forward reference (`from __future__ import annotations` or a string); the name is not the class here. |
| `other_name` (unknown) | `NameError`, as in any class body. |
| A global named `OrderStateEntity` referenced in the body | Shadowed by the factory; this is the documented cost. |

## 3. Fields and validation

Every declared field is initialised when the class is created.

| Case | Result |
| --- | --- |
| A field passed explicitly | The value is validated and stored. |
| A field omitted with a default | The default is stored. |
| A field omitted without a default | `ValidationError: Field required` at class creation. |
| A misspelled field (`sort_ordr=99`) | `ValidationError: Extra inputs are not permitted` at class creation. |
| A wrong type (`sort_order="abc"`) | `ValidationError` at class creation. |
| A coercible value (`sort_order="42"`) | Accepted and stored by Pydantic's lax rules (`42`, `int`). |

The validation is the ordinary Pydantic constructor: `code` and `display_name` are required and non-blank, the status is frozen, and `extra="forbid"` applies.

## 4. The catalogue

| Member | Type | Contract |
| --- | --- | --- |
| `members` | `tuple[BaseStateEntity, ...]` | The declared instances, in declaration order. |
| `codes()` | `list[str]` | The codes, in declaration order. |
| `by_code(code)` | `BaseStateEntity` | The declared instance; `KeyError` for an unknown code. |
| `entity_type` | `type[BaseStateEntity]` | The state type itself. |

A duplicate code is refused at class creation with a `ValueError` naming the type and the code.

## 5. Inheritance

| Case | Result |
| --- | --- |
| A subclass with no statuses | Inherits the parent's `members`, `codes()`, `by_code()`, `entity_type`. |
| A subclass that declares statuses | Gets its own catalogue from its own declarations; the parent's statuses are not extended into it. |
| A state type with no statuses | Valid; `members == ()`. |

## 6. Typing

- `OrderStateEntity.DRAFT` is typed as `OrderStateEntity`; every field is visible to mypy.
- No `cast` and no `TYPE_CHECKING` block is needed.
- `mypy --strict` is clean.
- The arguments of the call are checked by Pydantic at class creation; static checking of the argument names would need the `pydantic.mypy` plugin, which is out of scope.

## 7. What the state type is not

- It is not a `Lifecycle` and carries no transitions.
- It is not an entity of the model graph (`exclude_graph_model`).
- It does not own the axis; the axis names it.

## 8. Requirement map

| Contract | Requirement |
| --- | --- |
| The surface and the alias | FR-001, FR-006 |
| The instances and the order | FR-002 |
| The catalogue API | FR-003 |
| Inheritance | FR-004 |
| Fields and defaults | FR-005 |
| No cast and no `TYPE_CHECKING` | FR-015 |
| The factory is internal | FR-016 |
| The placeholders are excluded | FR-017 |
| The kind, the name and the graph exclusion | FR-018 |
