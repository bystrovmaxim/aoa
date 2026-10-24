# Relations between entities

A relationship field gives a link its cardinality, ownership meaning, direction and description. Core, Assoc, Detail and Spec hosts use the complete form. Dictionary targets use a single association with `NoInverse()`. State keeps its lifecycle contract.

Previously bare dictionary fields, explicit embedded entity values and one-sided inverse pairs were accepted. Migrate each field and both sides of a reciprocal pair; see [complete declarations and exact refusals](../how-to/explicit-entity-fields.md). `NoRelation` no longer declares an embedded entity.

## Ownership, inverse fields and partial loading

Containers carry ids even when the related entities are not loaded. Access to unloaded data raises `RelationNotLoadedError`; a container does not fetch rows. The ownership container expresses intent, without automatically implementing database deletion rules or a new pair-compatibility matrix.

[Script](../../examples/step_21_relations/01_relations.py) · [Executed notebook](../../examples/step_21_relations/01_relations.ipynb)

```python
"""01_relations.py — Entity relations: ownership, Inverse, partial loading
Run: .venv/bin/python examples/step_21_relations/01_relations.py


An Entity rarely stands alone: an order has a customer and line items. AOA
declares links with relation containers that carry both cardinality and
ownership meaning:

    CompositeOne / CompositeMany     strong ownership (parts can't exist alone)
    AggregateOne / AggregateMany     weak ownership
    AssociationOne / AssociationMany link without ownership

`Inverse(Target, "field")` names the reverse side so the coordinator can verify
reciprocal endpoint names when the graph is built — a broken
relation model fails at startup, not half a year later in a report. `NoInverse()`
marks a deliberately one-way link. Every declared edge carries `Field(description=)`.

Relations load partially like fields: the container always knows the id(s), but
the target row may not be hydrated — reaching through it raises
RelationNotLoadedError, never a silent None.


"""

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
        Inverse(field_name="customer"),
    ] = Field(description="Orders placed by this customer")


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")

    # association — order and customer exist independently
    customer: Annotated[
        AssociationOne[CustomerCoreEntity],
        Inverse(CustomerCoreEntity, "orders"),
    ] = Field(description="Customer who placed the order")

    # composition — line items cannot exist without this order
    lines: Annotated[
        CompositeMany[OrderLineDetailEntity],
        Inverse(field_name="order"),
    ] = Field(description="Line items of the order")


@entity(description="Single line of an order", domain=ShopDomain)
class OrderLineDetailEntity(BaseDetailEntity):
    id: str = Field(description="Line id")
    sku: str = Field(description="Product code")

    order: Annotated[
        AssociationOne[OrderCoreEntity],
        Inverse(OrderCoreEntity, "lines"),
    ] = Field(description="Parent order")


CustomerCoreEntity.model_rebuild()
OrderCoreEntity.model_rebuild()
OrderLineDetailEntity.model_rebuild()


def main() -> None:
    # 1) Startup check: building the machine builds the graph, which verifies
    #    every Inverse names a reciprocal endpoint. A broken relation
    #    model would raise here, not in production.
    ActionProductMachine()
    print("1) Machine built — relation model validated at startup (Inverse mirroring OK)")

    # 2) Id-only relations: the container knows the id, the target isn't hydrated.
    order = OrderCoreEntity(
        id="ord-1",
        total=1500.0,
        customer=AssociationOne[CustomerCoreEntity](id="cust-1"),
        lines=CompositeMany[OrderLineDetailEntity](ids=("line-1", "line-2")),
    )
    print("\n2) Id-only relations:")
    print(f"   order.customer.id  = {order.customer.id}   (is_loaded={order.customer.is_loaded})")
    print(f"   len(order.lines)   = {len(order.lines)}   (is_loaded={order.lines.is_loaded})")
    try:
        _ = order.customer.name  # target row not hydrated
    except RelationNotLoadedError as exc:
        print(f"   order.customer.name -> RelationNotLoadedError: {exc}")
    try:
        _ = list(order.lines)  # many: iteration requires loaded entities
    except RelationNotLoadedError as error:
        print("   iterating order.lines -> RelationNotLoadedError:", error)
    else:
        raise AssertionError("Unloaded collection was iterable")

    # 3) Hydrated relation: pass the loaded target entity; attribute access proxies to it.
    customer = CustomerCoreEntity(
        id="cust-1",
        name="Alice",
        orders=AssociationMany[OrderCoreEntity](ids=("ord-1",)),
    )
    order2 = OrderCoreEntity(
        id="ord-2",
        total=99.0,
        customer=AssociationOne[CustomerCoreEntity](id="cust-1", entity=customer),
        lines=CompositeMany[OrderLineDetailEntity](entities=(), entities_loaded=True),
    )
    assert order2.customer.name == "Alice"
    assert order2.lines.is_loaded
    print("\n3) Hydrated relation:")
    print(f"   order2.customer.name = {order2.customer.name}   (proxied through the loaded entity)")


if __name__ == "__main__":
    main()
```

