# Data Model: Maxitor Rooms Polish

Changes only; everything not named here is as in [spec 028's data model](../028-maxitor-rooms/data-model.md).

## Room (server, `RoomRegistry`)

| field | change |
|---|---|
| `settings` | unchanged shape (page → name → value); now also filled by `seed` from the room's creator, only where empty |
| `created_by` | now read by `SeedPageSettingsAction`: only the creator may seed |

## Tab (server)

| field | change |
|---|---|
| `pointer`, `pointer_at` | a mouse pointer is sent in `catch_up` whatever `pointer_at` is (no ten-second window) |
| `focus` | **new** — the last `focus` the tab relayed (`dict`), kept so a follower who starts following gets it at once |

## Relayed messages

| type | fields | to whom |
|---|---|---|
| `pointer` | `x`, `y`, `kind` | tabs on the sender's page (unchanged) |
| `viewport` | `cx`, `cy`, `w`, `h` | tabs on the sender's page (unchanged; sent up to 20/s) |
| `focus` | `page`, `hover`, `tooltip`, `selection`, `panels` | **new** — tabs of participants who follow the sender |

`ElementRef = {kind: "node" | "row" | "edge" | "table", id: string}`; `panels = {sidebar: string[] (open branch ids), filter: "open" | "domains" | "kinds" | null, legend: boolean}`. Validation: `kind` from the list, `id` a string ≤ 512 chars, `sidebar` ≤ 200 ids; anything else drops the message.

## Client state

| name | where | change |
|---|---|---|
| page setting value | `lib/pageSettings.ts` | inside a room: room value, else default (own value no longer read) |
| follow playback | `rooms/follow.ts` | **new** — the last two viewport samples with arrival times; the drawn view is interpolated |
| focus | `rooms/focusStore.ts` | **new** — this tab's own hover/selection/panels, every participant's last focus, the follow target; `useShownPanel` for panels |
| Graphviz focus | `rooms/graphvizFocus.ts` | **new** — names the hovered row/line/node, holds back a follower's own mouse, replays the followed hover with `mouseenter`/`mouseleave`, shows the tooltip text in a label |

## Graph interchange (`aoa-action-machine`)

| node / edge | property | change |
|---|---|---|
| `EntityField` node | `field_type` | now the clean label (FR-030 table) |
| `EntityField` node | `field_annotation` | **new** — the full annotation, as `field_type` was before |
| entity relation edge | `optional` | **new** — `true` when the relation field admits `None` (annotation `X \| None` or default `None`) |

## `list-entities` rows (Maxitor)

| field | change |
|---|---|
| `fields[].type` | the clean label (cleaned again on the client for older services) |
| `fields[].annotation` | **new** — the full annotation, for the tooltip |
| `relations[].source_cardinality`, `target_cardinality` | one of `one`, `zero_one`, `zero_many`, `one_many`; reference lines fixed (`zero_many` at the referring table, `one` at the dictionary) |

## Field type label rule

Pure, total, idempotent: `clean(clean(x)) == clean(x)`. The table is FR-030 of the spec; an annotation no rule matches is shown as given, cut with `…` beyond the column width.
