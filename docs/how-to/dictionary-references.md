# Select a dictionary value through an association

Use a dictionary selection when an object chooses one canonical value from a closed catalogue. Declare the field as `Annotated[AssociationOne[D], NoInverse()] = Field(description="...")`. A required selection has no default. For absence, put `| None` inside `Annotated`; add `default=None` only if callers may omit the selection.

Previously a bare `D` or `D | None` field selected the value and exported a special reference edge. The complete association is now required. Keep the dictionary's members and codes, replace the field annotation, and wrap Python arguments in `AssociationOne(id=code)`. Rebuild model exports after migration.

## Supported forms and boundaries

| Form | Result |
| --- | --- |
| `Annotated[AssociationOne[D], NoInverse()]` with assignment-side description | One required selection |
| `Annotated[AssociationOne[D] | None, NoInverse()]` | One selection or explicit absence; no automatic default |
| Bare `D`, optional bare `D` or `Annotated[D, ...]` | Refused at model build; use the complete association |
| Collection or `AssociationMany[D]` | Refused; model multiple selections as separate link entities |
| Composite, aggregate, specialization or generalization selecting D | Refused; the supported selection is a single association |
| `Inverse` on a dictionary selection | Refused; a catalogue selection has no reverse field |
| `NoRelation` around D | Refused; it does not create an embedded-value escape |
| Empty, undecorated or graph-excluded target catalogue | Refused; provide a nonempty decorated catalogue included in the graph |

Dictionary classes still use `value(...)` and immutable property annotations. An empty decorated catalogue is refused when `@entity` runs. Target and host field checks run during model assembly. Excluding a host or hiding an edge does not disable those checks. A catalogue may belong to another domain.

## Declaration refusals

The collection/complete-association/embedded-marker scenario includes the corrected alternative. The catalogue scenario distinguishes an empty catalogue from one deliberately excluded from graph publication. These refusals occur at model build, before instance validation.

[Script](../../examples/step_20_dictionaries/50_dictionary_declarations.py) · [Executed notebook](../../examples/step_20_dictionaries/50_dictionary_declarations.ipynb)

```text
EntityFieldDeclarationError: Field 'regions' on entity 'Offer50CoreEntity' is invalid: a collection of dictionary values has no declared form (tuple[__main__.Region50EnumEntity, ...]); a dictionary selection is one value. Write Annotated[AssociationOne[Region50EnumEntity], NoInverse()] = Field(description=...).
Complete dictionary association: eu
EntityFieldDeclarationError: Field 'region' on entity 'Offer52CoreEntity' is invalid: the field's type is NoRelation around a dictionary (Region52EnumEntity); only Annotated[AssociationOne[Region52EnumEntity] | None, NoInverse()] is a legal dictionary relationship.
```

[Script](../../examples/step_20_dictionaries/53_dictionary_catalogues.py) · [Executed notebook](../../examples/step_20_dictionaries/53_dictionary_catalogues.ipynb)

```text
EntityFieldDeclarationError: Field 'region' on entity 'Offer53CoreEntity' is invalid: EmptyEnumEntity declares no values; type the field with a concrete dictionary.
EntityFieldDeclarationError: Field 'region' on entity 'Offer54CoreEntity' is invalid: HiddenRegion54EnumEntity has no node in the graph: it is not a declared @entity class, or it is marked exclude_graph_model, so the reference could not be drawn. Keep the dictionary in the graph.
```

## A complete Python selection

[Script](../../examples/step_20_dictionaries/01_reference_field.py) · [Executed notebook](../../examples/step_20_dictionaries/01_reference_field.ipynb)

```python
"""A field holds the declared object.
Run: .venv/bin/python examples/step_20_dictionaries/01_reference_field.py


A price uses a currency value that other prices can share.
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
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
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""
    tag = PriceTagCoreEntity(
        id="tag-1", amount=9.99, currency=AssociationOne(id=CurrencyEnumEntity.EUR.code, entity=CurrencyEnumEntity.EUR)
    )
    print("Shared value:", tag.currency.entity is CurrencyEnumEntity.EUR)
    print("Symbol:", tag.currency.symbol)
    assert tag.currency.entity is CurrencyEnumEntity.EUR


if __name__ == "__main__":
    main()
```

Actual output:

```text
Shared value: True
Symbol: €
```

Python input requires an actual `AssociationOne` wrapper. Its `id` must be a nonblank declared string code. The wrapper may omit `entity`, or supply the identical canonical member returned by `D.by_code(code)`. Validation returns a new wrapper containing that member; the caller's original wrapper is unchanged. A raw member, string or Python mapping is refused. A copied member or a canonical member from the wrong code is also refused.

## JSON input and output are different formats

Selection input through `model_validate_json` is exactly `{"id":"eur"}` at the relationship field. Missing `id`, extra keys, a blank/non-string id and unknown codes fail during instance validation. The Python mapping `{"id":"eur"}` passed to ordinary model construction is not JSON mode and is refused.

