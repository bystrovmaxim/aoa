# Select dictionary members through complete relationships

Use a dictionary when the model chooses canonical members of a closed catalogue. A dictionary target now works with all six ordinary containers. Pick the role family for ownership meaning and One/Many for cardinality, then declare the complete field with `Annotated`, exactly one direction marker and an assignment-side `Field(description="...")`.

Previously the dictionary-specific validation accepted only AssociationOne with NoInverse. Existing single selections keep their wrapper and transport forms, but diagnostics now say dictionary relation. For multiple selections use a Many container; separate link entities are no longer required solely to select several dictionary members. Replace raw collections with a complete Many relationship, not with a bare dictionary annotation.

## Supported declaration forms

| Container | Python wrapper | JSON selection input | JSON export |
| --- | --- | --- | --- |
| AssociationOne[D] | AssociationOne(id=code) | One id object | One member reference |
| AggregateOne[D] | AggregateOne(id=code) | One id object | One member reference |
| CompositeOne[D] | CompositeOne(id=code) | One id object | One member reference |
| AssociationMany[D] | AssociationMany(ids=(...)) | Array of id objects | Array of member references |
| AggregateMany[D] | AggregateMany(ids=(...)) | Array of id objects | Array of member references |
| CompositeMany[D] | CompositeMany(ids=(...)) | Array of id objects | Array of member references |