Actual output:

```text
1) Machine built — relation model validated at startup (Inverse mirroring OK)

2) Id-only relations:
   order.customer.id  = cust-1   (is_loaded=False)
   len(order.lines)   = 2   (is_loaded=False)
   order.customer.name -> RelationNotLoadedError: Related object in AssociationOne is not loaded (id='cust-1'). Cannot access 'name' — only the identifier is present. Load the related entity through your persistence / manager layer.
   iterating order.lines -> RelationNotLoadedError: Related object in CompositeMany is not loaded (id=('line-1', 'line-2')). Cannot access '__iter__' — only the identifier is present. Load the related entity through your persistence / manager layer.

3) Hydrated relation:
   order2.customer.name = Alice   (proxied through the loaded entity)
```

## Declare both directions

A reciprocal pair needs `Inverse` on both endpoints, naming each other. An intentional one-way link uses `NoInverse()`. These checks happen during model assembly; normal container construction does not validate the global declaration graph.

[Script](../../examples/step_21_relations/65_reciprocal_directions.py) · [Executed notebook](../../examples/step_21_relations/65_reciprocal_directions.ipynb)

```python
"""Declare reciprocal pairs and migrate one-sided inverse markers.
Run: .venv/bin/python examples/step_21_relations/65_reciprocal_directions.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, Inverse, NoInverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
from aoa.action_machine.intents.entity import entity


class DirectionDomain(BaseDomain):
    """Group the direction declarations."""

    name = "directions"
    description = "Reciprocal directions"


@entity(description="Offer", domain=DirectionDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Collect the regions offering this product."""

    regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(description="Regions")


@entity(description="Region", domain=DirectionDomain)
class RegionCoreEntity(BaseCoreEntity):
    """Name the opposite endpoint explicitly."""

    offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")


@entity(description="One-way bookmark", domain=DirectionDomain)
class BookmarkCoreEntity(BaseCoreEntity):
    """Keep an intentional unpaired link."""

    offer: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Bookmarked offer")


@entity(description="Old reverse endpoint", domain=DirectionDomain)
class OldOfferCoreEntity(BaseCoreEntity):
    """Keep the previous unpaired reverse declaration."""

    regions: Annotated[AssociationMany[OldRegionCoreEntity], NoInverse()] = Field(description="Regions")


@entity(description="Old forward endpoint", domain=DirectionDomain)
class OldRegionCoreEntity(BaseCoreEntity):
    """Demonstrate the one-sided inverse refusal."""

    offer: Annotated[AssociationOne[OldOfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")


for model in (OfferCoreEntity, RegionCoreEntity, OldOfferCoreEntity, OldRegionCoreEntity):
    model.model_rebuild()


def reciprocal_pair() -> None:
    """Validate both endpoints after forward references resolve."""
    validate_entity_fields([OfferCoreEntity, RegionCoreEntity])
    validate_entity_inverses([OfferCoreEntity, RegionCoreEntity])
    offer = OfferCoreEntity(regions=AssociationMany(ids=("region-1",)))
    assert offer.regions.ids == ("region-1",)
    print("Reciprocal pair: accepted")


def one_way_link() -> None:
    """Accept an intentionally unpaired association."""
    validate_entity_fields([BookmarkCoreEntity])
    validate_entity_inverses([BookmarkCoreEntity])
    bookmark = BookmarkCoreEntity(offer=AssociationOne(id="offer-1"))
    assert bookmark.offer.id == "offer-1"
    print("NoInverse link: accepted")


def old_pair_refusal() -> None:
    """Refuse the old one-sided inverse declaration."""
    try:
        validate_entity_inverses([OldRegionCoreEntity])
    except EntityFieldDeclarationError as error:
        assert error.field_name == "offer"
        assert (
            type(error).__name__ + ": " + str(error)
            == "EntityFieldDeclarationError: Field 'offer' on entity 'OldRegionCoreEntity' is invalid: the reverse field 'regions' on OldOfferCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("A one-sided inverse was accepted")


def main() -> None:
    """Run the related direction cases."""
    reciprocal_pair()
    one_way_link()
    old_pair_refusal()


if __name__ == "__main__":
    main()
```

