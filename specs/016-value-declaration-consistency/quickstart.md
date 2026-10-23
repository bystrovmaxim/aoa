# Quickstart: proving the declaration, the reference form and the card

**Feature**: `specs/016-value-declaration-consistency` | **Plan**: [plan.md](./plan.md) | **Contracts**: [declared-value](./contracts/declared-value.md), [dictionary-card](./contracts/dictionary-card.md)

Every scenario below was run on the tree that carries phases 1–7, and the output quoted is what it printed — not an expectation. Each scenario names the test that keeps it true, so a scenario that stops printing what is shown here is a failing test, not a stale page.

## Prerequisites

```bash
git switch feature/issue-244-simplify-value-declarations
uv sync
```

Scratch modules live under `/tmp` and run with `uv run python /tmp/<name>.py`.

## Scenario 1 — declare a dictionary value and a status with `value(...)`

```python
from aoa.action_machine.domain import BaseEnumEntity, BaseStateEntity, value

class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the supported currencies."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")

class OrderStateEntity(BaseStateEntity):
    """Declare statuses and their properties."""

    requires_receipt: bool
    NEW = value(code="new", display_name="New", requires_receipt=False)
    PAID = value(code="paid", display_name="Payment received", requires_receipt=True)

print(type(CurrencyEnumEntity.EUR).__name__, CurrencyEnumEntity.EUR.symbol)
print(CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
print(OrderStateEntity.codes(), OrderStateEntity.PAID.requires_receipt)
```

```
CurrencyEnumEntity €
True
['new', 'paid'] True
```

Kept true by `test_declared_values.py`, `test_dictionary_scope.py`, `test_state_entity.py`.

## Scenario 2 — the replaced form fails at its own line

```python
from aoa.action_machine.domain import BaseEnumEntity

class OldFormEnumEntity(BaseEnumEntity):
    """Use the removed form."""

    EUR = OldFormEnumEntity(code="eur", display_name="Euro")
```

```
NameError: name 'OldFormEnumEntity' is not defined
```

Kept true by `test_declared_values.py::test_a_class_body_naming_its_own_class_fails`.

## Scenario 3 — a mutable property is refused; a status keeps its freedom

```python
from pydantic import Field
from aoa.action_machine.domain import BaseEnumEntity, BaseStateEntity, value

try:
    class LabelsEnumEntity(BaseEnumEntity):
        """Declare a value with nested data."""

        labels: list[str] = Field(description="Labels")
        ITEM = value(code="item", display_name="Item", labels=["original"])
except ValueError as error:
    print(error)

class StatusStateEntity(BaseStateEntity):
    """Carry data that need not be hashable, as the lifecycle suite does."""

    labels: list[str] = Field(default_factory=list, description="Labels")
    A = value(code="a", display_name="A")

print("status accepted:", StatusStateEntity.A.labels)
```

```
LabelsEnumEntity: field 'labels' is list, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
status accepted: []
```

The refusal binds the dictionary kind; the status class is accepted with the same `list[str]`. Kept true by `test_dictionary_property_types.py`.

## Scenario 4 — a serializer and a standard type reach the wire

```python
import json
from datetime import date
from pydantic import Field, field_serializer
from aoa.action_machine.domain import BaseEnumEntity, value

class DatedEnumEntity(BaseEnumEntity):
    """Declare a dated reference value."""

    since: date = Field(description="Start date")
    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        return moment.strftime("%d/%m/%Y")

print(json.dumps(DatedEnumEntity.ITEM.to_reference()))
print(DatedEnumEntity.ITEM.model_dump()["properties"]["since"])
```

```
{"code": "item", "display_name": "Item", "properties": {"since": "02/01/2020"}}
02/01/2020
```

Without the serializer the reference carries `"2020-01-02"`. `model_dump()` in Python mode keeps the serializer's text here, because a field serializer's default is `when_used="always"`; with no serializer it keeps a `date` object, while `to_reference()` emits the JSON string either way — the reference is defined as the JSON export. Kept true by `test_dictionary_core_schema.py`.

## Scenario 5 — the output schema describes the emitted property

```python
import json
from pydantic import BaseModel
from aoa.action_machine.domain import BaseEnumEntity, value

class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the accepted currency."""

    symbol: str
    EUR = value(code="eur", display_name="Euro", symbol="€")

class Invoice(BaseModel):
    """Reference a declared currency."""

    currency: CurrencyEnumEntity

print(json.dumps(Invoice.model_json_schema(mode="serialization")["properties"]["currency"], indent=1))
```

