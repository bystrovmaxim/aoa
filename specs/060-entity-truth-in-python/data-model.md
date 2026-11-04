# Data model: An entity tells the truth in Python

No new types. Two existing ones change behaviour.

## Relation container (`BaseRelationOne`, `BaseRelationMany` and their six concrete classes)

| Aspect | Rule |
| --- | --- |
| Identity | `id` (One) or `ids` (Many), always present |
| Loaded state | `entity` set (One); `entities_loaded` (Many) |
| Attribute forwarding | an ordinary name goes to the loaded entity; a name that starts and ends with `__` is never forwarded and raises `AttributeError` |
| Copy | `copy.copy` gives an equal container of the same class, rebuilt through the constructor |
| Deep copy | a new container of the same class: same ids, deep-copied entities, same loaded state |
| Pickle | rebuilt through the constructor; equal to the original and still frozen |
| Equality | unchanged: class and ids |

## Partial entity (`BaseEntity.partial(**fields)`)

| Aspect | Rule |
| --- | --- |
| Loaded field | a declared field the instance holds in its own `__dict__` |
| Construction | only the given fields are set; no default and no default factory of another field runs |
| Reading an unloaded field | `FieldNotLoadedError` (an `AttributeError`) |
| Dump | only loaded fields, in both modes |
| `model_copy(update=...)` | updated fields become loaded; the others stay unloaded |
| A partial with every field | indistinguishable from the full entity, `==` included |
| Full entity | unchanged: every field loaded, defaults applied |

State transition of a field: *unloaded* → *loaded* only by being given to `partial()` or to `model_copy(update=...)`; never by being read.
