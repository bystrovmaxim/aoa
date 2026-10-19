# Contract — what a status is, what an axis class guarantees, what it accepts

**Feature**: `specs/012-lifecycle-state-vocabularies` | **Date**: 2026-10-19

This is the declaration surface a model author writes. It is the part the feature promises to keep stable; the graph and the diagram shapes are in [graph-and-fsm-contract.md](./graph-and-fsm-contract.md).

## 1. A status

```python
class SalesOrderStateEntity(BaseStateEntity):
    sort_order: int = Field(default=0, description="Presentation order")
    color: str = Field(default="#9e9e9e", description="Diagram colour")
```

**Accepted**

- any number of additional fields, of any JSON-representable type, with `Field(description=...)` as everywhere else in an entity;
- `Field(exclude=True)` on a field that must not reach the graph.

**Refused at construction**

| Input | Refusal |
| --- | --- |
| `code=""`, `code="   "` | `ValueError`, naming the field |
| `display_name=""`, `display_name="   "` | `ValueError`, naming the field |
| a missing `code` or `display_name` | pydantic's required-field error |
| an undeclared field (a typo) | pydantic's `extra="forbid"` error |

**Guarantees**

- immutable;
- `code` is the identity inside an axis and the only identity a status has;
- a status carries no `initial`/`final` flag and no classification of any kind;
- the type never appears as an entity of the model graph, whatever the author writes.

## 2. The axis class — statuses and links in one declaration

```python
class SalesOrderLifecycle(Lifecycle, StateVocabulary):
    """The sales-order status axis: its statuses and the links between them."""

    NEW = SalesOrderStateEntity(code="new", display_name="New", sort_order=1)
    PAYMENT_PENDING = SalesOrderStateEntity(code="payment_pending", display_name="Payment pending", sort_order=2)
    CANCELLED = SalesOrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=6)

    _template = (
        Lifecycle()
        .state(NEW)
        .to(PAYMENT_PENDING, CANCELLED)
        .initial()
        .state(PAYMENT_PENDING)
        .to(CANCELLED)
        .intermediate()
        .state(CANCELLED)
        .final()
    )
```

**Accepted**

- any number of status attributes of one status type, in any order — declaration order is kept and is the fallback drawing order;
- a subclass of an axis that declares no statuses of its own: it inherits the parent's members and builds;
- a class that applies `StateVocabulary` only together with `Lifecycle`.

**Guaranteed**

| Guarantee | How it is observed |
| --- | --- |
| members in declaration order | `SalesOrderLifecycle.members` |
| lookup by code | `SalesOrderLifecycle.by_code("payment_pending")` |
| all codes | `SalesOrderLifecycle.codes()` |
| the shared status type | `SalesOrderLifecycle.entity_type` |
| a member is the object, not a wrapper | `SalesOrderLifecycle.NEW.code == "new"` |

The vocabulary API is **plain methods only**. `__iter__`, `__len__` and `__contains__` would be inherited by lifecycle instances and make `len(order.lifecycle)` answer the vocabulary question; that is a collision of meanings and is refused by design.

**Refused at class definition**

| Input | Refusal |
| --- | --- |
| statuses of two different types | `TypeError`, naming the member and its type |
| two members with the same code | `ValueError`, naming the code |
| an axis class that declares no statuses and no own `_template` | `ValueError` — an axis must declare at least one status |
| `StateVocabulary` applied to a class that is not a `Lifecycle` | `TypeError`, naming the class |
| a status in `_template` that is not one of the class's status attributes | `TypeError`, naming the status and the class |
| a class attribute that is not a status object | ignored — it is just an attribute of another kind |

**Guarantees**

- the axis class is a `Lifecycle`: `isinstance(axis_instance, Lifecycle)` and the runtime API are unchanged;
- the eight build rules are unchanged and keep owning reachability, finality and target existence;
- the class exposes the objects: `get_state_entity(code)`, `get_state_entities()`.

## 3. The template

```python
    _template = (
        Lifecycle()
        .state(NEW)
        .to(PAYMENT_PENDING, CANCELLED)
        .initial()
        ...
    )
```

**Accepted**

- `.state(status)` — the label comes from `status.display_name`; no second argument;
- `.to(*statuses)` — each is unwrapped to its code;
- a forward reference: `.to(X)` before `.state(X)`;
- any status declared on this class, finalized or not yet finalized.

**Refused at declaration**

| Input | Refusal |
| --- | --- |
| `.state("new", "New")` after phase 5 | `TypeError` — the string form no longer exists |
| `.to("cancelled")` after phase 5 | `TypeError` |
| `.state(status, "Override")` | `TypeError` — the label has one source |
| duplicate code in one template | `ValueError` — unchanged from today |

**Guarantees**

- the class's state metadata, current-state API, transition checking and serialization are unchanged;
- classification and transitions are the class's, never the status's;
- the same status object may be classified differently by two axis classes;
- one axis is one chain; two chains over one axis are out of scope.

## 4. Transitional state of this branch

Phases 1–4 accept both forms so that every commit stays importable; phase 5 removes the string form and replaces the transitional tests with the refusal tests. The contract above describes the delivered state, not the intermediate commits.
