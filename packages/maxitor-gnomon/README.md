# maxitor-gnomon

A service that can print its own graph keeps that graph in one file in its repository. The file changes in the same pull request as the code that changed the graph, so git holds the graph's whole history — no registry to keep by hand, nothing to drift from the code. `maxitor-gnomon` is the format of that file and the small command that keeps it current: `gnomon`.

The package knows nothing about AOA. Any producer whose output passes the graph schema can use it; AOA is the first.

*Gnomon* is the rod of a sundial: its shadow marks the hour. The graph file marks where a service's graph stood at each commit.

## The graph document

A JSON object with three fields:

| Field | Meaning |
|---|---|
| `schema_version` | the schema it follows: `1.0` or `1.1` |
| `nodes` | objects, each with an `id` |
| `edges` | objects, each with an `id` from `1.1` on |

Nodes and edges are matched by `id` wherever they sit in the file, so two versions of a graph compare element by element: what was added, what was removed, what changed.

A runnable tour of every case — the config, a saved graph against its schema, a rebuild equal to the file, a stale copy, another indent, an unknown version — is [examples/step_26_maxitor/12_graph_file.py](../../examples/step_26_maxitor/12_graph_file.py) ([notebook](../../examples/step_26_maxitor/12_graph_file.ipynb)).

## Schema versions

The format is a standard of its own, the **[Open Gnomon Protocol](protocol/README.md)**: each version is one JSON Schema file, [`protocol/graph/<version>.json`](protocol/graph/), and **a published version never changes** — a new shape of the graph is a new version. This package is one implementation of it; it ships the protocol inside its wheel and reads it from there.

| Version | What it is |
|---|---|
| `1.0` | the first shape; edges have no `id` |
| `1.1` | every edge has an `id` |

```python
from maxitor_gnomon.schemas import SCHEMA_VERSIONS, check_graph, graph_schema

SCHEMA_VERSIONS        # ("1.0", "1.1")
graph_schema("1.1")    # the JSON Schema, as a dict
check_graph(document)  # None, or GraphRefused naming the version, the place and the reason
```

A refusal names the place: `graph 1.1 at edges/3: 'id' is a required property`.

## `gnomon.toml`

At the repository root, one `[[graph]]` per graph:

```toml
gnomon = "1.0"                      # the config's own format version

[[graph]]
name  = "demo"                      # unique; names the graph in every message
cwd   = "."                         # optional, default "." — the folder the build runs in
build = "uv run python -m aoa.demo.print_graph"   # prints the graph to standard output
file  = "packages/aoa-demo/graph.json"           # unique — where the graph is saved
```

Paths are relative to the config's folder. The build prints the graph and nothing else; each graph is built in a process of its own, so two services never mix their nodes.

## The commands

```text
gnomon write [--config gnomon.toml]   build every graph, write each file whose bytes changed
gnomon check [--config gnomon.toml]   build every graph, write nothing, fail if a file is stale
gnomon validate <file | ->            say whether one document is a graph
gnomon skill                          print the gnomon-setup skill for coding agents
```

A file holds the graph with sorted keys, indented by two spaces, one newline at the end — the same graph always gives the same bytes, and a file whose graph did not change is not touched.

This repository's own run, after a change to one demo entity:

```text
$ gnomon check
stale demo: packages/aoa-demo/graph.json
  nodes[id=aoa.demo.model.clinical_supply.entities.cs_inbound_shipment_ticket.ClinicalInboundShipmentTicketCoreEntity].properties.description: Inbound partner lot keyed to SKU and packing posture (suppl… → Inbound partner lot keyed to SKU
ok maxitor
run: gnomon write --config gnomon.toml, and commit the graph files
$ gnomon write
ok demo (written)
ok maxitor (unchanged)
$ gnomon validate packages/aoa-demo/graph.json
ok 1.1: 3213 nodes, 4841 edges
```

| Exit | `write` | `check` |
|---|---|---|
| 0 | every graph built and its file current | every file is what its build prints |
| 1 | a build failed, or printed something that is not a graph | a file is stale or missing, or a build failed |
| 2 | the config was refused | the config was refused |

## How a graph travels with a pull request

1. You change the code.
2. You run `gnomon write` (or your check run does it as its last step).
3. You commit the changed `graph.json` together with the code.
4. CI runs `gnomon check`: it builds the graph again and compares. It only checks — it never writes.
5. Merged, the pull request carries the graph as it now is; `git log -p graph.json` is the graph's history.

Forgot step 2? CI fails and says what changed, by id. Run `gnomon write`, commit, push: one more commit to the same pull request, no new one.

## Three ways to start

Until `maxitor-gnomon` is on PyPI, `gnomon` runs from this repository with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from "git+https://github.com/bystrovmaxim/aoa@main#subdirectory=packages/maxitor-gnomon" gnomon --version
```

In CI pin a commit instead of `main`. Below, `gnomon` means that command.

### 1. By hand

1. **Make each service print its graph.** For an AOA service, a module of a few lines that imports the service's model and prints its graph:

   ```python
   # my_service/print_graph.py
   import importlib
   import sys

   from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator

   importlib.import_module("my_service.app")   # registers the service's actions
   sys.stdout.write(create_node_graph_coordinator().to_json())
   ```

   Prove it: `uv run python -m my_service.print_graph | gnomon validate -` prints `ok 1.1: …`.
2. **List the graphs** in `gnomon.toml` at the repository root, one `[[graph]]` each. The usual place for a file is the service's own folder, `<service>/graph.json`.
3. **Write them:** `gnomon write`, then commit `gnomon.toml` and the graph files.
4. **Check them in CI** — for GitHub Actions:

   ```yaml
   graph-files:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - uses: astral-sh/setup-uv@v5
       - run: uv sync
       - name: The graph files are current
         run: uvx --from "git+https://github.com/bystrovmaxim/aoa@<commit sha>#subdirectory=packages/maxitor-gnomon" gnomon check
   ```

An old hand-kept history — folders of numbered snapshots — is not migrated: git is the history from the first `graph.json` on.

### 2. From the command line, with a coding agent

Install the skill into your agent's skills folder, then ask the agent to run it:

```bash
mkdir -p .claude/skills/gnomon-setup
gnomon skill > .claude/skills/gnomon-setup/SKILL.md
```

(`.cursor/skills/` for Cursor.) Then: *"Run gnomon-setup."* The skill finds every service that produces a graph, proves a build command for each, asks where each file goes, and — once you answer — writes `gnomon.toml`, runs `gnomon write` and adds `gnomon check` to your CI. It never commits. Run it again later: on a configured repository it is an audit.

### 3. One sentence to an agent

> Set up graph history in this repository with the skill at https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md

The skill saves itself into the agent's skills folder and goes on with the setup.
