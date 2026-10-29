# Contract: the history actions, as the port's own server serves them

The port runs at `https://repo-graph-port.aoa.run` on the stand (`127.0.0.1:8102` locally, command `repo-graph-port`). Maxitor and any other client read it over HTTP.

All under `/api/v1/history/`. A configured history is named by its `id`; a private one's key comes in the header `X-Maxitor-History-Key`. A public history is named by its link and needs no key: `?link=https://github.com/<owner>/<repo>/blob/<branch>/<path>` on the `public` routes.

| Route | Action | Input | Answer |
|---|---|---|---|
| `GET /api/v1/history/{id}` | `DescribeHistoryAction` | the history id | `{id, repository, branch, graph_file, versions, newest}` |
| `GET /api/v1/history/{id}/versions` | `HistoryAction` | `after` (optional sha) | `{versions: [Version, …]}` oldest first; `ETag`; `304` for the same `If-None-Match` |
| `GET /api/v1/history/{id}/versions/{sha}` | `VersionAction` | `sha` | the graph file's bytes, `application/json`, `Cache-Control: public, max-age=31536000, immutable` |
| `GET /api/v1/history/public?link=…` | `DescribeHistoryAction` | the link | as for an id |
| `GET /api/v1/history/public/versions?link=…` | `HistoryAction` | the link, `after` | as for an id |
| `GET /api/v1/history/public/versions/{sha}?link=…` | `VersionAction` | the link, `sha` | as for an id |
| `POST /api/v1/history/events/github` | `ReceiveHostEventAction` | the host's event; its `X-Hub-Signature-256` checked over the raw body by a middleware before the adapter | `200 {"changed": [<history id>, …]}` — the configured histories it changed; a bad signature `401`, the action never runs |

Which histories an event changes (research R12): `push` — those of the repository and branch whose graph file changed between `before` and `after` by `git log --first-parent`; `create` of a tag — the tags of the repository's histories; `pull_request` edited or merged — the version whose commit is its `merge_commit_sha`, if any. Anything else changes nothing. When GitHub does not answer (down, or out of its rate limit), `history` still answers: a version shows its commit's message, a tag no release, and the next read asks again.

Refusals: an unknown, revoked or expired key; a key of another history; an unknown history; a version the history does not have — all `404 {"detail": "not found"}`. More than the set number of wrong keys from one client address in a minute: `429`.

Logs, error bodies and telemetry name the history `id`, the key's `name`, the client's origin — never the key, a token or a whole address with a key.
