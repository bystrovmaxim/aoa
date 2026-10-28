# Data Model: A Service Keeps Its Current Graph in One File, by the Format of maxitor-gnomon

## Graph (one entry of `gnomon.toml`)

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique within the config; names the graph in every message. |
| `cwd` | no, default `.` | The folder the build runs in, relative to the config's folder. |
| `build` | yes | A shell command that prints the graph document to standard output. |
| `file` | yes | Where the graph is saved, relative to the config's folder; unique within the config. |

The config itself carries `gnomon = "1.0"`, its own format version.

## Graph document

| Field | Meaning |
|---|---|
| `schema_version` | The schema version it follows: `1.0` or `1.1` today. |
| `nodes` | Objects, each with an `id`. |
| `edges` | Objects, each with an `id` from `1.1` on. |

## Schema version

One JSON Schema file per version, under `maxitor_gnomon/schemas/graph/`, never changed once published. `1.0`: edges without `id`. `1.1`: every edge has an `id`.

## Outcome of one graph

| Outcome | `write` | `check` | Exit |
|---|---|---|---|
| current | `ok … (unchanged)` | `ok …` | 0 |
| changed | `ok … (written)` | `stale …` + differences | 0 / 1 |
| missing file | written | `missing …` | 0 / 1 |
| build failed or timed out | `failed …` + command and output | same | 1 |
| not JSON, or not its schema | `refused …` + reason | same | 1 |

## Check-run step `Graph files (gnomon write)`

| State | When | Counts as |
|---|---|---|
| `OK` | every other step passed and `gnomon write` exited 0 | passed |
| `FAIL` | every other step passed and `gnomon write` exited non-zero | failed |
| `SKIPPED` | any other step failed | neither; the log says how many failed |
