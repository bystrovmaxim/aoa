# Closed dictionaries: declare values, then refer to them

[← Step 20 — Entity](step-20-entity.md) · [Step 21 — Relations →](step-21-relations.md)

A price needs an amount and a currency. Many prices can use EUR, and they should all
mean the same currency. A **dictionary** is the named set of values available for such
references. **Closed** means that the model declares the complete set in code: an input
cannot add a new currency merely by sending an unfamiliar code.

`BaseEnumEntity` is the base for this kind of entity. The dictionary class defines its
values; each declared attribute is a shared object with a stable `code`, a human-readable
`display_name` and any additional descriptive fields. A currency symbol describes a
currency. A dated exchange-rate quote is a separate business fact and should be modelled
as a business object. A dictionary maintained by users in a database is also outside this
closed-dictionary mechanism; use a core entity with an appropriate unique code for that case.

## Declare the vocabulary

Start with [the catalogue script](../../examples/step_20_entity/07_enumeration.py) or
[its notebook](../../examples/step_20_entity/07_enumeration.ipynb). `BaseEnumEntity`
supplies the required, nonblank `code` and `display_name`; the currency class adds `symbol`.
Inside the class body, `CurrencyEnumEntity(...)` records a value declaration. Once Python
has finished creating the class, `CurrencyEnumEntity.EUR` is a real instance of that class.

```python
from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Currencies accepted by the shop", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shop's currency vocabulary."""

    symbol: str = Field(description="Currency symbol")

    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")  # noqa: F821
    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")  # noqa: F821


print("Codes:", CurrencyEnumEntity.codes())
print("Members:", len(CurrencyEnumEntity.members))
print("Same object:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
print("Value:", CurrencyEnumEntity.EUR.display_name, CurrencyEnumEntity.EUR.symbol)
```

Output:

```text
Codes: ['eur', 'usd']
Members: 2
Same object: True
Value: Euro €
```

`members` is a tuple in declaration order. `codes()` returns the codes in that same
order, and `by_code("eur")` returns the declared EUR object itself. An unknown code raises
`KeyError`. `entity_type is CurrencyEnumEntity` is true: the class is both the type of a
value and the owner of its catalogue. The attribute name `EUR`, the stored code `eur` and
the display name `Euro` have different jobs; none is inferred from either of the others.

## Use the dictionary as a field type

The following complete preparation adds a price tag. Use it before any of the short
experiments below. Every linked script and notebook already includes its own preparation,
so it can be run independently. Run scripts from the repository root with
`uv run python <script-path>`; notebooks use the repository's Python environment.

```python
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Currencies accepted by the shop", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shop's currency vocabulary."""

    symbol: str = Field(description="Currency symbol")

    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")  # noqa: F821
    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")  # noqa: F821


@entity(description="Price tag", domain=ShopDomain)
class PriceTagCoreEntity(BaseCoreEntity):
    """Associate an amount with its currency."""

    id: str = Field(description="Tag identifier")
    amount: float = Field(description="Price amount")
    currency: CurrencyEnumEntity = Field(description="Money unit")
```

### A field holds the declared object

A price uses a currency value that other prices can share.

[Script](../../examples/step_20_dictionaries/01_reference_field.py) · [Notebook](../../examples/step_20_dictionaries/01_reference_field.ipynb)

```python
tag = PriceTagCoreEntity(id="tag-1", amount=9.99, currency=CurrencyEnumEntity.EUR)
print("Shared value:", tag.currency is CurrencyEnumEntity.EUR)
print("Symbol:", tag.currency.symbol)
assert tag.currency is CurrencyEnumEntity.EUR
```

Output:

```text
Shared value: True
Symbol: €
```

The annotation names the dictionary class. The field keeps the exact EUR object declared on that class, so its symbol is available without a query or a second copy of the currency.

### A reference resolves by code

A consumer sends a currency reference with an outdated label and symbol.

[Script](../../examples/step_20_dictionaries/02_reference_payload.py) · [Notebook](../../examples/step_20_dictionaries/02_reference_payload.ipynb)

```python
tag = PriceTagCoreEntity.model_validate(
    {
        "id": "tag-1",
        "amount": 9.99,
        "currency": {"code": "eur", "display_name": "Old label", "properties": {"symbol": "?"}},
    }
)
print("Shared value:", tag.currency is CurrencyEnumEntity.EUR)
print(tag.currency.display_name, tag.currency.symbol)
assert tag.currency is CurrencyEnumEntity.EUR
```

Output:

```text
Shared value: True
Euro €
```

The code selects EUR. The payload label and properties do not update, override or get compared with the declaration. The value in memory has the current declared label and symbol.

### A reference carries its description

Serialize a price so a reader without the Python model can understand its currency.

[Script](../../examples/step_20_dictionaries/03_serialization.py) · [Notebook](../../examples/step_20_dictionaries/03_serialization.ipynb)

