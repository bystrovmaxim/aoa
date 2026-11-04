# Data model: Every entity value has one JSON form

No new public types. Three existing ones get a JSON form.

## Relation to an ordinary entity (`AssociationOne` … `CompositeMany`)

| Aspect | Rule |
| --- | --- |
| JSON form, One | `{"id": <id>}` not loaded; `{"id": <id>, "entity": <target JSON>}` loaded |
| JSON form, Many | `{"ids": [...]}` not loaded; `{"ids": [...], "entities": [...]}` loaded (zero rows: `"entities": []`) |
| Python dump | the container |
| Input | the container of the declared class, or the JSON form as a dict, in every mode |
| Ids | validated by the target's `id` annotation; strict `str \| int` when the target has no `id` |
| Target inside | an instance as it is; a dict → `partial(**present fields)`, each field validated by its annotation |
| JSON Schema | closed object; `id`/`ids` typed; `entity`/`entities` by `$ref` to the target |
| Validation result | a new container of the declared class |

## Dictionary reference (the six containers with a `BaseEnumEntity` target)

| Aspect | Rule |
| --- | --- |
| JSON form | the declared value's reference `{"code", "display_name", "properties"}`; Many: an array |
| Input item | a container's code, `{"id": code}`, or `{"code": …[, "display_name", "properties"]}` (label and properties from the catalogue) |
| JSON Schema | validation: `anyOf` id object, reference object (array for Many); serialization: the reference |
| Reference cache | `code → reference` on the dictionary class, filled once after the catalogue; readers get a new dict |

## Lifecycle field

| Aspect | Rule |
| --- | --- |
| JSON form | `{"code", "display_name", "properties"}` of the current status, built on every call |
| Python dump | the lifecycle |
| Input | the lifecycle instance, or `{"code": …}` (other keys ignored); a bare string refused |
| Read back | `cls(code)`: the declared status object of the template |
| JSON Schema | `code` an enum of the template's codes; input requires `code`, output all three |
