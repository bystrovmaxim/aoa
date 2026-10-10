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
    BaseEntity,
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
class CustomerEntity(BaseEntity):
    id: str = Field(description="Customer id")
    name: str = Field(description="Display name")

    orders: Annotated[
        AssociationMany[OrderEntity],
        Inverse(OrderEntity, "customer"),
    ] = Rel(description="Orders placed by this customer")


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")

    # association — order and customer exist independently
    customer: Annotated[
        AssociationOne[CustomerEntity],
        Inverse(CustomerEntity, "orders"),
    ] = Rel(description="Customer who placed the order")

    # composition — line items cannot exist without this order
    lines: Annotated[
        CompositeMany[OrderLineEntity],
        Inverse(OrderLineEntity, "order"),
    ] = Rel(description="Line items of the order")


@entity(description="Single line of an order", domain=ShopDomain)
class OrderLineEntity(BaseEntity):
    id: str = Field(description="Line id")
    sku: str = Field(description="Product code")

    order: Annotated[
        AssociationOne[OrderEntity],
        Inverse(OrderEntity, "lines"),
    ] = Rel(description="Parent order")


CustomerEntity.model_rebuild()
OrderEntity.model_rebuild()
OrderLineEntity.model_rebuild()
```



`One`/`Many` set the cardinality, `composition`/`aggregation`/`association` set the meaning of ownership. These relations land in the graph and the ERD of [Maxitor](../index.md#vii-maxitor).

## Inverse: the reverse side and the startup check

`Inverse(Target, "field")` explicitly names the **paired field** on the other side. This is needed because the heuristic "find the reverse relation by type" breaks the moment an entity has two fields of the same type — whereas a single line `Inverse(OrderEntity, "lines")` is unambiguous and survives refactoring. Every declared relation must carry `Rel(description=...)` — the model stays a specification, not just code.

When the graph is built (and it is built when the machine is created), the coordinator **checks the mirroring**: that the paired field exists, that the types and target entities match, and that the cardinality is compatible. An error in the relation model surfaces **at startup**, not half a year later in a report. In the example this is visible in the first line: the machine assembled — which means the relations were validated.

For an honestly one-way link, put `NoInverse()` (the absence of a reverse side is intentional, not forgotten); `NoGraphEdge()` removes the edge from the interchange graph while keeping the field in the node metadata.

## Partial loading of relations

Loading the related object into a container is also called **hydration**. It does not happen automatically. The [partial-loading](step-20-entity.md#one-entity-different-load-levels) rule extends to relations too: the container **always knows the id**, but the related entity may not be loaded. Reaching through an un-hydrated container is a `RelationNotLoadedError`, not a silent `None` and not a hidden query:

```python
order = OrderEntity(
    id="ord-1", total=1500.0,
    customer=AssociationOne[CustomerEntity](id="cust-1"),          # id only
    lines=CompositeMany[OrderLineEntity](ids=("line-1", "line-2")),# ids only
)

