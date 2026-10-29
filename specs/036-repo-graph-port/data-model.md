# Data Model: Maxitor Reads a Graph's History from Its Repository

## History (in the histories config)

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique; names the history in the port's routes and logs. |
| `host` | yes | `github` today; `local` for a path (tests, local runs). |
| `repository` | yes | `owner/name` on the host, or a local path. |
| `branch` | yes | The branch whose first parents are the versions. |
| `graph_file` | yes | The graph file's path in the repository. |
| `keys` | no | Read keys; none means the history opens only as a public link. |

## Read key

| Field | Meaning |
|---|---|
| `name` | Who holds it; written to logs instead of the key. |
| `sha256` | SHA-256 of the key; the key itself is never stored. |
| `expires` | Optional date; after it the key is refused like an unknown one. |

A key: 256 random bits, base64url, printed once by `repo-graph-port history key new`.

## Version

| Field | Meaning |
|---|---|
| `sha` | The commit, by first parent, that changed the graph file. |
| `date` | The commit's date, UTC, ISO 8601. |
| `pr` | `{number, title, body, url}` from the host; absent when the commit had no pull request. |
| `message` | The commit's message, when there is no `pr`. |
| `tags` | `[{name, release: {title, url} | null}]` — the repository's tags placed on this version. |
| `nodes`, `edges` | Counts of its graph. |
| `refused` | The reason when its graph does not pass the protocol's schema; absent otherwise. |
| `digest` | Added by #303; absent until then. |

Immutable by `sha`: `date`, `nodes`, `edges`, `refused`, the graph. Refreshed: `pr` (an edit), `tags` (a new tag).

## Tag placement

For each tag on the branch's first-parent chain: the newest version whose commit is an ancestor-or-self of the tag's commit. A tag off that chain is not placed.

## Reader context (from the auth coordinator)

| Field | Value |
|---|---|
| `user.user_id` | the key's `name`, or none for a public link |
| `user.roles` | `HistoryReaderRole` with a key; `GuestRole` without |
| the history it opens | the `id` the key belongs to |

## Cache entries

| Entry | Key | Lives |
|---|---|---|
| mirror | repository | until removed; fetched by webhook or after the fallback interval |
| version facts + graph bytes | `(repository, sha)` | forever |
| pull request of a version | `(repository, sha)` | until an edit webhook or the fallback interval |
| tags with releases | repository | until a tag webhook or the fallback interval |
