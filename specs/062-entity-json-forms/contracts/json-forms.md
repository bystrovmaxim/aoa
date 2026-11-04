# Contract: the JSON forms a caller observes

Signatures do not change. Python-mode dumps do not change.

| Call | Today | After |
| --- | --- | --- |
| `order.model_dump(mode="json")`, unloaded One + Many | `PydanticSerializationError` | `…'customer': {'id': 'c1'}, 'lines': {'ids': ['l1', 'l2']}` |
| loaded One | `PydanticSerializationError` | `{'id': 'c1', 'entity': {'id': 'c1', 'name': 'Ann'}}` |
| `OrderCoreEntity.model_json_schema()` | `PydanticInvalidForJsonSchema` | builds; relations closed, targets by `$ref` |
| `model_validate_json` / `model_validate` of the forms | `ValidationError` | the containers, with typed ids and the loaded state |
| id of the wrong type | accepted as is | `ValidationError` at `<field>.id` |
| FastAPI `{"currency": {"id": "eur"}}` | `422 is_instance_of` | `200` |
| MCP `{"currency": {"id": "eur"}}` | `ValidationFieldError` | `CompositeOne(id='eur', loaded)` |
| `PriceParams.model_validate({"currency": {"id": "eur"}})` | `ValidationError` | accepted |
| reading back `{"code": "eur", …}` | `ValidationError` | `EUR`, label from the catalogue |
| a bare code `"eur"` for a dictionary relation | refused (`is_instance_of`) | refused, with a message naming the accepted forms |
| ten references to JSON | 25.3 µs | faster, byte-identical |
| lifecycle JSON dump | `PydanticSerializationError` | `{'code': 'draft', 'display_name': 'Draft', 'properties': {...}}` |
| `app.openapi()` with a lifecycle Result | `PydanticInvalidForJsonSchema` | builds; `code` enum of the template |
| `{"lifecycle": {"code": "draft"}}` | `ValidationError` | `OrderLifecycle("draft")` |
