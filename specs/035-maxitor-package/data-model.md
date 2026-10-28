# Data Model: The Protocol in a Folder with No Code; Maxitor as One Package with Extras

## Protocol folder — `packages/open-gnomon-protocol/`

| File | Meaning | Rule |
|---|---|---|
| `graph/1.0.json`, `graph/1.1.json` | the graph schemas by version (JSON Schema 2020-12) | content never changes once published; only `$id` changes, once, here |
| `README.md` | the specification: the graph document, vocabulary, versions and compatibility, identity | no graph-file, config or repository rules |
| `CHANGELOG.md` | the protocol's own history | one entry per protocol version |

`$id` = `https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/open-gnomon-protocol/graph/<version>.json`. No other file: no `pyproject.toml`, no `*.py`, no `src/`. A release is the git tag `open-gnomon-protocol-v<version>`.

## Schema copy

| Copy | Source | Used by |
|---|---|---|
| `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.json` | `graph/1.1.json` | `GRAPH_JSON_SCHEMA` — the export check |
| `packages/maxitor/src/maxitor/gnomon/schemas/1.0.json` | `graph/1.0.json` | `graph_schema("1.0")`, `check_graph` |
| `packages/maxitor/src/maxitor/gnomon/schemas/1.1.json` | `graph/1.1.json` | `graph_schema("1.1")`, `check_graph` |

Invariant: every copy is byte for byte its source; `tests/scripts/test_schema_copies.py` fails otherwise, naming the copy and the source.

## Package `maxitor`

| Field | Value |
|---|---|
| distribution | `maxitor`, version `3.0.0` |
| import | `maxitor` |
| parts | `maxitor.gnomon`, `maxitor.viewer`, `maxitor.skills` (later `maxitor.repo_graph_port`, #288) |
| commands | `gnomon` → `maxitor.gnomon.cli:main`; `maxitor-api` → `maxitor.launch:viewer` |
| extras | none, `viewer`, `all` (contracts/install.md) |

## Part

| Part | Holds | May import | Must not import |
|---|---|---|---|
| `gnomon` | the command, config and its schema, differences, writer, schema copies | standard library, `jsonschema`, `jsonschema_rs` | `aoa.*`, `maxitor.viewer` |
| `viewer` | API, model (core, diagrams, rooms), samples, built front, `build_graph` | AOA (`action_machine`), `maxitor.gnomon` | — |
| `skills` | `gnomon-setup/SKILL.md` | no code | — |
| `launch` | `viewer()` entry | standard library at import time | — |

## Service graph file

| Service | Build | File |
|---|---|---|
| viewer | `uv run --extra dev python -m maxitor.viewer.build_graph` | `packages/maxitor/graphs/viewer.json` |
| demo (unchanged) | `uv run --extra dev python -m aoa.demo.build_graph` | `packages/aoa-demo/graph.json` |

`gnomon.toml` names them `viewer` and `demo`. The viewer's graph after the move = the graph before, with every `aoa.maxitor` in an id or a reference replaced by `maxitor.viewer`, and nothing else.

## Boundary rule (in `scripts/package_boundaries.toml`)

| Key | Meaning |
|---|---|
| `[packages.maxitor]` `current_roots` | `packages/maxitor/src/maxitor/viewer` |
| `[packages.maxitor]` `import_prefixes` | `maxitor.viewer` |
| `[packages.maxitor]` `may_import` | `action_machine`, `gnomon` |
| `[standalone.gnomon]` `roots` | `packages/maxitor/src/maxitor/gnomon` |
| `[standalone.gnomon]` `forbid` (new) | `maxitor.viewer` — in addition to the existing ban on `aoa` |
