# Closed dictionaries: declare a vocabulary and use its values

[← Step 20 — Entity](step-20-entity.md) · [Step 21 — Relations →](step-21-relations.md)

A price contains an amount and a currency. Many prices can use EUR; they should agree on
what EUR means. A **dictionary** gives that shared vocabulary a name and a type. A
**closed dictionary** declares its complete set of values in Python. An input can select
an existing value, but it cannot add a currency by sending a new code.

`BaseEnumEntity` describes this role. Every value has a `code` for identification and a
`display_name` for people. Additional fields describe the value itself: a currency's
symbol belongs here; a dated exchange-rate quotation is a separate business fact. A table
whose entries users create at runtime is also a different model: use a core entity with
an appropriate unique code rather than a closed dictionary.

This chapter first declares a value, then uses it in a field, and finally follows it
through serialization, schemas and a diagram. A **reference** is the small object that
identifies a dictionary value when it crosses a boundary. A **schema** describes the
shape of such an object; it does not perform the catalogue lookup.

Run each linked script from the repository root with `uv run python <path>`. Its notebook
contains the same setup and experiment with saved output. Use a fresh repository kernel
for each notebook: graph construction sees the entity declarations loaded in the process.

## Declare values explicitly

The class describes the fields; value() supplies the fields of one catalogue member.

[Script](../../examples/step_20_dictionaries/00_declaration.py) · [Notebook](../../examples/step_20_dictionaries/00_declaration.ipynb)

```python
from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe one supported currency."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


print("Instance:", isinstance(CurrencyEnumEntity.EUR, CurrencyEnumEntity))
print("Codes:", CurrencyEnumEntity.codes())
print("Shared:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
print("Symbol:", CurrencyEnumEntity.EUR.symbol)
assert CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR
```

Output:

```text
Instance: True
Codes: ['eur']
Shared: True
Symbol: €
```

value() records keyword arguments while the class body runs. After class creation EUR is a validated CurrencyEnumEntity instance. The catalogue lookup returns that same object; it does not create a copy. Registration with @entity is only needed when the dictionary participates in the application graph.

The attribute name `EUR`, code `"eur"` and display name `"Euro"` serve different purposes.
None is inferred from the others. `members` returns a tuple in declaration order;
`codes()` returns codes in that order; `by_code()` returns the declared object or raises
`KeyError`. `entity_type` identifies the owning type.

The declaration factory uses normal Python name lookup. It does not substitute the class
name while the class body runs. When a class assigns its own field named `value`, import
the factory under another name:

### Use a field named value

Import the declaration factory under another name when the class binds value itself.

[Script](../../examples/step_20_dictionaries/17_factory_alias.py) · [Notebook](../../examples/step_20_dictionaries/17_factory_alias.ipynb)

```python
from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.domain import value as declared


class SizeEnumEntity(BaseEnumEntity):
    """Describe a size using a field named value."""

    value: int = Field(description="Size in millimetres")
    SMALL = declared(code="small", display_name="Small", value=10)


print("Size:", SizeEnumEntity.SMALL.value)
print("Codes:", SizeEnumEntity.codes())
assert SizeEnumEntity.SMALL.value == 10
```

Output:

```text
Size: 10
Codes: ['small']
```

The assigned class field named value would hide the imported function for later lines in the same body. The alias declared follows ordinary Python name lookup and leaves the field name available. It is still the same public value() function.

## Put a reference in an entity

The next preparation registers the dictionary and a price tag in one domain. A **domain**
groups related model declarations; `@entity` makes a class part of the application graph.
Neither decorator creates a database table or loads a row. An undecorated dictionary can
be used in an isolated value experiment, but a dictionary used by the domain graph must
be registered.

Use this preparation for the price-tag experiments below. Every linked file contains it
already, so the files run independently. The small standalone examples later in the
chapter define different dictionaries; return to this preparation when an experiment
uses `PriceTagCoreEntity` or the shop graph.

```python
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
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

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


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

The field holds the same object as CurrencyEnumEntity.EUR. Reading its symbol needs no second lookup, query or copy.

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

The code selects the member. An old label or symbol in the input is not applied to the model and is not compared with the declaration. A code-only object, {"code": "eur"}, selects exactly the same member.

### Resolve a storage code explicitly

The database column is called money_unit; the domain field is called currency.

[Script](../../examples/step_20_dictionaries/04_storage_mapping.py) · [Notebook](../../examples/step_20_dictionaries/04_storage_mapping.ipynb)

```python
from aoa.action_machine.domain import build

