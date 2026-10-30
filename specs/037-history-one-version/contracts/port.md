# Contract: what `repo-graph-port` adds

## Config

```toml
[[history]]
id = "orders"
host = "github"
repository = "owner/repo"
branch = "main"
graph_file = "services/orders/graph.json"
live = "https://orders.example.com"     # optional: the running service whose graph is Live
```

`live`, when given, MUST be an `http` or `https` URL with a host; otherwise the file is refused like any field out of shape (exit code `2` for `check`).

## `describe`

`GET /api/v1/history/{id}` and `GET /api/v1/history/public?link=…` answer, besides today's fields:

| Field | When | Meaning |
|---|---|---|
| `live` | the history's entry names one | the Live service's address |
| `reader` | opened with a key | the key's `name` |

Both are absent for a public link.

## Security events

| When | Level, channel | Line |
|---|---|---|
| a wrong key (unknown, revoked, expired, another history's) | `box.warning`, `security` | `Wrong key for history orders from 203.0.113.7` |
| a webhook with a wrong signature | `box.warning`, `security` | `Webhook with a wrong signature from 140.82.112.1` |
| a client blocked: more than 10 wrong keys in a minute | `box.critical`, `security` | `Blocked 203.0.113.7 for a minute: 11 wrong keys` |

Never the key, its hash or the signature. The block itself is unchanged from #288.

## `history` (the list of versions)

`GET /api/v1/history/{id}/versions` answers, besides each version's fields of #288:

| Field | Meaning |
|---|---|
| `pr` | as before, plus `author` and `avatar` when the host tells them (GitHub); taken from the merge commit's message (`Merge pull request #N from …`, then title and body) or a squash commit's first line (`Title (#N)`) when the host does not tell it — a local repository included; GitHub's merge line is never kept |
| `contribution` | from git: `author` (the first author of a merged branch, or the commit's), `co_authors`, `merged_by` (a merge commit's author; `null` for a squash or direct commit), `files`, `additions`, `deletions` against the first parent |
| `change` | against the previous version's graph: `added` and `removed` nodes by `type`, `changed` (nodes kept whose type, label or properties differ), `links: {added, removed}` (edges by `id`, or by source, relationship and target) |

`contribution` and `change` belong to the commit and are read from git once, then from the cache.

And a new list beside `versions`:

| Field | Meaning |
|---|---|
| `proposals` | the pull requests still open into the branch whose graph differs from the newest version's, oldest number first, each shaped like a version, its `pr` carrying `state`: `open` (review required), `approved` or `changes_requested`. On GitHub from the open pull requests and their reviews (each reviewer's last word; drafts left out), kept for the freshness interval; in a local repository from `refs/pull/<n>/head` not yet in the branch, state `open`. A pull request closed without being merged is not listed |

## `version`

`GET /api/v1/history/{id}/versions/{sha}` also serves the head of a pull request the repository keeps (`refs/pull/<n>/head`), so a reader looks at it before it is merged.

Nothing else changes; the webhook and every refusal stay as in `specs/036-repo-graph-port/contracts/actions.md`.
