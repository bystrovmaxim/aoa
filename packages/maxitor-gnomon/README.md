<p align="center">
  <img src="https://raw.githubusercontent.com/bystrovmaxim/aoa/main/docs/assets/aoa-logo.png" alt="AOA" width="540"><br><br>
  <a href="https://pypi.org/project/maxitor-gnomon/"><img src="https://img.shields.io/pypi/v/maxitor-gnomon?label=PyPI" alt="PyPI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <img src="https://img.shields.io/badge/tests-61-brightgreen" alt="61 tests">
  <a href="https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md"><img src="https://img.shields.io/badge/Open_Gnomon_Protocol-1.1-informational" alt="Open Gnomon Protocol 1.1"></a>
</p>

# maxitor-gnomon

**See every change to your system's model in the pull request that makes it.**

A diff shows which lines of code changed. It does not show what that did to the system: a new dependency, a renamed domain, an action wired into another application. `maxitor-gnomon` makes CI say it. Here is `gnomon check` on the AOA demo whose saved graph is one change behind its code:

```text
$ gnomon check
stale demo: packages/aoa-demo/graph.json
  edges[id=aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain.TelemetryPipelineDomain|application|aoa.action_machine.application.application.Application]: added
  nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
run: gnomon write --config gnomon.toml, and commit the graph files
```

Each service exports its model — domains, entities, actions and their dependencies — in the [Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md), and keeps it in one file, `graph.json`, beside its code. `gnomon` rebuilds those files from the code and fails CI when one is stale. So:

- **reviewers see the model change**, element by element, next to the code that changed it;
- **the model never drifts**: the code produces it, nobody draws it by hand;
- **git holds the model's history** — `git log -p graph.json` is how the system grew;
- **any tool reads the project without running it** — a viewer such as [Maxitor](https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-maxitor/README.md), an architecture check, a coding agent.

`maxitor-gnomon` knows nothing about any framework. [AOA](https://github.com/bystrovmaxim/aoa) services export the protocol out of the box; any service that can print a graph by its schema works the same way.

## Installation

```bash
pip install maxitor-gnomon
```

or run it without installing, with [uv](https://docs.astral.sh/uv/): `uvx --from maxitor-gnomon gnomon --version`. Python 3.12+.

## Get started

### The fastest way: one sentence to your coding agent

> Set up this project's model graphs with the skill at https://raw.githubusercontent.com/bystrovmaxim/aoa/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md

The agent installs the `gnomon-setup` skill and runs it. The skill finds every service, proves how each one's model is exported — writing a small exporter where a service has a model but nothing prints it — and shows you one table: each service, its build, its proof, where its file goes. Nothing changes until you answer. Then it writes `gnomon.toml`, saves the graphs and adds the CI check, and leaves the result for you to review and commit.

Already have the package? `gnomon skill > .claude/skills/gnomon-setup/SKILL.md` (or `.cursor/skills/…`), then ask the agent to *run gnomon-setup*. Run it again any time: on a configured project it is an audit.

### By hand, in four steps

**1. Export each service's model** — a command that prints its graph and nothing else. For an AOA service:

```python
# my_service/build_graph.py
import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    importlib.import_module("my_service.app")   # registers the service's actions, entities and resources
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()
```

**2. List the graphs** in `gnomon.toml` at the repository root:

```toml
gnomon = "1.0"

[[graph]]
name  = "my-service"
build = "uv run python -m my_service.build_graph"
file  = "my_service/graph.json"
```

**3. Write them** — `gnomon write` — and commit `gnomon.toml` with the graph files.

**4. Check them in CI:**

```yaml
- uses: astral-sh/setup-uv@v5
- run: uv sync
- name: The model graphs are current
  run: uvx --from "maxitor-gnomon==0.1.0" gnomon check
```

## Day to day

1. Change the code.
2. Run `gnomon write` — or let your check run do it as its last step.
3. Commit the changed `graph.json` with the code.
4. CI runs `gnomon check`. It rebuilds every graph, writes nothing, and fails on a stale file — naming what changed and the command that fixes it.

Forgot step 2? Run `gnomon write`, commit, push: one more commit to the same pull request.

## Commands

| Command | |
|---|---|
| `gnomon write` | Rebuild every graph; write each file whose content changed. An unchanged graph leaves its file untouched. |
| `gnomon check` | Rebuild every graph; write nothing; fail if a file is stale or missing, or a build fails. |
| `gnomon validate <file \| ->` | Say whether a document is a graph of the version it declares: `ok 1.1: 3213 nodes, 4841 edges`. |
| `gnomon skill` | Print the `gnomon-setup` skill for coding agents. |

`write` and `check` take `--config FILE` (default `gnomon.toml`). Each graph is built in a process of its own, with a 300-second limit. Exit codes: `0` all good · `1` a graph is stale, missing or broken · `2` the config is refused.

The same graph always gives the same bytes, so a file changes only when the model does. Differences are matched by `id` and read *what the file holds → what the code builds*; when only a file's layout differs, `check` says `only the formatting differs`.

## Configuration

| Key in `[[graph]]` | |
|---|---|
| `name` | Unique; names the graph in every message. |
| `build` | Shell command that prints the graph, and only it. |
| `file` | Unique; where the graph is kept. |
| `cwd` | Optional, default `.`; where the build runs. |

Paths are relative to `gnomon.toml`. A wrong config is refused by graph and field — `graph 'demo', file: required` — before anything is built.

## From Python

```python
from maxitor_gnomon.schemas import check_graph, graph_schema
from maxitor_gnomon.config import read_config

check_graph(document)       # None, or GraphRefused("graph 1.1 at edges/3: 'id' is a required property")
graph_schema("1.1")         # the JSON Schema of a protocol version
read_config("gnomon.toml")  # the repository's graphs, or ConfigRefused
```

A graph of thousands of elements is checked in a fraction of a second.

## Learn more

- **[Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md)** — the language itself: the document, its vocabulary, versions, identity and conformance
- **[gnomon-setup](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md)** — the skill an agent follows
- **[Every case, runnable](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/examples/step_26_maxitor/12_graph_file.py)** — a saved graph, a rebuild, a stale copy, an unknown version
- [Changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/CHANGELOG.md) · [Source](https://github.com/bystrovmaxim/aoa/tree/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon) · [Issues](https://github.com/bystrovmaxim/aoa/issues)

Apache License 2.0.
