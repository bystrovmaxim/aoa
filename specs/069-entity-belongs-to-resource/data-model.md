# Data model: an entity belongs to one resource

## `_entity_info` (written by `@entity`)

| Key | Before | After |
|---|---|---|
| `description` | non-empty `str` | unchanged |
| `domain` | `BaseDomain` subclass or `None` | **removed** |
| `resource` | — | one concrete `BaseResource` subclass with `@meta(domain=...)`, not excluded from the graph model |

The entity's domain is `MetaIntentResolver.resolve_domain_type(_entity_info["resource"])`. A subclass without its own `@entity` inherits the dict, resource included.

## Rules

| Rule | Checked | Raises |
|---|---|---|
| `resource=` given | `@entity` | `EntityDecoratorError` |
| exactly one class, a `BaseResource` subclass, not excluded, with a `@meta` domain | `@entity` | `EntityDecoratorError` |
| no `domain=` | Python signature | `TypeError` |
| relation, inverse side, specialization, generalization, dictionary field: both ends one resource | model build, `validate_entity_resources` | `EntityResourceError` |
| a state type: every entity using it through `Lifecycle[...]` has one resource | model build, `validate_entity_resources` | `EntityResourceError` |
| every `Entity` node: exactly one `entity_resource` edge | graph build | `InvalidGraphError` |
| every `entity_relation`, `entity_reference`, `entity_specialization`, `parent_entity` edge: both ends one resource | graph build | `InvalidGraphError` |
| state nodes grouped by `lifecycle_class_id`: every host one resource | graph build | `InvalidGraphError` |

## Graph

| Edge | From | To | `relationship` | `is_dag` | `properties` | id |
|---|---|---|---|---|---|---|
| `entity_resource` (new) | `Entity` | `Resource` | `Aggregation` | `true` | `{}` | `<entity>\|entity_resource\|<resource>` |
| `domain` (entity) | `Entity` | `Domain` | `Aggregation` | `true` | `{}` | target is now the resource's domain |

`schema_version`: `1.5` → `1.6`.
