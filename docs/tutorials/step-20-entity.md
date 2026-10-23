<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 20 — Entity: choose what the object represents

[← Resource](step-19-resource.md) · [Contents](../index.md) · [Relations →](step-21-relations.md)

An action works with an order, a customer, or a payment. The database may return these as rows, and an external service may return them as JSON. The action should not have to understand either storage format. An **entity** declares the information the domain needs; a [resource](step-19-resource.md) retrieves that information and constructs the entity.

Before declaring fields, decide what one instance represents. An order, an order line, and an order's current state are all useful domain information, but they have different identities and behaviour. An order line belongs to a particular order. A state describes a position in a process and can be shared by many orders. Treating all three as interchangeable objects would hide those differences from both the reader and the model's consumers.

AOA provides six **kind base classes**, also called markers. Each states the role of its descendants. A concrete entity inherits one kind, and its name carries the corresponding suffix. The common `BaseEntity` remains the foundation for fields, validation and partial loading; an ordinary application class chooses one of the six kinds instead of inheriting that foundation directly.

## Start with an independent object

[Script](../../examples/step_20_entity/01_entity.py) · [Notebook](../../examples/step_20_entity/01_entity.ipynb)

An order is something the business identifies in its own right. It stays the same order when its total or state changes. That makes it a **core entity**. Independence here does not mean isolation: an order may depend on a customer and refer to products while retaining its own business meaning.

```python
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, build
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order independently of its storage."""

    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")


order = build({"id": "ord-1", "total": 1500.0}, OrderCoreEntity)
print(type(order).__name__)
print(order.id, order.total)
```

```text
OrderCoreEntity
ord-1 1500.0
```

There are two separate declarations here. `BaseCoreEntity` supplies the kind and requires the `CoreEntity` suffix. `@entity` supplies the description used by the domain model; `domain=ShopDomain` assigns the owning domain, which entity graph construction requires. Python creates the class before applying the decorator, so inheritance and suffix errors occur before `@entity` runs. Neither declaration creates a database table or retrieves data.

## Understand the six kinds

**Identity** means what makes something the same object when its data changes. A database key may represent that identity, but choosing a marker is a domain decision. Neither an `id` column nor the number of foreign keys decides the kind.

| Base class | Meaning of one instance | Required suffix |
| --- | --- | --- |
| `BaseCoreEntity` | An independent domain object | `CoreEntity` |
| `BaseAssocEntity` | Only the fact that participants are connected | `AssocEntity` |
| `BaseDetailEntity` | An identifiable part of one owner | `DetailEntity` |
| `BaseSpecEntity` | Variant-specific data of the same general object | `SpecEntity` |
| `BaseEnumEntity` | A declared value of a closed dictionary | `EnumEntity` |
| `BaseStateEntity` | The description of a lifecycle state | `StateEntity` |

### A technical association records only a connection

[Script](../../examples/step_20_entity/04_association.py) · [Notebook](../../examples/step_20_entity/04_association.ipynb)

A product's membership in a category can be represented by a record containing two references: the product and the category. Its entire business meaning is that connection. This is the narrow meaning of **associative entity** in AOA: a technical association without domain data of its own.

A service identifier and insertion or update timestamps are allowed. They help maintain the record without adding meaning to the relationship. Field names alone are not enough to decide this: the time a database row was inserted can be technical, while the date an agreement takes effect is business information.

The example constructs one `ProductCategoryAssocEntity` with identifier-only references. It prints:

```text
product-1 belongs to category-1
```

An `AssociationOne` field holds a reference to another entity. `BaseAssocEntity` classifies the whole link record. These are different concepts: an order can contain an association to its customer and still be a core entity.

Now consider a supplier-product record containing a price, minimum quantity and delivery terms. It represents a supplier offer, with business content beyond the connection. Model it as a core entity. Likewise, an agreement that must be approved or suspended has its own business process and is not a technical association.

This boundary makes the marker useful to a viewer: it could show a technical association as a direct connection without losing business data. An offer must remain visible because hiding it would hide its terms. This branch provides the classification to Maxitor; it does not implement that rendering behaviour.

### A detail belongs to one owner

[Script](../../examples/step_20_entity/05_detail.py) · [Notebook](../../examples/step_20_entity/05_detail.ipynb)

