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

Nothing else changes; `history`, `version`, the webhook and every refusal stay as in `specs/036-repo-graph-port/contracts/actions.md`.
