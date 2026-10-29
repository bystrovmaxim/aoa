# certificates

Secrets this checkout reads with, kept on this machine and never in git. The folder's own `.gitignore` lets through only itself and this file; everything else placed here stays local.

## repo-graph-port/

The read keys of [`repo-graph-port`](../packages/maxitor/tools/repo_graph_port/README.md), one file per private history, named `<history id>.key`:

| File | Opens |
|---|---|
| `forecast-game-back.key` | `bystrovmaxim/gameoffer`, `packages/forecast-game-back/graph.json` on `main` |
| `forecast-adminpanel-back.key` | `bystrovmaxim/gameoffer`, `packages/forecast-adminpanel-back/graph.json` on `main` |

A key is one half of a pair. The key itself is the secret a reader sends in the header `X-Maxitor-History-Key`; it lives only here. The other half is the key's SHA-256, written to the port's histories config on the server (`/etc/aoa-repo-graph-port/histories.toml` on the stand); nothing can be read with a hash. A key opens its own history and nothing else, another history of the same repository included.

Both keys are issued to the name `maxitor`, the reader that will use them, with no expiry.

```bash
curl -H "X-Maxitor-History-Key: $(cat certificates/repo-graph-port/forecast-game-back.key)" https://repo-graph-port.aoa.run/api/v1/history/forecast-game-back
```

### Issuing, replacing, revoking

Keys are made on the server, never by hand; the command prints a key once, so it goes straight into its file:

```bash
ssh up2y-prod 'docker exec stand-repo-graph-port-1 repo-graph-port history key new --history <id> --name maxitor' > certificates/repo-graph-port/<id>.key
chmod 600 certificates/repo-graph-port/<id>.key
```

A key lost or shown somewhere: revoke it on the server, then issue a new one the same way.

```bash
ssh up2y-prod 'docker exec stand-repo-graph-port-1 repo-graph-port history key revoke --history <id> --name maxitor'
```

`repo-graph-port history key list` on the server shows each key's history, name and expiry — never a key or its hash.