An order line is a part of a particular order. In domain terms, “line 3” is incomplete identification; “line 3 of order ord-1” identifies the part. The value that distinguishes parts within an owner is called a **discriminator**, here the line number.

The example gives the line a storage identifier, an owning order, a line number and a quantity. It prints both forms of identification:

```text
domain identity: ord-1 3
storage key: {'id': 'line-uuid'}
```

These answers describe different layers. The domain treats the line as an owner-dependent part. The current `get_primary_key()` method returns `id` by convention; selecting `BaseDetailEntity` does not make it discover a composite key. The separate storage identifier does not turn the line into an independent core entity.

A detail can contain business data and have a lifecycle of its own: a line may have a price, quantity and fulfilment state. It can also own further details. Such content does not turn it into a technical association or an independent object. Its defining property is ownership. If the object must continue independently after its owner ceases to exist, reconsider the classification.

The example declares that ownership with `CompositeMany` on the order and a reverse reference on the line. [The next chapter](step-21-relations.md) explains these containers. They describe the relationship; the marker does not execute database deletions or persistence operations.

### A specialization describes what kind of object the head is

[Script](../../examples/step_20_entity/06_specialization.py) · [Notebook](../../examples/step_20_entity/06_specialization.ipynb)

A counterparty may be an organisation or an individual. The common entity holds the counterparty's identity and shared information. The organisation variant adds its registration data. The common entity is called the **head**; the variant-specific entity is a **specialization**.

The two describe the same counterparty. They use the same identity; the specialization does not introduce another object alongside the head. In the example both identifiers are `party-1`:

```text
same identity: True
registration: REG-42
```

This distinguishes a specialization from a detail. A line answers “which part of this order?” Organisation data answers “what kind of counterparty?” The former has a discriminator within its owner; the latter reuses the head's complete identity. A specialization of a detail likewise reuses the detail's identity without adding another discriminator.

The head's `Specialization[...]` field points to variant data and names a closed dictionary as its second type argument. The variant's `Generalization[...]` points back to the head, and its `Classifier` names one of that dictionary's values. These are model relationships: the concrete specialization does not inherit the head's Python fields. It inherits `BaseSpecEntity`; a core head inherits `BaseCoreEntity`.

The contract calls for one reverse generalization and at most one instance of a given variant per head. It permits a lifecycle for variant-specific data, but does not make the specialization another specialization head or an owned component. The build checks the declared relationship and the two-sided value comparison: every value the dictionary declares has exactly one alternative, and every alternative names exactly one of its values. The kind marker itself does not validate key equality or enforce every domain restriction. The examples follow the identity contract even where the runtime does not enforce it.

### An enumeration describes a shared reference value

[Script](../../examples/step_20_entity/07_enumeration.py) · [Notebook](../../examples/step_20_entity/07_enumeration.ipynb)

A currency is a value many prices refer to. The currency's name and symbol describe that
value; a dated exchange-rate quote is a separate business fact. Removing one price does
not remove its currency. Unlike a state, the currency is not a position in a process.

`BaseEnumEntity` describes a **closed dictionary**: the complete set of allowed values is
declared in the class body. It supplies required, nonblank `code` and `display_name`
fields. The currency class adds `symbol` and declares EUR and USD. These declarations
use `EUR = value(code="eur", display_name="Euro", symbol="€")`, with `value` imported
from `aoa.action_machine.domain`. The factory records arguments; after class creation
EUR is a validated, shared instance. Dictionary properties are restricted to supported
immutable annotations: use a tuple for a fixed sequence rather than a list.

The example reads the catalogue:

```text
Codes: ['eur', 'usd']
Members: 2
Same object: True
Value: Euro €
```

`codes()` preserves declaration order. `by_code("eur")` returns the declared EUR object;
an unknown code raises `KeyError`. A field typed as `CurrencyEnumEntity` holds a declared
value. Its serialized reference contains the code, label and descriptive properties.
A bare string, an unknown reference code and a constructed copy are refused.

A dictionary subclass inherits fields but declares its own catalogue. An undecorated
intermediate may have no values; a dictionary registered with `@entity` must have at least
one. A table whose entries users maintain in data has a different purpose: model it as a
core entity with a suitable unique code rather than pretending its set is closed in code.