Actual output:

```text
Reciprocal pair: accepted
NoInverse link: accepted
EntityFieldDeclarationError: Field 'offer' on entity 'OldRegionCoreEntity' is invalid: the reverse field 'regions' on OldOfferCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints.
```

For separate modules, postpone annotations, use `Inverse(field_name="...")` and rebuild both models with an explicit namespace in the composition root. Read the [cross-module script](../../examples/step_21_relations/67_cross_module_inverse.py), [notebook](../../examples/step_21_relations/67_cross_module_inverse.ipynb) and its [endpoint modules](../../examples/step_21_relations/inverse_model/offer.py). The marker itself does not accept a string class name.

## Every structural host uses the same complete form

The [stereotype scenario](../../examples/step_21_relations/66_complete_stereotypes.py) and [notebook](../../examples/step_21_relations/66_complete_stereotypes.ipynb) show Core, Assoc, Detail and Spec fields and an Enum selection. There is no shorthand exemption for technical or owned entities.

## Generalization and specialization

A specialization connects a common entity to one of several detail types. The head names the alternatives and dictionary. Each reverse generalization field carries `Classifier(variant=Dictionary.VALUE)`. The classifier no longer repeats its own field name: remove that argument from existing declarations. The field carrying the marker determines where it applies.

## Declare the complete model

Run this complete example in a fresh Python process.

[Script](../../examples/step_21_relations/02_specialization.py) · [Notebook](../../examples/step_21_relations/02_specialization.ipynb)

```python
"""A record with first-pressing details.

Construct the common record and its first-pressing data.
Run: uv run python examples/step_21_relations/02_specialization.py
"""

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
    Specialization,
    value,
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

    FIRST = value(code="first", display_name="First")
    REPRESS = value(code="repress", display_name="Repress")
    TEST = value(code="test", display_name="Test")


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.REPRESS),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.TEST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
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


if __name__ == "__main__":
    main()
```

Actual output:

```text
Model built
Kind of Blue
first
1A
rec-1
```

## An unknown variant is refused

Runtime construction validates the chosen dictionary value and loaded detail type. Storage code must still load the corresponding entity. Use the separate cases below for unloaded references, unknown codes, mismatched details and invalid declarations. Each prints the actual answer or caught exception and was executed in a fresh process.