order.customer.id      # ok — the id is always there
order.customer.name    # RelationNotLoadedError — the customer row is not loaded
len(order.lines)       # 2 — the number of ids is known
list(order.lines)      # RelationNotLoadedError — the line entities are not hydrated
```

To make a relation loaded, pass the entity itself (`One`) or the entities (`Many`) into the container; then attribute access is proxied to it:

```python
customer = CustomerEntity(
    id="cust-1", name="Alice",
    orders=AssociationMany[OrderEntity](ids=("ord-1",)),
)
order2 = OrderEntity(
    id="ord-2", total=99.0,
    customer=AssociationOne[CustomerEntity](id="cust-1", entity=customer),  # hydrated
    lines=CompositeMany[OrderLineEntity](entities=(), entities_loaded=True),
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

Different queries return one `OrderEntity` with different relation-load depth — and the system controls accidental access to the not-loaded, instead of quietly slipping in a `None` or going to the database behind your back.

## Generalization and specialization

### Start with the information we need to represent

Suppose we are building a catalogue of vinyl records. Every record has an identifier and an album title. We also want to describe how a particular copy was pressed. For a first pressing we record the stamper code; for a later re-pressing we record its year; for a test pressing we record who approved it. A stamper is the tool used to press the record, and its code identifies that tool.

These are different sets of information. Putting all three sets of fields on every record would make the reader of our model work out which fields belong together and which are relevant to a particular copy. Three independent association fields would describe three separate links, while our intention is one choice among kinds of pressing details.

We will therefore use one class for the common record information and a separate class for each kind of pressing details. In this relationship, the common class is called the **head**, and the possible detail classes are its **alternatives**. An alternative is also called a variant or an extension. Here the head is `VinylRecordEntity`; its alternatives are `FirstPressEntity`, `RepressEntity`, and `TestPressEntity`.

The head's `pressing` field can refer to any one of these alternatives. AOA calls this direction **specialization**, represented by `Specialization[FirstPressEntity | RepressEntity | TestPressEntity]`. The vertical bars are Python's union notation: the related object may have any of the listed types. Each detail class also declares a way back to the common record. That direction is **generalization**, represented by `Generalization[VinylRecordEntity]`.

This declaration does not make the detail classes Python subclasses of `VinylRecordEntity`. Each class inherits directly from `BaseEntity`. Nor does it create database tables. An application may store common data and detail data in separate tables, or assemble them from another source; the declarations describe the domain objects and their relationship.

We also need a way to name a kind of pressing in data. We choose the strings `first`, `repress`, and `test`. These strings are **codes**; they are application vocabulary, not Python class names. The record's `media` field holds such a code. A field used to distinguish the alternatives is called a **classifier field**. The `Classifier` marker names that field and the codes declared by the model. It describes a correspondence for application code to use; it does not perform a query or construct the chosen object.

### Declare the complete model

The following preparation is shared by the experiments in this section. Put it at the start of a Python file, then append the first experiment below. Later experiments replace that final block; they do not run on top of the previous experiment's data. Each linked script already contains its own complete copy of the necessary declarations, and each notebook starts with a fresh copy. Use one notebook per kernel session so that intentionally invalid declarations from another experiment do not enter the model being checked.

The imports supply Python's annotation tools, Pydantic's field descriptions, and AOA's declaration types. `MusicDomain` groups the catalogue in the model graph; it does not connect to a database. `@entity` registers each class as part of that declared model.


```python
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="Pressing identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="Pressing identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="Pressing identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordEntity, FirstPressEntity, RepressEntity, TestPressEntity):
    model.model_rebuild()
```

Read the declaration of `VinylRecordEntity.pressing` in three parts. `Specialization[...]` lists the allowed types of the related object. `Classifier(field="media", codes=Literal["first", "repress", "test"])` says where the code lives and which codes this declaration names. `Literal` describes specific values in Python's typing vocabulary. Finally, `Inverse(field_name="record")` says that the paired field on every alternative is called `record`. There is no single target class to give this head-side marker: the union already supplies the alternatives.

Now read `FirstPressEntity.record` in the other direction. `Generalization[VinylRecordEntity]` identifies the common class. Its `Classifier("record", Literal["first"])` declares the alternative's own code, `first`. On this reverse side, `record` names the reverse link; it is not a second ordinary data field containing a code. `Inverse(VinylRecordEntity, "pressing")` identifies the paired field on the head. The other two alternatives follow the same pattern with their own codes and detail fields.

`Rel(description=...)` supplies the description of each relationship. It does not supply a loaded relation value. We pass actual containers when constructing the objects below. Because the head and alternatives refer to one another, some names appear before their classes exist. `from __future__ import annotations` postpones their evaluation, and the final `model_rebuild()` calls resolve them after all four classes have been defined. This prepares Pydantic's types; it is different from building AOA's model graph.

The codes appear on both sides so that AOA can compare the head's list with the alternatives' declarations. Every named code must have an owner, and every alternative must contribute exactly one distinct code. The correspondence comes from the reverse declarations, not from matching positions in two lists. A later experiment changes the order to make that distinction visible.

### A record with first-pressing details

How do common record information and variant-specific information fit together?

First we create the machine. Creating `ActionProductMachine` assembles a graph of the loaded declarations and checks their consistency; this is the **model build**. `loggers=[]` keeps this small experiment's output focused on its own prints. A successful build says the declarations passed their checks. It says nothing about rows in a database.

Next we construct `first`, the details for one pressing. Its reverse link carries the identifier `rec-1` but no loaded record object. We then construct `record`, whose forward link carries `press-1`, the code `first`, and the already-created `first` object. The two identifiers differ deliberately: they identify different objects, and this feature does not require equal identifiers on the two sides.

[Script](../../examples/step_21_relations/02_specialization.py) · [Notebook](../../examples/step_21_relations/02_specialization.ipynb)


```python
ActionProductMachine(loggers=[])
first = FirstPressEntity(
    id="press-1",
    stamper="1A",
    record=Generalization[VinylRecordEntity](id="rec-1"),
)
record = VinylRecordEntity(
    id="rec-1",
    title="Kind of Blue",
    media="first",
    pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
        id="press-1",
        variant="first",
        entity=first,
    ),
)
print("Model built")
print(record.title)
print(record.pressing.variant)
print(record.pressing.entity.stamper)
print(first.record.id)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/02_specialization.py
```

Output:

```text
Model built
Kind of Blue
first
1A
rec-1
```

The title belongs to the common record. The stamper belongs to its first-pressing details. We supplied both links explicitly; neither link loaded or created the other object.

The five printed lines follow those steps. `Model built` follows successful machine creation. `Kind of Blue` comes from the head's `title`; `first` comes from the link's explicitly supplied `variant`; `1A` comes from the supplied detail object's `stamper`. Finally, `rec-1` is available on the reverse link even though that link has no loaded record object. The framework has not inferred any of these data values from the declarations.

### Use the same preparation for the next experiments

For the next examples, keep the complete declarations above and replace the code that follows them with the indicated block. Additional imports in a block belong with that block. The scripts remain independent, so you can also run them directly without copying anything. When an experiment changes a declaration, that change is shown before its code.

### A reference without the object

What can we read before pressing details have been loaded?

Sometimes an application has read the identifier and the pressing code but has not read the pressing details. It can still construct a reference. This experiment isolates that state: no entity object is passed to the container.

[Script](../../examples/step_21_relations/03_specialization_unloaded.py) · [Notebook](../../examples/step_21_relations/03_specialization_unloaded.ipynb)


```python
link = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
    id="press-1",
    variant="first",
)
print(link.id)
print(link.variant)
print(link.entity)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/03_specialization_unloaded.py
```

Output:

```text
press-1
first
None
```

The identifier and code survive without the object. Here entity is None. No database call occurs, and this container does not proxy stamper access.

Unlike the ownership containers described earlier, `Specialization` exposes the loaded object through `.entity`; it does not forward arbitrary attributes to it. Test `link.entity is not None` before reading its fields. Here `None` means that this container has no loaded object. It does not prove that the related data is absent from storage. Loading that data and constructing a new container is the resource or application code's responsibility.

### Reading the common information from the details

How does a loaded reverse link differ from an identifier-only reverse link?

The reverse direction can also be read at two load levels. Here we construct a record whose own pressing link is identifier-only, then make two reverse links to that same record. Only one receives the record object.

[Script](../../examples/step_21_relations/04_specialization_reverse.py) · [Notebook](../../examples/step_21_relations/04_specialization_reverse.ipynb)


```python
record = VinylRecordEntity(
    id="rec-1",
    title="Kind of Blue",
    media="first",
    pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
        id="press-1",
        variant="first",
    ),
)
unloaded = Generalization[VinylRecordEntity](id="rec-1")
loaded = Generalization[VinylRecordEntity](id="rec-1", entity=record)
print(unloaded.id, unloaded.entity)
print(loaded.entity.title)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/04_specialization_reverse.py
```

Output:

```text
rec-1 None
Kind of Blue
```

Both links identify the same record. Only the second has a record object because we passed entity=record. Generalization carries no variant field: its target type is already known.

### Reading the declared code-to-class mapping

Does a code identify a class by its position in the union?

To inspect the declared correspondence, AOA provides `EntityIntentResolver.resolve_entity_specializations`. Each returned description represents one specialization field together with its classifier and alternatives. This combination is called a **specialization axis**. The term is useful when a head has more than one such field; in our first model there is only the `pressing` axis.

For this experiment, replace just the `Classifier` line on `VinylRecordEntity.pressing` with:


```python
Classifier(field="media", codes=Literal["test", "first", "repress"]),
```

Keep the union and all reverse declarations unchanged. `[0]` below selects the sole axis description. `code_to_target` is its dictionary from code strings to Python classes; `__name__` prints each class's readable name.

[Script](../../examples/step_21_relations/05_specialization_mapping.py) · [Notebook](../../examples/step_21_relations/05_specialization_mapping.ipynb)


```python
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

ActionProductMachine(loggers=[])
axis = EntityIntentResolver.resolve_entity_specializations(VinylRecordEntity)[0]
print("Field:", axis.field_name)
print("Classifier:", axis.classifier_field)
for code in axis.codes:
    print(code, "->", axis.code_to_target[code].__name__)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/05_specialization_mapping.py
```

Output:

```text
Field: pressing
Classifier: media
test -> TestPressEntity
first -> FirstPressEntity
repress -> RepressEntity
```

The head lists codes in a different order from the union. Each code still points to the class that declares it on its reverse field. The resolver reads declarations; it does not load data.

Notice that `test` still maps to `TestPressEntity`, although that class is third in the unchanged union. If application code reads a data code, it can look it up in this mapping and decide what to load. The resolver itself only reads class declarations. Restore the original code order before using the unmodified preparation in the following examples.

### Rejecting an unrelated object

Does the container accept a record where pressing details are required?

The type argument has an immediate effect on value construction. Here we deliberately pass a common record object where one of the pressing detail objects is required. The `try` block contains the one construction expected to fail. We print the exception name and its structured error type, leaving out Pydantic's repeated union-branch descriptions.

[Script](../../examples/step_21_relations/06_specialization_wrong_type.py) · [Notebook](../../examples/step_21_relations/06_specialization_wrong_type.ipynb)


```python
from pydantic import ValidationError

record = VinylRecordEntity(
    id="rec-1",
    title="Kind of Blue",
    media="first",
    pressing=Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
        id="press-1",
        variant="first",
    ),
)
try:
    Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
        id="press-1",
        variant="first",
        entity=record,
    )
except ValidationError as error:
    print(type(error).__name__)
    print(sorted({item["type"] for item in error.errors()}))
else:
    raise AssertionError("An unrelated entity was accepted")
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/06_specialization_wrong_type.py
```

Output:

```text
ValidationError
['model_type']
```

Pydantic checks the entity value against the union when constructing the container. A VinylRecordEntity is not one of the three pressing classes. This check needs no machine build.

### A declaration does not validate a data code

Does a successfully built model reject an unknown code in a link?

Checking an object's type is different from checking whether its data code is declared. Our `media` annotation is `str`, and the container's `variant` accepts a string. This experiment uses an unknown string on both sides after a successful model build.

[Script](../../examples/step_21_relations/07_specialization_data_codes.py) · [Notebook](../../examples/step_21_relations/07_specialization_data_codes.ipynb)


```python
ActionProductMachine(loggers=[])
link = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
    id="press-1",
    variant="unknown",
)
record = VinylRecordEntity(id="rec-1", title="Kind of Blue", media="unknown", pressing=link)
print("Model built")
print(record.media)
print(record.pressing.variant)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/07_specialization_data_codes.py
```

Output:

```text
Model built
unknown
unknown
```

Both fields are strings, so the unknown code is accepted. Classifier metadata validates the declared mapping, not the values in an instance. The loading layer must decide how to reject or handle unknown data codes.

If your application requires a closed set of values for `media`, an appropriate field annotation such as `Literal["first", "repress", "test"]` can restrict normal Pydantic construction of that field. That still does not check agreement with the link's `variant`, verify a database row, or add automatic loading. Keep the declaration checks and the application's data checks separate.

### A link does not choose its object

Does variant="first" require the supplied object to be a FirstPressEntity?

There is a second, separate data question: does the supplied object agree with the supplied code? This experiment keeps a valid object type but deliberately labels a re-pressing as `first`.

[Script](../../examples/step_21_relations/08_specialization_mismatched_data.py) · [Notebook](../../examples/step_21_relations/08_specialization_mismatched_data.ipynb)


```python
repress = RepressEntity(
    id="press-2",
    year=1997,
    record=Generalization[VinylRecordEntity](id="rec-1"),
)
link = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
    id="press-2",
    variant="first",
    entity=repress,
)
print(link.variant)
print(type(link.entity).__name__)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/08_specialization_mismatched_data.py
```

Output:

```text
first
RepressEntity
```

RepressEntity is inside the union, so the object passes type validation even though its code should be repress. The container does not compare variant to the object type. A loader must enforce that agreement.

The result is accepted, so application code must not assume that checking the union also checks this correspondence. The same responsibility covers agreement between the record's `media`, the link's `variant`, the linked object's identifier, and the reverse link. The declarations describe the intended relationship; these containers do not establish all of those instance-level agreements.

### Replacing a link instead of changing it

Can an existing link have its variant changed?

After a container has been constructed, its fields cannot be assigned new values. This property is called immutability. The experiment attempts one assignment and then reads the original value to distinguish a refused change from a successful one.

[Script](../../examples/step_21_relations/09_specialization_frozen.py) · [Notebook](../../examples/step_21_relations/09_specialization_frozen.ipynb)


```python
from pydantic import ValidationError

link = Specialization[FirstPressEntity | RepressEntity | TestPressEntity](
    id="press-1",
    variant="first",
)
try:
    link.variant = "repress"
except ValidationError as error:
    print(error.errors()[0]["type"])
else:
    raise AssertionError("A frozen link was changed")
print(link.variant)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/09_specialization_frozen.py
```

Output:

```text
frozen_instance
first
```

The frozen_instance error means assignment was refused. The original code remains first. Construct a new link when representing a different relation; Generalization is frozen in the same way.

### More than one choice on a head

A catalogue might retain its own pressing classification and another catalogue's reported classification. This gives us two specialization fields on the same record. Each needs a separate code field. In this experiment both choices use exactly the same three detail classes and their existing `record` reverse field.

Replace only the `VinylRecordEntity` class from the preparation with this complete version. The other classes and the final rebuild loop remain unchanged:


```python
@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    reported_media: str = Field(description="Pressing code reported by another catalogue")
    reported_pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="reported_media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Pressing reported by another catalogue")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")
```

### Two classifications on the same record

Can a record carry the catalogue classification and a separately reported classification?

[Script](../../examples/step_21_relations/11_specialization_two_axes.py) · [Notebook](../../examples/step_21_relations/11_specialization_two_axes.ipynb)


```python
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

ActionProductMachine(loggers=[])
for axis in EntityIntentResolver.resolve_entity_specializations(VinylRecordEntity):
    print(axis.field_name, "by", axis.classifier_field)
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/11_specialization_two_axes.py
```

Output:

```text
reported_pressing by reported_media
pressing by media
```

Each field has its own classifier, so the model builds. Both axes deliberately use the same alternatives and reverse field. This is a narrow supported example: the current validator rejects disjoint sets of alternatives on the same head. It also does not check that the two instance values agree.

Do not generalize this result to arbitrary independent variant sets. The current validator compares every alternative's reverse link to every axis on that head. A class accepted by one axis but omitted from another is refused. The [different-set diagnostic](../how-to/specialization-declaration-fails.md#a-second-axis-has-a-different-alternative-set) demonstrates this restriction with a real model. This is why the example uses the same alternatives, rather than promising that a pressing choice and an unrelated condition choice can be declared independently on this head.

### From declarations to the diagram

The model graph is a description of classes and their declared relationships. A **node** represents an item such as an entity class or field; an **edge** connects two nodes. The graph contains the possible alternatives even when no record instances have been created. The next experiment returns to the original one-axis preparation and reads those edges.

### The two directions in the model graph

What does the built graph say about the declared alternatives?

[Script](../../examples/step_21_relations/10_specialization_graph.py) · [Notebook](../../examples/step_21_relations/10_specialization_graph.ipynb)


```python
machine = ActionProductMachine(loggers=[])
nodes = machine.graph_coordinator.get_all_nodes()
head = next(node for node in nodes if node.label == "VinylRecordEntity")
for edge in head.get_all_edges():
    if edge.edge_name == "entity_specialization":
        print(edge.edge_name, edge.properties["classifier_value"], "->", edge.target_node.label)
first_node = next(node for node in nodes if node.label == "FirstPressEntity")
for edge in first_node.get_all_edges():
    if edge.edge_name == "parent_entity":
        print(edge.edge_name, edge.properties["classifier_value"], "->", edge.target_node.label)
print("Columns:", [edge.target_node.label for edge in head.get_all_edges() if edge.edge_name == "entity_field"])
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/10_specialization_graph.py
```

Output:

```text
entity_specialization first -> FirstPressEntity
entity_specialization repress -> RepressEntity
entity_specialization test -> TestPressEntity
parent_entity first -> VinylRecordEntity
Columns: ['id', 'title', 'media', 'pressing']
```

Each forward edge names one allowed class and its code. The reverse edge records the same declared relationship from the alternative. The pressing field also remains a column. These are class declarations, not links between stored record instances.

The class graph has three forward edges because the declaration permits three alternatives. A particular `Specialization` value still carries only one object reference. The reverse `parent_entity` edge records the relationship from a detail class back to the common class; it does not mean Python inheritance. The [Maxitor chapter](step-26-maxitor.md#specialization-the-variants-in-one-frame) explains how the entity–relationship diagram, or **ERD**, turns this declaration into field rows and a frame around alternatives.

### Hiding the forward edges

Sometimes the relationship should stay in the data model but its forward edges should be omitted from the exported graph. Starting from the original preparation, add `NoGraphEdge` to the imports from `aoa.action_machine.domain`, and replace the complete `pressing` field declaration with:


```python
pressing: Annotated[
    Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
    Classifier(field="media", codes=Literal["first", "repress", "test"]),
    Inverse(field_name="record"),
    NoGraphEdge(),
] = Rel(description="Details of this pressing")
```

### Hiding forward edges

Does hiding a specialization edge remove the field or its reverse edge?

[Script](../../examples/step_21_relations/12_specialization_hidden_edges.py) · [Notebook](../../examples/step_21_relations/12_specialization_hidden_edges.ipynb)


```python
machine = ActionProductMachine(loggers=[])
nodes = machine.graph_coordinator.get_all_nodes()
head = next(node for node in nodes if node.label == "VinylRecordEntity")
first = next(node for node in nodes if node.label == "FirstPressEntity")
print("Forward edges:", len(head.specializations))
print("Reverse edges:", len(first.generalizations))
print("Field present:", any(edge.target_node.label == "pressing" for edge in head.entity_field_edges))
```

Run from the repository root:

```bash
uv run python examples/step_21_relations/12_specialization_hidden_edges.py
```

Output:

```text
Forward edges: 0
Reverse edges: 1
Field present: True
```

NoGraphEdge on pressing suppresses the forward specialization edges. It preserves the field and does not suppress the alternative-side parent_entity edge. Without forward edges Maxitor cannot construct the alternatives group.

## Invariants

For the ownership containers, `One`/`Many` describes the number of targets and `Composite`/`Aggregate`/`Association` describes ownership. They require an explicit inverse declaration or an intentional `NoInverse`, and their access rules distinguish identifiers from loaded objects.

Specialization describes a different aspect of the model: which kinds of detail object may accompany common information. The head and alternatives declare matching codes; each alternative belongs to one head; each axis on a head has its own classifier; specialization relationships must not form cycles. Their containers expose the object explicitly through `.entity`, which may be `None`, and do not load it or validate all agreements between instance values.

The [reference](../reference/intents-and-invariants.md#entity-specialization-the-build-rules) lists the checks and their timing. For an invalid declaration, use [Diagnosing a specialization declaration](../how-to/specialization-declaration-fails.md), whose experiments start with this same working model and isolate one mistake at a time.

## Review questions

1. How do cardinality and ownership differ in `CompositeMany` and `AssociationOne`?
2. Why must an inverse relation name a particular field rather than only a class?
3. Which information is available in an identifier-only ownership container? What happens when you try to read the object?
4. Why does the record example need separate detail classes? Which class is the head?
5. What does `Classifier` declare on the head, and what does it declare on an alternative?
6. Why does changing the head code order leave the code-to-class correspondence intact?
7. How do `model_rebuild()`, the machine's model build, and constructing a relation value differ?
8. What does `.entity is None` tell you, and what does it leave unknown?
9. Which mistake in the examples produces `ValidationError`, and which inconsistent data is accepted?
10. Why do three edges in the model graph not imply three loaded objects in a particular record?

> **Exercise (ownership).** In `01_relations.py`, change `Inverse(CustomerEntity, "orders")` to a field name that does not exist and observe the build failure. Restore it, then pass two loaded `OrderLineEntity` objects to the order's `lines` container and iterate over them.

> **Exercise (specialization).** In `05_specialization_mapping.py`, change only the order of the codes again. Predict the printed mapping and verify it. Then change the `first` code on one side only and use the diagnostics guide to explain the mismatch.

Next — **[Lifecycle](step-22-lifecycle.md)**: declaring an entity's permitted state transitions.

<table width="100%"><tr>
  <td align="left"><a href="step-20-entity.md">← Step 20 — Entity</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-22-lifecycle.md">Step 22 — Lifecycle →</a></td>
</tr></table>
