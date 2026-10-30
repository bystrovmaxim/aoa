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
| **`repo-graph-port`** | A service that reads each graph's history from its repository — every merged pull request that changed the graph file is a version, with its description and tags — and serves any version's graph; the only part that talks to GitHub | `pip install "maxitor[repo-graph-port]"` |
| **skills** | `aoa-graph-builder-setup`, the skill a coding agent follows to connect a project | comes with every install |

`pip install "maxitor[all]"` installs everything. The base install brings only `jsonschema` and `jsonschema-rs` — nothing of AOA, no server — so it is all a CI job needs. A command whose part is not installed says which extra to add.

## Get started

### The fastest way: one prompt to your coding agent

```text
Install and run this skill for the current project:
https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/maxitor/skills/aoa-graph-builder-setup/SKILL.md

Walk me through the wizard in my language. Ask one question at a time and wait for my answer. For each decision, explain in plain words: what you found, what you propose to change, why you recommend this option, and what happens if I choose another. Explain each technical term the first time you use it.

First check whether the current project fits. If it is empty or has no source of graphs, explain the situation and stop without creating any configuration or checks. If some services are already connected, keep the settings that work, and discuss the new services one at a time.

If I do not understand a question, give a concrete example and come back to the same decision. Before applying anything, show the summary: my decisions, which files will change, and what will remain to do by hand. Apply changes only after I confirm. Do not create commits or pull requests.
```

The agent follows a four-stage wizard in your language: discover the project, settle each service's choices, choose updating and checking, then review the proposed changes. Each question explains one decision, a recommendation and the consequences of the alternatives. You can ask for an example, go back, change an answer or pause. Nothing is applied to the target project until the proposed changes are reviewed and authorized. Asking to review or edit the skill itself does not start setup.

The wizard proves exports in a temporary folder, then applies the accepted exporters, graph files and integrations. A deferred optional integration remains explicitly manual; mandatory release versioning cannot be deferred. It leaves the result for you to review and commit; serving graph history from the main branch requires those files to reach that branch.

Already have the package? `graph-builder skill > .claude/skills/aoa-graph-builder-setup/SKILL.md` (or `.cursor/skills/…`), then ask the agent to *run aoa-graph-builder-setup*. Run it again any time: on a configured project it is an audit.

### What the wizard asks you to decide

Revision 2 also audits mandatory release versions on every run. Broken existing items come first, the new required version decision next, optional choices afterward. The familiar per-service questions below are unchanged. Decisions are retained in `[setup]` in `graph-builder.toml`; a version refusal leaves setup incomplete. See [mandatory release versions](../../docs/how-to/graph-setup-version-tags.md) for the audit, first-tag consent, CI and monorepo cases.

It finishes one service before moving to the next. First decide whether to connect a newly discovered service (including its exporter if needed), then where to save its map if that is not already established. After the services, choose how to refresh their maps and how to detect a forgotten refresh. Existing working arrangements are retained, not turned into repeat questions. Technical commands and proof accompany the final review rather than crowding each question.

An illustrative question, with fictional project paths:

> **2/4 · Services · game-back — save a map of this service?**
>
> `game-back` contains the game's model, but no command saves its map. A small exporter has been proven in a temporary folder. Connecting it lets you review model changes alongside code changes.
>
> 1. **Connect it (recommended):** add `packages/game-back/game_back/build_graph.py`, the program that produces the map. You will review the saved map when the model changes; its location comes next.
> 2. **Leave it out for now:** add nothing for this service; this setup will not track its model changes.

If you answer “leave it out”, the wizard acknowledges that consequence and skips that service's file-location question. If you answer “I do not understand”, it explains a concrete case: “Adding an entity changes the model. The saved map lets the same code review show that new entity. Leaving this service out means this setup will not save that map.” It then returns to the same decision, without treating the explanation request as acceptance. This is an illustrative dialogue, not a recorded agent run.

| Case | What the wizard does |
|---|---|
| New service with an export command | Proves the command; settles inclusion and any unresolved file location |
| Model with no export command | Proves a small exporter; explains its addition as part of connecting this service |
| No graph producer | Explains the prerequisite and leaves the service out; never invents a graph |
| Current configured graph | Preserves its destination and working integrations |
| Missing saved graph | Writes it when applying the accepted setup; no redundant missing-file question |
| Stale saved graph | Explains that it describes the old model; offers proven refresh or explicit exclusion from checks |
| Broken build or refused graph format | Shows the cause and a proven correction, or a blocker; exclusion leaves the old file untouched |
| Invalid configuration | Treats it as a configuration problem and prepares a repair before dependent decisions |
| No local check run | Explains an explicit update command/target versus manual refresh; does not invent a full test pipeline |
| Update only after a dependency update | Explains that service-code changes still require a refresh; asks about the extra integration separately |
| Missing CI | Offers a check for the actual hosting provider or deferral; deferral leaves checks manual |
| No included services | Creates no empty config and asks no irrelevant integration questions |
| Fully healthy audit | All mandatory items, including version tags and enforcing CI, are done; reports evidence without a redundant question |
| “Details” or “show my choices” | Shows the requested information while retaining the current unanswered decision |
| “Back” or a changed answer | Revisits that decision and removes invalid dependent choices; retains unrelated answers |
| Ambiguous answer, silence or “I do not understand” | Keeps the choice pending; clarifies or explains |
| “Do what is best” | Accepts the current recommendation, unless broader delegation is explicitly stated |
| Pause or stop before applying | Pause keeps a resumable summary; stop discards temporary drafts; neither changes project files |
| Apply fails or scope changes | Reports partial changes and exact failure, or returns to the changed decision; does not claim success or erase user work |

Updating and checking are different: `graph-builder write` refreshes files; `graph-builder check` detects stale files without rewriting them. A failing CI check blocks merging only when repository rules require it. The wizard does not change those rules. A local update step runs only after the other checks pass.

Before applying, you see the before/after table, affected files, prepared changes, commands, proof and any manual work left. You can apply, revise a choice or stop. The skill remains a single file, so `graph-builder skill` delivers the whole wizard. A live conversation is still needed to judge how clearly a particular agent follows these instructions; package tests alone do not establish that.

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
- **[The front](https://github.com/bystrovmaxim/aoa/blob/main/packages/maxitor/front/README.md)** — the diagrams, the API, running it, its architecture
- **[`repo-graph-port`](https://github.com/bystrovmaxim/aoa/blob/main/packages/maxitor/tools/repo_graph_port/README.md)** — a graph's history from its repository: versions, keys, public links, webhooks
- **[aoa-graph-builder-setup](https://github.com/bystrovmaxim/aoa/blob/main/packages/maxitor/skills/aoa-graph-builder-setup/SKILL.md)** — the skill an agent follows
- **[Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/open-gnomon-protocol/README.md)** — the graph's language, which any language can follow
- [Changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/CHANGELOG.md) · [Source](https://github.com/bystrovmaxim/aoa/tree/maxitor-v3.0.0/packages/maxitor) · [Issues](https://github.com/bystrovmaxim/aoa/issues)

`maxitor` 3.0.0 replaces two earlier packages, the app's and the command's; [the changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-v3.0.0/packages/maxitor/CHANGELOG.md) says what to change in an install or an import.

Apache License 2.0.