Every row still needs the complete source declaration. A required field has no default. Put `| None` inside `Annotated` to permit absence; add `default=None` only to permit omission. A required nullable field still needs an argument. Raw members, bare codes and raw lists/tuples are not implicit relationship wrappers; a dict with the id object or the reference is accepted on every path (see [Every path takes the same input](#every-path-takes-the-same-input)).

The catalogue must be nonempty, decorated with `@entity` and included in the graph. An empty decorated catalogue fails while its decorator runs; incomplete fields and unavailable targets fail during model assembly or public graph projection. NoRelation is not an embedding alternative. State keeps its lifecycle contract. A dictionary used to classify a specialization is a separate role from a relationship target.

## A complete selection and transport example

This independent file uses CompositeOne and AggregateMany to demonstrate that dictionary relationships are not limited to association. The ownership role does not create database cascades or mutate the shared catalogue.

```python
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import (
    AggregateMany, BaseCoreEntity, BaseDomain, BaseEnumEntity, CompositeOne, NoInverse, value,
)
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.intents.entities import entities


class PricingDomain(BaseDomain):
    """Group the pricing declarations."""
    name = "pricing"
    description = "Pricing"


@entity(description="Currencies", domain=PricingDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare canonical currency values."""
    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Prices", domain=PricingDomain)
class PricesCoreEntity(BaseCoreEntity):
    """Use explicit ownership and cardinality for dictionary links."""
    primary: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Primary currency")
    alternatives: Annotated[AggregateMany[CurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Alternative currencies"
    )


@meta(description="Stores the pricing entities")
@entities(
    CurrencyEnumEntity,
    PricesCoreEntity,
)
class PricingStorage(BaseStorage):
    """Hold the pricing entities."""


original = AggregateMany(ids=("usd", "eur"))
price = PricesCoreEntity(primary=CompositeOne(id="eur"), alternatives=original)
assert price.primary.entity is CurrencyEnumEntity.EUR
assert price.alternatives.entities == (CurrencyEnumEntity.USD, CurrencyEnumEntity.EUR)
assert price.alternatives is not original and original.entities == ()
transported = PricesCoreEntity.model_validate_json(
    '{"primary":{"id":"eur"},"alternatives":[{"id":"usd"}]}'
)
empty = PricesCoreEntity(primary=CompositeOne(id="eur"), alternatives=AggregateMany(ids=()))
absent = PricesCoreEntity(primary=CompositeOne(id="eur"))
assert empty.alternatives.is_loaded and empty.alternatives.entities == ()
assert absent.alternatives is None
print("Selected codes:", price.alternatives.ids)
print("JSON export:", transported.model_dump(mode="json")["alternatives"])
print("Empty:", empty.model_dump(mode="json")["alternatives"])
print("Absent:", absent.model_dump(mode="json")["alternatives"])
```

Actual output:

```text
Selected codes: ('usd', 'eur')
JSON export: [{'code': 'usd', 'display_name': 'US dollar', 'properties': {'symbol': '$'}}]
Empty: []
Absent: None
```

## Normalization and canonical identity

Each to-one id resolves to the identical member returned by `D.by_code(code)`. A supplied entity must be that canonical member for the same code. Each Many id resolves in input order. Repeated codes remain repeated; no uniqueness restriction is introduced. Supplied nonempty entities must match the id count and canonical member at every position. Foreign, copied and mismatched members are refused.

Validation returns a new container of the declared class and does not mutate the input wrapper. Id-only dictionary wrappers become loaded because their catalogue is available locally. An empty Many selection becomes loaded with zero entities; it exports `[]`. An absent nullable field is `None` and exports `null`. Normalization resolves all selected codes rather than leaving a partially loaded dictionary relationship. Ordinary structural-entity loading behavior is unchanged.

## Every path takes the same input

A to-one input is the container, the id object `{"id":"eur"}`, or the reference object `{"code":"eur", ...}` the relation writes. A to-many input is the container or an array of those objects, such as `[{"id":"usd"},{"code":"eur"}]`, with `[]` for no values; it is not an `{"ids":[...]}` object. The same rule holds for JSON, for a dict in code and for a FastAPI or MCP request, which validate parsed dicts. A reference is chosen by its `code`; its `display_name` and `properties` come from the catalogue, so a client cannot relabel a value. An id object with another key, a reference with an undeclared key, a bare code, a raw member, a blank or wrong-type code and an unknown catalogue code are refused during host instance validation.

[Script](../../examples/how_to/11_dictionary_input_forms.py) · [Notebook](../../examples/how_to/11_dictionary_input_forms.ipynb)

```text
1) A dict in code, as FastAPI and MCP pass it
   primary: CompositeOne(id='eur', loaded) | alternatives: ('usd',)
2) The reference written is read back
   written: {'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': '€'}}
   read back equal: True
3) The code chooses; the catalogue labels
   primary label: Euro
   alternatives: ('usd', 'eur')
4) What is refused
   refused: eur
   refused: {'id': 'eur', 'extra': 1}
   refused: {'display_name': 'Euro'}
   refused: {'id': 'gbp'}
5) Input schema: [['id'], ['code']]
```

Export uses each canonical member's `to_reference()` representation: code, display_name and properties. Dictionary property serializers still run. Each declared value's reference is computed once, when the dictionary declares its values, and every dump writes it into new dicts, so a dump cannot change the catalogue. Python-mode `model_dump()` retains the relationship wrappers.

## Dump in Python mode and in JSON mode

[Script](../../examples/how_to/10_dictionary_python_dump.py) · [Notebook](../../examples/how_to/10_dictionary_python_dump.ipynb)

Python mode is for code that keeps working with the entity: each wrapper stays as it is, holding the canonical members. JSON mode is for the wire: each selected member becomes its reference. With `price` from the example above:

```python
python_dump = price.model_dump()
print("Python primary:", python_dump["primary"])
print("Python alternatives:", python_dump["alternatives"])
print("Canonical member kept:", python_dump["primary"].entity is CurrencyEnumEntity.EUR)
print("JSON primary:", price.model_dump(mode="json")["primary"])
```

```text
Python primary: CompositeOne(id='eur', loaded)
Python alternatives: AggregateMany(count=2, entities_loaded=yes, n_entities=2)
Canonical member kept: True
JSON primary: {'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': '€'}}
```

[Script](../../examples/step_24_relations/72_role_dictionary.py) · [Executed notebook](../../examples/step_24_relations/72_role_dictionary.ipynb)

```text
All six container classes retained
Selection order and repeats: ('usd', 'eur', 'usd')
Caller loaded: False validated loaded: True
Empty selection: () loaded: True
Exported selections: [{'code': 'usd', 'display_name': 'US dollar', 'properties': {'symbol': 'Currency $'}}, {'code': 'eur', 'display_name': 'Euro', 'properties': {'symbol': 'Currency €'}}]
Empty export: [] absent export: None
Input item keys: ['id']
Output item keys: ['code', 'display_name', 'properties']
ValidationError: 1 validation error for PriceListCoreEntity
alternatives
  Value error, item 1: 'xxx' is not a declared value of CurrencyEnumEntity. Declared: ['eur', 'usd']. [type=value_error, input_value=[{'id': 'eur'}, {'id': 'xxx'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
ValidationError: 1 validation error for PriceListCoreEntity
alternatives
  Value error, item 0: the supplied entity is not the declared value for code 'eur'. [type=value_error, input_value=AssociationMany(count=1, ...oaded=yes, n_entities=1), input_type=AssociationMany]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
Graph roles: {'primary': ('association', 'one'), 'quoted': ('aggregation', 'one'), 'snapshot': ('composition', 'one'), 'alternatives': ('association', 'many'), 'available': ('aggregation', 'many'), 'bundled': ('composition', 'many')}
```

The failure's structured location is the relationship field. A failing Many item is identified by text such as `item 1` in the message; it is not currently a separate numeric component of `ValidationError.errors()[0]["loc"]`. The scenario asserts the actual field location and exact message.

## Direction markers and paired roles

NoInverse is available on each ordinary container for an unpaired link. Two opposite-direction NoInverse fields are independent relationships. An Inverse needs an actual reciprocal Inverse endpoint, and the pair must pass the [role matrix](../reference/intents-and-invariants.md#endpoint-role-compatibility). No role is forbidden merely because the target is Enum.

There is an implementation gap: catalogue property validation currently rejects a relationship-valued reverse field while the dictionary class is created. Thus a general inverse rule exists, but a complete reciprocal dictionary example cannot currently be declared through that API. The [minimal reproduction](../reports/endpoint-role-verification.md#dictionary-reverse-endpoints) records this gap; do not interpret it as a supported dictionary-only NoInverse restriction.

## Graph and consumer contract

A graph-visible dictionary field emits one ordinary `entity_relation` edge with its declared `relation_type` (association, aggregation or composition) and `cardinality` (one or many). The field name, description and direction metadata follow the ordinary relationship contract. Nullability does not change declaration-level cardinality or remove the edge when an instance holds None.

The graph retains an EntityField row and its `reference_qualname` identifying the dictionary. Catalogue values stay in the dictionary node's values. Newly generated relationships emit no special entity_reference edge. Older imported graphs may retain that historical edge type.

The [graph scenario above](../../examples/step_24_relations/72_role_dictionary.py) asserts all six role/cardinality combinations and their field hints. Maxitor preserves the three relation families, but its query currently emits both a retained field row and synthesized FK row for the same dictionary field. This is a [confirmed consumer defect](../reports/endpoint-role-verification.md#dictionary-field-rows-in-the-erd), not two domain fields or two relationship arrows.

## Schema modes and current limits

Validation schemas describe id objects or arrays of id objects. Serialization schemas describe references or arrays of references. They reject unknown top-level reference keys and require code/display_name/properties. Runtime validation still establishes catalogue membership and refuses whitespace-only codes.

The emitted relationship schema currently describes nested properties only as an object. It does not retain the standalone dictionary's typed custom-property definitions. The exported values and serializers work, but malformed custom-property types can pass that schema. See the [schema reproduction](../reports/endpoint-role-verification.md#typed-custom-property-schemas). Standalone dictionary/ordinary DTO schemas retain their separate typed export contract.

See [complete entity fields](explicit-entity-fields.md), [dictionary property validation](dictionary-validation-and-export.md), the [dictionary tutorial](../tutorials/step-23-dictionaries.md) and the [verification report](../reports/endpoint-role-verification.md).
