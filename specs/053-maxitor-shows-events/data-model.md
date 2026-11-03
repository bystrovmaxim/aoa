# Data model: Maxitor shows events

Nothing new is stored; everything derives from the graph document.

- **EventsDiagram**: `domain_id`, `domain_label`, `typed_events`, `actions[]`, `bands[]`.
- **ActionRow**: `id`, `label`, `methods[]`; actions with no emitting method are left out.
- **MethodRow**: `id`, `label`, `kind` (the node's type), `emits[]` of event ids.
- **EventBand**: `name` (`in_vocabulary`, `not_emitted`, `emitted`), `events[]` of `{id, label}`.
- **EventCard**: `fields[]` with descriptions, `methods[]` with their actions, `domains[]` each with `in_vocabulary`.

Rules: an event appears once per diagram; with `typed_events` false only `emitted` exists; with true, `in_vocabulary` holds every vocabulary event this domain emits and `not_emitted` the rest.
