---
name: gnomon-setup
description: Set up or check a project's graph history with maxitor-gnomon — find every service that produces a graph document, prove how to build it, choose where each graph file lives, write gnomon.toml and the CI check. Use when asked to set up, audit or repair graph files, graph history, gnomon or gnomon.toml.
---

# gnomon-setup

A service that can print its own graph — a JSON document with `schema_version`, `nodes` and `edges` — keeps that graph in one file in its repository. The file changes in the same pull request as the code that changed the graph, so git holds the graph's whole history. `gnomon` builds each graph, writes its file, and lets CI fail when a file is stale.

This skill has one command, **Setup**. Run it the first time and any time after: on a configured repository it is an audit.

## If you read this from a link

Save this file, unchanged, as `SKILL.md` in a folder `gnomon-setup` inside the skills folder of the agent you are: `.claude/skills/`, `.cursor/skills/` or `.dsh/skills/` at the repository root (ask if none of them is yours). Then go on with **Setup** at once; do not wait to be asked again.

## Running gnomon

Until `maxitor-gnomon` is published on PyPI, run it from its repository with `uvx`:

```bash
uvx --from "git+https://github.com/bystrovmaxim/aoa@main#subdirectory=packages/maxitor-gnomon" gnomon --version
```

Below, `gnomon` means that whole command — or plain `gnomon` when the project's own environment already has `maxitor-gnomon` installed (then run it the way the project runs its tools, e.g. `uv run gnomon`). In CI, replace `main` with a commit sha, so a check never changes under the project's feet. Once the package is on PyPI: `uvx --from maxitor-gnomon gnomon …`, or `pip install maxitor-gnomon`.

The commands:

| Command | What it does | Exit |
|---|---|---|
| `gnomon write` | builds every graph of `gnomon.toml`, writes each file whose bytes changed | 0 ok, 1 a build failed, 2 config refused |
| `gnomon check` | builds every graph, writes nothing, fails if a file is not what its build prints | 0 current, 1 stale / missing / failed, 2 config refused |
| `gnomon validate <file \| ->` | says whether one document is a graph: `ok 1.1: N nodes, M edges` or why not | 0 / 1 |
| `gnomon skill` | prints this file | 0 |

## Setup

Do these steps in order. Change nothing before step 6, and never commit.

1. **Read the config.** Look for `gnomon.toml` at the repository root. If it exists, run `gnomon check` and note each graph's state. If it does not, no graph is configured yet: skip step 2.
2. **Check every configured graph.** For each `[[graph]]`, run its `build` in its `cwd` and pipe the output into `gnomon validate -`. A graph is **current** (its file matches), **stale** (the file differs — `gnomon check` lists what changed, by id), **missing** (no file yet), **broken** (the build fails or prints something that is not JSON — `gnomon check` says `failed`), or **refused** (JSON, but not a graph of the version it claims — `refused`). A file holds the graph formatted (sorted keys, indent 2), so it never equals the build's raw output byte for byte: only `gnomon check` says whether a file is current, never `cmp` or `diff`. Then look at the CI the project uses: does a job run `gnomon check`? A configured repository without it is the most common gap — say so under the table.
3. **Find graphs that are not configured.** Search the repository for every place that produces a graph document:
   - code that builds and prints or serves JSON with `schema_version`, `nodes` and `edges` (an HTTP route such as `/graph-json`, a function such as `to_json()` on a graph builder, a script);
   - what the project's own README or docs call its graph, its model map or its architecture graph;
   - one per service: a package or application that registers its own model and builds or serves a graph of it. Libraries that only provide building blocks (adapters, plugins, the graph builder itself) are not services.
   The schema is the only test of "this is a graph": nothing else about the producer matters.
   A graph found here may already have a file (`graph.json` beside the service, say); note it, and in step 5 check it with `gnomon validate <file>`.
4. **Prove a build command for each** new graph, and a fixed one for each broken graph. Write a shell command that prints the graph to standard output and nothing else — usually `python -m <package>.print_graph` with a module of a few lines that imports the service's model and prints the graph. Name that module with a verb, `print_graph.py`, so it is never mistaken for the graph file it feeds; a module the project already has for this keeps its name. Run it in a process of its own, from the folder it will run in, and pipe it into `gnomon validate -`. A command that has not printed `ok` is not proven. Build each service's graph in its own process: importing two services in one process mixes their nodes.
5. **Propose where each file goes.** A configured graph keeps its file unless the user wants it moved. For each new graph, in this order:
   - a place that follows the repository's own conventions — a folder that already holds generated or exported files, an existing graph file, the service's own folder;
   - the standard place, `<service folder>/graph.json`;
   - a place the user names.
   Then show **one table** and ask the user which graphs to keep, add, fix or drop, and where each file goes:

   | Service | Service folder | Build command (cwd) | Proof | File (alternatives) | State |
   |---|---|---|---|---|---|
   | game-back | `packages/game-back` | `uv run python -m game_back.print_graph` (`.`) | `ok 1.1: 517 nodes, 646 edges` | `packages/game-back/graph.json` | new |

   States of a configured graph: current, stale, missing, broken, refused (step 2). A graph not configured yet is **new**; when a file for it already exists, say so in the File column and whether it holds a graph (`gnomon validate <file>`) — once it is configured, `gnomon check` tells whether it is current.
6. **Apply what the user chose.** Write `gnomon.toml` (example below); run `gnomon write`; add `gnomon check` to the CI the project uses (ask which, if there are several; GitHub Actions example below); run `gnomon check` and show that it passes.
7. **Hand over.** List the files you changed and the graph files you wrote, and say the next step is the user's: commit them together. Do not commit, push or open a pull request.

### Rules

- Never edit a graph file by hand; it is always what its build prints, written by `gnomon write`.
- An old hand-kept history (folders of numbered snapshots, an index file) is not migrated: git is the history from the first `graph.json` on. Point it out and let the user delete it.
- CI only checks. The developer runs `gnomon write` and commits the files with the change; a stale file fails the pull request until they do.

## Example `gnomon.toml`

```toml
gnomon = "1.0"                      # the config's own format version

[[graph]]
name  = "game-back"                 # unique; names the graph in every message
cwd   = "packages/game-back"        # optional, default "." — relative to this file
build = "uv run python -m game_back.print_graph"   # prints the graph to standard output
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
      run: uvx --from "git+https://github.com/bystrovmaxim/aoa@<commit sha>#subdirectory=packages/maxitor-gnomon" gnomon check
```

If the builds need the project's own environment (they usually do), install it first in the same job, the way the project's other jobs do.
