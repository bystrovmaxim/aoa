# Quickstart: proving the declaration, the reference form and the card

**Feature**: `specs/016-value-declaration-consistency` | **Plan**: [plan.md](./plan.md) | **Contracts**: [declared-value](./contracts/declared-value.md), [dictionary-card](./contracts/dictionary-card.md)

Every scenario is runnable from the repository root with the repository's own environment. Outputs below are the expected ones: they are executed when the phase that produces them lands, and the documentation phase re-runs each script before the page quotes it. Each scenario states the test that keeps it true, so a scenario that stops printing what is shown here is a failing test, not a stale page.

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

class LabelsEnumEntity(BaseEnumEntity):
    """Declare a value with nested data."""

    labels: list[str] = Field(description="Labels")
    ITEM = value(code="item", display_name="Item", labels=["original"])

class StatusStateEntity(BaseStateEntity):
    """Carry data that need not be hashable, as the lifecycle suite does."""

    labels: list[str] = Field(default_factory=list, description="Labels")
    A = value(code="a", display_name="A")
```

```
ValueError: LabelsEnumEntity: field 'labels' is list, which a declared value cannot carry;
supported: str, int, float, bool, Decimal, date, datetime, time, UUID, Enum, Literal, tuple[…]
```

The status class is accepted; only the dictionary is refused. Kept true by `test_dictionary_property_types.py`.

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
print(DatedEnumEntity.ITEM.model_dump()["since"])
```

```
{"code": "item", "display_name": "Item", "properties": {"since": "02/01/2020"}}
02/01/2020
```

Without the serializer the reference carries `"2020-01-02"`; the Python-mode dump would carry a `date` object, and the page says so. Kept true by `test_dictionary_core_schema.py`.

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

print(json.dumps(Invoice.model_json_schema(mode="serialization")["$defs"]["CurrencyEnumEntity"], indent=1))
```

```
{
 "additionalProperties": false,
 "properties": {
  "code": {"minLength": 1, "type": "string"},
  "display_name": {"minLength": 1, "type": "string"},
  "properties": {
   "additionalProperties": false,
   "properties": {"symbol": {"type": "string"}},
   "type": "object"
  }
 },
 "required": ["code", "display_name", "properties"],
 "type": "object"
}
```

Kept true by `test_dictionary_json_schema.py`.

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
from aoa.action_machine.domain import BaseEnumEntity, value
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

class DatedEnumEntity(BaseEnumEntity):
    """Declare a dated reference value."""

    since: date
    ITEM = value(code="item", display_name="Item", since=date(2020, 1, 2))

document = json.dumps(EntityGraphNode(DatedEnumEntity).properties["values"])
print(document)
```

```
[{"code": "item", "display_name": "Item", "properties": {"since": "2020-01-02"}}]
```

The assertion is that `json.dumps` does not raise and the leaf is a string. Kept true by `test_dictionary_reference_json.py`.

## Scenario 8 — the card shows the properties, escaped and rendered

```bash
cd packages/aoa-maxitor/client && node --experimental-strip-types scripts/check-erd-dictionary-values.ts
```

```
Dictionary card: properties preserved, escaped and rendered
```

Extend the same script with a value carrying no properties, and with a property whose value is an array, before the phase closes.

## Scenario 9 — the group label names the dictionary once

```bash
cd packages/aoa-maxitor/client && node --experimental-strip-types scripts/check-erd-group-label.ts
```

```
Group label: kind (by EditionKindEnumEntity)
```

The script feeds the payload `test_list_entities_specialization_contract.py` produces into `buildDotSource`, so a layer that composes the name twice fails here.

## Scenario 10 — the corpus is on one form

```bash
uv run python specs/016-value-declaration-consistency/evidence/scan_value_declarations.py
```

```
area                           class-name value(...) suppressed  classes  files  sup files
total                                   0        373          0      187    116          0
```

The same script run on the baseline printed `373` class-name declarations and `332` suppressed lines; the two runs are the evidence for SC-001 and SC-002.
