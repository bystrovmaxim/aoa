# repo-graph-port

**A service's graph history, read from the repository that keeps its graph file.**

A service that keeps its model graph in a file beside its code (see [`graph-builder`](../graph_builder/README.md)) has the graph's whole history in git: every merge that changed the file is a version. `repo-graph-port` is the service that reads it and serves it — the versions, each with its pull request and the repository's tags, and the graph of any version, byte for byte. Maxitor shows and compares what it serves; anything else may read it too.

It is the only part of Maxitor that talks to GitHub. A private repository is read with a GitHub App installed on it; a public one needs nothing.

```bash
pip install "maxitor[repo-graph-port]"
MAXITOR_HISTORIES=histories.toml repo-graph-port
```

It listens on `127.0.0.1:8102` (`REPO_GRAPH_PORT_HOST`, `REPO_GRAPH_PORT_PORT`). Setting it up on a server — the App, the config, the secrets, the keys — is [the how-to page](../../../../docs/how-to/run-the-repo-graph-port.md).

## What a version is

A history is one graph file on one branch of one repository. Its versions are the commits of that branch, by first parent, that changed the file — one per merged pull request, plus any commit made on the branch itself; commits inside a pull request's branch are not versions. Each version carries:

- `sha` and `date` (UTC);
- `pr` — the pull request's number, title, description and link (on GitHub also its author's login and picture), or `message` — the commit's message when there is none. With no host to ask — a local repository — the pull request is read from the merge commit's message (`Merge pull request #N from …`, then the title and description) or a squash commit's first line (`Title (#N)`);
- `contribution` — from git: who made it (the first author of a merged branch, or the commit's), how many others, who merged it (the merge commit's author; none for a squash or direct commit), and its size against its first parent: files, lines added and removed;
- `change` — what it did to the previous version's graph: nodes added and removed by kind, nodes changed, links added and removed;
- `tags` — the repository's tags placed on it, each with its release's title and link: a tag on a later commit that did not change the graph belongs to the version before it;
- `nodes` and `edges`, or `refused` — why the file is not a graph of the protocol's version it claims.

## Two ways to name a history

- **Configured** — a private repository, named by an `id` in the histories config; a reader sends a read key in the header `X-Maxitor-History-Key`. A key opens one history and nothing else.
- **By link** — a public repository's graph file, `https://github.com/<owner>/<repo>/blob/<branch>/<path>`, given as `link=` with no key and no config.

## The routes

| Route | Answer |
|---|---|
| `GET /api/v1/history/{id}` | `{id, repository, branch, graph_file, versions, newest}` |
| `GET /api/v1/history/{id}/versions[?after=<sha>]` | `{versions: […], proposals: […]}`, oldest first; `after` returns only newer ones; an `ETag`, and `304` to a reader that holds it. `proposals` are the pull requests still open into the branch whose graph differs from the newest version's, each shaped like a version with `pr.state` — `open`, `approved` or `changes_requested`: on GitHub from its open pull requests and their reviews, drafts left out; in a local repository from each `refs/pull/<n>/head` not yet in the branch |
| `GET /api/v1/history/{id}/versions/{sha}` | the graph file as committed, `Cache-Control: immutable` — a version's, or an open pull request's head |
| `GET /api/v1/history/public…?link=…` | the same three, for a public link |
| `POST /api/v1/history/events/github` | GitHub's webhook: `{changed: [<id>, …]}` |
| `GET /health` | `{"status": "ok"}` |

Every refusal — no key, a wrong, revoked or expired key, a key to another history, an unknown history, a commit that is not a version — is the same `404 {"detail": "not found"}`. More than ten wrong keys from one address in a minute: `429`.

## The histories config

The TOML file named by `MAXITOR_HISTORIES`, read again whenever it changes:

```toml
[github]
app_id = 5525124
private_key_env = "GITHUB_APP_PRIVATE_KEY"     # the variable holding the App's private key
webhook_secret_env = "GITHUB_WEBHOOK_SECRET"   # the variable holding the webhook's secret

[[history]]
id = "orders"
host = "github"                                # or "local", a path on this machine
repository = "owner/repo"
branch = "main"
graph_file = "services/orders/graph.json"

[[history.keys]]                               # written by `key new`, never by hand
name = "anna"
sha256 = "9c1e…"
expires = 2027-06-01
```

Keys are administered on the server, never over HTTP:

| Command | Does |
|---|---|
| `repo-graph-port history key new --history <id> --name <who> [--expires <date>]` | prints a new key once; writes only its SHA-256, name and expiry |
| `repo-graph-port history key revoke --history <id> --name <who>` | removes that key |
| `repo-graph-port history key list [--history <id>]` | names and dates, never keys or hashes |
| `repo-graph-port history check` | each history's graph file is on its branch, read as the port reads it |

Exit codes: `0` done, `1` a check failed, `2` the config is refused or the command is wrong.

## Freshness and cache

- Each repository is a partial git mirror under `MAXITOR_HISTORY_CACHE` (default `~/.cache/maxitor/history`): commits and trees, file contents only when a version is read.
- A version's file and counts never change: they are read once and kept on disk.
- GitHub's webhooks keep histories fresh at once. A **push** gives new versions only to the histories whose graph file it changed — git decides, so a push that touches no graph file changes nothing; a **new tag** has its release read again; an **edited or merged pull request** refreshes the version it made. Without a webhook, a history is fetched again when its last fetch is older than `MAXITOR_HISTORY_REFRESH_SECONDS` (600).
- When GitHub does not answer, a history still answers: a version shows its commit's message, a tag no release, and the next read asks again. With an App set, even a public history's GitHub reads carry the App's token, so they are not held to GitHub's 60 anonymous calls an hour.

## Security

The App's private key, the webhook's secret and every token stay in memory: git receives the token as configuration of one call, never in a remote URL, so no mirror's config holds it. No key or token reaches a log, an error or a `repr`; the log names the history and the key's name. A webhook's signature is checked over the raw body before anything reads it.

## Docker

[`Dockerfile`](Dockerfile) builds the service from this repository with `git`; the container listens on `0.0.0.0:8102` and keeps its cache in `/var/cache/repo-graph-port`. The demonstrator stand runs it at `https://repo-graph-port.aoa.run` ([`deploy/stand`](../../../../deploy/stand/README.md)).

Its own graph, as every AOA service keeps one, is [`graph.json`](graph.json) beside this file.
