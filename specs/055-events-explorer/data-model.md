# Data model: Events explorer

## Wire (`events_explorer`)

| Field | Shape | Notes |
|---|---|---|
| `domains[]` | `{id, label, short_label, accent_color, vocabulary: bool}` | every domain; `vocabulary` true for an empty one too |
| `actions[]` | `{id, label, short_label, domain_id}` | every action; `domain_id` empty when it has none |
| `events[]` | `{id, label, fields: [{name, type, description}]}` | every event |
| `holds[]` | `{domain_id, event_id}` | vocabulary pairs (`domain_event`) |
| `emits[]` | `{action_id, method_id, method, kind, event_id}` | one per `@emits` of a method of the five kinds |

All lists sorted by id; one graph gives one answer. A document older than 1.3 gives domains and actions with empty `events`, `holds`, `emits`.

In Diff the client adds `diff: "added" | "removed" | "changed" | "unchanged"` to each element and to each pair.

## Derived on the client

- **Coverage of a domain**: with events when `vocabulary` or one of its actions emits.
- **Standing of an event**: `not_emitted` when no `emits` names it; else `emitted_held` when a `holds` names it; else `emitted_free`.
- **Count of a domain**: `vocabulary` → "N in vocabulary" / "empty vocabulary"; else emitted events → "N emitted · no vocabulary"; else "no events".
- **Neighbours of a port**: domain→events = held ∪ emitted by its actions; domain→actions = all its actions; event→actions = its emitters; event→domains = holders, then emitters' domains; action→events; action→domain.

## Screen state

| Name | Value | Rules |
|---|---|---|
| `mode` | `domains` \| `events` \| `actions` | change closes every port and fits |
| `opened` | `["<kind>:<id>><port>"]` | a port of a node not shown is kept and ignored |
| `domains` | ids or `null` (all) | as ERD |
| `off` | `["<section>:<row>"]` | `coverage:*` applies in Domains mode only; `methods:<kind>` removes that kind's `emits` |
| `paint` / `paint_diff` | a section id | falls back to `domains` when its section is not on the panel |
| `layout` | `dot_lr` \| `dot_tb` | |

**Layer** of a node: 0 for the first layer, else one more than the node whose open port reached it first (breadth first). Ports: layer 0 both; layer 1 the one toward the kind not yet on the path; layer ≥ 2 the joining one toward the first layer's kind. A **link** is drawn when its ends are on neighbouring layers, or when an open joining port of one end asks for it.