row = {"tag_key": "tag-1", "price": 9.99, "money_unit": "eur"}
selected = CurrencyEnumEntity.by_code(row["money_unit"])
tag = build(
    row,
    PriceTagCoreEntity,
    lambda fields, data: {
        fields.id: data["tag_key"],
        fields.amount: data["price"],
        fields.currency: selected,
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

Storage names belong to the resource. Resolve the stored code explicitly with by_code(), then map the declared value to the domain field. A bare code string is not accepted in a dictionary-typed field.

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

An optional reference with None means no currency was selected. An unknown code is an error, not another spelling of absence.

## Choose supported descriptive fields

Values are shared, so a dictionary rejects unsupported property annotations when its
class is created. It does not accept a `list` annotation and secretly store a `tuple`.
Choose the representation explicitly. The check includes inherited fields and recurses
through tuples and unions.

| Supported annotations | Examples |
| --- | --- |
| Scalar types | `str`, `int`, `float`, `bool`, `Decimal` |
| Dates and identifiers | `date`, `datetime`, `time`, `UUID` |
| Fixed choices | `Literal["small", "large"]`, an `Enum` subclass (see the schema limitation below) |
| Collections | `tuple[str, ...]`, `tuple[str, int]`, nested tuples of supported types |
| Unions and absence | `str | int`, `date | None` |

`list`, `dict`, `set`, `frozenset`, `Any`, `object`, arbitrary classes and nested Pydantic
models are outside this set. `frozenset` illustrates that this is an explicit supported-type
contract, not a test that accepts every object Python happens to treat as immutable.

### Keep a collection as a tuple

A dictionary can describe several aliases without carrying a mutable list.

[Script](../../examples/step_20_dictionaries/10_tuple_property.py) · [Notebook](../../examples/step_20_dictionaries/10_tuple_property.ipynb)

```python
from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Give a currency a fixed collection of aliases."""

    aliases: tuple[str, ...]
    EUR = value(code="eur", display_name="Euro", aliases=("EUR", "€"))


print("Aliases:", CurrencyEnumEntity.EUR.aliases)
print("Python type:", type(CurrencyEnumEntity.EUR.aliases).__name__)
assert CurrencyEnumEntity.EUR.aliases == ("EUR", "€")
```

Output:

```text
Aliases: ('EUR', '€')
Python type: tuple
```

The annotation and stored value are both tuples. The framework checks supported property annotations when the dictionary class is created; it does not silently change a list-typed field into a tuple-typed field. Choose immutable nested types explicitly.

### Allow an absent description

An optional descriptive field can have no value while the dictionary member still exists.

[Script](../../examples/step_20_dictionaries/18_optional_property.py) · [Notebook](../../examples/step_20_dictionaries/18_optional_property.ipynb)

```python
from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Permit an omitted explanatory note."""

    note: str | None = None
    EUR = value(code="eur", display_name="Euro")


print("Note:", CurrencyEnumEntity.EUR.note)
print("Properties:", CurrencyEnumEntity.EUR.to_reference()["properties"])
assert CurrencyEnumEntity.EUR.note is None
```

Output:

```text
Note: None
Properties: {'note': None}
```

Optional applies to the property, not to the existence of the currency. EUR remains a declared member; its note is None, exported as JSON null. A separate optional dictionary reference would mean no currency was selected.

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

The frozen model rejects assignment to a value attribute. Frozen is not a promise to inspect arbitrary custom objects recursively; the supported-property annotation rule is a separate check.

### Understand the boundary of the protection

The current check examines annotations. Custom validators must preserve those types:
an after-validator can currently return a list for a field annotated as a tuple, and the
declaration hook does not recheck the resulting value. Likewise, accepting an `Enum`
annotation is not a recursive audit of an enum member's internals. Do not use these paths
to attach mutable data to shared values. They are limitations of the current implementation,
not an alternative supported declaration technique.

The dictionary restriction does **not** apply to `BaseStateEntity`. Statuses use the same
`value(...)` syntax but retain their existing property types. Their frozen models prevent
attribute replacement, not mutation inside a list. See the separate
[status-property script](../../examples/step_22_lifecycle/21_status_property_scope.py) and
[notebook](../../examples/step_22_lifecycle/21_status_property_scope.ipynb).

## Export a reference

A dictionary reference has three top-level members: `code`, `display_name` and
`properties`. Extra fields go under `properties`, so a consumer that does not have the
Python class can still display the value. `to_reference()` always chooses JSON mode.
It returns a Python dictionary of JSON-compatible values, not an encoded JSON string.

### A reference carries its description

Serialize a price so a reader without the Python model can understand its currency.

[Script](../../examples/step_20_dictionaries/03_serialization.py) · [Notebook](../../examples/step_20_dictionaries/03_serialization.ipynb)

```python
tag = PriceTagCoreEntity(id="tag-1", amount=9.99, currency=CurrencyEnumEntity.EUR)
print(tag.model_dump(mode="json")["currency"])
# The reference form is the JSON export; a Python-mode dump may keep a native value.
assert tag.model_dump(mode="json")["currency"] == CurrencyEnumEntity.EUR.to_reference()
```

Output:

```text
{'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': '€'}}
```

The containing entity and the dictionary value emit the same reference shape in JSON mode. Python mode can keep native property types, so choose the mode deliberately.

### Export a JSON reference

A native date becomes a string at the reference boundary.

[Script](../../examples/step_20_dictionaries/11_json_reference.py) · [Notebook](../../examples/step_20_dictionaries/11_json_reference.ipynb)

```python
import json
from datetime import date

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Describe a fixed catalogue edition."""

    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))


item = EditionEnumEntity.FIRST
print("Python dump type:", type(item.model_dump()["properties"]["published"]).__name__)
reference = item.to_reference()
print("Reference type:", type(reference["properties"]["published"]).__name__)
print(json.dumps(reference))
assert reference == item.model_dump(mode="json")
```

Output:

```text
Python dump type: date
Reference type: str
{"code": "first", "display_name": "First edition", "properties": {"published": "2020-01-02"}}
```

to_reference() is the JSON-mode export: it can be encoded by json.dumps without a conversion at the caller. Ordinary model_dump() uses Python mode and can keep a date object. Both have the same outer code/display_name/properties structure, but their property values need not have the same Python types.

### Apply a field serializer

The dictionary controls how its date is presented to a consumer.

[Script](../../examples/step_20_dictionaries/12_field_serializer.py) · [Notebook](../../examples/step_20_dictionaries/12_field_serializer.ipynb)

```python
import json
from datetime import date

from pydantic import field_serializer

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Give the edition date an explicit display format."""

    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))

    @field_serializer("published")
    def serialize_published(self, published: date) -> str:
        """Write the day before the month."""
        return published.strftime("%d/%m/%Y")


reference = EditionEnumEntity.FIRST.to_reference()
print(json.dumps(reference))
assert reference["properties"]["published"] == "02/01/2020"
```

Output:

```text
{"code": "first", "display_name": "First edition", "properties": {"published": "02/01/2020"}}
```

The reference wrapper lets Pydantic serialize each field before collecting the extra fields under properties. The field serializer therefore runs, and its result reaches the reference. With the default when_used="always", this serializer also runs in Python mode; use when_used="json" when it should apply only to JSON export.

### Keep exported arrays separate

A consumer edits an exported JSON array without changing the shared catalogue member.

[Script](../../examples/step_20_dictionaries/16_export_isolation.py) · [Notebook](../../examples/step_20_dictionaries/16_export_isolation.ipynb)

```python
from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Keep immutable aliases on the shared currency."""

    aliases: tuple[str, ...]
    EUR = value(code="eur", display_name="Euro", aliases=("EUR", "€"))


reference = CurrencyEnumEntity.EUR.to_reference()
reference["properties"]["aliases"].append("edited")
print("Payload:", reference["properties"]["aliases"])
print("Declared:", CurrencyEnumEntity.EUR.aliases)
print("Fresh export:", CurrencyEnumEntity.EUR.to_reference()["properties"]["aliases"])
assert CurrencyEnumEntity.EUR.aliases == ("EUR", "€")
```

Output:

```text
Payload: ['EUR', '€', 'edited']
Declared: ('EUR', '€')
Fresh export: ['EUR', '€']
```

JSON arrays are ordinary mutable Python lists in the exported payload. The source field is an immutable tuple, and the export creates a separate list. Editing the payload therefore does not edit the shared value or its next export.

Standard JSON-mode conversion represents dates and times as strings, UUID as a string,
Decimal as a string and tuples as arrays. A field serializer can replace that representation.
Its result must itself support JSON serialization; an arbitrary unserializable result is
still an error. Export creates payload containers; the annotation restriction does not mean
that the payload contains no lists or dictionaries.

## Describe input and output separately

A caller may know only a code, while a response includes its current description. These
are different contracts. Pydantic exposes them with `mode="validation"` and
`mode="serialization"`; the word *mode* here selects which contract to describe, not
whether to execute model validation.

### Describe accepted reference input

An input schema allows the code alone because the model already knows its description.

[Script](../../examples/step_20_dictionaries/13_input_schema.py) · [Notebook](../../examples/step_20_dictionaries/13_input_schema.ipynb)

```python
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe the supported currency."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


class Price(BaseModel):
    """Hold a dictionary reference."""

    currency: CurrencyEnumEntity


schema = Price.model_json_schema(mode="validation")
payload = {"currency": {"code": "eur"}}
Draft202012Validator(schema).validate(payload)
price = Price.model_validate(payload)
print("Required input:", schema["properties"]["currency"]["required"])
print("Resolved:", price.currency is CurrencyEnumEntity.EUR)
assert price.currency is CurrencyEnumEntity.EUR
```

Output:

```text
Required input: ['code']
Resolved: True
```

The validation schema requires code, not a repeated label and description. The model resolves that code to its catalogue member. The schema checks the reference shape; runtime validation still checks catalogue membership, so an unknown nonempty code is not accepted just because it fits the JSON shape.

### Describe the emitted reference

The output schema names the property that a consumer will receive.

[Script](../../examples/step_20_dictionaries/14_output_schema.py) · [Notebook](../../examples/step_20_dictionaries/14_output_schema.ipynb)

```python
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from aoa.action_machine.domain import BaseEnumEntity, value


class CurrencyEnumEntity(BaseEnumEntity):
    """Describe the supported currency."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")


class Price(BaseModel):
    """Hold a dictionary reference."""

    currency: CurrencyEnumEntity


schema = Price.model_json_schema(mode="serialization")
reference_schema = schema["properties"]["currency"]
price = Price(currency=CurrencyEnumEntity.EUR)
Draft202012Validator(schema).validate(price.model_dump(mode="json"))
properties = reference_schema["properties"]["properties"]
print("Required output:", reference_schema["required"])
print("Property definitions:", properties["properties"])
print("Extra keys:", properties["additionalProperties"])
assert properties["properties"]["symbol"] == {"type": "string"}
```

Output:

```text
Required output: ['code', 'display_name', 'properties']
Property definitions: {'symbol': {'type': 'string'}}
Extra keys: False
```

The output has code, display_name and properties. The nested properties schema describes symbol as a string and rejects undeclared keys. In the current implementation the nested keys themselves are not listed as required: this schema is not a guarantee that every property key is present in an arbitrary document.

### Describe the serialized property type

A serializer that returns text makes its output property a string.

[Script](../../examples/step_20_dictionaries/15_serializer_schema.py) · [Notebook](../../examples/step_20_dictionaries/15_serializer_schema.ipynb)

```python
from datetime import date

from pydantic import field_serializer

from aoa.action_machine.domain import BaseEnumEntity, value


class EditionEnumEntity(BaseEnumEntity):
    """Format an edition date as text."""

    published: date
    FIRST = value(code="first", display_name="First edition", published=date(2020, 1, 2))

    @field_serializer("published")
    def serialize_published(self, published: date) -> str:
        """Return a day-first date string."""
        return published.strftime("%d/%m/%Y")


schema = EditionEnumEntity.model_json_schema(mode="serialization")
property_schema = schema["properties"]["properties"]["properties"]["published"]
print("Emitted type:", property_schema)
assert property_schema == {"type": "string"}
```

Output:

```text
Emitted type: {'type': 'string'}
```

The schema follows the serializer return type, not the original Python date annotation. This output is ordinary text, so the schema does not incorrectly label the day-first text as an ISO date. Annotate a custom serializer return type so schema generation can describe the result.

The input schema checks structure: an object with a nonempty string code and no unknown
top-level keys. It does not enumerate catalogue codes, and its `minLength` does not reject
whitespace-only strings. Runtime validation performs both checks. Its optional description
fields are described as a string and an object; runtime lookup ignores their contents.
Schema validation and model validation therefore have different responsibilities.

One output-schema limitation remains: an extra field annotated with an `Enum` subclass
can serialize successfully, but generating its serialization schema currently raises
`KeyError` for the enum's `#/$defs/...` reference. The schema generator does not preserve
that definition. Do not treat an accepted property annotation as proof that every schema
combination is supported. The scalar, tuple and custom-serializer examples above are
executed against the current implementation.

## Reuse fields without inheriting dictionary values

### A subclass declares its own catalogue

A child dictionary reuses fields while declaring a different set of currencies.

[Script](../../examples/step_20_dictionaries/06_inheritance.py) · [Notebook](../../examples/step_20_dictionaries/06_inheritance.ipynb)

```python
class LocalCurrencyEnumEntity(CurrencyEnumEntity):
    """Reuse the currency fields with a separate vocabulary."""

    GBP = value(code="gbp", display_name="Pound", symbol="£")


print("Parent:", CurrencyEnumEntity.codes())
print("Child:", LocalCurrencyEnumEntity.codes())
assert LocalCurrencyEnumEntity.codes() == ["gbp"]
```

Output:

```text
Parent: ['eur', 'usd']
Child: ['gbp']
```

The child reuses the field definitions but owns a new catalogue. Python may still expose inherited class attributes; catalogue membership is determined by members/by_code(), not by whether getattr can find a parent attribute.

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

An undecorated intermediate can share field definitions without declaring values. Registration with @entity requires a nonempty catalogue. This differs from a state subclass with no new statuses, which can reuse its parent catalogue.

## Follow values into the graph and Maxitor

The **application graph** describes registered classes and their relationships. A
closed dictionary is one Entity node with a `values` list. Its members are rows in that
list, not separate graph nodes. A reference field identifies the target dictionary with
`reference_qualname`.

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

The graph carries the catalogue and the reference target. It describes the model; it does not fetch a price or create lookup tables.

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

Maxitor reads the graph and turns each properties object into a list of name/value text rows. The typed list fits the strict response schema. The renderer escapes these strings and places them inside the dictionary card; it knows no currency-specific field names.

See [the Maxitor chapter](step-26-maxitor.md#dictionaries-values-inside-the-entity-card)
for the payload boundary and the rendered diagram. A specialization uses a dictionary
as its choice vocabulary, while its alternative classes hold the actual business details.
The [relations chapter](step-21-relations.md#generalization-and-specialization) builds
that distinction from a complete model.

## Read a refusal as a specific contract violation

Each file below demonstrates one refusal. The scripts catch the expected exception and
fail if the invalid input is accepted. These are separate experiments, not successive
steps in one long scenario.

### Invalid references

| Input | Why it fails | Script / notebook |
| --- | --- | --- |
| A bare string | The field expects an object reference or a declared instance. | [Script](../../examples/step_20_dictionaries/20_bare_code.py) · [Notebook](../../examples/step_20_dictionaries/20_bare_code.ipynb) |
| An unknown code | The code names no member. | [Script](../../examples/step_20_dictionaries/21_unknown_code.py) · [Notebook](../../examples/step_20_dictionaries/21_unknown_code.ipynb) |
| A separately constructed instance | Matching fields do not establish declared identity. | [Script](../../examples/step_20_dictionaries/22_copy.py) · [Notebook](../../examples/step_20_dictionaries/22_copy.ipynb) |
| No code | The description cannot identify a member. | [Script](../../examples/step_20_dictionaries/23_missing_code.py) · [Notebook](../../examples/step_20_dictionaries/23_missing_code.ipynb) |
| A whitespace-only code | There is no usable identity. | [Script](../../examples/step_20_dictionaries/24_blank_reference.py) · [Notebook](../../examples/step_20_dictionaries/24_blank_reference.ipynb) |
| A constructor-shaped mapping | Extra fields belong under properties, and only declared codes resolve. | [Script](../../examples/step_20_dictionaries/25_flat_fields.py) · [Notebook](../../examples/step_20_dictionaries/25_flat_fields.ipynb) |

For example, constructing a copy is still possible outside a class body, but the copy cannot be used as a dictionary member:

### A constructed copy is refused

Construct a new object with the same fields as EUR, then try to use it as a reference.

[Script](../../examples/step_20_dictionaries/22_copy.py) · [Notebook](../../examples/step_20_dictionaries/22_copy.ipynb)

```python
try:
    PriceTagCoreEntity(id="tag-1", amount=1.0, currency=CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€"))
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

The constructor validates fields; it does not insert an object into the catalogue. Use CurrencyEnumEntity.EUR or resolve a reference by code instead.

### Invalid declarations

| Declaration | Result | Script / notebook |
| --- | --- | --- |
| Two values with one code | ValueError at class creation | [Script](../../examples/step_20_dictionaries/26_duplicate_code.py) · [Notebook](../../examples/step_20_dictionaries/26_duplicate_code.ipynb) |
| Blank declared code | ValidationError | [Script](../../examples/step_20_dictionaries/27_blank_code.py) · [Notebook](../../examples/step_20_dictionaries/27_blank_code.ipynb) |
| Blank display name | ValidationError | [Script](../../examples/step_20_dictionaries/28_blank_label.py) · [Notebook](../../examples/step_20_dictionaries/28_blank_label.ipynb) |
| The removed class-name alias | NameError when the class name has no existing binding | [Script](../../examples/step_20_dictionaries/38_old_declaration.py) · [Notebook](../../examples/step_20_dictionaries/38_old_declaration.ipynb) |
| `list[str]` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/30_mutable_list.py) · [Notebook](../../examples/step_20_dictionaries/30_mutable_list.ipynb) |
| `dict[str, int]` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/31_mutable_dict.py) · [Notebook](../../examples/step_20_dictionaries/31_mutable_dict.ipynb) |
| `set[str]` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/32_mutable_set.py) · [Notebook](../../examples/step_20_dictionaries/32_mutable_set.ipynb) |
| `frozenset[str]` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/33_frozenset.py) · [Notebook](../../examples/step_20_dictionaries/33_frozenset.ipynb) |
| `tuple[list[str], ...]` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/34_nested_mutable.py) · [Notebook](../../examples/step_20_dictionaries/34_nested_mutable.ipynb) |
| `Any` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/35_any_property.py) · [Notebook](../../examples/step_20_dictionaries/35_any_property.ipynb) |
| `Detail` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/36_nested_model.py) · [Notebook](../../examples/step_20_dictionaries/36_nested_model.ipynb) |
| `list[str] \| None` | ValueError naming the field and refused type | [Script](../../examples/step_20_dictionaries/37_optional_mutable.py) · [Notebook](../../examples/step_20_dictionaries/37_optional_mutable.ipynb) |

### Refuse list[str]

The property annotation is checked when the dictionary class is created.

[Script](../../examples/step_20_dictionaries/30_mutable_list.py) · [Notebook](../../examples/step_20_dictionaries/30_mutable_list.ipynb)

```python
from aoa.action_machine.domain import BaseEnumEntity, value

try:

    class InvalidEnumEntity(BaseEnumEntity):
        """Attempt to declare an unsupported property type."""

        detail: list[str]
        ITEM = value(code="item", display_name="Item")
except ValueError as error:
    print(str(error))
    assert "field 'detail' is list" in str(error)
else:
    raise AssertionError("The unsupported property was accepted")
```

Output:

```text
InvalidEnumEntity: field 'detail' is list, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

Use tuple[str, ...] for a fixed sequence of labels. The error names the class, field and unsupported type. This check runs before the value arguments are validated, so it does not depend on supplying an example of the forbidden value.

## Migrate an existing declaration

Import `value` from `aoa.action_machine.domain` and replace the constructor-looking call
inside each dictionary or status class:

```python
# Previous declaration inside CurrencyEnumEntity:
EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")

# Current declaration inside that same class:
EUR = value(code="eur", display_name="Euro", symbol="€")
```

Keep the attribute name, stored code and descriptive values. Existing member lookups,
lifecycle transitions and specialization annotations keep their meaning. This syntax
change does not mean replacing normal constructor calls throughout the application.

If a dictionary declares an unsupported property type, choose a supported representation
as well; mutable property declarations are no longer accepted. Consumers requiring native
Python values should use the ordinary Python-mode dump; consumers of a reference should
expect JSON-compatible property values. Request the appropriate input or output schema.

## Check your understanding

1. Why is EUR one shared object even when a thousand prices refer to it?
2. What is the difference between value(...), a constructor call, and by_code(...)?
3. Why does a tuple property become an editable array in a reference without making the source mutable?
4. Why can a code fit the input schema and still fail runtime validation?
5. Which rules are shared by dictionaries and statuses, and which differ?
