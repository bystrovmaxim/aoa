# Data Model: Events in the graph and its JSON

## `Event` node

| Member | Value |
|---|---|
| `id` | dotted class path |
| `type` | `Event` |
| `label` | class name |
| `properties` | `{}` |

Exists when the class is named in an `events` or an `@emits`. Holds `field` edges to `Field` nodes (own fields only, with the written description or `""`) and `property` edges to `PropertyField` nodes.

## `Domain` node

Gains the required property `typed_events` (boolean): true when the domain has `events`, declared, inherited or empty.

## Edges

| Type | From | To | Relationship | `is_dag` | Properties | `id` |
|---|---|---|---|---|---|---|
| `domain_event` | `Domain` | `Event` | Aggregation | false | `{}` | `<domain>\|domain_event\|<event>` |
| `@emits` | `RegularAspect`, `SummaryAspect`, `Compensator`, `ErrorHandler`, `AccessDecide` | `Event` | Association | false | `{}` | `<method>\|@emits\|<event>` |

## Rules

- One `Event` node per class; a subclass of an event is another event.
- `@emits` edges come only from methods of the action's own class.
- In mode 3 each `@emits` target must be in the domain's `events`, or the build fails.
