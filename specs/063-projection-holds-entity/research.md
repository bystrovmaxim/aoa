# Research: A projection holds the entity

Measured on `main` at `f35ce11e8` (after #405–#407), Python 3.12, Pydantic 2.14.1.

## Before, re-measured

| Case | Output |
| --- | --- |
| 6.1 `OrderSummaryResult(order=order)` | `ValidationError: 1 validation error for OrderSummaryResult` |
| 6.2 `type(params.order)`, `params.order.id` | `'dict'`, `AttributeError: 'dict' object has no attribute 'id'` |
| 6.3 `OrderCoreEntity.schema(schema=LEAK_WIRE)` | accepted, `secret` included |
| 6.4 a partial in a field typed by the bare entity | accepted; JSON `{'order': {'id': 'o2'}}` |

## R1. One reader of "a partial entity from these fields"

**Decision**: a new module `domain/partial_fields.py` holds what #407 put inside `relation_containers.py`: a validator per entity field, built on first use (`TypeAdapter` of the field's annotation with its constraints), and `validated_partial(entity_cls, fields)` that validates each given field and returns `entity_cls.partial(...)`, refusing an undeclared field. The relation's target step and the projection both use it.

**Rationale**: a projection on input and a relation's `"entity"` do the same thing — read some fields of an entity from a dict, each by its own type. One place keeps the rule and its messages; it imports only Pydantic, so `relation_containers`, `entity_schema_marker` and `entity` all import it without a cycle.

## R2. The projection's validator

**Decision**: `EntitySchemaMarker`'s per-value function:

1. a value of the entity class → its JSON form of the projection's fields it holds (`model_dump(mode="json", include=…)`) is checked by the projection's schema (the check of #406); the held values themselves become the partial entity — no re-validation of what the entity already validated;
2. a dict → checked by the projection's schema as it is today, then each field validated by the entity's field type (R1);
3. anything else, an entity of another class included → refused.

Every error keeps today's wording, `<Entity> wire projection: …`. The JSON serializer is the entity's own (it writes the fields the partial holds); Python mode keeps the entity. The JSON Schema the field publishes stays the projection's schema.

**Rationale**: checking the JSON form by the schema keeps one meaning of the schema for every input; building the partial from the held values keeps a full entity's validated objects (relation containers with typed ids, declared statuses) instead of round-tripping them.

## R3. A projection names only fields of its entity

**Decision**: `EntitySchemaMarker.__post_init__` refuses a schema whose `properties` name a key that is not a field of the entity, and a schema without `properties` (a projection lists its fields), with `ValueError` naming the keys and the entity. `BaseEntity.schema()` creates the marker, so the declaration fails.

## R4. A field typed by the bare entity refuses a partial

**Decision**: `BaseParams` and `BaseResult` refuse, after validation, a partial entity (a model missing a declared field) in any field and in each item of a list or tuple, with `"<field>: <Entity> is partial (loaded: a, b); this field takes a full entity. Declare a projection with <Entity>.schema(...)."`. A projection's field is skipped: its marker declares `holds_partial_entity = True`, found in the field's metadata or inside its annotation (`… | None`).

**Rationale**: the first attempt wrapped the entity's own core schema with the check. It reached every validation of the entity and broke the JSON Schema of a recursive pair (measured: `RecursionError` in Pydantic's definitions remapping, a schema dict containing itself). The check belongs where the issue puts it — fields of Params and Result — and there it needs neither the entity's schema nor an import of the domain layer.

**Alternatives considered**: `revalidate_instances` on entities — refused: it copies every full entity, fills the defaults of a partial one instead of refusing it, and reports a generic `Field required`.

## R5. The graph edge

**Decision**: `FieldGraphNode` and `PropertyFieldGraphNode` take the edge's target from the projection marker, as today, or else from the annotation unwrapped from `| None` and `list[...]` when it is an entity class (any `BaseEntity` subclass, dictionaries included — clarification 1).

## R6. Repository impact

| Search | Result |
| --- | --- |
| tests comparing a projection value to a dict | `test_entity_schema_pydantic.py` (`== {...}`, `is order`), `aoa-demo/tests/model/test_entity_projection_samples.py` (`== {...}`) |
| projection declarations | 23 `.schema(schema=` call sites; the closing check run proves each names only fields of its entity |
| graph files | the edge of R5 changes them where a Result field is typed by an entity; phase 4 rebuilds them |
