# Data Model: Lifecycle Diagram Comparison

No stored data changes. These are the shapes the client works with.

## State (read from the server, marked by the client)

| Field | Source | Note |
|---|---|---|
| `id` | new, the graph node's id | identity across versions |
| `key`, `display_name`, `state_type`, `transitions`, `attributes` | as today | B's wins in the union |
| `diff` | client, Diff only | `added`, `removed`, `changed`, `unchanged` |

## Transition

| Field | Source | Note |
|---|---|---|
| `id` | new, the graph edge's id | `<source>\|lifecycle_transition\|<target>\|<from_state>` |
| `source`, `target` | as today | state keys |
| `diff` | client, Diff only | never changed by a new target: that is another id |

## Lifecycle diagram of a pair

The payload of today, with `states` and `transitions` the union sorted by `id`, `initial_state_keys` the union, and:

| Field | Note |
|---|---|
| `entry_exit` | client, Diff only: each dot's arrows with their status (research R5) |

Rules:

- Each element appears once, matched by `id`.
- A lifecycle in one version only gives a union of that version; all `added` or all `removed`.
- `counts`: states plus transitions, of what the filters leave.
- Entry and exit arrows are never in `counts` or the change list.

## Left panel row

`NodeRow` keeps `only: "a" | "b"` and gains `changed?: true`, set only on a `lifecycle_state_diagram` row present in both versions.

## Change list

A `GraphvizChange` per marked element: states by display name first, then transitions by the display names of their ends; one order, whatever is in view.