| Case | Runnable script | Executed notebook |
| --- | --- | --- |
| specialization unloaded | [03_specialization_unloaded](../../examples/step_21_relations/03_specialization_unloaded.py) | [Notebook](../../examples/step_21_relations/03_specialization_unloaded.ipynb) |
| specialization reverse | [04_specialization_reverse](../../examples/step_21_relations/04_specialization_reverse.py) | [Notebook](../../examples/step_21_relations/04_specialization_reverse.ipynb) |
| specialization mapping | [05_specialization_mapping](../../examples/step_21_relations/05_specialization_mapping.py) | [Notebook](../../examples/step_21_relations/05_specialization_mapping.ipynb) |
| specialization wrong type | [06_specialization_wrong_type](../../examples/step_21_relations/06_specialization_wrong_type.py) | [Notebook](../../examples/step_21_relations/06_specialization_wrong_type.ipynb) |
| specialization data codes | [07_specialization_data_codes](../../examples/step_21_relations/07_specialization_data_codes.py) | [Notebook](../../examples/step_21_relations/07_specialization_data_codes.ipynb) |
| specialization mismatched data | [08_specialization_mismatched_data](../../examples/step_21_relations/08_specialization_mismatched_data.py) | [Notebook](../../examples/step_21_relations/08_specialization_mismatched_data.ipynb) |
| specialization frozen | [09_specialization_frozen](../../examples/step_21_relations/09_specialization_frozen.py) | [Notebook](../../examples/step_21_relations/09_specialization_frozen.ipynb) |
| specialization graph | [10_specialization_graph](../../examples/step_21_relations/10_specialization_graph.py) | [Notebook](../../examples/step_21_relations/10_specialization_graph.ipynb) |
| specialization two axes | [11_specialization_two_axes](../../examples/step_21_relations/11_specialization_two_axes.py) | [Notebook](../../examples/step_21_relations/11_specialization_two_axes.ipynb) |
| specialization hidden edges | [12_specialization_hidden_edges](../../examples/step_21_relations/12_specialization_hidden_edges.py) | [Notebook](../../examples/step_21_relations/12_specialization_hidden_edges.ipynb) |
| specialization erd | [13_specialization_erd](../../examples/step_21_relations/13_specialization_erd.py) | [Notebook](../../examples/step_21_relations/13_specialization_erd.ipynb) |
| specialization single alternative | [14_specialization_single_alternative](../../examples/step_21_relations/14_specialization_single_alternative.py) | [Notebook](../../examples/step_21_relations/14_specialization_single_alternative.ipynb) |
| specialization storage | [15_specialization_storage](../../examples/step_21_relations/15_specialization_storage.py) | [Notebook](../../examples/step_21_relations/15_specialization_storage.ipynb) |
| specialization reference | [16_specialization_reference](../../examples/step_21_relations/16_specialization_reference.py) | [Notebook](../../examples/step_21_relations/16_specialization_reference.ipynb) |
| specialization absent | [17_specialization_absent](../../examples/step_21_relations/17_specialization_absent.py) | [Notebook](../../examples/step_21_relations/17_specialization_absent.ipynb) |
| specialization bare code | [18_specialization_bare_code](../../examples/step_21_relations/18_specialization_bare_code.py) | [Notebook](../../examples/step_21_relations/18_specialization_bare_code.ipynb) |
| specialization foreign pair | [19_specialization_foreign_pair](../../examples/step_21_relations/19_specialization_foreign_pair.py) | [Notebook](../../examples/step_21_relations/19_specialization_foreign_pair.ipynb) |
| error missing classifier | [20_error_missing_classifier](../../examples/step_21_relations/20_error_missing_classifier.py) | [Notebook](../../examples/step_21_relations/20_error_missing_classifier.ipynb) |
| error missing code | [21_error_missing_code](../../examples/step_21_relations/21_error_missing_code.py) | [Notebook](../../examples/step_21_relations/21_error_missing_code.ipynb) |
| error unknown head code | [23_error_unknown_head_code](../../examples/step_21_relations/23_error_unknown_head_code.py) | [Notebook](../../examples/step_21_relations/23_error_unknown_head_code.ipynb) |
| error duplicate code | [25_error_duplicate_code](../../examples/step_21_relations/25_error_duplicate_code.py) | [Notebook](../../examples/step_21_relations/25_error_duplicate_code.ipynb) |
| error inverse name | [29_error_inverse_name](../../examples/step_21_relations/29_error_inverse_name.py) | [Notebook](../../examples/step_21_relations/29_error_inverse_name.ipynb) |
| error no reverse | [30_error_no_reverse](../../examples/step_21_relations/30_error_no_reverse.py) | [Notebook](../../examples/step_21_relations/30_error_no_reverse.ipynb) |
| error two reverse fields | [31_error_two_reverse_fields](../../examples/step_21_relations/31_error_two_reverse_fields.py) | [Notebook](../../examples/step_21_relations/31_error_two_reverse_fields.ipynb) |
| error undeclared entity | [32_error_undeclared_entity](../../examples/step_21_relations/32_error_undeclared_entity.py) | [Notebook](../../examples/step_21_relations/32_error_undeclared_entity.ipynb) |
| error two heads | [34_error_two_heads](../../examples/step_21_relations/34_error_two_heads.py) | [Notebook](../../examples/step_21_relations/34_error_two_heads.ipynb) |
| error outside alternative | [35_error_outside_alternative](../../examples/step_21_relations/35_error_outside_alternative.py) | [Notebook](../../examples/step_21_relations/35_error_outside_alternative.ipynb) |
| error cycle | [37_error_cycle](../../examples/step_21_relations/37_error_cycle.py) | [Notebook](../../examples/step_21_relations/37_error_cycle.ipynb) |
| error axis subset | [38_error_axis_subset](../../examples/step_21_relations/38_error_axis_subset.py) | [Notebook](../../examples/step_21_relations/38_error_axis_subset.ipynb) |
| error codes not literal | [41_error_codes_not_literal](../../examples/step_21_relations/41_error_codes_not_literal.py) | [Notebook](../../examples/step_21_relations/41_error_codes_not_literal.ipynb) |
| error head classifier | [44_error_head_classifier](../../examples/step_21_relations/44_error_head_classifier.py) | [Notebook](../../examples/step_21_relations/44_error_head_classifier.ipynb) |
| error marker field | [45_error_marker_field](../../examples/step_21_relations/45_error_marker_field.py) | [Notebook](../../examples/step_21_relations/45_error_marker_field.ipynb) |
| error empty dictionary | [46_error_empty_dictionary](../../examples/step_21_relations/46_error_empty_dictionary.py) | [Notebook](../../examples/step_21_relations/46_error_empty_dictionary.ipynb) |
| error foreign value | [47_error_foreign_value](../../examples/step_21_relations/47_error_foreign_value.py) | [Notebook](../../examples/step_21_relations/47_error_foreign_value.ipynb) |
| error copied value | [48_error_copied_value](../../examples/step_21_relations/48_error_copied_value.py) | [Notebook](../../examples/step_21_relations/48_error_copied_value.ipynb) |
| error unregistered dictionary | [49_error_unregistered_dictionary](../../examples/step_21_relations/49_error_unregistered_dictionary.py) | [Notebook](../../examples/step_21_relations/49_error_unregistered_dictionary.ipynb) |
| error one argument | [50_error_one_argument](../../examples/step_21_relations/50_error_one_argument.py) | [Notebook](../../examples/step_21_relations/50_error_one_argument.ipynb) |
| group label | [51_group_label](../../examples/step_21_relations/51_group_label.py) | [Notebook](../../examples/step_21_relations/51_group_label.ipynb) |
| required relation | [52_required_relation](../../examples/step_21_relations/52_required_relation.py) | [Notebook](../../examples/step_21_relations/52_required_relation.ipynb) |
| optional relation | [53_optional_relation](../../examples/step_21_relations/53_optional_relation.py) | [Notebook](../../examples/step_21_relations/53_optional_relation.ipynb) |
| former embedded entity refused | [54_embedded_entity](../../examples/step_21_relations/54_embedded_entity.py) | [Notebook](../../examples/step_21_relations/54_embedded_entity.ipynb) |
| bare entity refused | [55_bare_entity_refused](../../examples/step_21_relations/55_bare_entity_refused.py) | [Notebook](../../examples/step_21_relations/55_bare_entity_refused.ipynb) |
| relation description | [56_relation_description](../../examples/step_21_relations/56_relation_description.py) | [Notebook](../../examples/step_21_relations/56_relation_description.ipynb) |
| relation factory | [57_relation_factory](../../examples/step_21_relations/57_relation_factory.py) | [Notebook](../../examples/step_21_relations/57_relation_factory.ipynb) |
| relation null default | [58_relation_null_default](../../examples/step_21_relations/58_relation_null_default.py) | [Notebook](../../examples/step_21_relations/58_relation_null_default.ipynb) |
| relation object default | [59_relation_object_default](../../examples/step_21_relations/59_relation_object_default.py) | [Notebook](../../examples/step_21_relations/59_relation_object_default.ipynb) |
| entity collection | [60_entity_collection](../../examples/step_21_relations/60_entity_collection.py) | [Notebook](../../examples/step_21_relations/60_entity_collection.ipynb) |
| marker on relation | [61_marker_on_relation](../../examples/step_21_relations/61_marker_on_relation.py) | [Notebook](../../examples/step_21_relations/61_marker_on_relation.ipynb) |
| marker on scalar | [62_marker_on_scalar](../../examples/step_21_relations/62_marker_on_scalar.py) | [Notebook](../../examples/step_21_relations/62_marker_on_scalar.ipynb) |
| conflicting markers | [63_conflicting_markers](../../examples/step_21_relations/63_conflicting_markers.py) | [Notebook](../../examples/step_21_relations/63_conflicting_markers.ipynb) |
| nullable required relation | [64_nullable_required_relation](../../examples/step_21_relations/64_nullable_required_relation.py) | [Notebook](../../examples/step_21_relations/64_nullable_required_relation.ipynb) |

## Boundaries

Descriptions and defaults are checked for ownership relations, specializations and generalizations. Exactly one direction marker is required. Hidden edges and graph-excluded models still undergo declaration validation. Required nullable fields have no default; `default=None` permits omission only when the container annotation is nullable. Factories and preconstructed defaults are refused.

`NoRelation` does not allow entity embedding. An unchanged inherited endpoint keeps its base identity; an explicit same-signature override has a [confirmed validation defect](../reports/complete-relationship-verification.md#explicit-overrides). States use lifecycle types. See [specialization refusals](../how-to/specialization-declaration-fails.md), [dictionary selections](../how-to/dictionary-references.md) and [the invariant reference](../reference/intents-and-invariants.md).

Ordinary relationship pairs undergo reciprocal endpoint checks. Specialization/generalization pairs still have a [confirmed direction-check gap](../reports/complete-relationship-verification.md#specialization-directions): a reverse `Inverse` can currently be paired with a head marked `NoInverse`. Use reciprocal markers on both endpoints; do not rely on the missing refusal.
