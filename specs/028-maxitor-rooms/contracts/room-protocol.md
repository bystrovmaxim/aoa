# Contract: the room connection

`wss://<maxitor>/api/v1/rooms/{room_id}/live?participant=<id>&tab=<id>&participant_name=<name>&start_page=<page key>[&source=<graph-json URL>]`

`room_id` `new` opens a room for `source` (required then) with the connecting participant as its creator; any other id joins that room and ignores `source`. The name and page are `participant_name` and `start_page` because a message's own fields `name` (`rename`, `setting`) and `page` (`page`, `setting`) must not collide with connection values.

Every message is one JSON object with a `type`. Coordinates are diagram coordinates (data-model.md). Names in messages are the participants' own; they never reach the log.

## Opening

The query runs `JoinRoomAction`. An origin is accepted when it is empty, listed in `MAXITOR_ROOM_ORIGINS`, or has the same host as the request's `Host` header. It refuses with a close code the page turns into one sentence:

| Code | Reason | Page says |
|---|---|---|
| `4404` | `room ended` | *This room has ended* (FR-014) |
| `4409` | `room full` | *This room is full (20 people)* (FR-063) |
| `4422` | `invalid name` | the name dialog shows the rule (FR-011) |
| `4403` | `origin not allowed` | *This page cannot join the room* (FR-016) |
| `4503` | `too many rooms` | *Too many rooms are open on this server; try again later* (FR-015) |
| `4502` | `the service's graph cannot be built now` | the same sentence; only when opening a room (**Reload** in a room answers `refused` 4502 and keeps the connection, FR-065) |
| `4413`, `4429`, `4008` | adapter limits (size, rate, slow client) | *The connection was closed: <reason>* (FR-015) |

On success the server sends `welcome` to the newcomer and `joined` to everyone else (or nothing, when it is a return within two minutes, FR-062).

## Client → server

| `type` | Fields | Action | Notes |
|---|---|---|---|
| `page` | `page`, `build`, `fingerprint`, `layout_hash`, `settings_digest` | `ReportPageAction` | on arrival, navigation and every redraw; also marks activity (FR-013, FR-090) |
| `activity` | `visible` | `ReportPageAction` | tab shown/hidden or active again (FR-013, FR-044) |
| `setting` | `page`, `name`, `value` | `SetPageSettingAction` | "set to", never toggle (FR-031) |
| `rename` | `name` | `RenameParticipantAction` | FR-061 |
| `follow` | `target` | `FollowAction` | refused with `follow_refused` when it would close a circle (FR-054) |
| `stop_following` | — | `StopFollowingAction` | FR-051 |
| `leave` | — | `LeaveRoomAction` | **Leave room**; the socket then closes (FR-019) |
| `reload` | — | `ReloadSourceForRoomAction` | **Reload** in a room (FR-065) |
| `pointer` | `kind`, `x`, `y` | relayed | ≤ 20 / s, only when moved (FR-043); never logged (FR-068) |
| `viewport` | `cx`, `cy`, `w`, `h` | relayed | on change, ≤ 10 / s; with pointers a tab stays ≤ 30 messages / s (FR-043) |

## Server → client

| `type` | Fields | When |
|---|---|---|
| `welcome` | `you` (id, colour), `room` (source, participants, page settings of every page, follow links, `created_by`), `server_build`, `fallback_page` | after a successful join; `fallback_page` is set when the link's page does not exist for the room's source (FR-010) |
| `joined` / `left` | participant (id, name, colour) | someone joins or leaves; not sent for a return within two minutes (FR-027, FR-062) |
| `presence` | participant id, `page`, `visible`, `away` | active page or visibility changed; `away` while the connection is lost (FR-013, FR-044, FR-062) |
| `renamed` | participant id, `name` | FR-061 |
| `setting` | `page`, `name`, `value`, `by` | a setting changed (FR-030) |
| `follows` | the full set of follow links | after any follow change (FR-023, FR-056) |
| `follow_refused` | `target`, `reason` | FR-054 |
| `pointer` / `viewport` | participant id + fields | relayed; only to tabs on the same page. A tab arriving on a page (joining, or a `page` report naming another page) is also sent, at once, each participant's last `viewport` there and their mouse `pointer` if it moved in the last 10 s, so going to someone does not wait for them to move (FR-050; commit 13) |
| `check` | `build`: ok / reload; `fingerprint`: ok / reread; `layout`: ok / off | answer to `page` (FR-091 … FR-093) |
| `graph_changed` | `fingerprint` | the room's source was rebuilt (FR-076) |
| `refused` | `code`, `reason` | a message action refused |
| `error` | `reason` | a message that could not be read |

## Order and delivery

- Durable messages (everything except `pointer`, `viewport`) reach each tab in the order the server produced them.
- `pointer` and `viewport` are volatile: a slow tab receives the newest of each per participant, never a backlog (FR-043, FR-068).
- After a reconnect, the client asks nothing: the server sends a fresh `welcome`.