```
{
 "additionalProperties": false,
 "properties": {
  "code": {
   "minLength": 1,
   "type": "string"
  },
  "display_name": {
   "minLength": 1,
   "type": "string"
  },
  "properties": {
   "type": "object",
   "additionalProperties": false,
   "properties": {
    "symbol": {
     "type": "string"
    }
   }
  }
 },
 "required": [
  "code",
  "display_name",
  "properties"
 ],
 "type": "object"
}
```

The schema is inlined at the field, not registered under `$defs`, and `properties` names `symbol` with its emitted type. Kept true by `test_dictionary_json_schema.py`.

## Scenario 6 — the input schema accepts a code-only reference

```python
from jsonschema import Draft202012Validator
from pydantic import BaseModel
from aoa.action_machine.domain import BaseEnumEntity, value

class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the accepted currency."""

    EUR = value(code="eur", display_name="Euro")

class Invoice(BaseModel):
    """Reference a declared currency."""

    currency: CurrencyEnumEntity

schema = Invoice.model_json_schema(mode="validation")
for payload in ({"currency": {"code": "eur"}}, {"currency": {"code": ""}}):
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
    print(payload, "->", errors or "valid")
print(Invoice.model_validate({"currency": {"code": "eur"}}).currency is CurrencyEnumEntity.EUR)
```

```
{'currency': {'code': 'eur'}} -> valid
{'currency': {'code': ''}} -> ["'' should be non-empty"]
True
```

Kept true by `test_dictionary_json_schema.py`.

## Scenario 7 — the graph document carries the serializer's text

```python
import json
from datetime import date
from pydantic import Field
from aoa.action_machine.domain import BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity

class DatedDomain(BaseDomain):
    """Domain for the graph case."""

    name = "dated"
    description = "Dated"

@entity(description="Dated reference value", domain=DatedDomain)
class DatedEnumEntity(BaseEnumEntity):
    """Declare a dated reference value."""

    since: date = Field(description="Start date")
    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

document = json.dumps(EntityGraphNode(DatedEnumEntity).properties["values"])
print(document)
```

```
[{"code": "item", "display_name": "Item", "properties": {"since": "2020-01-02"}}]
```

The class is decorated because the node resolves its `@entity` metadata; the assertion is that `json.dumps` does not raise and the leaf is a string. Kept true by `test_dictionary_reference_json.py`.

## Scenario 8 — the card shows the properties, escaped and rendered

```bash
cd packages/aoa-maxitor/client && node scripts/check-erd-dictionary-values.ts
```

```
Dictionary card: properties preserved, escaped and rendered
```

The check covers a value with two properties, one containing `<`, `>`, `&`, a value with an array property and a value with no properties — asserting the DOT escaping, the JSON text of the array, the absence of a row for the empty value, and the same text inside the rendered SVG. Kept true by `test_list_entities_payload_dictionary.py` and the script itself.

## Scenario 9 — the group label names the dictionary once

```bash
cd packages/aoa-maxitor/client && node scripts/check-erd-group-label.ts
```

```
Group label: composed once, rendered as received
```

The script feeds a group payload shaped like the server's through `buildDotSource`, including a stale payload that still carries `dictionary_label`, and counts the dictionary name: a layer that composes it twice fails here. Kept true by `test_list_entities_specialization_contract.py` and the script itself.

## Scenario 10 — the corpus is on one form

```bash
uv run python specs/016-value-declaration-consistency/evidence/scan_value_declarations.py
```

```
area                           class-name value(...) suppressed  classes  files  sup files
packages/aoa-action-machine             0         82          2       67     22          2
packages/aoa-maxitor                    0          0          0        0      0          0
packages/aoa-demo                       0        103          0       34     25          0
examples                                0        194          0       91     71          0
total                                   0        379          2      192    118          2
```

The same script on the baseline printed `373` class-name declarations in `116` files and `332` suppressed lines in `117` files. The tree grew to `379` declarations in `118` files because the phases added test fixtures; the two remaining suppressions are deliberate — an undefined name under test in `test_state_entity.py` and an undefined annotation in `test_aspect_signature_types.py`.
