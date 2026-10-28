---
name: gnomon-setup
description: Connect a project to the Open Gnomon Protocol, the shared language for describing a project's model as a graph — find or add the code that exports each service's model, prove it, save each model description in a graph.json beside the service, and add the CI check that keeps it current. Use when asked to set up, initiate, audit or repair a project's model graph, model description, graph files, graph history, gnomon or gnomon.toml.
---

# gnomon-setup

The [Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md) is a shared language for describing a project's model: its domains, entities, actions and how they relate, as a graph — a JSON document with `schema_version`, `nodes` and `edges` that passes the protocol's schema. A person, a viewer or another agent can read that description without importing the project's code.

This skill connects a project to that language. It is the project's initiation: it gets a description of each service's model, saves it, and keeps it current. When it is done, the repository has:

- a **build command** per service that prints the service's model description — an exporter module the project already has, or one this skill adds;
- **`gnomon.toml`** at the root, listing each graph, its build command and its file;
- a **`graph.json`** per service, the saved description, which changes in the same pull request as the code that changes the model — so git also holds the model's history;
- a **CI step** running `gnomon check`, which fails when a saved description is stale;
- a passing `gnomon check`.

The skill has one command, **Setup**. Run it the first time and any time after: on a configured repository it is an audit.

## If you read this from a link

Save this file, unchanged, as `SKILL.md` in a folder `gnomon-setup` inside the skills folder of the agent you are: `.claude/skills/`, `.cursor/skills/` or `.dsh/skills/` at the repository root (ask if none of them is yours). Then go on with **Setup** at once; do not wait to be asked again.

## Running gnomon