[Closed dictionaries in practice](step-20-dictionaries.md) develops these rules through
separate runnable cases: a typed field, a stale reference payload, storage mapping,
serialization, optional absence, inheritance, graph export and each invalid input.

### A state describes a position in a process

[Script](../../examples/step_20_entity/08_state.py) · [Notebook](../../examples/step_20_entity/08_state.ipynb)

“Paid” describes where an order stands in its lifecycle. Unlike a currency, it participates in a process with allowed transitions. The lifecycle template defines those transitions and determines which states are initial, intermediate or final. The state object holds its code, human-readable name and any additional descriptive fields.

`BaseStateEntity` supplies `code` and `display_name` and requires nonblank values. Statuses are declared with `PAID = value(...)` and can be shared. Their model is frozen
against attribute reassignment, but nested mutable properties are not recursively frozen;
the dictionary's property-type restriction does not apply to states. A thousand paid orders can point to the same declared `PAID` object while each lifecycle instance holds its own current-state reference.

The example moves a draft order lifecycle to paid and prints:

```text
code: paid
receipt required: True
shared declared object: True
excluded from entity graph: True
```

`current_state` returns the code used for storage or exchange. `current_status` returns the declared object, including its additional fields. State classes do not need `@entity`; the state type declares its statuses and carries their catalogue, and `Lifecycle[StateType]` names it. They are excluded from ordinary Entity nodes, while the lifecycle exports its own State nodes. [Step 22](step-22-lifecycle.md) develops this distinction and the transition rules.

### Choose one role for each class

Foreign keys do not make an object associative. Business fields do not automatically make it core: details and specializations also have business content. A code does not make every object an enumeration: states describe positions in processes.

One class carries one kind because one instance must have a clear role. Separate related classes express the other roles: an order, its lines, its variant data, its currency and its current state. The framework checks inheritance and names. Deciding whether the chosen kind accurately represents the domain remains the model author's responsibility; it does not inspect `price` and reclassify a technical link for you.

## Hydrate the entity at the resource boundary

[Script](../../examples/step_20_entity/02_mapping.py) · [Notebook](../../examples/step_20_entity/02_mapping.ipynb)

Selecting a kind leaves the common entity operations available. If storage columns differ from domain field names, the resource supplies a mapping:

```python
row = {"order_id": "ord-2", "amount": 99.5}
order = build(
    row,
    OrderCoreEntity,
    lambda fields, row: {
        fields.id: row["order_id"],
        fields.total: row["amount"],
    },
)
print(order.id, order.total)
```

```text
ord-2 99.5
```

`fields.id` and `fields.total` are field-name tokens used by the mapper. The resource translates storage vocabulary; an action receives the same `OrderCoreEntity`. Entity instances remain frozen, and undeclared fields are forbidden. An [entity schema projection](step-15-schema-results.md) is a separate concern: it describes which fields leave the application through an external result.

## Distinguish unloaded data from a loaded value

[Script](../../examples/step_20_entity/03_partial.py) · [Notebook](../../examples/step_20_entity/03_partial.ipynb)

A query may retrieve only an identifier. Use `OrderCoreEntity.partial(id="ord-3")` to represent that load level. The type still declares `total`, but that instance has not loaded it:

```text
total loaded: False
FieldNotLoadedError
```

`is_field_loaded("total")` reports availability without reading the field. Reading an unloaded declared field raises `FieldNotLoadedError`, rather than silently returning `None`. This allows one domain class to serve several load levels without pretending every field is available. Partial construction does not turn the object into another kind.

## Inherit a kind and add ordinary behaviour

[Intermediate class: script](../../examples/step_20_entity/09_inheritance.py) · [Notebook](../../examples/step_20_entity/09_inheritance.ipynb)

Common fields may live in `BaseDocumentCoreEntity`, with `InvoiceCoreEntity` inheriting from it. Both names must end in `CoreEntity`: the rule follows the whole inheritance chain. The example uses an abstract method to make the intermediate class abstract and `@exclude_graph_model` to keep it out of discovery. A `Base` prefix alone does not do either. The concrete invoice prints `Invoice inv-1`.

[Ordinary mixin: script](../../examples/step_20_entity/10_mixin.py) · [Notebook](../../examples/step_20_entity/10_mixin.ipynb)

