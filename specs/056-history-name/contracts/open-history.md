# Contract: `GET /api/history/open` (OpenHistoryAction)

The result gains one field; nothing else changes.

| Field | Before | After |
| --- | --- | --- |
| `title` | `owner/repo` for a public history, the id for a private one | the graph file's folder (`web`), the repository's name at the root (`aoa`); the id for a private one |
| `path` (new) | — | `bystrovmaxim/aoa/packages/maxitor/web`; `bystrovmaxim/aoa` at the root; the address without the key for a private one |

Example, for `https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json`:

```json
{"name": "https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json", "title": "aoa-demo", "path": "bystrovmaxim/aoa/packages/aoa-demo", "host": "github", "repository": "bystrovmaxim/aoa", "...": "..."}
```