```python
tag = PriceTagCoreEntity(id="tag-1", amount=9.99, currency=CurrencyEnumEntity.EUR)
print(tag.model_dump()["currency"])
assert tag.model_dump()["currency"] == CurrencyEnumEntity.EUR.to_reference()
```

Output:

```text
{'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': '€'}}
```

The reference contains code, display_name and properties. Additional declared fields, such as symbol, are collected under properties. Serializing the value itself produces the same shape.

### Resolve a storage code explicitly

The database column is called money_unit; the domain field is called currency.

[Script](../../examples/step_20_dictionaries/04_storage_mapping.py) · [Notebook](../../examples/step_20_dictionaries/04_storage_mapping.ipynb)

```python
from aoa.action_machine.domain import build

row = {"tag_key": "tag-1", "price": 9.99, "money_unit": "eur"}
value = CurrencyEnumEntity.by_code(row["money_unit"])
tag = build(
    row,
    PriceTagCoreEntity,
    lambda fields, data: {
        fields.id: data["tag_key"],
        fields.amount: data["price"],
        fields.currency: value,
    },
)
print(tag.id, tag.currency.code)
print("Shared value:", tag.currency is CurrencyEnumEntity.EUR)
```

Output:

```text
tag-1 eur
Shared value: True
```

The resource owns the mapping from storage columns to model fields. by_code raises KeyError for an unknown code; it never invents a default currency. Writing back uses tag.currency.code. No database connection is needed for this mapping experiment.

### An absent reference is None

A quote may have no settlement currency yet.

[Script](../../examples/step_20_dictionaries/05_optional.py) · [Notebook](../../examples/step_20_dictionaries/05_optional.ipynb)

```python
class QuoteCoreEntity(BaseCoreEntity):
    """Allow an explicitly absent settlement currency."""

    currency: CurrencyEnumEntity | None = Field(default=None, description="Settlement unit")

quote = QuoteCoreEntity()
print("Absent:", quote.currency is None)
assert quote.currency is None
```

Output:

```text
Absent: True
```

None is accepted because this field explicitly permits it. An unknown code is still an error; it does not become None. A default of None also permits omission of this field.

### A subclass declares its own catalogue

A child dictionary reuses fields while declaring a different set of currencies.

[Script](../../examples/step_20_dictionaries/06_inheritance.py) · [Notebook](../../examples/step_20_dictionaries/06_inheritance.ipynb)

```python
class LocalCurrencyEnumEntity(CurrencyEnumEntity):
    """Reuse the currency fields with a separate vocabulary."""

    GBP = LocalCurrencyEnumEntity(code="gbp", display_name="Pound", symbol="£")  # noqa: F821

print("Parent:", CurrencyEnumEntity.codes())
print("Child:", LocalCurrencyEnumEntity.codes())
assert LocalCurrencyEnumEntity.codes() == ["gbp"]
```

Output:

```text
Parent: ['eur', 'usd']
Child: ['gbp']
```

Fields can be inherited, but catalogue membership cannot. LocalCurrencyEnumEntity.by_code("eur") raises KeyError. Python may still expose an inherited EUR class attribute; it is not a member of the child dictionary and cannot fill a field typed by the child.

### A declared value cannot be edited

Many objects may share EUR, so changing its label through one reference must fail.

[Script](../../examples/step_20_dictionaries/07_frozen.py) · [Notebook](../../examples/step_20_dictionaries/07_frozen.ipynb)

```python
try:
    CurrencyEnumEntity.EUR.display_name = "Changed"
except ValidationError as error:
    print(error.errors()[0]["type"])
else:
    raise AssertionError("The shared value was modified")
print(CurrencyEnumEntity.EUR.display_name)
```

Output:

```text
frozen_instance
Euro
```

The frozen_instance error means assignment was refused. Change the declaration in code when changing the vocabulary. This is not a business lifecycle transition.

### The dictionary carries values in the graph

Inspect the dictionary and a field that refers to it.

[Script](../../examples/step_20_dictionaries/08_graph.py) · [Notebook](../../examples/step_20_dictionaries/08_graph.ipynb)

```python
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

dictionary = EntityGraphNode(CurrencyEnumEntity)
tag = EntityGraphNode(PriceTagCoreEntity)
field = next(edge.target_node for edge in tag.entity_field_edges if edge.target_node.label == "currency")
print("Kind:", dictionary.properties["entity_kind"])
print("Values:", [value["code"] for value in dictionary.properties["values"]])
print("Reference:", field.properties["reference_qualname"].split(".")[-1])
```

Output:

```text
Kind: enum
Values: ['eur', 'usd']
Reference: CurrencyEnumEntity
```

The Entity node represents the dictionary class and carries an ordered values array. EUR and USD are not separate Entity nodes. reference_qualname identifies the dictionary from the referencing field; it is model metadata, not a stored price.

