# Contract: room protocol changes

Extends [028 room-protocol.md](../../028-maxitor-rooms/contracts/room-protocol.md). Route, close codes and every message not named here are unchanged.

## Client → server

| message | when | server |
|---|---|---|
| `{type: "seed", page, settings: {name: value}}` | once per own setting (one setting per message; a value over 4 KB is not sent), right after the welcome of a room the tab opened | `SeedPageSettingsAction`: from the creator only; each value applied only if the room has none for `page`/`name`; each applied value broadcast as `setting` with `by` = creator. From anyone else: ignored with a `security` warning. Over 4 KB: `4413` as for any message |
| `{type: "focus", page, hover, tooltip, selection, panels}` | on change, at most 10/s | relayed, never an action, never logged; validated as in [data-model.md](../data-model.md); sent only to tabs of participants who follow the sender |
| `{type: "viewport", cx, cy, w, h}` | unchanged shape; now at most 20/s | unchanged |

## Server → client

| message | change |
|---|---|
| `{type: "focus", participant, page, hover, tooltip, selection, panels}` | **new** — only to followers of `participant`; also sent once when a tab starts following someone who has a focus |
| `{type: "pointer", …}` in `catch_up` | the last mouse pointer of every present participant on the page, whatever its age |

## Limits

| limit | before | now |
|---|---|---|
| messages per second per connection (rooms route) | 40 | 80 |
| message size | 4 KB | 4 KB |

## Following

- A follower draws the followed person's view interpolated between the last two viewports, one sample interval behind (research R3), and settles exactly on the last one.
- While following, the follower's diagram shows the followed person's `focus`; the follower's own hover and clicks on the diagram do not change it. Esc, the stop button or panning stops following (unchanged) and returns hover, selection and panels to the follower, starting from what was shown.
