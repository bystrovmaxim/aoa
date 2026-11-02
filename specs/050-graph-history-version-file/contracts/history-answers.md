# Contract: history answers

#345 reads this.

## Parameters

`GET /api/v1/history/public…` takes `version_link` and `version_key` beside `link`, on all three routes. `version_link` must be a blob link to the same repository and branch. Otherwise it is a `version_problem`.

## `GET /api/v1/history/{id}`

Adds:

```json
{"version_file": "packages/aoa-demo/pyproject.toml", "version_problem": null}
```

Both are `null` with no version file.

## `GET /api/v1/history/{id}/versions`

Adds `version_problem` beside `versions` and `proposals`, because Maxitor polls only this answer. Each version adds:

```json
{"graph_changed": false, "version": "1.3.1", "version_changed": true}
```

Open pull requests carry the neutral values: `graph_changed` true, `version` `null`, `version_changed` false.

## `GET /api/v1/history/{id}/versions/{sha}`

Answers for every point. A version-only point returns the graph file in that commit.

## Config

```toml
[[history]]
id = "demo"
host = "github"
repository = "owner/repo"
branch = "main"
graph_file = "packages/aoa-demo/graph.json"
version_file = "packages/aoa-demo/pyproject.toml"
version_key = "project.version"
graph_file_before = ["old/graph.json"]
version_file_before = ["old/pyproject.toml"]
```

A wrong type of value is refused when the file is read, as today. A wrong path is not: it is a `version_problem`.
