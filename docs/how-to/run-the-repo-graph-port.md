# Run the repo-graph-port on a server

`repo-graph-port` reads services' graph histories from their repositories and serves them ([its README](../../packages/maxitor/tools/repo_graph_port/README.md)). This page sets it up on a server so that it reads your private repositories live and hears every push at once. You need: a server with Docker (or Python 3.12 and `git`), an HTTPS address for it, and the repositories, each with its graph file committed on its branch by [`graph-builder`](../../packages/maxitor/tools/graph_builder/README.md).

## 1. Create the GitHub App

GitHub → *Settings* → *Developer settings* → *GitHub Apps* → *New GitHub App*:

| Field | Value |
|---|---|
| Homepage URL | any full URL, e.g. your Maxitor's |
| Callback URL, Setup URL | empty — the port never signs users in |
| Request user authorization (OAuth), Device flow | off |
| Webhook | active; URL `https://<your address>/api/v1/history/events/github`; a secret from `openssl rand -hex 32` |
| Repository permissions | *Contents*: read-only, *Pull requests*: read-only (*Metadata*: read-only comes with them) |
| Subscribe to events | *Push*, *Create*, *Pull request* |

Keep the webhook's secret: never paste it into a chat, an issue or a screenshot. After *Create GitHub App*, note the **App ID**, then open *Credentials* → *Key pairs* and generate a private key — a `.pem` file downloads. Pass it on by its file name only, never by pasting or attaching its contents. Then *Install App* → your account → *Only select repositories* → the repositories whose histories the port serves.

## 2. Write the histories config

`histories.toml` — the App, and one `[[history]]` per graph file:

```toml
[github]
app_id = 5525124
private_key_env = "GITHUB_APP_PRIVATE_KEY"
webhook_secret_env = "GITHUB_WEBHOOK_SECRET"

[[history]]
id = "orders"
host = "github"
repository = "owner/repo"
branch = "main"
graph_file = "services/orders/graph.json"
```

A repository with several graph files gets one history per file. A public repository needs no entry: it is read by a link to its graph file.

## 3. Put the secrets in the environment

The port reads the App's private key and the webhook's secret from the variables the config names. In an environment file the key goes on one line, its newlines written as `\n`:

```bash
printf 'GITHUB_APP_PRIVATE_KEY=%s\n' "$(awk '{printf "%s\\n", $0}' app.private-key.pem)" > secrets.env
echo 'GITHUB_WEBHOOK_SECRET=<the secret from step 1>' >> secrets.env
chmod 600 secrets.env
```

## 4. Run it

With Docker, from a checkout of this repository:

```bash
docker build -f packages/maxitor/tools/repo_graph_port/Dockerfile -t repo-graph-port .
```
```bash
docker run -d --name repo-graph-port -p 127.0.0.1:8103:8102 --env-file secrets.env -e MAXITOR_HISTORIES=/config/histories.toml -v "$PWD/config:/config" -v repo-graph-port-cache:/var/cache/repo-graph-port repo-graph-port
```

`config/` holds `histories.toml` and is mounted writable: the key commands write into it. Put your HTTPS front end before `127.0.0.1:8103`, passing `X-Forwarded-For` and allowing request bodies of 25 MB (GitHub's webhooks). Without Docker: `pip install "maxitor[repo-graph-port]"`, then `MAXITOR_HISTORIES=histories.toml repo-graph-port` with the secrets in its environment (`REPO_GRAPH_PORT_HOST`, `REPO_GRAPH_PORT_PORT` choose where it listens).

A host whose network MTU is below 1500 (a cloud VM often has 1450) needs the same MTU on the container's network: with Docker's default 1500, connections to GitHub stall in the TLS handshake and a clone times out. Give the port a network of its own, e.g. `docker network create --opt com.docker.network.driver.mtu=1450 egress`, and run it with `--network egress`; `ip link` shows the host's MTU.

The demonstrator stand of this repository runs it this way at `https://repo-graph-port.aoa.run`; [its README](../../deploy/stand/README.md) says what lives where on that host.

## 5. Check, then issue keys

```bash
docker exec repo-graph-port repo-graph-port history check
```

One line per history, read as the port reads it — with the App's token:

| Line | Means |
|---|---|
| `ok  orders: ok` | the graph file is on its branch |
| `FAIL orders: the App is not installed on owner/repo` | install the App on that repository (step 1) |
| `FAIL orders: no services/orders/graph.json on main` | the file is not committed on that branch yet |
| `FAIL orders: no [github] App to read a private repository with` | the config has no `[github]` table, or its variables are empty |

Then one key per reader of each history:

```bash
docker exec repo-graph-port repo-graph-port history key new --history orders --name anna --expires 2027-06-01
```

The key is printed once; only its hash is written. Send it straight into a file that never enters git — this repository keeps such files in [`certificates/`](../../certificates/README.md) — and hand it to its holder only:

```bash
docker exec repo-graph-port repo-graph-port history key new --history orders --name anna > certificates/repo-graph-port/orders.key
```

 `key list` shows names and dates; `key revoke --history orders --name anna` removes one; a changed config needs no restart.

## 6. Read a history

```bash
curl -H "X-Maxitor-History-Key: <anna's key>" https://<your address>/api/v1/history/orders/versions
```
```bash
curl -G --data-urlencode "link=https://github.com/owner/open-repo/blob/main/graph.json" https://<your address>/api/v1/history/public/versions
```

Merge a pull request that changes the graph file: GitHub's webhook reaches the port, and the next read has the new version. The App's page → *Advanced* → *Recent Deliveries* shows each webhook and the port's answer, `{"changed": ["orders"]}` — the histories it changed, and none for a push that touched no graph file.

If *Recent Deliveries* shows only timeouts and no request reaches your HTTPS front end, GitHub cannot connect to your host — check that its addresses (`https://api.github.com/meta`, `hooks`) are let in. The port still serves fresh histories without webhooks: a read fetches the repository again when its last fetch is older than `MAXITOR_HISTORY_REFRESH_SECONDS` (600), so a merge shows within ten minutes.