### Read dictionary values in the ERD payload

Follow one dictionary through the actual Maxitor query.

[Script](../../examples/step_20_dictionaries/09_erd.py) · [Notebook](../../examples/step_20_dictionaries/09_erd.ipynb)

```python
import json

from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

machine = ActionProductMachine(loggers=[])
domain = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "ShopDomain")
store = DuckDBGraphResource.build_from_json(json.loads(machine.graph_coordinator.to_json()))
diagram = ListEntitiesAction._slice_payload(store, domain, include_neighbors=False)
currency = next(item for item in diagram["entities"] if item["label"] == "CurrencyEnumEntity")
tag = next(item for item in diagram["entities"] if item["label"] == "PriceTagCoreEntity")
print(currency["values"][0])
print(next(field["reference_qualname"] for field in tag["fields"] if field["name"] == "currency").split(".")[-1])
```

Output:

```text
{'code': 'eur', 'display_name': 'Euro', 'properties': [{'name': 'symbol', 'value': '€'}]}
CurrencyEnumEntity
```

The diagram query preserves values and their descriptive fields. Its presentation payload expresses properties as name/value rows of text, which the card renders below the label. The full graph retains the original properties object. _slice_payload is an internal inspection API, used here to reproduce the viewer without an HTTP service.

## Recognize invalid inputs and declarations

Each of the following cases attempts one invalid operation. A caught error is the
expected result; each program raises an assertion if the invalid operation unexpectedly
succeeds. The notebook shows the same operation and its actual diagnostic.

### A bare code is refused

Pass a string directly into the typed currency field.

[Script](../../examples/step_20_dictionaries/20_bare_code.py) · [Notebook](../../examples/step_20_dictionaries/20_bare_code.ipynb)

```python
try:
    PriceTagCoreEntity(id="tag-1", amount=1.0, currency="eur")
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, CurrencyEnumEntity: a bare code is not accepted; pass the declared value or its reference object {'code', 'display_name', 'properties'}.
```

A string is a storage code. Resolve it with CurrencyEnumEntity.by_code before constructing the model, or pass a reference object.

### An unknown reference code is refused

The producer sends a code outside the declared vocabulary.

[Script](../../examples/step_20_dictionaries/21_unknown_code.py) · [Notebook](../../examples/step_20_dictionaries/21_unknown_code.ipynb)

```python
try:
    PriceTagCoreEntity(id="tag-1", amount=1.0, currency={"code": "unknown"})
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, 'unknown' is not a declared value of CurrencyEnumEntity. Declared: ['eur', 'usd'].
```

The error names the code and declared set. Treat this as a data/model mismatch; do not silently replace it with None or a default.

### A constructed copy is refused

Construct a new object with the same fields as EUR, then try to use it as a reference.

[Script](../../examples/step_20_dictionaries/22_copy.py) · [Notebook](../../examples/step_20_dictionaries/22_copy.ipynb)

```python
try:
    PriceTagCoreEntity(
        id="tag-1", amount=1.0, currency=CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")
    )
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, CurrencyEnumEntity: a copy of a declared value is not a value; use the declared attribute (for example CurrencyEnumEntity.<value>).
```

Constructing an object does not register a new dictionary member. Only the declared EUR instance is a value of this dictionary; equality of fields does not establish membership.

### A reference without a code is malformed

A label alone cannot identify the value.

[Script](../../examples/step_20_dictionaries/23_missing_code.py) · [Notebook](../../examples/step_20_dictionaries/23_missing_code.ipynb)

```python
try:
    PriceTagCoreEntity(id="tag-1", amount=1.0, currency={"display_name": "Euro"})
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, CurrencyEnumEntity: a reference object needs a non-empty 'code'.
```

The code is required for lookup. A malformed object is not an absent value.

### A blank reference code is malformed

Whitespace cannot identify a value.

[Script](../../examples/step_20_dictionaries/24_blank_reference.py) · [Notebook](../../examples/step_20_dictionaries/24_blank_reference.ipynb)

```python
try:
    PriceTagCoreEntity(id="tag-1", amount=1.0, currency={"code": " "})
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, CurrencyEnumEntity: a reference object needs a non-empty 'code'.
```

Codes must contain non-whitespace characters. Lookup is exact; it does not trim, change case or guess.

### Flat model data cannot create a value

Put an undeclared code and a symbol at the top level of a mapping.

[Script](../../examples/step_20_dictionaries/25_flat_fields.py) · [Notebook](../../examples/step_20_dictionaries/25_flat_fields.ipynb)

```python
try:
    PriceTagCoreEntity(
        id="tag-1", amount=1.0, currency={"code": "bootleg", "display_name": "Unknown", "symbol": "?"}
    )
except ValidationError as error:
    print("Field:", error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("The invalid reference was accepted")
```

