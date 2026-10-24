# Declare complete entity relationships

Use a relationship field whenever an entity refers to another entity. Choose a container for cardinality and ownership, put its direction marker in `Annotated`, and put exactly one `Field(description="...")` after `=`. The description must contain non-whitespace text.

Previously a bare dictionary selected a value, `NoRelation("reason")` could declare an embedded structural entity, and a reverse endpoint could omit its `Inverse`. Those forms now fail when the model is built. Replace embedded entity snapshots with complete links, or use a separate non-entity value model when the data is truly a value. Do not wrap an entity type in a list, tuple, mapping or a mixed union to bypass the rule.

## Choose the form for each stereotype

| Entity kind | Relationship declaration |
| --- | --- |
| Core | Ordinary links use a supported container, one direction marker and an assignment-side `Field` |
| Assoc | Each endpoint is a complete relationship; a technical connection has no shorthand exemption |
| Detail | Its owner link and other links each use the complete form |
| Spec | Ordinary links use the complete form; the head link uses `Generalization[Head]`, `Classifier(variant=D.VALUE)` and reciprocal `Inverse` |
| Enum | Dictionary targets support all six ordinary containers with a complete declaration; current catalogue property validation blocks a declared reverse relationship ([gap](../reports/endpoint-role-verification.md#dictionary-reverse-endpoints)) |
| State | Keep the lifecycle contract; use a `Lifecycle[...]` subclass on the owning field, rather than an ordinary link to a status entity |

A dictionary is a catalogue of values, not a host for arbitrary entity-valued properties. Its property type check runs at dictionary class creation. The Enum rule above describes selecting that catalogue from another entity. It does not relax property restrictions.

`AssociationOne`/`AssociationMany` express links without ownership; `CompositeOne`/`CompositeMany` express composition; `AggregateOne`/`AggregateMany` express aggregation. A reciprocal ordinary pair may have at most one Aggregate or Composite endpoint; its reverse must be an association. Specialization pairs only with Generalization. One/Many does not alter compatibility. These declarations do not implement storage deletion or database constraints. See the [complete matrix and migration](relationship-role-compatibility.md).

## Complete declarations and values

This independent example includes Core, Assoc, Detail and Spec hosts and an Enum target. Each field has its own complete declaration. The Spec example shows ordinary links; a classified head and its alternatives are covered by the [specialization tutorial](../tutorials/step-21-relations.md#generalization-and-specialization).

[Script](../../examples/step_21_relations/66_complete_stereotypes.py) · [Executed notebook](../../examples/step_21_relations/66_complete_stereotypes.ipynb)

```python
"""Use complete relationship fields on Core, Assoc, Detail and Spec hosts.
Run: .venv/bin/python examples/step_21_relations/66_complete_stereotypes.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AggregateMany,
    AssociationMany,
    AssociationOne,
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
from aoa.action_machine.intents.entity import entity


class KindDomain(BaseDomain):
    """Group the relationship kinds."""

    name = "kinds"
    description = "Complete relationship fields"


@entity(description="Region catalogue", domain=KindDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Provide a shared selection target."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", domain=KindDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Select a dictionary value from a Core host."""

    region: Annotated[AssociationOne[RegionEnumEntity], NoInverse()] = Field(description="Sales region")


@entity(description="Technical offer link", domain=KindDomain)
class OfferAssocEntity(BaseAssocEntity):
    """Link technical endpoints with explicit directions."""

    offer: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Linked offer")
    related: Annotated[AssociationMany[OfferCoreEntity], NoInverse()] = Field(description="Other offers")


@entity(description="Offer detail", domain=KindDomain)
class OfferDetailEntity(BaseDetailEntity):
    """Name the owner through an association."""

    owner: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Owning offer")


@entity(description="Offer variant data", domain=KindDomain)
class OfferSpecEntity(BaseSpecEntity):
    """Use ordinary links alongside variant-specific data."""

    related: Annotated[AggregateMany[OfferCoreEntity], NoInverse()] = Field(description="Related offers")
    detail: Annotated[CompositeOne[OfferDetailEntity] | None, NoInverse()] = Field(
        default=None, description="Extra detail"
    )


def main() -> None:
    """Validate each host and construct its relation values."""
    validate_entity_fields([OfferCoreEntity, OfferAssocEntity, OfferDetailEntity, OfferSpecEntity])
    validate_entity_inverses([OfferCoreEntity, OfferAssocEntity, OfferDetailEntity, OfferSpecEntity])
    core = OfferCoreEntity(region=AssociationOne(id="eu"))
    assoc = OfferAssocEntity(offer=AssociationOne(id="offer-1"), related=AssociationMany(ids=("offer-2",)))
    detail = OfferDetailEntity(owner=AssociationOne(id="offer-1"))
    spec = OfferSpecEntity(related=AggregateMany(ids=("offer-2",)))
    assert core.region.entity is RegionEnumEntity.EU
    assert assoc.offer.id == detail.owner.id == "offer-1"
    assert spec.detail is None and spec.related.ids == ("offer-2",)
    print("Core: eu; Assoc: offer-1; Detail: offer-1; Spec: nullable detail")


if __name__ == "__main__":
    main()
```

Actual output:

```text
Core: eu; Assoc: offer-1; Detail: offer-1; Spec: nullable detail
```

## Required values, nullable values and defaults

A required relationship has no default. Nullable does not mean optional to supply: `Annotated[AssociationOne[T] | None, NoInverse()] = Field(description="Target")` still requires the argument, but accepts `None`. Add `default=None` only when omission should mean absence. Factories, preconstructed containers and other defaults are refused at model build. Put the union inside `Annotated`, and keep a single non-null container type.

See [required](../../examples/step_21_relations/52_required_relation.py) ([notebook](../../examples/step_21_relations/52_required_relation.ipynb)), [omittable](../../examples/step_21_relations/53_optional_relation.py) ([notebook](../../examples/step_21_relations/53_optional_relation.ipynb)) and [nullable but required](../../examples/step_21_relations/64_nullable_required_relation.py) ([notebook](../../examples/step_21_relations/64_nullable_required_relation.ipynb)).

## Both inverse endpoints must agree

`NoInverse()` remains the way to declare a one-way link. If one endpoint uses `Inverse`, the named reverse field must exist, use its own `Inverse`, and name the originating entity and field. An inverse paired with `NoInverse()` is refused. Migrate an old one-sided pair by adding the matching marker to the other side; use `NoInverse()` only when no reciprocal pair is intended.

`Inverse(Target, "reverse")` requires a class object. A string class name is not accepted. `Inverse(field_name="reverse")` infers the target from the resolved container argument and now works for ordinary relationships as well as specialization heads. With postponed annotations, import both modules in the composition root and call `model_rebuild(_types_namespace=...)` on both models before building the machine. This avoids runtime imports between endpoint modules. See [the cross-module script](../../examples/step_21_relations/67_cross_module_inverse.py) and [notebook](../../examples/step_21_relations/67_cross_module_inverse.ipynb).

The [direction scenario](../../examples/step_21_relations/65_reciprocal_directions.py) ([notebook](../../examples/step_21_relations/65_reciprocal_directions.ipynb)) demonstrates a reciprocal pair, a valid one-way link and the former one-sided form. Its exact refusal is:

```text
EntityFieldDeclarationError: Field 'offer' on entity 'OldRegionCoreEntity' is invalid: the reverse field 'regions' on OldOfferCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints.
```

An unchanged inherited relationship keeps its base endpoint. Do not rely on an explicitly redeclared field being distinguished from that inherited endpoint: a same-signature override is currently accepted after a rebuild. This is a [confirmed defect](../reports/complete-relationship-verification.md#explicit-overrides), not an alternative declaration form.

## Refusals and checking time

These are model declarations, not database row validations. Defining a structural host may succeed; assembling `ActionProductMachine` or its coordinator validates loaded declarations before publishing the graph. Direct `EntityGraphNode` projection validates that host too. `NoGraphEdge` hides an edge, and `exclude_graph_model` hides a graph model; neither grants an exemption from declaration checks. Unresolved forward references must be rebuilt before assembly.

### Former embedded declaration

[Script](../../examples/step_21_relations/54_embedded_entity.py) · [Executed notebook](../../examples/step_21_relations/54_embedded_entity.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation no longer declares an embedded value; the field's type is an entity (TargetCoreEntity). Declare the complete relationship (Annotated[AssociationOne[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...)).
```

### Bare entity

[Script](../../examples/step_21_relations/55_bare_entity_refused.py) · [Executed notebook](../../examples/step_21_relations/55_bare_entity_refused.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: the field's type is an entity (TargetCoreEntity), so the field cannot be a scalar. Declare the complete relationship (Annotated[AssociationOne[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...)).
```

### Non-nullable field with None default

[Script](../../examples/step_21_relations/58_relation_null_default.py) · [Executed notebook](../../examples/step_21_relations/58_relation_null_default.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: default=None needs a nullable annotation; write Annotated[aoa.action_machine.domain.relation_containers.AssociationOne[__main__.TargetCoreEntity] | None, ...] = Field(default=None, description=...).
```

### Collection of entity instances

[Script](../../examples/step_21_relations/60_entity_collection.py) · [Executed notebook](../../examples/step_21_relations/60_entity_collection.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: the field's type is a collection of an entity (list[__main__.TargetCoreEntity]); a collection is not a relation. Declare the many relationship (Annotated[AssociationMany[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...)).
```

### NoRelation on a container

[Script](../../examples/step_21_relations/61_marker_on_relation.py) · [Executed notebook](../../examples/step_21_relations/61_marker_on_relation.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation no longer declares an embedded value; the field's type is an entity (aoa.action_machine.domain.relation_containers.AssociationOne[__main__.TargetCoreEntity]). Declare the complete relationship (Annotated[AssociationOne[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...)).
```

### NoRelation on a scalar

[Script](../../examples/step_21_relations/62_marker_on_scalar.py) · [Executed notebook](../../examples/step_21_relations/62_marker_on_scalar.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, which no longer exists; this field's type is str, not an entity. Declare the field as an ordinary scalar.
```

### Conflicting markers

[Script](../../examples/step_21_relations/63_conflicting_markers.py) · [Executed notebook](../../examples/step_21_relations/63_conflicting_markers.ipynb)

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation no longer declares an embedded value; the field's type is an entity (TargetCoreEntity). Declare the complete relationship (Annotated[AssociationOne[TargetCoreEntity], Inverse(...) or NoInverse()] = Field(description=...)).
```

## Source spelling and runtime semantics

The assignment-side `Field` requirement also has a source check. Runtime Pydantic models merge `Field` metadata, so runtime validation alone cannot prove whether a `Field` was inside `Annotated`. Run the source checker on the roots you maintain as well as building the model. It parses files without importing them. Do not mistake a successful model build for proof of source placement.

```sh
.venv/bin/python scripts/check_complete_entity_fields.py examples/step_21_relations/65_reciprocal_directions.py examples/step_21_relations/66_complete_stereotypes.py examples/step_21_relations/67_cross_module_inverse.py
```

See the [dictionary selection guide](dictionary-references.md), [relationship tutorial](../tutorials/step-21-relations.md) and [invariant reference](../reference/intents-and-invariants.md#entity-relations). Current verification limits and reproductions are in the [verification report](../reports/complete-relationship-verification.md).

Specialization and Generalization now refuse NoInverse on either endpoint. Ordinary NoInverse fields remain valid one-way links, including two opposite-direction fields that declare independent relationships. The [direction scenario](../../examples/step_21_relations/73_role_directions.py) and [notebook](../../examples/step_21_relations/73_role_directions.ipynb) distinguish these cases.
