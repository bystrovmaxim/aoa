# Quickstart: the nine proofs this change has to run

**Feature**: `specs/018-dictionary-reference` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md) | **Contracts**: [dictionary-reference-field](./contracts/dictionary-reference-field.md), [reference-edge](./contracts/reference-edge.md), [refusal-diagnostics](./contracts/refusal-diagnostics.md)

Every proof below is runnable from the repository root after `uv sync --extra dev`. Each one names the requirement it proves and the answer it must produce; a proof that prints something else is a failing phase. The answers are the acceptance the phase must produce — the baseline probe in `evidence/baseline_probe.py` records what each one prints today.

## Prerequisites

```bash
uv sync --extra dev
(cd packages/aoa-maxitor/client && npm ci)
```

## 1. The bare dictionary type is the reference

Proves FR-001, FR-002, US1 scenarios 1–2.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Currencies", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the money vocabulary."""
    USD = value(code="usd", display_name="US dollar")

@entity(description="Price", domain=ShopDomain)
class PriceCoreEntity(BaseCoreEntity):
    """Reference a dictionary, once required and once optional."""
    id: str = Field(description="Price id")
    currency: CurrencyEnumEntity = Field(description="Money unit")
    settlement_currency: CurrencyEnumEntity | None = Field(default=None, description="Optional unit")

validate_entity_fields([PriceCoreEntity])
print("accepted")
PY
```

Expected: `accepted`. Both fields are the declared reference and the rule does not refuse them.

## 2. A collection of dictionary values is refused

Proves FR-003, US1 scenario 3.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Regions", domain=ShopDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""
    EU = value(code="eu", display_name="Europe")

class OfferCoreEntity(BaseCoreEntity):
    """Try to store many references in one field."""
    id: str = Field(description="Offer id")
    regions: tuple[RegionEnumEntity, ...] = Field(description="Regions served")

try:
    validate_entity_fields([OfferCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming `OfferCoreEntity.regions`, `RegionEnumEntity`, and the two accepted forms; it must not mention `AssociationMany`.

## 3. A relation container around a dictionary is refused

Proves FR-004, US1 scenario 4.

```bash
uv run --extra dev python - <<'PY'
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseDomain, BaseEnumEntity, NoInverse, value
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Regions", domain=ShopDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""
    EU = value(code="eu", display_name="Europe")

class OfferCoreEntity(BaseCoreEntity):
    """Wrap a shared value in an association."""
    id: str = Field(description="Offer id")
    region: Annotated[AssociationOne[RegionEnumEntity], NoInverse()] = Field(description="Region")