A plain mixin may supply methods alongside one kind base. `OrderCoreEntity(LabelMixin, BaseCoreEntity)` is valid because `LabelMixin` does not supply a second entity kind. The example's inherited method prints `OrderCoreEntity`. Combining `BaseCoreEntity` and `BaseDetailEntity` is different: both attempt to classify the same instance.

## Read the kind from the exported graph

[Script](../../examples/step_20_entity/11_graph_kind.py) · [Notebook](../../examples/step_20_entity/11_graph_kind.ipynb)

Every exported Entity row includes `properties.entity_kind`. The value comes from the kind base in the inheritance chain, rather than a separately maintained field on each model. The six wire values are `core`, `assoc`, `detail`, `spec`, `enum` and `state`; state types are excluded from Entity rows, so normal graph export does not produce `state` there.

The example builds a graph, loads it into Maxitor's DuckDB store, and reads the same value from both:

```text
graph: core
Maxitor store: core
```

The kind is a required graph property, not an optional hint. [The missing-property case](../../examples/step_20_entity/26_graph_requires_kind.py) ([notebook](../../examples/step_20_entity/26_graph_requires_kind.ipynb)) removes it and prints `Entity row without entity_kind: rejected`. Rebuild graph exports produced before this property was required. Concrete class renames also change graph labels and identifiers containing qualified class names; check consumers that store those identifiers.

Maxitor preserves the kind, but this branch does not make its renderer automatically collapse associative entities. See [Step 26](step-26-maxitor.md) for graph and diagram usage.

## Understand declaration failures

Each example below contains one invalid declaration and catches its expected exception. It raises an assertion if the framework unexpectedly accepts it, so successful execution demonstrates the refusal. Run any script from the repository root, for example:

```bash
uv run python examples/step_20_entity/22_kind_suffix.py
```

| Case | Why it fails | Result | Runnable example |
| --- | --- | --- | --- |
| Ordinary `OrderEntity(BaseEntity)` | No kind was selected | `DeclarationStructureError` | [Script](../../examples/step_20_entity/20_direct_base.py) · [Notebook](../../examples/step_20_entity/20_direct_base.ipynb) |
| Core and Detail in one hierarchy | Two kinds classify the same instance | `DeclarationStructureError` | [Script](../../examples/step_20_entity/21_two_kinds.py) · [Notebook](../../examples/step_20_entity/21_two_kinds.ipynb) |
| `OrderEntity(BaseCoreEntity)` | Generic `Entity` is not the required `CoreEntity` suffix | `NamingSuffixError` | [Script](../../examples/step_20_entity/22_kind_suffix.py) · [Notebook](../../examples/step_20_entity/22_kind_suffix.ipynb) |
| `OrderDetailEntity(BaseCoreEntity)` | Name and inherited kind disagree | `NamingSuffixError` | [Script](../../examples/step_20_entity/23_wrong_kind_suffix.py) · [Notebook](../../examples/step_20_entity/23_wrong_kind_suffix.ipynb) |
| `BaseDocumentEntity(BaseCoreEntity, ABC)` | Intermediate classes also need the kind suffix | `NamingSuffixError` | [Script](../../examples/step_20_entity/24_intermediate_suffix.py) · [Notebook](../../examples/step_20_entity/24_intermediate_suffix.ipynb) |
| `BaseCoreEntity()` | A kind base is not an application object | `TypeError` | [Script](../../examples/step_20_entity/25_marker_instance.py) · [Notebook](../../examples/step_20_entity/25_marker_instance.ipynb) |

The naming example prints the actual diagnostic:

```text
NamingSuffixError: Class 'OrderEntity' must end with 'CoreEntity'. Rename it to 'OrderEntityCoreEntity'.
```

The suggested name mechanically appends the suffix. `OrderCoreEntity` is a clearer valid rename. Changing the decorator or waiting until graph construction cannot repair the bad declaration: Python has already refused to create the class. An undecorated class is checked in the same way. A kind base's construction error, by contrast, occurs when the example attempts to instantiate it.

For the complete validation reference, see [Intents and invariants](../reference/intents-and-invariants.md#entity-kinds). The next chapter explains how these distinct objects are connected through [relations](step-21-relations.md).
