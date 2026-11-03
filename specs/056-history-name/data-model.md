# Data Model: A history named after what was opened

## PublicHistory (server, `history_address.py`)

| Field | Meaning |
| --- | --- |
| `link`, `owner`, `repo`, `version_link`, `version_key` | as today |
| `path` (new, stored) | the graph file's path inside the repository, as the link gives it: `packages/maxitor/web/graph.json` |
| `title` (property) | the last folder of `path`; `repo` when the graph file is at the root |
| `full_path` (property) | `owner/repo` followed by the folder of `path`; `owner/repo` at the root |

## PrivateHistory

| Property | Meaning |
| --- | --- |
| `title` | its id, as today |
| `full_path` | its `name`: the port's address without the key |

## HistoryEntry and the open answer

Both gain `path: str`, the history's full path. `title` keeps its name and now holds the folder name for a public history.

## OpenHistory (client)

Gains `path: string`, read from the open answer.
