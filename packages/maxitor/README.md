<p align="center">
  <img src="https://raw.githubusercontent.com/bystrovmaxim/aoa/main/docs/assets/aoa-logo.png" alt="AOA" width="540"><br><br>
  <a href="https://pypi.org/project/maxitor/"><img src="https://img.shields.io/pypi/v/maxitor?label=PyPI" alt="PyPI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/open-gnomon-protocol/README.md"><img src="https://img.shields.io/badge/Open_Gnomon_Protocol-1.1-informational" alt="Open Gnomon Protocol 1.1"></a>
</p>

# maxitor

**Your system's model, built from its code: kept with every change, checked in CI, and drawn as live diagrams.**

Maxitor is one package with parts you choose at install time:

| Part | What it does | Install |
|---|---|---|
| **`graph-builder`** | Keeps each service's model graph in one file beside its code, by the [Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/open-gnomon-protocol/README.md), and fails CI when a file is stale — every pull request shows what it did to the model | `pip install maxitor` |
| **the front** | Maxitor's web part: the full graph, entity diagrams, use cases and lifecycles of an AOA service, live in the browser | `pip install "maxitor[front]"` |
| **skills** | `graph-builder-setup`, the skill a coding agent follows to connect a project | comes with every install |

`pip install "maxitor[all]"` installs everything. The base install brings only `jsonschema` and `jsonschema-rs` — nothing of AOA, no server — so it is all a CI job needs. A command whose part is not installed says which extra to add.

## Get started

### The fastest way: one sentence to your coding agent

> Set up this project's model graphs with the skill at https://raw.githubusercontent.com/bystrovmaxim/aoa/maxitor-v3.0.0/packages/maxitor/skills/graph-builder-setup/SKILL.md

The agent installs the `graph-builder-setup` skill and runs it. The skill finds every service, proves how each one's model is exported — writing a small exporter where a service has a model but nothing prints it — and shows you one table: each service, its build, its proof, where its file goes. Nothing changes until you answer. Then it writes `graph-builder.toml`, saves the graphs and adds the CI check, and leaves the result for you to review and commit.

Already have the package? `graph-builder skill > .claude/skills/graph-builder-setup/SKILL.md` (or `.cursor/skills/…`), then ask the agent to *run graph-builder-setup*. Run it again any time: on a configured project it is an audit.

### By hand, in four steps

**1. Export each service's model** — a command, in any language, that prints the service's graph by the [protocol's schema](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/open-gnomon-protocol/README.md) and nothing else. Only the project knows its model, so the project writes this command; `graph-builder` runs it, checks what it prints, and keeps the file.

An AOA service (Python) — the framework builds the graph:

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

A Node service — the project's own code describes its model:

```js
// scripts/export-graph.mjs
import { buildModelGraph } from "../src/model/graph.js";
process.stdout.write(JSON.stringify(buildModelGraph()));
```

Any other stack works the same way: a Java task, a 1C export, or `cat build/graph.json` when another step already wrote the file.

**2. List the graphs** in `graph-builder.toml` at the repository root:

```toml
graph_builder = "1.0"

[[graph]]
name  = "my-service"
build = "uv run python -m my_service.build_graph"    # or: node scripts/export-graph.mjs
file  = "my_service/graph.json"
```

**3. Write them** — `graph-builder write` — and commit `graph-builder.toml` with the graph files. Without installing anything but [uv](https://docs.astral.sh/uv/): `uvx --from maxitor graph-builder write` (uv fetches its own Python; the project needs none).

**4. Check them in CI**: prepare the project's environment the way its other jobs do, then one step:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-node@v4          # or setup-java, or setup-uv + uv sync — whatever the builds need
- run: npm ci
- uses: bystrovmaxim/aoa/packages/maxitor/tools/graph_builder@maxitor-v3.0.0
```

The step runs `graph-builder check`: every build again, every graph checked against the protocol's schema, every file compared with what its build prints.

From then on, a pull request that changes the model without its graph file fails, naming each difference by id — and `graph-builder write` with one more commit fixes it.

### See the system

```bash
pip install "maxitor[front]"
maxitor
```

Open `http://127.0.0.1:8000` and point it at an AOA service's graph.

## Learn more

- **[The `graph-builder` command](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/tools/graph_builder/README.md)** — commands, configuration, how graphs are kept in a repository, the CI check, use from Python
- **[The app](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/front/README.md)** — the diagrams, the API, running it, its architecture
- **[graph-builder-setup](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/skills/graph-builder-setup/SKILL.md)** — the skill an agent follows
- **[Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/open-gnomon-protocol/README.md)** — the graph's language, which any language can follow
- [Changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/CHANGELOG.md) · [Source](https://github.com/bystrovmaxim/aoa/tree/maxitor-v3.0.0/packages/maxitor) · [Issues](https://github.com/bystrovmaxim/aoa/issues)

`maxitor` 3.0.0 replaces two earlier packages, the app's and the command's; [the changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/CHANGELOG.md) says what to change in an install or an import.

Apache License 2.0.