Output:

```text
Field: currency
Value error, CurrencyEnumEntity: a reference object may only contain 'code', 'display_name' and 'properties'; put descriptive fields under 'properties'.
```

The field accepts a reference, not raw constructor data. Put descriptive fields under properties; even then the code must name a declared value. This closes a route that previously bypassed catalogue membership.

### Duplicate codes are refused

Two names in one dictionary try to claim the same code.

[Script](../../examples/step_20_dictionaries/26_duplicate_code.py) · [Notebook](../../examples/step_20_dictionaries/26_duplicate_code.ipynb)

```python
try:

    class DuplicateEnumEntity(BaseEnumEntity):
        """Intentionally give two values one identity."""

        FIRST = DuplicateEnumEntity(code="same", display_name="First")  # noqa: F821
        SECOND = DuplicateEnumEntity(code="same", display_name="Second")  # noqa: F821
except ValueError as error:
    print(str(error))
else:
    raise AssertionError("Duplicate codes were accepted")
```

Output:

```text
DuplicateEnumEntity: duplicate value code(s) in ['same'].
```

Uniqueness is checked while Python creates the class, before @entity could register it. Give each value a distinct code.

### A declared code cannot be blank

Declare a value with a whitespace-only code.

[Script](../../examples/step_20_dictionaries/27_blank_code.py) · [Notebook](../../examples/step_20_dictionaries/27_blank_code.ipynb)

```python
try:

    class BlankEnumEntity(BaseEnumEntity):
        """Intentionally omit meaningful identity or label text."""

        VALUE = BlankEnumEntity(code=" ", display_name="Label")  # noqa: F821
except ValidationError as error:
    print(error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("A blank field was accepted")
```

Output:

```text
code
Value error, An enum entity's 'code' and 'display_name' cannot be empty or whitespace-only.
```

The declaration factory constructs and validates each value when the class is created. code and display_name are supplied by BaseEnumEntity and both are required and nonblank.

### A declared display_name cannot be blank

Declare a value with a whitespace-only display_name.

[Script](../../examples/step_20_dictionaries/28_blank_label.py) · [Notebook](../../examples/step_20_dictionaries/28_blank_label.ipynb)

```python
try:

    class BlankEnumEntity(BaseEnumEntity):
        """Intentionally omit meaningful identity or label text."""

        VALUE = BlankEnumEntity(code="valid", display_name=" ")  # noqa: F821
except ValidationError as error:
    print(error.errors()[0]["loc"][0])
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("A blank field was accepted")
```

Output:

```text
display_name
Value error, An enum entity's 'code' and 'display_name' cannot be empty or whitespace-only.
```

The declaration factory constructs and validates each value when the class is created. code and display_name are supplied by BaseEnumEntity and both are required and nonblank.

### A decorated dictionary cannot be empty

An intermediate class can define shared fields; a concrete dictionary must supply values.

[Script](../../examples/step_20_dictionaries/29_empty_dictionary.py) · [Notebook](../../examples/step_20_dictionaries/29_empty_dictionary.ipynb)

```python
class MoneyBaseEnumEntity(BaseEnumEntity):
    """Define shared fields without declaring a concrete dictionary."""

    symbol: str = Field(description="Currency symbol")

print("Intermediate members:", MoneyBaseEnumEntity.members)
try:

    @entity(description="Missing vocabulary", domain=ShopDomain)
    class EmptyEnumEntity(MoneyBaseEnumEntity):
        """Intentionally declare no values."""
except ValueError as error:
    print(str(error))
else:
    raise AssertionError("An empty dictionary was registered")
```

Output:

```text
Intermediate members: ()
EmptyEnumEntity declares no values; a closed dictionary states its values.
```

The empty intermediate is allowed. @entity is the boundary at which a concrete dictionary must have at least one value. Inheriting a concrete dictionary without declaring new values is empty by the same rule.

## What the reference contract guarantees

A field stores a declared object, not an arbitrary object with a matching code. A reference
mapping is resolved by code; its label and properties are informational. The emitted
reference and published JSON Schema contain all three keys: `code`, `display_name`,
`properties`. Python validation also accepts a short reference such as `{"code": "eur"}`;
use the complete emitted shape when exchanging data against the published schema.

The state kind uses the same declaration syntax and catalogue operations, but has a
different meaning. A state describes a position in a process governed by a lifecycle.
A dictionary describes a reference value. A state subclass with no new statuses may reuse
its parent's catalogue; a dictionary subclass always has its own catalogue. See
[Step 22](step-22-lifecycle.md) for states and transitions.

A specialization can use a dictionary to name its alternative classes. That adds a
relationship between common and variant-specific data; it does not turn the dictionary
values into those data objects. [Step 21](step-21-relations.md#generalization-and-specialization)
builds that model from the beginning.
