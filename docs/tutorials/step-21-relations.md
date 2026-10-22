<!-- translated-from: step-21-relations_draft.md @ 2026-06-17T17:53:37Z · sha256:7b2c3bf4bfe3 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 21 — Relations between entities

<table width="100%"><tr>
  <td align="left"><a href="step-20-entity.md">← Step 20 — Entity</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-22-lifecycle.md">Step 22 — Lifecycle →</a></td>
</tr></table>

- [Containers: cardinality and ownership](#containers-cardinality-and-ownership)
- [Inverse: the reverse side and the startup check](#inverse-the-reverse-side-and-the-startup-check)
- [Partial loading of relations](#partial-loading-of-relations)
- [Generalization and specialization](#generalization-and-specialization)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

An [entity](step-20-entity.md) rarely stands alone: an order has a customer and lines, a customer has orders. In an ordinary project these are foreign keys and ORM "lazy" relations — hidden queries when you touch a field, and a silent `None` when the related data was not loaded. AOA declares relations **explicitly**: with a container that carries both the cardinality and the meaning of ownership, and is checked at startup.

[▶ Try in Colab](https://drive.google.com/file/d/1i3f6nn3qS79i2aBMB1s6Hr4uyfpByUxP/view?usp=drive_link) · [Open in project](../../examples/step_21_relations/01_relations.py)

The full domain picture: [▶ Try in Colab](https://drive.google.com/file/d/10H7oiSPR7d9rtJask9ccCzqDKSa4H9wQ/view?usp=drive_link) · [Open in project](../../examples/domain_model/01_domain_model.py)

---


The [previous chapter](step-20-entity.md) distinguishes an entity's kind from its relationships. A core order can have an association to a core customer and own detail lines through composition. The presence of an association field does not turn the order into an associative entity. `BaseAssocEntity` is reserved for a separate technical link record with no domain data of its own. Likewise, variant-specific data uses `BaseSpecEntity`, not `BaseDetailEntity`: it describes the same head object rather than one of its parts.


## Containers: cardinality and ownership

A relation container is an object that keeps the identifier of a related entity and, when available, the entity itself. The ownership containers describe two dimensions: **how many** (`One`/`Many`) and **whose ownership**:

| Container | Ownership | Meaning |
|-----------|-----------|---------|
| `CompositeOne` / `CompositeMany` | strong | the part does not exist without the whole (order lines) |
| `AggregateOne` / `AggregateMany` | weak | the part can live separately |
| `AssociationOne` / `AssociationMany` | none | an independent reference (order ↔ customer) |

A relation is declared in `Annotated`: the container type plus the `Inverse(...)` marker (or `NoInverse()`), with a mandatory `Rel(description=...)` as the field's value:

The complete declarations below are the preparation for the order examples in this section. Run them once before the later value-construction blocks. `Annotated` attaches relation metadata to a field type, and `model_rebuild()` resolves references to classes declared later in the file.

```python
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDetailEntity,
    CompositeMany,
    Inverse,
    Rel,
    RelationNotLoadedError,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="Customer account", domain=ShopDomain)
class CustomerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Customer id")
    name: str = Field(description="Display name")

    orders: Annotated[
        AssociationMany[OrderCoreEntity],
        Inverse(OrderCoreEntity, "customer"),
    ] = Rel(description="Orders placed by this customer")


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")

    # association — order and customer exist independently
    customer: Annotated[
        AssociationOne[CustomerCoreEntity],
        Inverse(CustomerCoreEntity, "orders"),
    ] = Rel(description="Customer who placed the order")

    # composition — line items cannot exist without this order
    lines: Annotated[
        CompositeMany[OrderLineDetailEntity],
        Inverse(OrderLineDetailEntity, "order"),
    ] = Rel(description="Line items of the order")


@entity(description="Single line of an order", domain=ShopDomain)
class OrderLineDetailEntity(BaseDetailEntity):
    id: str = Field(description="Line id")
    sku: str = Field(description="Product code")

    order: Annotated[
        AssociationOne[OrderCoreEntity],
        Inverse(OrderCoreEntity, "lines"),
    ] = Rel(description="Parent order")


CustomerCoreEntity.model_rebuild()
OrderCoreEntity.model_rebuild()
OrderLineDetailEntity.model_rebuild()
```



`One`/`Many` set the cardinality, `composition`/`aggregation`/`association` set the meaning of ownership. These relations land in the graph and the ERD of [Maxitor](../index.md#vii-maxitor).

## Inverse: the reverse side and the startup check

`Inverse(Target, "field")` explicitly names the **paired field** on the other side. This is needed because the heuristic "find the reverse relation by type" breaks the moment an entity has two fields of the same type — whereas a single line `Inverse(OrderCoreEntity, "lines")` is unambiguous and survives refactoring. Every declared relation must carry `Rel(description=...)` — the model stays a specification, not just code.

When the graph is built (and it is built when the machine is created), the coordinator **checks the mirroring**: that the paired field exists, that the types and target entities match, and that the cardinality is compatible. An error in the relation model surfaces **at startup**, not half a year later in a report. In the example this is visible in the first line: the machine assembled — which means the relations were validated.

For an honestly one-way link, put `NoInverse()` (the absence of a reverse side is intentional, not forgotten); `NoGraphEdge()` removes the edge from the interchange graph while keeping the field in the node metadata.

## Partial loading of relations

Loading the related object into a container is also called **hydration**. It does not happen automatically. The [partial-loading](step-20-entity.md#distinguish-unloaded-data-from-a-loaded-value) rule extends to relations too: the container **always knows the id**, but the related entity may not be loaded. Reaching through an un-hydrated container is a `RelationNotLoadedError`, not a silent `None` and not a hidden query:

```python
order = OrderCoreEntity(
    id="ord-1", total=1500.0,
    customer=AssociationOne[CustomerCoreEntity](id="cust-1"),          # id only
    lines=CompositeMany[OrderLineDetailEntity](ids=("line-1", "line-2")),# ids only
)

order.customer.id      # ok — the id is always there
order.customer.name    # RelationNotLoadedError — the customer row is not loaded
len(order.lines)       # 2 — the number of ids is known
list(order.lines)      # RelationNotLoadedError — the line entities are not hydrated
```

To make a relation loaded, pass the entity itself (`One`) or the entities (`Many`) into the container; then attribute access is proxied to it:

```python
customer = CustomerCoreEntity(
    id="cust-1", name="Alice",
    orders=AssociationMany[OrderCoreEntity](ids=("ord-1",)),
)
order2 = OrderCoreEntity(
    id="ord-2", total=99.0,
    customer=AssociationOne[CustomerCoreEntity](id="cust-1", entity=customer),  # hydrated
    lines=CompositeMany[OrderLineDetailEntity](entities=(), entities_loaded=True),
)
order2.customer.name   # "Alice"
```

**Run:**

```bash
uv run python examples/step_21_relations/01_relations.py
```

**Output:**

```text
1) Machine built — relation model validated at startup (Inverse mirroring OK)

2) Id-only relations:
   order.customer.id  = cust-1   (is_loaded=False)
   len(order.lines)   = 2   (is_loaded=False)
   order.customer.name -> RelationNotLoadedError: Related object in AssociationOne is not loaded (id='cust-1'). Cannot access 'name' — only the identifier is present. Load the related entity through your persistence / manager layer.
   iterating order.lines -> RelationNotLoadedError (ids known, rows not loaded)

3) Hydrated relation:
   order2.customer.name = Alice   (proxied through the loaded entity)
```

Different queries return one `OrderCoreEntity` with different relation-load depth — and the system controls accidental access to the not-loaded, instead of quietly slipping in a `None` or going to the database behind your back.

## Generalization and specialization

### Start with the information we need to represent

Consider a catalogue of vinyl records. Every record has an identifier and an album title.
A first pressing additionally has a stamper code; a re-pressing has the year it was pressed
again; a test pressing has the name of its reviewer. A stamper is the tool used to press
the record. These fields describe different kinds of the same record, rather than three
independent objects that happen to be related to it.

We put shared information in `VinylRecordCoreEntity`. This class is called the **head**.
The classes containing the different sets of specific information are its **alternatives**:
`FirstPressSpecEntity`, `RepressSpecEntity` and `TestPressSpecEntity`. An alternative inherits
`BaseSpecEntity` and shares the head object's identity. It is not a component with a
separate identity, and it is not a Python subclass of the head.

The head's `pressing` field points towards one alternative. This direction is called
**specialization**. Each alternative's `record` field points back towards the shared
information. That direction is **generalization**. The corresponding containers are
`Specialization[Alternatives, Dictionary]` and `Generalization[Head]`. They carry references
and optionally loaded objects; they do not load rows or generate database tables.

Before connecting these classes, we need names for the possible choices. The closed
dictionary `VinylRecordKindEnumEntity` declares `FIRST`, `REPRESS` and `TEST`, with codes
`first`, `repress` and `test`. A code is an identifier within this dictionary, not a Python
class name. If closed dictionaries are new to you, read
[the dictionary guide](step-20-dictionaries.md) first.

One specialization field together with its dictionary and alternative classes is an
**axis**. Here `pressing` is the only axis. The term becomes useful when an object has
several such fields, because each field describes a separate choice.

### Declare the complete model

This preparation is complete: dictionary, head, alternatives and the type-resolution
calls. Run it before an experiment below. Every linked script and notebook contains its
own copy, so each experiment can also be run independently. Do not import several of the
intentionally invalid examples into one process: model build examines loaded declarations.

```python
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Kind of VinylRecordCoreEntity", domain=MusicDomain)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    FIRST = VinylRecordKindEnumEntity(code="first", display_name="First")  # noqa: F821
    REPRESS = VinylRecordKindEnumEntity(code="repress", display_name="Repress")  # noqa: F821
    TEST = VinylRecordKindEnumEntity(code="test", display_name="Test")  # noqa: F821


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(field="record", variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(field="record", variant=VinylRecordKindEnumEntity.REPRESS),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(field="record", variant=VinylRecordKindEnumEntity.TEST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()
```

Read `pressing` from the inside out. The first argument of `Specialization` is a union:
the vertical bars mean that loaded details can have any of the three listed types.
The second argument names the dictionary that supplies the allowed values. The head
stores the selected value in its container's `variant`; it needs no second scalar field
and no `Classifier` marker. `Inverse(field_name="record")` names the paired field on every
alternative. `Rel` provides the relationship description, not loaded data.

Now read `FirstPressSpecEntity.record`. `Generalization[VinylRecordCoreEntity]` identifies
the head. `Classifier(field="record", variant=VinylRecordKindEnumEntity.FIRST)` says which
reverse field this marker describes and which dictionary value selects this class.
`Inverse(VinylRecordCoreEntity, "pressing")` identifies the paired field on the head.
The other alternatives follow the same form with their own values.

The dictionary declares the vocabulary once. Each alternative names a member of that
vocabulary. Model build checks that every value selects exactly one alternative, and
that every alternative names an actual member of this dictionary. Equal strings on a
copied or foreign object do not establish membership.

Three different events are involved. Creating Python classes records declarations and
constructs dictionary values. `model_rebuild()` resolves annotations that mention classes
defined later. Creating `ActionProductMachine` builds and checks AOA's declared model.
Finally, constructing a container validates the particular data supplied to it. A valid
model does not prove that every row in a database is valid.

### A record with first-pressing details

Construct the common record and its first-pressing data.

[Script](../../examples/step_21_relations/02_specialization.py) · [Notebook](../../examples/step_21_relations/02_specialization.ipynb)

```python
ActionProductMachine(loggers=[])
first = FirstPressSpecEntity(
    id="rec-1",
    stamper="1A",
    record=Generalization[VinylRecordCoreEntity](id="rec-1"),
)
record = VinylRecordCoreEntity(
    id="rec-1",
    title="Kind of Blue",
    pressing=Specialization[
        FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity
    ](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
        entity=first,
    ),
)
print("Model built")
print(record.title)
print(record.pressing.variant.code)
print(record.pressing.entity.stamper)
print(first.record.id)
```

Output:

```text
Model built
Kind of Blue
first
1A
rec-1
```

The head and its details describe the same record, so both use rec-1. variant holds FIRST; entity holds the FirstPressSpecEntity instance already in memory. This does not fetch data, create tables or copy fields between the two classes.

### Known variant, unloaded details

Keep a reference to a first pressing without loading its stamper data.

[Script](../../examples/step_21_relations/03_specialization_unloaded.py) · [Notebook](../../examples/step_21_relations/03_specialization_unloaded.ipynb)

```python
link = Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
    id="rec-1",
    variant=VinylRecordKindEnumEntity.FIRST,
)
print(link.id)
print(link.variant.code)
print(link.entity)
```

Output:

```text
rec-1
first
None
```

The identifier and dictionary value remain available. entity is None because no object was supplied. It does not prove that the corresponding stored row is missing.

For the next example, the head field explicitly permits absence: its type is `Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity] | None`. All other declarations stay the same.

### No classification yet

An explicitly optional specialization can be absent while its model remains declared.

[Script](../../examples/step_21_relations/17_specialization_absent.py) · [Notebook](../../examples/step_21_relations/17_specialization_absent.ipynb)

```python
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

ActionProductMachine(loggers=[])
record = VinylRecordCoreEntity(id="rec-1", title="Kind of Blue", pressing=None)
print("No choice:", record.pressing is None)
print("Declared axes:", len(EntityIntentResolver.resolve_entity_specializations(VinylRecordCoreEntity)))
assert record.pressing is None
```

Output:

```text
No choice: True
Declared axes: 1
```

None means this object has no selected variant. This differs from a container whose variant is known and whose entity is None. The optional annotation does not remove the axis or its coverage checks from the graph.

### Read back from details to the head

Compare two Generalization references to the same record.

[Script](../../examples/step_21_relations/04_specialization_reverse.py) · [Notebook](../../examples/step_21_relations/04_specialization_reverse.ipynb)

```python
record = VinylRecordCoreEntity(
    id="rec-1",
    title="Kind of Blue",
    pressing=Specialization[
        FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity
    ](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
    ),
)
unloaded = Generalization[VinylRecordCoreEntity](id="rec-1")
loaded = Generalization[VinylRecordCoreEntity](id="rec-1", entity=record)
print(unloaded.id, unloaded.entity)
print(loaded.entity.title)
```

Output:

```text
rec-1 None
Kind of Blue
```

Both identify rec-1. Only the reference supplied with entity=record exposes the album title through entity.title. Generalization needs no variant because its target class is already fixed.

### Read a stored variant

Resolve a storage code before constructing the head.

[Script](../../examples/step_21_relations/15_specialization_storage.py) · [Notebook](../../examples/step_21_relations/15_specialization_storage.ipynb)

```python
row = {"id": "rec-1", "title": "Kind of Blue", "edition_key": "first"}
value = VinylRecordKindEnumEntity.by_code(row["edition_key"])
record = VinylRecordCoreEntity(
    id=row["id"],
    title=row["title"],
    pressing=Specialization[
        FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity
    ](id=row["id"], variant=value),
)
print(record.pressing.variant.code)
print("Same value:", record.pressing.variant is VinylRecordKindEnumEntity.FIRST)
print("Details:", record.pressing.entity)
```

Output:

```text
first
Same value: True
Details: None
```

edition_key is the resource's column name, not a field required by AOA. by_code resolves the value; this example deliberately leaves details unloaded. A loader can use axis.code_to_target[value.code] to select a class, then apply its own class-to-storage mapping.

### Read a variant reference

A reference object selects a declared value without loading its details.

[Script](../../examples/step_21_relations/16_specialization_reference.py) · [Notebook](../../examples/step_21_relations/16_specialization_reference.ipynb)

```python
link = Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
    id="rec-1", variant={"code": "first", "display_name": "Stale", "properties": {}}
)
print("Same value:", link.variant is VinylRecordKindEnumEntity.FIRST)
print(link.model_dump()["variant"])
assert link.variant is VinylRecordKindEnumEntity.FIRST
```

Output:

```text
Same value: True
{'code': 'first', 'display_name': 'First', 'properties': {}}
```

The second type argument validates variant exactly as a dictionary-typed ordinary field. It resolves the code and emits the current declaration. The container does not construct or fetch the alternative object.

The next standalone example changes the dictionary declaration order to TEST, FIRST, REPRESS. Its union remains FIRST, REPRESS, TEST.

### The dictionary orders the mapping

Declare TEST before FIRST and REPRESS, keeping the alternative union unchanged.

[Script](../../examples/step_21_relations/05_specialization_mapping.py) · [Notebook](../../examples/step_21_relations/05_specialization_mapping.ipynb)

```python
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

ActionProductMachine(loggers=[])
axis = EntityIntentResolver.resolve_entity_specializations(VinylRecordCoreEntity)[0]
print("Field:", axis.field_name)
print("Dictionary:", axis.dictionary.__name__)
for code in axis.codes:
    print(code, "->", axis.code_to_target[code].__name__)
```

Output:

```text
Field: pressing
Dictionary: VinylRecordKindEnumEntity
test -> TestPressSpecEntity
first -> FirstPressSpecEntity
repress -> RepressSpecEntity
```

The dictionary supplies presentation order. Each alternative's Classifier supplies the correspondence. TestPressSpecEntity still owns test regardless of its position in the union; the resolver performs no loading.

### An unrelated loaded object is refused

Pass the head record where pressing details are required.

[Script](../../examples/step_21_relations/06_specialization_wrong_type.py) · [Notebook](../../examples/step_21_relations/06_specialization_wrong_type.ipynb)

```python
from pydantic import ValidationError

record = VinylRecordCoreEntity(
    id="rec-1",
    title="Kind of Blue",
    pressing=Specialization[
        FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity
    ](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
    ),
)
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
        entity=record,
    )
except ValidationError as error:
    print(type(error).__name__)
    print(sorted({item["type"] for item in error.errors()}))
else:
    raise AssertionError("An unrelated entity was accepted")
```

Output:

```text
ValidationError
['model_type']
```

The first type argument checks which object classes can fill entity. The head is outside that union, so Pydantic reports model_type. This is different from a permitted alternative paired with the wrong value.

### A bare variant code is refused

A string cannot fill the dictionary-typed variant field.

[Script](../../examples/step_21_relations/18_specialization_bare_code.py) · [Notebook](../../examples/step_21_relations/18_specialization_bare_code.ipynb)

```python
from pydantic import ValidationError

try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1", variant="first"
    )
except ValidationError as error:
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("A bare code was accepted")
```

Output:

```text
Value error, VinylRecordKindEnumEntity: a bare code is not accepted; pass the declared value or its reference object {'code', 'display_name', 'properties'}.
```

Even a known code must be resolved explicitly or wrapped in a reference object. This keeps storage representation separate from the declared value used in memory.

### An unknown variant is refused

Pass a reference whose code is unknown after a successful model build.

[Script](../../examples/step_21_relations/07_specialization_data_codes.py) · [Notebook](../../examples/step_21_relations/07_specialization_data_codes.ipynb)

```python
ActionProductMachine(loggers=[])
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant={"code": "unknown"},
    )
except ValidationError as error:
    print("Refused:", error.errors()[0]["msg"])
else:
    raise AssertionError("A case the example exists to refuse was accepted")
```

Output:

```text
Refused: Value error, 'unknown' is not a declared value of VinylRecordKindEnumEntity. Declared: ['first', 'repress', 'test'].
```

The build checks declarations; constructing the container checks the incoming value. An unknown code is not a legitimate unloaded or absent variant.

### The loaded class must match the value

Pair FIRST with an otherwise valid RepressSpecEntity.

[Script](../../examples/step_21_relations/08_specialization_mismatched_data.py) · [Notebook](../../examples/step_21_relations/08_specialization_mismatched_data.ipynb)

```python
repress = RepressSpecEntity(
    id="rec-1",
    year=1997,
    record=Generalization[VinylRecordCoreEntity](id="rec-1"),
)
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
        entity=repress,
    )
except ValidationError as error:
    print("Refused:", error.errors()[0]["msg"])
else:
    raise AssertionError("A case the example exists to refuse was accepted")
```

Output:

```text
Refused: Value error, variant 'first' does not match RepressSpecEntity, which declares 'repress'
```

The entity type belongs to the union, but its declared value is REPRESS. The container rejects the pair. Matching uses the declared value's identity, so equal codes from different dictionaries cannot substitute for one another.

### Equal codes from different dictionaries do not match

Pair a first-pressing object with another dictionary's value named first.

[Script](../../examples/step_21_relations/19_specialization_foreign_pair.py) · [Notebook](../../examples/step_21_relations/19_specialization_foreign_pair.ipynb)

```python
from pydantic import ValidationError

class OtherKindEnumEntity(BaseEnumEntity):
    """Supply a distinct vocabulary with a coincidentally equal code."""

    FIRST = OtherKindEnumEntity(code="first", display_name="Other first")  # noqa: F821

first = FirstPressSpecEntity(id="rec-1", stamper="1A", record=Generalization[VinylRecordCoreEntity](id="rec-1"))
try:
    Specialization[FirstPressSpecEntity, OtherKindEnumEntity](
        id="rec-1", variant=OtherKindEnumEntity.FIRST, entity=first
    )
except ValidationError as error:
    print("Equal codes:", OtherKindEnumEntity.FIRST.code == VinylRecordKindEnumEntity.FIRST.code)
    print("Pair accepted:", False)
    assert "does not match" in error.errors()[0]["msg"]
else:
    raise AssertionError("Equal codes bypassed the pairing check")
```

Output:

```text
Equal codes: True
Pair accepted: False
```

Codes identify values inside their own dictionary. The loaded class declares VinylRecordKindEnumEntity.FIRST; an equal string on OtherKindEnumEntity.FIRST does not make it that object. Normal model build also rejects alternatives declared with foreign values.

### Replace a link instead of editing it

Try to change the selected value on an existing container.

[Script](../../examples/step_21_relations/09_specialization_frozen.py) · [Notebook](../../examples/step_21_relations/09_specialization_frozen.ipynb)

```python
from pydantic import ValidationError

link = Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
    id="rec-1",
    variant=VinylRecordKindEnumEntity.FIRST,
)
try:
    link.variant = "repress"
except ValidationError as error:
    print(error.errors()[0]["type"])
else:
    raise AssertionError("A frozen link was changed")
print(link.variant.code)
```

Output:

```text
frozen_instance
first
```

The container is frozen. Build a new link to represent another selection; the original variant remains first.

For the next example, the head declares `reported_pressing` alongside `pressing`, with the same container type, dictionary and reverse field. The standalone source includes both declarations.

### Reuse a dictionary on two axes

The catalogue and another source can report separate classifications.

[Script](../../examples/step_21_relations/11_specialization_two_axes.py) · [Notebook](../../examples/step_21_relations/11_specialization_two_axes.ipynb)

```python
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

ActionProductMachine(loggers=[])
for axis in EntityIntentResolver.resolve_entity_specializations(VinylRecordCoreEntity):
    print(axis.field_name, "by", axis.dictionary.__name__)
```

Output:

```text
reported_pressing by VinylRecordKindEnumEntity
pressing by VinylRecordKindEnumEntity
```

Each field borrows the same dictionary and must cover it completely. This example deliberately reuses the same alternatives. The current closure check rejects disjoint alternative sets on one head; the dictionary change does not remove that restriction.

### Read the declared alternatives from the graph

Inspect forward edges, one reverse edge and the head's fields.

[Script](../../examples/step_21_relations/10_specialization_graph.py) · [Notebook](../../examples/step_21_relations/10_specialization_graph.ipynb)

```python
machine = ActionProductMachine(loggers=[])
nodes = machine.graph_coordinator.get_all_nodes()
head = next(node for node in nodes if node.label == "VinylRecordCoreEntity")
for edge in head.get_all_edges():
    if edge.edge_name == "entity_specialization":
        print(edge.edge_name, edge.properties["classifier_value"], "->", edge.target_node.label)
first_node = next(node for node in nodes if node.label == "FirstPressSpecEntity")
for edge in first_node.get_all_edges():
    if edge.edge_name == "parent_entity":
        print(edge.edge_name, edge.properties["classifier_value"], "->", edge.target_node.label)
print("Columns:", [edge.target_node.label for edge in head.get_all_edges() if edge.edge_name == "entity_field"])
```

Output:

```text
entity_specialization first -> FirstPressSpecEntity
entity_specialization repress -> RepressSpecEntity
entity_specialization test -> TestPressSpecEntity
parent_entity first -> VinylRecordCoreEntity
Columns: ['id', 'title', 'pressing']
```

Three forward edges describe three allowed alternatives, not three simultaneously loaded objects. The head has id, title and pressing; there is no separate selector field. Every forward edge also names the dictionary.

For the next example, add `NoGraphEdge()` inside the head field's `Annotated` metadata, beside `Inverse`. The standalone source imports this marker and shows the complete annotation.

### Hide forward edges only

Add NoGraphEdge to the head's pressing field.

[Script](../../examples/step_21_relations/12_specialization_hidden_edges.py) · [Notebook](../../examples/step_21_relations/12_specialization_hidden_edges.ipynb)

```python
machine = ActionProductMachine(loggers=[])
nodes = machine.graph_coordinator.get_all_nodes()
head = next(node for node in nodes if node.label == "VinylRecordCoreEntity")
first = next(node for node in nodes if node.label == "FirstPressSpecEntity")
print("Forward edges:", len(head.specializations))
print("Reverse edges:", len(first.generalizations))
print("Field present:", any(edge.target_node.label == "pressing" for edge in head.entity_field_edges))
```

Output:

```text
Forward edges: 0
Reverse edges: 1
Field present: True
```

The field and reverse Generalization remain. Without the forward edges Maxitor cannot form the alternatives group. NoGraphEdge changes graph visibility, not the accepted runtime values.

## Invariants and application responsibilities

Ownership containers describe cardinality and ownership. Specialization instead describes
which specific information accompanies one common object. Its dictionary value and loaded
class must agree, and the declaration must cover the whole dictionary. Containers are
immutable; `.entity` is the explicitly supplied object or `None`.

Keep the head and details identifiers equal when they describe the same object. The
containers do not compare all identifiers, inspect storage, enforce database uniqueness or
load missing data. The resource remains responsible for reading the right row and deciding
how to report invalid storage data. `by_code` has no fallback for an unknown code.

The [reference](../reference/intents-and-invariants.md#entity-specialization-the-build-rules)
lists declaration checks and current limitations. The
[diagnostic guide](../how-to/specialization-declaration-fails.md) gives one independent
broken model per error. [Step 26](step-26-maxitor.md#specialization-the-variants-in-one-frame)
shows how Maxitor turns the model into a diagram.

## Review questions

1. Why is pressing-specific information a specialization rather than an owned part?
2. What do the two arguments of `Specialization[Alternatives, Dictionary]` each declare?
3. Where is the selected value stored, and why is a separate selector unnecessary?
4. How do an absent axis, a known variant with unloaded details and an unknown code differ?
5. Why does reordering the dictionary change presentation order without changing the mapping?
6. Which checks happen at class declaration, model build and container construction?
7. What must the resource still check when it loads the head and its details?

> **Exercise.** Run the mapping example, then change only the dictionary's declaration
> order and predict the output. Next, pass REPRESS with first-pressing details and explain
> why this fails even though FirstPressSpecEntity is in the union.

Next — **[Lifecycle](step-22-lifecycle.md)**: declaring an entity's permitted state transitions.

<table width="100%"><tr>
  <td align="left"><a href="step-20-entity.md">← Step 20 — Entity</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-22-lifecycle.md">Step 22 — Lifecycle →</a></td>
</tr></table>
