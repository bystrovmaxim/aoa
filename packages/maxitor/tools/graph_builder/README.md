# graph_builder — the model's graph, kept and checked in the repository

Part of the [`maxitor`](../../README.md) package: `pip install maxitor` with no extra installs this command and nothing else — no AOA, no server.

**See every change to your system's model in the pull request that makes it.**

A diff shows which lines of code changed. It does not show what that did to the system: a new dependency, a renamed domain, an action wired into another application. `graph-builder` makes CI say it. Here is `graph-builder check` on the AOA demo whose saved graph is one change behind its code:

```text
$ graph-builder check
stale demo: packages/aoa-demo/graph.json
  edges[id=aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain.TelemetryPipelineDomain|application|aoa.action_machine.application.application.Application]: added
  nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
run: graph-builder write --config graph-builder.toml, and commit the graph files
```

Each service exports its model — domains, entities, actions and their dependencies — in the [Open Gnomon Protocol](../../../open-gnomon-protocol/README.md), and keeps it in one file, `graph.json`, beside its code. `graph-builder` rebuilds those files from the code and fails CI when one is stale. So:

- **reviewers see the model change**, element by element, next to the code that changed it;
- **the model never drifts**: the code produces it, nobody draws it by hand;
- **git holds the model's history** — `git log -p graph.json` is how the system grew;
- **any tool reads the project without running it** — a viewer such as [Maxitor](../../front/README.md), an architecture check, a coding agent.

`graph-builder` knows nothing about any framework, and installing it brings nothing of AOA. [AOA](https://github.com/bystrovmaxim/aoa) services export the protocol out of the box; any service that can print a graph by its schema works the same way.

## Day to day

1. Change the code.
2. Run `graph-builder write` — or let your check run do it as its last step.
3. Commit the changed `graph.json` with the code.
4. CI runs `graph-builder check`. It rebuilds every graph, writes nothing, and fails on a stale file — naming what changed and the command that fixes it.

Forgot step 2? Run `graph-builder write`, commit, push: one more commit to the same pull request.

## Commands

| Command | |
|---|---|
| `graph-builder write` | Rebuild every graph; write each file whose content changed. An unchanged graph leaves its file untouched. |
| `graph-builder check` | Rebuild every graph; write nothing; fail if a file is stale or missing, or a build fails. |
| `graph-builder validate <file \| ->` | Say whether a document is a graph of the version it declares: `ok 1.1: 3213 nodes, 4841 edges`. |
| `graph-builder skill` | Print the `graph-builder-setup` skill for coding agents. |

`write` and `check` take `--config FILE` (default `graph-builder.toml`). Each graph is built in a process of its own, with a 300-second limit. Exit codes: `0` all good · `1` a graph is stale, missing or broken · `2` the config is refused.

The same graph always gives the same bytes, so a file changes only when the model does. Differences are matched by `id` and read *what the file holds → what the code builds*; when only a file's layout differs, `check` says `only the formatting differs`.

## Configuration

| Key in `[[graph]]` | |
|---|---|
| `name` | Unique; names the graph in every message. |
| `build` | Shell command that prints the graph, and only it. |
| `file` | Unique; where the graph is kept. |
| `cwd` | Optional, default `.`; where the build runs. |

Paths are relative to `graph-builder.toml`. A wrong config is refused by graph and field — `graph 'demo', file: required` — before anything is built.

## Keeping graphs in a repository

The [Open Gnomon Protocol](../../../open-gnomon-protocol/README.md) defines the graph document. How a repository keeps its graphs — one file per service, listed in `graph-builder.toml`, checked in CI — is this command's convention, below.

### The graph file

- A service keeps its graph in one file, conventionally `graph.json` in the service's folder.
- The file MUST hold the document and nothing else, in UTF-8, with object keys sorted, an indent of two spaces, non-ASCII characters as they are, and one newline at the end — `json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`. The same document therefore always gives the same bytes. The formatting MUST NOT reorder `nodes` or `edges`.
- The file MUST be written by the service's build, never edited by hand. It SHOULD change in the same pull request as the code that changed the model, and CI SHOULD check that it is current.

### The project configuration

A repository lists its graphs in `graph-builder.toml` at its root ([its schema](src/maxitor/graph_builder/config_schema.json)):

```toml
graph_builder = "1.0"                         # the configuration's own version

[[graph]]
name  = "shop"                         # unique
cwd   = "."                            # optional, default "."
build = "python -m shop.build_graph"   # prints the graph document, and only it
file  = "shop/graph.json"              # unique
```

- Relative paths start at the configuration's folder; absolute paths are allowed.
- A build MUST exit with 0 and print exactly one graph document; otherwise it produced no graph and nothing is written. Each graph MUST be built in a process of its own, so that two services' models never mix.
- The configuration's version is independent of the graph's.

### A conforming repository

A repository conforms when it lists its graphs in `graph-builder.toml`, keeps each file as above, and checks in CI that every file is current.

## From Python

```python
from maxitor.graph_builder.schemas import check_graph, graph_schema
from maxitor.graph_builder.config import read_config

check_graph(document)       # None, or GraphRefused("graph 1.1 at edges/3: 'id' is a required property")
graph_schema("1.1")         # the JSON Schema of a protocol version
read_config("graph-builder.toml")  # the repository's graphs, or ConfigRefused
```

A graph of thousands of elements is checked in a fraction of a second.

## The CI check

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-node@v4          # the project's own environment, in which its builds run
- run: npm ci
- uses: bystrovmaxim/aoa/packages/maxitor/tools/graph_builder@maxitor-v3.0.0
```

[`action.yml`](action.yml) installs uv — which fetches its own Python, so the project needs none — and runs `graph-builder check` from the `maxitor` release of its tag: every build again, every graph checked against the protocol's schema of the version it declares, every file compared with what its build prints. It does not prepare the project's environment; the steps before it do, in whatever language the project is. Inputs:

| Input | Default | |
|---|---|---|
| `config` | `graph-builder.toml` | the config to check |
| `graph-builder` | that release, run with `uvx` | how to run the command, when the project has its own |

## Learn more

- **[Get started](../../README.md#get-started)** — connect a project: one sentence to a coding agent, or four steps by hand
- **[Open Gnomon Protocol](../../../open-gnomon-protocol/README.md)** — the language itself: the document, its vocabulary, versions, identity
- **[graph-builder-setup](../../skills/graph-builder-setup/SKILL.md)** — the skill an agent follows
- **[Every case, runnable](../../../../examples/step_26_maxitor/12_graph_file.py)** — a saved graph, a rebuild, a stale copy, an unknown version
