# Contract — declaring an entity of a kind

**Feature**: `specs/013-entity-type-markers` | **Audience**: a model author writes these lines; the framework is held to them.

## Public surface

```python
from aoa.action_machine.domain import (
    BaseCoreEntity, BaseAssocEntity, BaseDetailEntity,
    BaseSpecEntity, BaseEnumEntity, BaseStateEntity,
)
from aoa.action_machine.intents.entity import entity
```

The six kind base classes are exported from `aoa.action_machine.domain`, the facade the demo and the examples are allowed to import from (`scripts/check_maxitor_samples_public_api.py`). There is no other name to import: no enum, no registry, no decorator on the base classes.

## The six kinds

| Kind base class | Suffix | Wire word | Declare it when the instance is … |
| --- | --- | --- | --- |
| `BaseCoreEntity` | `CoreEntity` | `core` | a domain object in its own right: an order, a customer, a product, a contract, a supplier offer — even when its table looks like a join table |
| `BaseAssocEntity` | `AssocEntity` | `assoc` | nothing but the fact that participants are connected: a product's membership in a category. No domain data, no lifecycle, no specialization, not an owned part |
| `BaseDetailEntity` | `DetailEntity` | `detail` | an identifiable part of one owner: an order line, a recipe step. Identity = owner + discriminator; a separate UUID does not free it |
| `BaseSpecEntity` | `SpecEntity` | `spec` | what is specific to one kind of a general object: organisation data on a counterparty head. Identity = exactly the head's |
| `BaseEnumEntity` | `EnumEntity` | `enum` | a shared reference value: a currency, a country, an edition kind. Code-identified; no business lifecycle |
| `BaseStateEntity` | `StateEntity` | `state` | a state of a lifecycle, declared through a `Lifecycle` (and optionally a `StateVocabulary`), not decorated with `@entity` |

The decision is made by what an instance represents, never by the number of foreign keys, the presence of an `id` column, or the shape of a table. The suffix and the word are not repeated anywhere: they are the base class's name minus `Base` (and minus `Entity` for the word).

## Accepted declarations

```python
@entity(description="Customer order", domain=ShopDomain)
class SalesOrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    lifecycle: SalesOrderLifecycle = Field(description="Order status axis")


@entity(description="Line of an order", domain=ShopDomain)
class SalesOrderLineDetailEntity(BaseDetailEntity):
    id: str = Field(description="Line id")


class SalesOrderStateEntity(BaseStateEntity):
    sort_order: int = Field(default=0, description="Presentation order")


class BaseTransportCoreEntity(BaseCoreEntity, ABC):
    """An intermediate abstract descendant — held to the suffix like any descendant."""
```

An ordinary mixin may accompany a kind base class:

```python
class AuditStampCoreEntity(AuditMixin, BaseCoreEntity):   # accepted: one kind
    ...
```

## Refusals

| Declaration | Raised | Message names |
| --- | --- | --- |
| a class inheriting `BaseEntity` directly (and not being a kind base class) | `DeclarationStructureError` | the class; that it inherits the entity base directly; the six kind base classes |
| a class inheriting two kind base classes | `DeclarationStructureError` | the class; both |
| `OrderEntity` deriving from `BaseCoreEntity` | `NamingSuffixError` | the class; the expected `CoreEntity`; the rename suggestion |
| `OrderSpecEntity` deriving from `BaseDetailEntity` | `NamingSuffixError` | the class; the expected `DetailEntity` |
| a status class named `OrderStatus` | `NamingSuffixError` | the class; the expected `StateEntity` |
| `BaseCoreEntity(...)` | `TypeError` | the class; that it is the base class of a kind and cannot be instantiated |

All of these are raised while the module is imported — before a graph exists, before any instance is created. No refusal is a warning, and none is deferred to build time.

## How the check is organised

| Rule | Where it lives | Why there |
| --- | --- | --- |
| name ends with `Entity` | `BaseEntity.__init_subclass__` | it is about the base, not about a kind |
| no direct inheritance, one kind in the chain | `BaseEntity.__init_subclass__` | they are about the hierarchy and know no kind |
| a kind base class is abstract and out of the graph | `BaseEntity.__init_subclass__`, which recognises one by direct inheritance plus an overridden hook | it follows from the class's own shape, not from an attribute |
| name ends with the kind's suffix | each kind base class's own `__init_subclass__` | the base class owns the suffix, so it owns the message and the rule |
| the suffix and the wire word | the kind base class's own name | one source, so the two cannot disagree |

## Unchanged

- The generic `…Entity` name invariant on `BaseEntity.__init_subclass__` stays and fires before the kind rules.
- `@entity` still writes `_entity_info` with `description` and `domain`; the decorator's signature does not change, and it gains no new check.
- A class that carries a kind base class and no `@entity` is not refused: the framework's negative fixtures and the three example scripts that teach a declaration mistake depend on it, and the missing decorator remains a build-time error of the entity and specialization inspectors.
- `BaseStateEntity` keeps `code`, `display_name`, its blank validation and the exclusion of every status type from the model graph.
