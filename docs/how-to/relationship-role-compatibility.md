# Choose compatible relationship endpoint roles

Choose a container separately on each endpoint to express what that field means. Association links peers. Aggregate expresses weak ownership; Composite expresses strong ownership. The One/Many suffix states how many related identifiers the field holds. Specialization and Generalization describe the two directions of a classified head/alternative relationship.

A reciprocal link declares `Inverse` on both endpoints. The model checks their roles during assembly, before publishing its graph. Previously a complete ownership/ownership declaration could pass. It now raises `RoleCompatibilityError`. Change the reverse endpoint to an association if only the first side owns the other. Do not change Many to One to repair an ownership-family mismatch.

## The three compatibility rules

1. Specialization pairs only with Generalization, and conversely.
2. An ordinary pair may contain at most one Aggregate or Composite endpoint. Its opposite endpoint must be AssociationOne or AssociationMany. Two associations also form a permitted pair.
3. One/Many does not change compatibility between families. Swapping the two endpoints preserves the verdict and keeps each role attached to its own field.

The [complete 8×8 reference matrix](../reference/intents-and-invariants.md#endpoint-role-compatibility) contains 22 permitted and 42 prohibited directed cells. Counting each unordered combination once gives 12 permitted and 24 prohibited combinations. Compatibility alone does not prove that the markers, target types or classifier declarations are correct.

## Build a complete ownership pair

This independent file builds the real machine with a composition endpoint and its association reverse. The declarations do not implement storage deletion or database cascades. A different permitted cardinality has different domain meaning, even though it passes the same compatibility rule.

```python
from __future__ import annotations
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDetailEntity, BaseDomain, CompositeMany, Inverse
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class PartsDomain(BaseDomain):
    """Group owners and their parts."""
    name = "parts"
    description = "Owners and parts"


@entity(description="Owner", domain=PartsDomain)
class OwnerCoreEntity(BaseCoreEntity):
    """Keep one composition endpoint."""
    id: str = Field(description="Owner identifier")
    parts: Annotated[CompositeMany[PartDetailEntity], Inverse(field_name="owner")] = Field(description="Owned parts")


@entity(description="Part", domain=PartsDomain)
class PartDetailEntity(BaseDetailEntity):
    """Point back through an association."""
    id: str = Field(description="Part identifier")
    owner: Annotated[AssociationOne[OwnerCoreEntity], Inverse(field_name="parts")] = Field(description="Owner")


OwnerCoreEntity.model_rebuild()
PartDetailEntity.model_rebuild()
machine = ActionProductMachine(loggers=[])
owner = OwnerCoreEntity(id="owner-1", parts=CompositeMany(ids=("part-1", "part-2")))
assert machine.graph_coordinator.get_all_nodes()
assert owner.parts.ids == ("part-1", "part-2")
print("CompositeMany / AssociationOne: accepted")
print("Known part ids:", owner.parts.ids)
```

Actual output:

```text
CompositeMany / AssociationOne: accepted
Known part ids: ('part-1', 'part-2')
```

For required versus nullable values, defaults, source placement and cross-module rebuilding, see [complete entity fields](explicit-entity-fields.md). A nullable container without a default remains required; `default=None` permits omission only for a nullable annotation.

## Associations and cardinality

An association on each endpoint permits One/One, One/Many and Many/Many. Cardinality is read from the declaring field: a team with `AssociationMany[Member]` holds member identifiers; each member's `AssociationOne[Team]` holds a team identifier. This does not fetch or reconcile stored rows.

[Script](../../examples/step_21_relations/68_role_plain_associations.py) · [Executed notebook](../../examples/step_21_relations/68_role_plain_associations.ipynb)

```text
AssociationOne / AssociationOne: accepted
AssociationOne / AssociationMany: accepted
AssociationMany / AssociationMany: accepted
customer.account.id: a1
team.members.ids: ('m1', 'm2')
```

## Aggregation and migration

AggregateOne/AssociationMany and AggregateMany/AssociationOne are permitted, as are their reversed endpoint orders. Aggregate/Aggregate is refused. The scenario keeps the aggregate endpoint and changes the reverse field to AssociationOne; the corrected pair passes. The caught exception below occurs during public entity graph projection, after its declaration and inverse checks.

[Script](../../examples/step_21_relations/69_role_aggregation.py) · [Executed notebook](../../examples/step_21_relations/69_role_aggregation.ipynb)

```text
RoleCompatibilityError: Role pair 'AggregateOne' ↔ 'AggregateOne' is not permitted between 'b' on AggregateACoreEntity and 'a' on AggregateBCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain.
AggregateOne / AssociationMany: accepted
AggregateMany / AssociationOne: accepted
AggregateOne / AssociationOne: accepted
```

## Composition and migration

CompositeMany/AssociationOne and CompositeOne/AssociationMany are permitted. Composite/Composite and Aggregate/Composite are refused. Pick which endpoint expresses ownership and declare the other as an association. The scenario shows both refusals and a corrected pair; changing the roles is an explicit domain-model migration.

[Script](../../examples/step_21_relations/70_role_composition.py) · [Executed notebook](../../examples/step_21_relations/70_role_composition.ipynb)

```text
RoleCompatibilityError: Role pair 'CompositeOne' ↔ 'CompositeMany' is not permitted between 'b' on CompositeACoreEntity and 'a' on CompositeBCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain.
RoleCompatibilityError: Role pair 'AggregateOne' ↔ 'CompositeMany' is not permitted between 'b' on CompositeOverAggregateCoreEntity and 'a' on AggregateReverseCoreEntity: both endpoints carry ownership roles; the reverse of an ownership endpoint must be AssociationOne or AssociationMany; change one of these two endpoints to an association role according to which side owns the other in your domain.
CompositeMany / AssociationOne: accepted
CompositeOne / AssociationMany: accepted
CompositeOne / AssociationOne: accepted
```

## Specialization and generalization

A valid classified axis needs Specialization on its head, Generalization on each alternative, reciprocal `Inverse` markers and the existing `Classifier(variant=...)` mapping. Same-role specialized pairs and specialized/ordinary pairs are prohibited. The scenario demonstrates both refusal families, a valid loaded alternative, and the earlier `EntityFieldDeclarationError` for NoInverse on either specialized role.

[Script](../../examples/step_21_relations/71_role_specialization.py) · [Executed notebook](../../examples/step_21_relations/71_role_specialization.ipynb)

```text
RoleCompatibilityError: Role pair 'Specialization' ↔ 'AssociationOne' is not permitted between 'pressing' on SpecOrdinaryHeadCoreEntity and 'record' on OrdinaryReverseCoreEntity: Specialization and Generalization pair exclusively with each other; declare the reverse endpoint as the matching Specialization or Generalization role.
RoleCompatibilityError: Role pair 'Generalization' ↔ 'Generalization' is not permitted between 'b' on GeneralizationACoreEntity and 'a' on GeneralizationBCoreEntity: Specialization and Generalization pair exclusively with each other; declare the reverse endpoint as the matching Specialization or Generalization role.
EntityFieldDeclarationError: Field 'pressing' on entity 'UnpairedHeadCoreEntity' is invalid: a specialization/generalization field requires Inverse, never NoInverse; declare a reciprocal Inverse(field_name=...) on both endpoints.
EntityFieldDeclarationError: Field 'record' on entity 'UnpairedAlternativeSpecEntity' is invalid: a specialization/generalization field requires Inverse, never NoInverse; declare a reciprocal Inverse(field_name=...) on both endpoints.
Specialization / Generalization: accepted
```

The role check supplements classifier membership and coverage checks. It does not turn an arbitrary association into a classified axis. See [the complete specialization tutorial](../tutorials/step-21-relations.md#generalization-and-specialization).

## NoInverse means an independent relationship

| Declaration | Meaning and result |
| --- | --- |
| One ordinary field with NoInverse | Accepted as a one-way relationship |
| Two mutually resolving Inverse fields | A reciprocal pair; its roles must pass the matrix |
| Inverse points at NoInverse | EntityFieldDeclarationError: an unpaired field cannot be the reverse of a pair |
| Two opposite-direction fields with NoInverse | Two independent links, not a reciprocal pair; no inverse metadata is inferred |
| NoInverse on Specialization or Generalization | EntityFieldDeclarationError at declaration validation during assembly/projection |

NoInverse is permitted on all six ordinary containers. The matrix does not compare the roles of two unrelated one-way fields. Merely targeting each other's types, using similar names or having matching ids does not pair them. The independent composition and aggregation below are two links, not a permitted composition/aggregation reciprocal pair.

[Script](../../examples/step_21_relations/73_role_directions.py) · [Executed notebook](../../examples/step_21_relations/73_role_directions.ipynb)

```text
Single NoInverse: accepted
Two NoInverse fields: two independent links, no reciprocal pair
Two reciprocal Inverse fields: accepted
EntityFieldDeclarationError: Field 'target' on entity 'SourceCoreEntity' is invalid: the reverse field 'source' on UnpairedCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints.
```

## Error contract and checking boundaries

Import `RoleCompatibilityError` from `aoa.action_machine.domain`. It exposes `first_entity`, `first_field`, `second_entity`, `second_field`, `first_role`, `second_role`, `rule` and `correction`. This is a separate exception class, not a subclass of EntityFieldDeclarationError; an existing handler for that earlier error must also handle RoleCompatibilityError if it handles all model-build refusals. Endpoint order in the message follows the endpoint inspected first; reversing inspection does not change compatibility. The scenarios pin the exact text they print.

These are checks of real model declarations during assembly, not checks of database rows on each business call. A missing direction marker, unresolved type or invalid reverse endpoint can produce `EntityFieldDeclarationError` before a role-pair check is reached. Classifier problems retain their specialization diagnostics. Hidden edges and graph-excluded hosts remain subject to declaration checks. NoGraphEdge changes presentation, not the rules.

A build or projection that raises has failed: do not use a partial result. Keep deliberately invalid models in separate fresh processes when running a broader application. Each teaching scenario uses public graph projection to inspect its valid and invalid declarations locally; the association scenario also builds the full machine.

## Dictionary targets

All six ordinary containers can target a dictionary. Choose One/Many and ownership meaning in the same way as for another target, then validate actual selected codes and canonical members. The [dictionary guide](dictionary-references.md) covers wrappers, arrays of id objects, export, schema limits and graph roles. The [dictionary scenario](../../examples/step_21_relations/72_role_dictionary.py) and [notebook](../../examples/step_21_relations/72_role_dictionary.ipynb) exercise all six forms.

A dictionary target has no special NoInverse-only rule. A paired declaration still needs an actual reverse endpoint. Current catalogue property validation prevents declaring that reverse relationship on an Enum; see the [verified implementation gap](../reports/endpoint-role-verification.md#dictionary-reverse-endpoints). This is not a new role-pair restriction.

Custom container subclasses currently have a [confirmed compatibility-check gap](../reports/endpoint-role-verification.md#custom-container-subclasses). Use the eight supplied roles; an accepted ownership subclass is not evidence that an ownership/ownership pair is legal.
