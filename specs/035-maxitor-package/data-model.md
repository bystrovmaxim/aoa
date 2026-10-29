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
| `packages/maxitor/tools/graph_builder/src/maxitor/graph_builder/schemas/1.0.json` | `graph/1.0.json` | `graph_schema("1.0")`, `check_graph` |
| `packages/maxitor/tools/graph_builder/src/maxitor/graph_builder/schemas/1.1.json` | `graph/1.1.json` | `graph_schema("1.1")`, `check_graph` |

Invariant: every copy is byte for byte its source; `tests/scripts/test_schema_copies.py` fails otherwise, naming the copy and the source.

## Package `maxitor`

| Field | Value |
|---|---|
| distribution | `maxitor`, version `3.0.0` |
| import | `maxitor` |
| parts | `maxitor.graph_builder`, `maxitor.viewer`, `maxitor.skills` (later `maxitor.repo_graph_port`, #288) |
| commands | `graph-builder` → `maxitor.graph_builder.cli:main`; `maxitor-api` → `maxitor.launch:viewer` |
| extras | none, `viewer`, `all` (contracts/install.md) |

## Part

| Part | Holds | May import | Must not import |
|---|---|---|---|
| `graph-builder` | the command, config and its schema, differences, writer, schema copies | standard library, `jsonschema`, `jsonschema_rs` | `aoa.*`, `maxitor.viewer` |
| `viewer` | API, model (core, diagrams, rooms), samples, built front, `build_graph` | AOA (`action_machine`), `maxitor.graph_builder` | — |
| `skills` | `graph-builder-setup/SKILL.md` | no code | — |
| `viewer.launch` | `viewer()`, the `maxitor-api` entry | standard library at import time | — |

## Service graph file

| Service | Build | File |
|---|---|---|
| maxitor (the application) | `uv run --extra dev python -m maxitor.viewer.build_graph` | `packages/maxitor/app/graph.json` |
| demo (unchanged) | `uv run --extra dev python -m aoa.demo.build_graph` | `packages/aoa-demo/graph.json` |

`graph-builder.toml` names them `maxitor` and `demo`. The viewer's graph after the move = the graph before, with every `aoa.maxitor` in an id or a reference replaced by `maxitor.viewer`, and nothing else.

## Boundary rule (in `scripts/package_boundaries.toml`)

| Key | Meaning |
|---|---|
| `[packages.maxitor]` `current_roots` | `packages/maxitor/app/src/maxitor/viewer` |
| `[packages.maxitor]` `import_prefixes` | `maxitor.viewer` |
| `[packages.maxitor]` `may_import` | `action_machine`, `graph-builder` |
| `[standalone.graph_builder]` `roots` | `packages/maxitor/tools/graph_builder/src/maxitor/graph_builder` |
| `[standalone.graph_builder]` `forbid` (new) | `maxitor.viewer` — in addition to the existing ban on `aoa` |
