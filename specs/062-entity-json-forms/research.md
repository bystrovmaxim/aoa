# Research: Every entity value has one JSON form

Measured on `main` at `44c5bf813` (after #405 and #406), Python 3.12, Pydantic 2.14.1, pydantic-core 2.50.1. The probes live outside the repository; their outputs are quoted.

## Before, re-measured on today's main

| Case | Output |
| --- | --- |
| 3.1 `order.model_dump(mode="json")` | `PydanticSerializationError: Unable to serialize unknown type: <class '…AssociationOne'>` |
| 3.2 `OrderCoreEntity.model_json_schema()` | `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.IsInstanceSchema (<class '…AssociationOne'>)` |
| 3.3 `model_validate_json` of the id forms | `ValidationError: 2 validation errors for OrderCoreEntity` |
| 4.3 `PriceParams.model_validate({"currency": {"id": "eur"}})` | `ValidationError: 1 validation error for PriceParams` |
| 4.4 read back `model_dump_json()` of a reference | `ValidationError: 1 validation error for PricesCoreEntity` |
| 5.2 `{"lifecycle": {"code": "draft"}}` | `ValidationError: 1 validation error for Order2CoreEntity` |
| lifecycle JSON dump / schema | `PydanticSerializationError … OrderLifecycle` / `PydanticInvalidForJsonSchema … OrderLifecycle` |

## R1. A relation to an ordinary entity: one core schema for every mode

**Decision**: `BaseRelationOne/Many.__get_pydantic_core_schema__` keeps the dictionary branch (R2) and, for an ordinary target, returns a chain:

1. a *before* step that turns a container of the declared class into its form (`{"id", "entity"?}` / `{"ids", "entities"?}`), refuses a container of another class, and passes a dict on;
2. a closed typed dict: `id` (or each of `ids`) validated by the core schema of the target's `id` annotation — `handler.generate_schema(id_type)` — or strict `str | int` when the target has no `id`; `entity` (or each of `entities`) validated by a *target* step (below);
3. an *after* step that builds a new container of the declared class from the validated dict (`entities_loaded=True` when `"entities"` is present).

The *target* step accepts an instance of the target as it is and builds `target.partial(**fields)` from a dict, validating each present field by that field's own annotation (a `TypeAdapter` per field, built on first use and cached), refusing an undeclared key. It publishes the target's schema (`handler.generate_schema(target)`) as its JSON-Schema input, so the field's schema names the target by `$ref`.

Serialization, JSON mode only: the form as a dict whose `entity`/`entities` are the entity instances; the serializer's return schema is the same typed dict, so Pydantic writes the nested entity with its own serializer (partial entities included, #405). Python mode keeps the container.

**Rationale**: the typed dict gives exact error locations (`customer.id`, `lines.ids.0`) and one validator for JSON, dicts and containers (rule 1). Generating the target's schema through the handler makes Pydantic register it as a definition, so a recursive pair is finite. Prototype outputs:

| Probe | Result |
| --- | --- |
| order with unloaded One + Many, JSON dump | `{'id': 'o1', 'customer': {'id': '00000000-…-0001'}, 'lines': {'ids': ['l1', 'l2']}}` |
| Python dump | `AssociationOne(id=UUID('…'), id_only)` |
| read back | equal; both not loaded |
| loaded, zero rows | `{'ids': [], 'entities': []}` → `is_loaded True` |
| loaded partial customer | `{'id': '…', 'entity': {'id': '…', 'name': 'Ann'}}` → reads back, `orders` not loaded |
| id `"abc"` for a UUID target | `ValidationError`, `uuid_parsing` |
| recursive pair `Customer.orders ↔ Order.customer` | schema builds: `$defs` `CustomerCoreEntity`, `LineDetailEntity`, `OrderCoreEntity`; `customer` = `{"type": "object", "properties": {"id": {"format": "uuid", …}, "entity": {"$ref": "#/$defs/CustomerCoreEntity"}}, "required": ["id"], "additionalProperties": false}` |

**Alternatives considered**: *validate `entity` with the target's full model schema* — refused: a partial target (missing required fields) would be refused, against #405; *a plain function validating everything* (the first prototype) — refused: errors land on the field, not on the id.

## R2. Dictionary references: one validator, two input objects, a reference computed once

**Decision**:

- The dictionary branch becomes one Python-mode chain used for every mode: a *before* step turns the container into its codes; each item is a container's code, an id object `{"id": code}` or a reference object (`code` required; `display_name`, `properties` allowed and ignored); the after step resolves codes to the canonical members and returns a new container (today's `_dictionary_one_value` / `_dictionary_many_value` logic, kept with its messages). The JSON-only branch goes away.
- The published validation schema is `anyOf` the id object and the reference object (an array of them for Many); serialization mode keeps the reference.
- `BaseEnumEntity` computes each declared value's reference once, after `_DeclaredValues` fills the catalogue, and keeps the map `code → reference` on the dictionary class. `_serialize_as_reference` and the relation serializers return a new dict built from it (`{"code", "display_name", "properties": dict(...)}`); `to_reference()` keeps returning a new dict.

**Rationale**: FastAPI and MCP validate parsed dicts in Python mode (#407 section 4), so the JSON-only branch is unreachable for them. A field typed by the dictionary already reads a reference by its code (4.4), so the relation does the same. The class-level map avoids a private attribute, which an entity cannot read today (#414), and leaves value equality untouched.

**Alternatives considered**: *a private attribute on the value* (the issue's wording) — refused for #414; *return the stored dict itself* — refused: a caller could change it.

## R3. Lifecycle: a schema hook on `Lifecycle`

**Decision**: `Lifecycle.__get_pydantic_core_schema__` (classmethod) returns: accept an instance of the declared lifecycle class as it is; a mapping with a non-empty string `code` (other keys ignored) builds `cls(code)` (the template's own check names the valid states); a bare string and a class without a template are refused. Serialization, JSON mode only: the current status's reference — `code`, `display_name`, and every other field of the status's JSON dump under `properties`, built on every call (5.3: statuses may be mutable). `__get_pydantic_json_schema__` publishes `{code: {"type": "string", "enum": [template codes]}, display_name, properties}`, `code` required on input, all three on output.

**Rationale**: the lifecycle class carries its template, so the hook has the codes; `cls(code)` already selects the declared status object, so 5.4 holds by construction.

## R4. Repository impact

| Search | Result |
| --- | --- |
| tests asserting the old dictionary messages | `test_dictionary_association_schema.py` (`exactly one 'id'`, twice) |
| examples asserting old messages/types | `examples/step_23_dictionaries/20_bare_code.py`, `23_missing_code.py`, `25_flat_fields.py`, `56_selection_transport.py` |
| code reading the `dictionary_relation` metadata | `relation_containers.py`; tests `test_dictionary_relation_containers.py`, `aoa-demo/tests/test_demo_dictionary_graph.py` — the metadata is kept |
| `Specialization` / `Generalization` | separate Pydantic models, not relation containers — unaffected |

Containers whose ids do not match the target's `id` type (an `int` id for a `str` target) are now refused; the closing check run finds every such test or example, and each is corrected in this work (FR-011).

## R5. Timings

Case 4.5 is measured and reported (SC-004), not asserted; the test pins the byte-identical JSON and that each reference is computed once (a counting probe on the value's dump during repeated serialization).