JSON export is the canonical member's reference: `{"code":"eur","display_name":"Euro","properties":{...}}`. Field serializers on dictionary properties still run. Exported references cannot be fed unchanged into the association's JSON input. Convert the output code to an `id` selection explicitly. `model_dump()` in Python mode keeps the wrapper.

The [transport scenario](../../examples/step_20_dictionaries/56_selection_transport.py) and [executed notebook](../../examples/step_20_dictionaries/56_selection_transport.ipynb) check canonical identity, new-wrapper normalization, raw-member refusal, JSON selection, nullable absence, export and both schema modes. The [JSON input script](../../examples/step_20_dictionaries/02_reference_payload.py) ([notebook](../../examples/step_20_dictionaries/02_reference_payload.ipynb)) isolates transport selection.

## Exact instance refusals

Each scenario catches `pydantic.ValidationError` and prints its actual type and text. These errors arise while constructing or validating the host instance, rather than while building the graph.

### Raw code

[Script](../../examples/step_20_dictionaries/20_bare_code.py) · [Executed notebook](../../examples/step_20_dictionaries/20_bare_code.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Input should be an instance of AssociationOne [type=is_instance_of, input_value='eur', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/is_instance_of
```

### Unknown wrapped code

[Script](../../examples/step_20_dictionaries/21_unknown_code.py) · [Executed notebook](../../examples/step_20_dictionaries/21_unknown_code.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Value error, 'unknown' is not a declared value of CurrencyEnumEntity. Declared: ['eur', 'usd']. [type=value_error, input_value=AssociationOne(id='unknown', id_only), input_type=AssociationOne]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
```

### Copied member inside the wrapper

[Script](../../examples/step_20_dictionaries/22_copy.py) · [Executed notebook](../../examples/step_20_dictionaries/22_copy.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Value error, the supplied entity is not the declared value for code 'eur'; pass CurrencyEnumEntity.by_code('eur'). [type=value_error, input_value=AssociationOne(id='eur', loaded), input_type=AssociationOne]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
```

### JSON object missing id

[Script](../../examples/step_20_dictionaries/23_missing_code.py) · [Executed notebook](../../examples/step_20_dictionaries/23_missing_code.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Value error, a dictionary association JSON input is an object with exactly one 'id' key. [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
```

### Blank wrapped id

[Script](../../examples/step_20_dictionaries/24_blank_reference.py) · [Executed notebook](../../examples/step_20_dictionaries/24_blank_reference.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Value error, a dictionary association id must be a non-empty string code, got ' '. [type=value_error, input_value=AssociationOne(id=' ', id_only), input_type=AssociationOne]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error
```

### Raw Python mapping

[Script](../../examples/step_20_dictionaries/25_flat_fields.py) · [Executed notebook](../../examples/step_20_dictionaries/25_flat_fields.ipynb)

```text
ValidationError: 1 validation error for PriceTagCoreEntity
currency
  Input should be an instance of AssociationOne [type=is_instance_of, input_value={'code': 'bootleg', 'disp...Unknown', 'symbol': '?'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/is_instance_of
```

## The exported graph

A selection emits an ordinary `entity_relation` edge from its host to D, with `relation_type="association"`, `cardinality="one"` and `has_inverse=false`. It has the field name and description, and no inverse endpoint properties. A nullable selection still has cardinality `one`; graph declarations do not depend on an instance's current value.

The host retains its `EntityField` row, description, ordering and `reference_qualname` naming D. Dictionary members remain entries in the dictionary node's `values`, not separate nodes. Newly built graphs do not emit an `entity_reference` edge for this field. Older exported graphs may still contain those special edges; consumers that support old imports must distinguish them from newly generated ordinary associations.

See the [graph script](../../examples/step_20_dictionaries/08_graph.py) and [notebook](../../examples/step_20_dictionaries/08_graph.ipynb). Maxitor reads the ordinary association and dictionary values, but currently duplicates the retained field and synthesized FK row. Its payload must not be treated as having one row per field until that [confirmed defect](../reports/complete-relationship-verification.md#dictionary-fields-in-maxitor) is fixed.

## Schema boundaries

`mode="validation"` describes the `id` object and rejects extra top-level keys. Membership and whitespace-only identifiers are checked at runtime. `mode="serialization"` describes code/display_name/properties. The association's nested `properties` schema is currently only an object; it does not retain the typed custom-property schema available from a standalone dictionary model. Do not rely on it to reject malformed exported custom properties. See the [schema reproduction](../reports/complete-relationship-verification.md#association-serialization-schema).

See [complete entity fields](explicit-entity-fields.md), [dictionary validation and export](dictionary-validation-and-export.md), [the dictionary tutorial](../tutorials/step-20-dictionaries.md) and [entity invariants](../reference/intents-and-invariants.md#closed-dictionaries-and-declared-values).
