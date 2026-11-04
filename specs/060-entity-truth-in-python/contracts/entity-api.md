# Contract: the public behaviour that changes

The signatures do not change. What a caller observes does:

| Call | Today | After |
| --- | --- | --- |
| `loaded.__pydantic_serializer__` (any `__dunder__`) | the entity's attribute | `AttributeError` |
| `loaded.name` (an ordinary name) | the entity's attribute | the same |
| `entity.model_dump()` with a dictionary reference | `KeyError: 'code'` | the container |
| `entity.model_dump(mode="json")` with a loaded structural relation | `{}` for the relation | `PydanticSerializationError` naming the container, until #407 |
| `copy.deepcopy(loaded)`, `model_copy(deep=True)` | the entity | a container of the same class |
| `copy.copy(container)`, `pickle` round trip | `AttributeError: … is frozen` | an equal frozen container |
| `partial(id=…).field_with_default` | the default | `FieldNotLoadedError` |
| `partial(id=…).model_dump()` | includes defaulted fields | only loaded fields |
| `partial()` with a factory that needs a missing field | the factory's error | an instance with nothing loaded |
| `partial(…).model_copy(update={f: v}).is_field_loaded(f)` | `False` | `True` |
| `partial(every field) == full` | `True` | `True` |
