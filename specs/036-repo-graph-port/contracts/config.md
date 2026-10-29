# Contract: the histories config and the key commands

The file named by `MAXITOR_HISTORIES`; reread when it changes.

```toml
[github]
app_id = 123456
private_key_env = "GITHUB_APP_PRIVATE_KEY"     # the App's private key, from the environment
webhook_secret_env = "GITHUB_WEBHOOK_SECRET"   # the webhooks' secret, from the environment

[[history]]
id = "orders"
host = "github"
repository = "owner/repo"
branch = "main"
graph_file = "services/orders/graph.json"

[[history.keys]]
name = "anna"
sha256 = "9c1e…"
expires = "2027-06-01"
```

Commands (`maxitor history …`, the core's CLI):

| Command | Does |
|---|---|
| `key new --history <id> --name <who> [--expires <date>]` | prints a new key once; writes only its hash, name and expiry |
| `key revoke --history <id> --name <who>` | removes that key |
| `key list [--history <id>]` | names and expiry dates, never keys or hashes |
| `check` | the config is valid; the App reaches each private repository; each history's graph file exists on its branch |

Exit codes: `0` ok, `1` a check failed, `2` the config is refused.
