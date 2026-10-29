# Data Model: Maxitor Opens a History and Shows Any Version

## History address (what the user types)

| Form | Example | Key |
|---|---|---|
| Private | `https://repo-graph-port.aoa.run/api/v1/history/orders#key=<key>` | in the fragment (R1) |
| Public | `https://github.com/owner/repo/blob/main/graph.json` | none |
| Live only (M1) | the service's own address, `https://orders.example.com` | none |

Parsed into `{port, id | link, key?}`. The address without the key is the history's **name** inside Maxitor: the `history` parameter, the room's `history`, the `HistoryStore` key.

## Page address

In the browser's address bar: `?history=<address without key>&b=<first 12 hex of the commit | live>&view=…&domain=…&node=…&host=…&room=…` — never the key (FR-010a).

A link Maxitor makes (**Copy link**, the room's link): the same plus `#key=<key>`. Opened, the page moves the key to `sessionStorage` for the tab and removes the fragment.

`source` is absent while a history is open. `b` the history does not have → its default version, and the address is rewritten (FR-022).

## HistoryEntry (server, `HistoryStore`, per history name)

| Field | Meaning |
|---|---|
| `name` | the history's address without the key |
| `port`, `id` or `link` | where it is read |
| `title` | the service's name shown in the picker (`id`, or `owner/repo` for a public link) |
| `repository` | from `describe`; links `#123` in messages (R12) |
| `host` | `github` or `local` |
| `live` | the Live service's address, or none |
| `reader` | the key's name, for the log; none for a public link |
| `versions` | the port's list, oldest first ([port contract](https://github.com/bystrovmaxim/aoa/blob/main/specs/036-repo-graph-port/data-model.md#version)) |
| `etag` | the port's `ETag` of `versions` |
| `last_checked`, `checking` | as on `GraphEntry` |
| `keys` | in memory only, the keys the port accepted for it while a tab of it is open, newest first; never logged, never in `repr` (R18) |

## GraphEntry (existing) — one addition

| Field | Meaning |
|---|---|
| `immutable` | true for a version's graph: never due for a check (FR-006) |

## Access record (`HistoryAccess`)

`(history name, SHA-256 of key) → accepted_at`. Valid 30 s (R6). Never holds the key.

## Room ticket (`HistoryAccess`)

`ticket → (history name, SHA-256 of key, expires_at)`; 128 random bits, 60 s, one use (R18).

## Version as the client shows it

Derived from the port's `Version`:

| Field | Rule |
|---|---|
| `name` | R10: release tag · `<release> · #<pr>` · `#<pr>` · short commit · `Live` |
| `isRelease` | a tag with `release` |
| `flags` | tags without a release |
| `tooltip` | `#<pr> <title>`, date, `<nodes> nodes · <edges> edges`, tags |
| `message` | `pr.title + "\n\n" + pr.body`, or `message`; none for Live |
| `refused` | the port's reason, or none |

## Mode (client, derived)

`M1 … M7` by `(has history, has live, number of versions)` — [contracts/ui.md](contracts/ui.md#modes).

## Room — two additions

| Field | Meaning |
|---|---|
| `history` | the history's name, or none for a room on a service |
| `version` | the first 12 hex of the commit, or `live`; the room's graph is its source; last `version` message wins |

## Recent record (client, `localStorage`)

`{address, kind: "service" | "history", name?, versions?, live?}`; up to 10; old string records read as `kind: "service"`.

## Port config — one addition

`[[history]] live = "<http(s) address>"`, optional. `describe` adds `live?` and `reader?`.