try:
    validate_entity_fields([OfferCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal stating that a dictionary value is a shared reference, not an association target; the baseline accepts this form and grows an `entity_relation` edge, which is the inconsistency the phase removes.

## 4. `NoRelation` on a dictionary says the type already declares the reference

Proves FR-005, US1 scenario 5.

```bash
uv run --extra dev python - <<'PY'
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, NoRelation, value
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Regions", domain=ShopDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""
    EU = value(code="eu", display_name="Europe")

class OfferCoreEntity(BaseCoreEntity):
    """Mark a reference as an embedded value."""
    id: str = Field(description="Offer id")
    region: Annotated[RegionEnumEntity, NoRelation("a value")] = Field(description="Region")

try:
    validate_entity_fields([OfferCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal saying the bare dictionary type already declares the reference; the baseline says the marker applies only to another kind.

## 5. The empty catalogue is refused by the rule

Proves FR-006, US1 scenario 6.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity

class EmptyEnumEntity(BaseEnumEntity):
    """A dictionary that declares no values; @entity refuses one, so it stays bare."""

class PriceCoreEntity(BaseCoreEntity):
    """Type a field with it."""
    id: str = Field(description="Price id")
    currency: EmptyEnumEntity = Field(description="Money unit")

try:
    validate_entity_fields([PriceCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming `PriceCoreEntity.currency` and `EmptyEnumEntity` before any graph is built; the baseline refuses it later, in the graph edge.

## 6. A dictionary outside the graph is refused before the edge

Proves FR-014, US2 scenario 5.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, BaseDomain, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@exclude_graph_model
@entity(description="A dictionary outside the graph", domain=ShopDomain)
class HiddenEnumEntity(BaseEnumEntity):
    """Stay out of the graph on purpose."""
    USD = value(code="usd", display_name="US dollar")

@entity(description="A host inside the graph", domain=ShopDomain)
class PriceCoreEntity(BaseCoreEntity):
    """Reference the hidden dictionary."""
    id: str = Field(description="Price id")
    currency: HiddenEnumEntity = Field(description="Money unit")

try:
    validate_entity_fields([PriceCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming the field and `HiddenEnumEntity`; the build never reaches a dangling `entity_reference` target.

## 7. The graph carries the reference as an edge

Proves FR-010, FR-011, FR-012, FR-013, US2 scenarios 1–3.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Regions", domain=ShopDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""
    EU = value(code="eu", display_name="Europe")

@entity(description="Offer", domain=ShopDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Reference the dictionary."""
    id: str = Field(description="Offer id")
    region: RegionEnumEntity = Field(description="Primary region")

node = EntityGraphNode(OfferCoreEntity)
for edge in node.get_all_edges():
    if edge.edge_name == "entity_reference":
        print("edge:", edge.properties["field_name"], "->", edge.target_node_id)
for edge in node.entity_field_edges:
    field = edge.target_node
    if field.label == "region":
        print("row:", field.properties.get("reference_qualname"))
PY
```

Expected: `edge: region -> ...RegionEnumEntity` and `row: ...RegionEnumEntity`. The baseline prints neither.

## 8. The ERD shows the reference

Proves FR-017, FR-018, FR-021, US3.

```bash
uv run --extra dev python - <<'PY'
import json
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, value
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

class ShopDomain(BaseDomain):
    """Group the declarations."""
    name = "shop"
    description = "Shop"

@entity(description="Regions", domain=ShopDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""
    EU = value(code="eu", display_name="Europe")

@entity(description="Offer", domain=ShopDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Reference the dictionary."""
    id: str = Field(description="Offer id")
    region: RegionEnumEntity = Field(description="Primary region")

machine = ActionProductMachine(loggers=[])
domain = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "ShopDomain")
store = DuckDBGraphResource.build_from_json(json.loads(machine.graph_coordinator.to_json()))
diagram = ListEntitiesAction._slice_payload(store, domain, include_neighbors=True)
print([r for r in diagram["relations"] if r["relationship_kind"] == "reference"])
PY
```

Expected: one entry with `label` `region`, `source` the offer, `target` the dictionary, `relationship_kind` `reference`. The rendered SVG draws the arrow; the row still prints `→ RegionEnumEntity`; the dictionary card prints no code.

## 9. A refusal names the shape that is wrong

Proves FR-023, FR-024, FR-025, US4.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseSpecEntity
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity

class FirstCoreEntity(BaseCoreEntity):
    """One entity."""
    id: str = Field(description="Id")

class SecondSpecEntity(BaseSpecEntity):
    """Another entity."""
    id: str = Field(description="Id")

class UnionCoreEntity(BaseCoreEntity):
    """Try a union of two entities."""
    id: str = Field(description="Id")
    ref: FirstCoreEntity | SecondSpecEntity = Field(description="Union")

class MixedCoreEntity(BaseCoreEntity):
    """Try a heterogeneous collection."""
    id: str = Field(description="Id")
    ref: tuple[FirstCoreEntity, SecondSpecEntity] = Field(description="Mixed")

class MappingCoreEntity(BaseCoreEntity):
    """Try a mapping."""
    id: str = Field(description="Id")
    ref: dict[str, FirstCoreEntity] = Field(description="Mapping")

for cls in (UnionCoreEntity, MixedCoreEntity, MappingCoreEntity):
    try:
        validate_entity_fields([cls])
    except Exception as error:
        print(cls.__name__, "->", getattr(error, "details", error))
PY
```

Expected: each of the three refusals names its shape — union, collection, mapping — and names every entity it holds; none of them is accepted. The baseline calls all three a collection.

## Recorded answers (phase 1)

Proofs 1–6 were run on the branch at the end of the rule phase; these are their exact answers,
copied from the run.

```text
proof 1: accepted
proof 2: EntityFieldDeclarationError Field 'regions' on entity 'OfferCoreEntity' is invalid: a collection of dictionary values has no declared form (tuple[__main__.RegionEnumEntity, ...]); a dictionary reference is one value. Write RegionEnumEntity, or RegionEnumEntity | None for an optional one.
proof 3: EntityFieldDeclarationError Field 'region' on entity 'OfferCoreEntity' is invalid: the field's type is a relation container around a dictionary (RegionEnumEntity); a dictionary value is a shared reference, not an association target. Write RegionEnumEntity on the field instead.
proof 4: EntityFieldDeclarationError Field 'region' on entity 'OfferCoreEntity' is invalid: NoRelation marks an embedded structural entity, and this field's type is a dictionary (RegionEnumEntity): the bare dictionary type already declares the reference. Remove the marker and keep RegionEnumEntity on the field.
proof 5: EntityFieldDeclarationError Field 'currency' on entity 'PriceCoreEntity' is invalid: EmptyEnumEntity declares no values; type the field with a concrete dictionary.
proof 6: EntityFieldDeclarationError Field 'currency' on entity 'PriceCoreEntity' is invalid: HiddenEnumEntity has no node in the graph: it is not a declared @entity class, or it is marked exclude_graph_model, so the reference could not be drawn. Keep the dictionary in the graph.
```

proof 7: edge: region -> RegionEnumEntity / row: RegionEnumEntity
proof 8: one relation with label `region`, kind `reference`, target the dictionary
proof 9: UnionCoreEntity -> the field's type is a union of entities (...), so the field names FirstCoreEntity and SecondSpecEntity at once
         MixedCoreEntity -> the field's type is a collection of 2 entities (...); ... Declare one field per entity (FirstCoreEntity, SecondSpecEntity)
         MappingCoreEntity -> the field's type is a mapping to an entity (...), and a mapping is not a relation

## What a green phase looks like

- Proofs 1 and 7 pass, and proofs 2–6 and 9 refuse with the message their contract states.
- `bash scripts/run_checks_with_log.sh` reports only the two accepted remarks.
- The rendered SVG shows one arrow per reference and the dictionary card unchanged from #249.
