# Quickstart: proving a closed dictionary and the axis that borrows it

**Feature**: `specs/015-closed-dictionary-variants` | **Plan**: [plan.md](./plan.md) | **Contracts**: [dictionary-declaration](./contracts/dictionary-declaration.md), [specialization-codes](./contracts/specialization-codes.md)

Every scenario below is runnable from the repository root with the repository's own environment. Expected output is quoted, not paraphrased.

## Prerequisites

```bash
git switch feature/issue-241-closed-dictionary-variants
uv sync
```

The scenarios use a scratch module; write it under `/tmp` and run it with the workspace packages on the path:

```bash
uv run python /tmp/dictionary_demo.py
```

## Scenario 1 — a dictionary declares its values

```python
from pydantic import Field
from aoa.action_machine.domain import BaseEnumEntity, BaseDomain
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop model"

@entity(description="Currency reference value", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    symbol: str = Field(description="Currency symbol")
    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")
    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")

print(CurrencyEnumEntity.codes())
print(CurrencyEnumEntity.by_code("eur").display_name)
print(CurrencyEnumEntity.EUR is CurrencyEnumEntity.by_code("eur"))
```

Expected:

```
['usd', 'eur']
Euro
True
```

## Scenario 2 — an undeclared code and a copy are refused

```python
try:
    CurrencyEnumEntity.by_code("bootleg")
except KeyError as exc:
    print("KeyError", exc)

copy = CurrencyEnumEntity(code="usd", display_name="Copy", symbol="?")
print("copy built:", copy.code, "| declared:", copy is CurrencyEnumEntity.USD)
```

Expected:

```
KeyError 'bootleg'
copy built: usd | declared: False
```

Building a copy is allowed — it is the dictionary-typed **field** that refuses it, with the message naming the field and the declared value to use (contract §2). The same field refuses the unknown code, naming the field, the code and the declared codes.

## Scenario 3 — a reference reads by the code

```python
from aoa.action_machine.domain import BaseCoreEntity

class SliceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Slice id")
    currency: CurrencyEnumEntity = Field(description="Money unit")

payload = {"id": "s1", "currency": {"code": "usd", "display_name": "Dollar (stale)", "properties": {"symbol": "?"}}}
row = SliceCoreEntity.model_validate(payload)
print(row.currency is CurrencyEnumEntity.USD)
print(row.model_dump()["currency"])
```

Expected:

```
True
{'code': 'usd', 'display_name': 'US dollar', 'properties': {'symbol': '$'}}
```

The stale label in the payload changed nothing, and serializing the row emits the declared label.

## Scenario 4 — an axis takes its codes from the dictionary

The head names the dictionary as the second type argument of its specialization field and carries no classifier field; each extension names its field and its value:

```python
class RecordCoreEntity(BaseCoreEntity):
    id: str = Field(description="Record id")
    kind: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity, EditionKindEnumEntity],
        Inverse(field_name="record"),
    ] = Rel(description="Which pressing this is")

class FirstPressSpecEntity(BaseSpecEntity):
    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(field="record", variant=EditionKindEnumEntity.FIRST),
    ] = Rel(description="The head row")
```

Then build the graph:

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_vocabulary.py -q
```

Expected: every axis that covers the dictionary fully builds; the refusals of `contracts/specialization-codes.md` §5 each raise their named error; and a container built with a value that disagrees with its hydrated class is refused at construction.

## Scenario 5 — the corpus is on the new form

```bash
uv run python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py
```

Expected (after phase 5): `dictionaries without values: 0`, `duplicate codes: 0`, `Classifier(…, Literal[…]) in packages/aoa-demo: 0`, `in examples: 0`, `in tests: 0`, `currency_iso: str in packages/aoa-demo: 0`, `axes on dictionaries: 110`.

## Scenario 6 — the demo graph carries the dictionary

```bash
uv run python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py --graph baseline.after.json
uv run python specs/015-closed-dictionary-variants/evidence/compare_baselines.py \
  specs/015-closed-dictionary-variants/evidence/baseline.before.json \
  specs/015-closed-dictionary-variants/evidence/baseline.after.json
```

Expected: the comparison reports the intended difference and nothing else — one `enum` node with three values, 25 `EntityField` rows carrying `reference_qualname`, and one `entity_specialization` edge set carrying `dictionary_qualname` and `dictionary_label`.

## Scenario 7 — the viewer shows it

```bash
cd packages/aoa-maxitor/client && npm run build && cd -
uv run python -m aoa.maxitor.api.main
```

Load the demo graph in Maxitor, open the ERD, and check: the dictionary is one card with its value rows; a referencing entity's field points at that card; the specialization container reads `kind (by Edition kind)`; the `enum` kind appears in the kind legend. None of these names is in Maxitor's source.

## Scenario 8 — the closing check

```bash
bash scripts/run_checks_with_log.sh
```

Expected: the run is clean apart from the two accepted remarks named in the constitution (the Vite chunk-size advisory and LangGraph's pending-deprecation warning). A new remark is fixed, not triaged.
