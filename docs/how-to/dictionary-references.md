# Declare dictionary references

Use a dictionary field when an object selects one value from a closed catalogue. Keep the bare dictionary type: `region: RegionEnumEntity`. Use `RegionEnumEntity | None` when absence is allowed, and `Field(default=None, description="Region")` when callers may omit it.

Previously a dictionary field supplied a column with a reference hint. Now it also supplies an `entity_reference` edge to the dictionary. Existing scalar declarations need no annotation change. Rebuild exported graphs to make the edges available to diagram consumers.

## Supported declarations

| Declaration | Result at model build | Migration |
| --- | --- | --- |
| `D`, `Annotated[D, ...]` without relation markers | One reference edge and the existing field row | Keep the declaration |
| `D | None` | Same edge with cardinality `one`; the value may be absent | Keep the declaration; add a default only if omission is intended |
| Collection of `D`, including tuple, sequence and frozen set | Declaration refusal | Model multiple selections with a separate link entity |
| Relation container around `D` | Declaration refusal | Replace the container with `D` |
| `Annotated[D, NoRelation("reason")]` | Declaration refusal | Remove the marker |
| Empty dictionary target | Declaration refusal | Declare a concrete nonempty catalogue |
| Undecorated or graph-excluded target | Declaration refusal | Decorate and include the dictionary |

Declaration validation runs when the model is assembled, before graph gathering. The refusal scripts invoke the same declaration check explicitly to isolate each invalid field. These field shapes need not fail when Python defines the host class. Decorating an empty dictionary with `@entity` already fails at declaration; the empty-target example therefore uses an undecorated empty type.

Optional references, inherited fields and resolved forward references retain the same edge. A dictionary in another domain may be referenced. A dictionary used as a specialization vocabulary is still a separate concern: its axis does not replace a field's reference edge. Dictionary values remain rows in a single catalogue, rather than individual graph nodes.

## A complete reference

The following standalone example keeps the existing declaration and checks the new edge.

```python
"""The dictionary carries values and references in the graph.
Run: uv run python examples/step_20_dictionaries/08_graph.py

Inspect the dictionary, the field that refers to it, and the edge that carries the reference.
"""

from pydantic import Field

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


def main() -> None:
    """Run this one learning experiment."""
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

    dictionary = EntityGraphNode(CurrencyEnumEntity)
    tag = EntityGraphNode(PriceTagCoreEntity)
    field = next(edge.target_node for edge in tag.entity_field_edges if edge.target_node.label == "currency")
    reference = next(edge for edge in tag.references if edge.properties["field_name"] == "currency")
    print("Kind:", dictionary.properties["entity_kind"])
    print("Values:", [value["code"] for value in dictionary.properties["values"]])
    print("Reference:", field.properties["reference_qualname"].split(".")[-1])
    print("Edge:", reference.edge_name, "->", reference.target_node_id.split(".")[-1])


if __name__ == "__main__":
    main()
```

Actual output:

```text
Kind: enum
Values: ['eur', 'usd']
Reference: CurrencyEnumEntity
Edge: entity_reference -> CurrencyEnumEntity
```

The exported edge has `field_name` and `cardinality: "one"`. Its target is the dictionary entity identifier. The field row keeps `reference_qualname`. Maxitor projects it as a relation with `relationship_kind: "reference"`, retaining the field name and the dictionary type hint. Rebuild older graph exports; a column hint alone does not supply this relation.

## Choose the reference form

Collections cannot represent one selected code. A shared dictionary value is neither an association target nor an embedded structural object.

[Script](../../examples/step_20_dictionaries/50_dictionary_declarations.py) · [Executed notebook](../../examples/step_20_dictionaries/50_dictionary_declarations.ipynb). Run each script in a fresh process. These are exact outputs when invoked as scripts:

```text
EntityFieldDeclarationError: Field 'regions' on entity 'Offer50CoreEntity' is invalid: a collection of dictionary values has no declared form (tuple[__main__.Region50EnumEntity, ...]); a dictionary reference is one value. Write Region50EnumEntity, or Region50EnumEntity | None for an optional one.
EntityFieldDeclarationError: Field 'region' on entity 'Offer51CoreEntity' is invalid: the field's type is a relation container around a dictionary (Region51EnumEntity); a dictionary value is a shared reference, not an association target. Write Region51EnumEntity on the field instead.
EntityFieldDeclarationError: Field 'region' on entity 'Offer52CoreEntity' is invalid: NoRelation marks an embedded structural entity, and this field's type is a dictionary (Region52EnumEntity): the bare dictionary type already declares the reference. Remove the marker and keep Region52EnumEntity on the field.
```

## Keep the catalogue available

A reference requires a concrete nonempty catalogue that participates in the graph.

[Script](../../examples/step_20_dictionaries/53_dictionary_catalogues.py) · [Executed notebook](../../examples/step_20_dictionaries/53_dictionary_catalogues.ipynb). Run each script in a fresh process. These are exact outputs when invoked as scripts:

```text
EntityFieldDeclarationError: Field 'region' on entity 'Offer53CoreEntity' is invalid: EmptyEnumEntity declares no values; type the field with a concrete dictionary.
EntityFieldDeclarationError: Field 'region' on entity 'Offer54CoreEntity' is invalid: HiddenRegion54EnumEntity has no node in the graph: it is not a declared @entity class, or it is marked exclude_graph_model, so the reference could not be drawn. Keep the dictionary in the graph.
```

## Read structural diagnostics

Structural unions, heterogeneous collections and mappings were already refused. Their messages now identify their actual shape and the supported correction.

[Script](../../examples/step_20_dictionaries/55_refusal_diagnostics.py) · [Executed notebook](../../examples/step_20_dictionaries/55_refusal_diagnostics.ipynb). Run each script in a fresh process. These are exact outputs when invoked as scripts:

```text
EntityFieldDeclarationError: Field 'ref' on entity 'UnionCoreEntity' is invalid: the field's type is a union of entities (__main__.FirstCoreEntity | __main__.SecondSpecEntity), so the field names FirstCoreEntity and SecondSpecEntity at once. Declare one field per entity, each with its own relation or embedded-value form.
EntityFieldDeclarationError: Field 'ref' on entity 'MixedCoreEntity' is invalid: the field's type is a collection of 2 entities (tuple[__main__.FirstCoreEntity, __main__.SecondSpecEntity]); a collection is not a relation. Declare one field per entity (FirstCoreEntity, SecondSpecEntity), each with its own relation or embedded-value form.
EntityFieldDeclarationError: Field 'ref' on entity 'MappingCoreEntity' is invalid: the field's type is a mapping to an entity (dict[str, __main__.FirstCoreEntity]), and a mapping is not a relation. Declare the relation on the owning entity, or model the mapping as its own entity.
```

## Graph and diagram examples

[Graph script](../../examples/step_20_dictionaries/08_graph.py) · [Notebook](../../examples/step_20_dictionaries/08_graph.ipynb).
[Diagram script](../../examples/step_20_dictionaries/09_erd.py) · [Notebook](../../examples/step_20_dictionaries/09_erd.ipynb).

The diagram example returns:

```text
{'code': 'eur', 'display_name': 'Euro', 'properties': [{'name': 'symbol', 'value': '€'}]}
CurrencyEnumEntity
Relation: currency -> CurrencyEnumEntity
```

See [dictionary validation and export](dictionary-validation-and-export.md),
[explicit structural fields](explicit-entity-fields.md),
[the dictionary tutorial](../tutorials/step-20-dictionaries.md), and
[entity invariants](../reference/intents-and-invariants.md).
