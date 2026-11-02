# Quickstart: validating the feature

Run from the repository root.

```bash
uv run --extra dev pytest packages/maxitor/tools/repo_graph_port/tests -q
```

| Scenario | Expected |
|---|---|
| Six commits covering User Story 1 | the three fields match each commit |
| `version.toml`, `pyproject.toml` with a key, a JSON file | numbers from each |
| Each bad link | `version_problem` in both answers, and the graph opens |
| Two graphs at one commit, both orders, cold and warm | each gets its own bytes |
| A cache written by the old version | `versions/` is removed and nothing old is served |
| No version file | the same points as before |
| A file broken mid-history | only the points of the spec's edge cases change |
| A moved folder with old paths | points from both sides of the move |
| A version-only point | no `.graph` file is written until it is opened |

Breaks that must make a test fail: remove the path from the cache key; treat a reordering as a change; let a comment in `version.toml` become a point; read the graph on a version-only point; let a bad link raise.

Count the requests to GitHub on a real history before and after, and write the result in the pull request.