`gnomon` is the command of the `maxitor-gnomon` package on PyPI. Run it without installing, with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from maxitor-gnomon gnomon --version
```

Below, `gnomon` means that whole command — or plain `gnomon` when the project's own environment already has `maxitor-gnomon` installed (then run it the way the project runs its tools, e.g. `uv run gnomon`), or after `pip install maxitor-gnomon`. In CI, pin the version — `uvx --from "maxitor-gnomon==0.1.0" gnomon check` — so a check never changes under the project's feet.

| Command | What it does | Exit |
|---|---|---|
| `gnomon write [--config FILE]` | runs every build of the config, writes each file whose bytes changed | 0 ok, 1 a build failed or printed no graph, 2 config refused |
| `gnomon check [--config FILE]` | runs every build, writes nothing, fails if a file is not what its build prints | 0 current, 1 stale / missing / failed / refused, 2 config refused |
| `gnomon validate <file \| ->` | says whether one document is a graph: `ok 1.1: N nodes, M edges` or why not | 0 / 1 |
| `gnomon skill` | prints this file | 0 |

`write` and `check` run each build themselves: they see its exit code, its output and the schema at once. `validate -` sees only what reaches it through a pipe — a build that prints a graph and then fails still pipes a valid graph — so never use a pipe into `validate -` as proof of a build.

## Setup

Setup has two phases. **Survey** (steps 1–5) changes nothing in the repository: everything it needs to try — a draft exporter, a config, an output file — goes into a temporary folder outside the repository, created only when step 4 needs it. Keep it until the user answers, since Apply uses its proven drafts, and delete it at the end of Apply — or at once, if the user applies nothing. **Apply** (steps 6–7) writes the project's files, and only after the user has answered the question that ends the survey. Never commit.

### Survey

1. **Read the config and the CI.** Look for `gnomon.toml` at the repository root; if there is none, no graph is configured yet, and step 2 has nothing to check. Either way, look at the CI the project uses: does a job run `gnomon check`? A configured repository without that job is the most common gap; a job that runs it without a config fails on every change. Say which, under the table.
2. **Check every configured graph.** Run `gnomon check` once; it gives each graph's state: **current** (its file is what its build prints), **stale** (the file differs — `check` lists what changed, by id), **missing** (no file yet), **broken** (`failed`: the build exits with an error, times out, or prints something that is not JSON), or **refused** (JSON, but not a graph of the version it claims). A file holds the graph formatted (sorted keys, indent 2), so it never equals the build's raw output byte for byte: only `gnomon check` says whether a file is current, never `cmp` or `diff`.
3. **Find every service and how its model can be exported.** A service is a package or application with a model of its own; libraries that only provide building blocks (adapters, plugins, a graph builder) are not services. For each service, find which of these it is:
   - **it exports already** — a command that prints its graph document to standard output (a module named like `build_graph`, a script). A graph that is only served over HTTP (a route such as `/graph-json`) or only built in code (`to_json()` on a graph builder) shows that the model can be exported, but a build cannot wait for a running server: treat that service as the next case and add an exporter that prints the same document;
   - **it has a model, and nothing exports it yet** — the service is built on a framework that can export its model as a graph, but no code does. For AOA, the first producer of the protocol: the service registers actions, entities or resources, and its graph is `create_node_graph_coordinator().to_json()` once the modules that register them are imported (see the example exporter below);
   - **it has no producer** — no framework or code that can export its model as a protocol graph. Do not invent a graph for it: writing a description of the model by hand is not setup, and it would drift from the code. Name the service in the table as `no producer` and go on.
   Also note what the project's own docs call its model, its graph or its architecture map, and any `graph.json` that already exists (check it with `gnomon validate <file>`; step 4 tells whether it is current). The schema is the only test of "this is a graph": nothing else about the producer matters.
4. **Prove a build for each new or broken graph — in the temporary folder.** A build is a shell command that prints the graph to standard output and nothing else, run in a process of its own: importing two services in one process mixes their models.
   - For a service that **exports already**, the command calls what exists.
   - For a service with a **model and no exporter**, write a draft exporter in the temporary folder (the example below) and run it by its path, e.g. `uv run python <temporary folder>/build_graph.py`, from the folder the service's build will run in — with whatever the project's own commands need (extras, environment variables). In the repository it will become a module of the service named with a verb, `build_graph.py`, so it is never mistaken for the graph file it feeds; a module the project already has for this keeps its name.
   - For a **broken** graph, find why its build fails and prove a fixed command.
   Prove each command the way CI will run it: write a temporary config in the temporary folder with one `[[graph]]` — `cwd` the absolute path of the folder the build runs in, `build` the command, `file` a path in the temporary folder (absolute paths are allowed in a config; relative ones start at the config's folder) — and run `gnomon write --config <temporary config>`. The proof is its line `ok <name> (written)` and exit 0; then `gnomon validate <that file>` gives the size, `ok 1.1: N nodes, M edges`. Anything else is not proven: say what the build printed and why it failed. When the service already has a graph file, also run `gnomon check` on a temporary config whose `file` is that existing file: `ok <name>` means it is already current, and `check` writes nothing.
5. **Propose where each file goes, and ask.** A configured graph keeps its file unless the user wants it moved. For each new graph, in this order:
   - a place that follows the repository's own conventions — a folder that already holds generated or exported files, an existing graph file, the service's own folder;
   - the standard place, `<service folder>/graph.json`;
   - a place the user names.
   Then show **one table** and ask the user which graphs to keep, add, fix or drop, and where each file goes. When everything is configured, current and checked in CI, there is nothing to apply: say so, and ask only whether to keep it as it is.

   | Service | Service folder | Build command (cwd) | Proof | File (alternatives) | State |
   |---|---|---|---|---|---|
   | game-back | `packages/game-back` | `uv run python -m game_back.build_graph` (`packages/game-back`) | `ok 1.1: 517 nodes, 646 edges` | `packages/game-back/graph.json` | new — exporter to add |
   | game-admin | `packages/game-admin` | `uv run python -m game_admin.build_graph` (`packages/game-admin`) | `ok 1.1: 440 nodes, 550 edges` | `packages/game-admin/graph.json` (existing file, current) | new |
   | billing-worker | `services/billing` | — | — | — | no producer |

   States: **current**, **stale**, **missing**, **broken**, **refused** for a configured graph (step 2); **new** for a graph found in step 3, with **exporter to add** when its build needs the module this skill will write; **no producer** for a service whose model nothing can export. The Build column shows the command the config will hold — for an exporter to add, its final `python -m <service package>.build_graph`, while the Proof column shows what the draft printed. For a new graph whose file already exists, the File column says whether that file is current (step 4). The Proof of a configured graph is its `gnomon check` line and its size from `gnomon validate <file>`; of a new or fixed one, its proof from step 4. Under the table, say what Apply will create, change and run — every file by its path — and what the CI already does (step 1).

### Apply

6. **Apply what the user chose.** In this order:
   1. add each exporter the user accepted, as `<service package>/build_graph.py` (the draft, proven in step 4), and point its build at it, `python -m <service package>.build_graph`;
   2. write `gnomon.toml` (example below);
   3. run `gnomon write` — every graph is built again from the repository's own files, so a build that only worked from the temporary folder fails here;
   4. add `gnomon check` to the CI the project uses, unless a job already runs it (ask which CI, if there are several; GitHub Actions example below);
   5. run `gnomon check` and show that it passes.
7. **Hand over.** Delete the temporary folder. List every file you created or changed, and the graph files you wrote, and say the next step is the user's: review them and commit them together. Do not commit, push or open a pull request.

### Rules

- Never edit a graph file by hand; it is always what its build prints, written by `gnomon write`.
- Never pipe a build into `gnomon validate -` as proof; prove builds with `gnomon write` on a temporary config (step 4). If you must pipe for another reason, run it under `set -o pipefail`.
- An old hand-kept history (folders of numbered snapshots, an index file) is not migrated: git is the history from the first `graph.json` on. Point it out and let the user delete it.
- CI only checks. The developer runs `gnomon write` and commits the files with the change; a stale file fails the pull request until they do.

## Example exporter (an AOA service)

```python
# game_back/build_graph.py — prints this service's model as an Open Gnomon Protocol graph
import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    """Register the service's model, then write its graph to standard output."""
    importlib.import_module("game_back.app")   # the module that imports every action, entity and resource
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()
```

Nothing else may be printed: standard output is the graph. Import only what this service registers and serves — shared actions it really serves belong in its graph, another service's own modules do not.

## Example `gnomon.toml`

```toml
gnomon = "1.0"                      # the config's own format version

[[graph]]
name  = "game-back"                 # unique; names the graph in every message
cwd   = "packages/game-back"        # optional, default "." — relative to this file
build = "uv run python -m game_back.build_graph"   # prints the graph to standard output
file  = "packages/game-back/graph.json"           # unique — relative to this file
```

## Example CI step (GitHub Actions)

```yaml
graph-files:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
    - name: The graph files are current
      run: uvx --from "git+https://github.com/bystrovmaxim/aoa@<commit sha>#subdirectory=packages/maxitor" gnomon check
```

If the builds need the project's own environment (they usually do), install it first in the same job, the way the project's other jobs do.
