# The demonstrator stand

Three containers on one host, each behind the host's TLS front end:

| Service | Domain | On the host | What it is |
|---|---|---|---|
| `demo` | `dev.demo.aoa.run` | `127.0.0.1:8100` | the reference AOA service |
| `maxitor` | `dev.maxitor.aoa.run` | `127.0.0.1:${MAXITOR_PORT}` | Maxitor's front |
| `repo-graph-port` | `repo-graph-port.aoa.run` | `127.0.0.1:8103` | reads services' graph histories from their repositories; the only container that talks to GitHub |
| `maxitor-public-port` | — (not published) | — | Maxitor's own port: the `repo-graph-port` image with an empty config, through which Maxitor reads public GitHub links (`MAXITOR_PUBLIC_PORT`); no history, no key, no App; only Maxitor reaches it, on the stand's network |

One command deploys all three: `scripts/deploy_demonstrator_stand.sh`. It checks DNS and the TLS front end, builds the images, starts the containers, waits until each is healthy, adds the virtual hosts and certificates it lacks, checks every domain over HTTPS, and rolls back to the images that ran before on any failure. `--local` does the same on a laptop, on loopback, with no domains.

## What lives on the host, outside the repository

Nothing below ever enters the repository.

### `/etc/aoa-stand.env`

The stand's named configuration: copy [`.env.example`](.env.example) there and fill it in. The deploy script reads it.

### `/etc/aoa-repo-graph-port/histories.toml`

The histories the port serves. Start from [`repo-graph-port/histories.toml`](repo-graph-port/histories.toml):

```toml
[github]
app_id = 5525124
private_key_env = "GITHUB_APP_PRIVATE_KEY"
webhook_secret_env = "GITHUB_WEBHOOK_SECRET"

[[history]]
id = "orders"                       # how readers name it
host = "github"
repository = "owner/repo"           # a repository the GitHub App is installed on
branch = "main"
graph_file = "services/orders/graph.json"
```

The folder is mounted into the container writable: the key commands write key hashes into this file. A public repository needs no entry — it is read by a link to its graph file.

### `/etc/aoa-repo-graph-port/secrets.env`

The GitHub App's secrets, read only by the `repo-graph-port` container:

```bash
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE…\n-----END RSA PRIVATE KEY-----\n
GITHUB_WEBHOOK_SECRET=<the secret set in the App's webhook settings>
```

The private key goes on one line, its newlines written as `\n`; the port turns them back. From the downloaded `.pem`:

```bash
printf 'GITHUB_APP_PRIVATE_KEY=%s\n' "$(awk '{printf "%s\\n", $0}' maxitor-repo-graph-port.private-key.pem)" > /etc/aoa-repo-graph-port/secrets.env
```

Then add the `GITHUB_WEBHOOK_SECRET=` line, and `chmod 600 /etc/aoa-repo-graph-port/secrets.env`. To replace the key later, rewrite only its line, so the webhook's secret stays.

### `/etc/aoa-certificates/repo-graph-port/`

The read keys issued to Maxitor, one `<history id>.key` per private history, root only (`600`) — the same files as [`certificates/`](../../certificates/README.md) in the maintainer's checkout. They live outside `/opt/aoa-stand`, which every deploy replaces.

## The GitHub App

`maxitor-repo-graph-port`, App ID `5525124`, webhook `https://repo-graph-port.aoa.run/api/v1/history/events/github`. How it is set up — permissions, events, installation — is [the how-to page](../../docs/how-to/run-the-repo-graph-port.md#1-create-the-github-app). It is installed on `bystrovmaxim/gameoffer` only.

GitHub's webhook deliveries do not reach this host: no connection from GitHub's addresses arrives at its interface, while port 443 opens from elsewhere. Until the stand moves to another host, the port runs without events — a history is fetched again on a read when its last fetch is older than ten minutes.

The host's MTU is 1450. The port reaches GitHub through a network of its own, `egress`, with that MTU ([`docker-compose.host.yml`](docker-compose.host.yml)); with Docker's 1500 its TLS handshakes to GitHub stalled.

## After a deploy

The key commands run inside the port's container:

```bash
docker exec stand-repo-graph-port-1 repo-graph-port history check
```
```bash
docker exec stand-repo-graph-port-1 repo-graph-port history key new --history orders --name maxitor > /etc/aoa-certificates/repo-graph-port/orders.key
```

`check` says, for each history, whether its graph file is on its branch as the port reads it — with the App's token. `key new` prints a key once, so it goes straight into its file; hand it to its holder only. `key list` shows names and dates; `key revoke --history <id> --name <who>` removes one.
