# Contract — declaring an entity of a kind

**Feature**: `specs/013-entity-type-markers` | **Audience**: a model author writes these lines; the framework is held to them.

## Public surface

```python
from aoa.action_machine.domain import (
    BaseCoreEntity, BaseAssocEntity, BaseDetailEntity,
    BaseSpecEntity, BaseEnumEntity, BaseStateEntity,
    EntityKind,
)
from aoa.action_machine.intents.entity import entity
```

All six marker names and `EntityKind` are exported from `aoa.action_machine.domain`, which is the facade the demo and the examples are allowed to import from (`scripts/check_maxitor_samples_public_api.py`). No new module path is part of the contract.

## The six kinds

| Kind | Marker | Suffix | Declare it when the instance is … |
| --- | --- | --- | --- |
| `CORE` | `BaseCoreEntity` | `CoreEntity` | a domain object in its own right: an order, a customer, a product, a contract, a supplier offer — even when its table looks like a join table |
| `ASSOC` | `BaseAssocEntity` | `AssocEntity` | nothing but the fact that participants are connected: a product's membership in a category. No domain data, no lifecycle, no specialization, not an owned part |
| `DETAIL` | `BaseDetailEntity` | `DetailEntity` | an identifiable part of one owner: an order line, a recipe step. Identity = owner + discriminator; a separate UUID does not free it |
| `SPEC` | `BaseSpecEntity` | `SpecEntity` | what is specific to one kind of a general object: organisation data on a counterparty head. Identity = exactly the head's |
| `ENUM` | `BaseEnumEntity` | `EnumEntity` | a shared reference value: a currency, a country, an edition kind. Code-identified; no business lifecycle |
| `STATE` | `BaseStateEntity` | `StateEntity` | a state of a lifecycle, declared through a `Lifecycle` (and optionally a `StateVocabulary`), not decorated with `@entity` |

The decision is made by what an instance represents, never by the number of foreign keys, the presence of an `id` column, or the shape of a table.

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
    """An intermediate abstract descendant — exempt from the suffix rule."""
```

An ordinary mixin may accompany a marker:

```python
class AuditStampCoreEntity(AuditMixin, BaseCoreEntity):   # accepted: one marker
    ...
```

A declaration whose chain carries no marker, or two, is refused; so is a name that does not carry the kind's suffix. An **intermediate abstract** class — a base that descends from a marker and is not decorated with `@entity` — is allowed, is exempt from the suffix rule, and is kept out of the graph only if it is itself marked `exclude_graph_model` (today's rule).

## Refusals

| Declaration | Raised | Message names |
| --- | --- | --- |
| `@entity` on a class with no marker in its MRO | `DeclarationStructureError` | the class; that no marker was found; the six markers |
| `@entity` on a class with two or more markers | `DeclarationStructureError` | the class; both markers |
| `@entity` on a marker itself | `DeclarationStructureError` | the class; that it is a marker, not an entity |
| `@entity` on `OrderEntity` deriving from `BaseCoreEntity` | `NamingSuffixError` | the class; the expected `CoreEntity`; the rename suggestion |
| `@entity` on `OrderSpecEntity` deriving from `BaseDetailEntity` | `NamingSuffixError` | the class; the name's `SpecEntity`; the expected `DetailEntity` |
| a status class named `OrderStatus` | `NamingSuffixError` | the class; the expected `StateEntity` |
| `BaseCoreEntity(...)` | `TypeError` | the class; that a marker cannot be instantiated |

All of these are raised while the module is imported — before a graph exists, before any instance is created. No refusal is a warning, and none is deferred to build time.

## Unchanged

- The generic `…Entity` name invariant on `BaseEntity.__init_subclass__` stays.
- `@entity` still writes `_entity_info` with `description` and `domain`; the decorator's signature does not change.
- A class that inherits `BaseEntity` and carries no `@entity` is not refused by these rules: the framework's negative fixtures and the three example scripts that teach a declaration mistake depend on it, and the missing decorator remains a build-time error of the entity and specialization inspectors.
- `BaseStateEntity` keeps `code`, `display_name`, its blank validation and its exclusion from the model graph; it gains the suffix check on its descendants.
