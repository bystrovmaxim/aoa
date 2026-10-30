# Contract: rooms on a history

Adds to `specs/028-maxitor-rooms/contracts/room-protocol.md` and `specs/029-maxitor-rooms-polish/contracts/room-protocol.md`.

## Opening

`/api/v1/rooms/new/live?…&history=<name>&version=<sha|live>` opens a room on a history, in place of `source`. The name carries no key. For a private history the tab adds `ticket=<room_ticket>` from `OpenHistoryAction` (research R18), on opening and on joining (`/api/v1/rooms/<id>/live?…&ticket=…`); a missing, used, expired or foreign ticket closes the socket with the "not found" code before `welcome`, so the tab learns nothing of the room. The tab's key is never sent over the socket; the server reads the room's pages with a remembered key the port still accepts, and when none is left, every tab is told "not found".

`<sha12>` is the first 12 hex characters of the version's commit, as in the page's `b`.

## Messages

| Direction | Message | Meaning |
|---|---|---|
| client → server | `{"type": "version", "b": "<sha12>" \| "live"}` | set the room's version; a value, never a step |
| server → room | `{"type": "version", "b": "<sha12>" \| "live", "by": "<participant>"}` | everyone moves to it; a page the version does not offer falls back as on joining |
| server → room | `{"type": "history_changed"}` | the history's list changed (a new version, tag, or description); read it again |
| server → tab | `welcome.room` gains `history` and `version` | a joiner gets the room's version, whatever their link said |

Refusals of `version`: a version the history does not have, or one it lists as refused → `{"type": "error", "reason": …}` to the sender alone; the room does not move. `live` in a history without Live → the same.

Two `version` messages at once: the server applies them in arrival order; the last wins, and everyone ends on it.
