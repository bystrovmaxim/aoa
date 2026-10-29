# Contract: maxitor-gnomon

What a project, AOA and the check run can rely on. Everything not named here is internal.

## The graph document

A JSON object with `schema_version` (string), `nodes` (array) and `edges` (array); every node and every edge has an `id`. Its exact shape is the schema of the version it declares.

## Schemas

```python
from maxitor_gnomon.schemas import graph_schema, check_graph, SCHEMA_VERSIONS

SCHEMA_VERSIONS          # ("1.0", "1.1")
graph_schema("1.1")      # -> dict, the JSON Schema of that version
check_graph(document)    # -> None; raises GraphRefused naming the version, or the first error and its path
```

- A published schema file never changes; a new version is a new file.
- `graph_schema` of an unknown version raises `GraphRefused` naming it.

## Config — `gnomon.toml`

```toml
gnomon = "1.0"                       # the config's own format version

[[graph]]
name  = "demo"                       # required, unique
cwd   = "packages/aoa-demo"          # optional, default "." — relative to this file's folder
build = "uv run python -m some.mod"  # required — prints the graph document to standard output
file  = "packages/aoa-demo/graph.json"  # required, unique — relative to this file's folder
```

```python
from maxitor_gnomon.config import read_config
read_config("gnomon.toml")   # -> list[Graph], in file order; raises ConfigRefused naming the graph and the field
```

## Commands

```bash
gnomon write [--config gnomon.toml]
gnomon check [--config gnomon.toml]
gnomon validate <file | ->        # one document; prints `ok 1.1: N nodes, M edges` or the refusal; exit 0 / 1; writes nothing
gnomon skill                      # prints the gnomon-setup skill file
```

| Exit code | `write` | `check` |
|---|---|---|
| 0 | every graph built, checked, and its file current (written only if it changed) | every file equals what its build prints |
| 1 | a build failed, timed out, printed something that is not a valid graph | a file is stale, missing, or a build failed |
| 2 | the config was refused | the config was refused |

Output, one line per graph — `ok demo (unchanged)`, `ok demo (written)`, `stale demo: packages/aoa-demo/graph.json` followed by its differences — and, on any failure, the command that fixes it.

Difference lines (at most 20 per graph, then `… and N more`):

```text
  nodes[id=pkg.Order]: added
  edges[id=pkg.Order|entity_relation|items].target_id: pkg.Item → pkg.Line
  schema_version: 1.0 → 1.1
  only the formatting differs
```

## The graph file

`json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)` followed by one newline, UTF-8. Nothing else is in it.

## The skill `gnomon-setup`

One file inside the package (`maxitor_gnomon/skills/gnomon-setup/SKILL.md`), printed by `gnomon skill`, reachable by its raw GitHub link. One command, **Setup**, for first and later setup; it asks before every change and never commits. It begins with what an agent that read it from a link does first: save it into its own skills folder, then run Setup at once.
