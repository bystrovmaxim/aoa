---
name: aoa-graph-builder-setup
description: Guide a project through model-graph setup or audit with one understandable decision at a time. Discover and prove graph exports, explain choices and consequences, then apply the reviewed plan for graph files, CI and local updates. Use for setting up or repairing graph-builder.toml and model-graph files; requests to review or rewrite this skill do not start setup.
---

# aoa-graph-builder-setup

## Purpose and scope

Help the user understand and choose how their project's model is saved as a graph and kept current. A graph is a map of the model's entities, actions and relationships, generated from code. The Open Gnomon Protocol is the format of that map; introduce its name only when useful. Do not begin with a protocol lesson or a list of commands.

The normal result is a proven export command and a saved `graph.json` per selected service, `graph-builder.toml` describing them, a CI check for stale graphs, and an update step in the project's local check run. CI means automatic checks on proposed code changes. A user may defer an integration; explicitly report the remaining manual work instead of claiming complete automation.

Run **Setup** for a request to connect, audit or repair a project. Merely attaching, quoting, reviewing or editing this skill is not a request to run it.

## If you read this from a link

When explicitly asked to set up from a link, save this self-contained file in the current agent's supported skills folder and continue; use the project's agent conventions (`.dsh/skills/`, `.claude/skills/`, `.cursor/skills/`, or the current agent's documented location). Do not guess an unsupported folder.

## The conversation contract

- Speak the user's language. Keep paths, commands and generated code unchanged and code-facing text in English. For a Russian-speaking user, conduct the wizard in Russian.
- Lead with the decision and its practical effect. Explain an unfamiliar term where it first matters: an **exporter** is a small program that reads the model from code and prints its graph; **CI** checks changes automatically; the **local check run** is what a developer runs before submitting changes.
- Ask **one decision per turn**, for **one service at a time**. Finish that service's relevant choices before moving to the next. Shared CI and update decisions come once, with their scope named.
- Keep a question compact: a short title, two or three sentences of context, and two or three genuinely distinct options. Prefer roughly 100–160 words; use less when the decision is simple. Do not squeeze two decisions into one option or force a word budget at the cost of clarity.
- Put the recommendation first and explain why it fits this project. Describe the visible outcome and material cost or limitation of each option. A recommendation is not consent; declining is a valid answer.
- Use the host's question tool when available. Put the complete context in its question, since the card may be read alone. Respect its option limits; if it already provides free text, do not add a redundant “Other” option. Otherwise accept a number or the user's own words.
- Use the stable stage names **1/4 Discover**, **2/4 Services**, **3/4 Updates and checks**, **4/4 Review**. Translate these labels for the user. Within Services, name the current service and, when known, its position among discovered services. Do not invent “question 3 of 7”: later questions depend on earlier answers.
- A path identifies the affected file; its role explains the decision. Say “the script that updates AOA, `update-aoa.sh`”, not just its name. Use real discovered paths in live questions, never template placeholders. Commands, dependency pins, environment preparation and full logs belong in technical detail at Review, unless they affect the current choice.
- Use facts found in the project for recommendations. Do not ask the user to rediscover files, choose internal implementation mechanics, or repeat a choice already settled by their instructions or the repository. Surface settled choices in the review.
- After an answer, acknowledge its consequence in one sentence, record it, and ask only the next applicable question. Do not repeat the entire plan after every answer.
- “I do not understand” or a request for an example pauses this decision. Explain it with one concrete before/after situation, then return to the same choice. “Do what is best” accepts the stated recommendation for the current question, unless the user explicitly delegates more. Clarify ambiguous answers; silence, a timeout and a preselected option are not answers.
- Accept **back**, **change an answer**, **show my choices**, **details**, **pause** and **stop** at any point, including equivalent natural language. A changed answer invalidates dependent choices: excluding a service removes its pending path/exporter changes and updates the CI scope. Keep unaffected decisions. A pause produces a short resumable summary; a stop before Apply leaves project files untouched and removes temporary drafts. Neither means approval.

## Setup

Use four conversational stages, followed by applying the reviewed choices. Discover and the dialogue do not edit the target project. Draft exporters, configs and output files live in a temporary folder outside it; keep them until Apply or remove them on cancellation. Check a build's side effects before running it: a temporary config isolates graph output, not arbitrary work done by the build. If safe proof needs unavailable dependencies or credentials, report that limit rather than calling the build proven.

### 1/4 Discover

Start with a short orientation in the user's language, for example: “I will inspect the project, explain the choices one at a time, and show the proposed changes before applying them.” Do the survey below without turning routine discovery into a questionnaire. Then give a short plain-language finding per service, what already works, and the next decision. Keep full commands and proof output for Review.

1. **Read the config, the CI and the check run.** Look for `graph-builder.toml` at the repository root; if there is none, no graph is configured yet, and step 2 has nothing to check. Then find:
   - **the CI** the project uses — `.github/workflows/`, `.gitlab-ci.yml`, or another — and whether a job runs `graph-builder check`, and over which config. A configured repository without that job is the most common gap; a job that runs it without a config fails on every change; a repository may have **no CI at all**;
   - **the check run** — what the project's developers run before a change is done: a script (`scripts/check*.sh`, `run_checks*`), a task (`make check`, a `[tool.taskipy]` or `package.json` script), a `pre-commit` config — and whether it runs `graph-builder write`. A project may have none.
   The later update and checking decisions start from both.
2. **Check every configured graph.** Run `graph-builder check` once; it gives each graph's state: **current** (its file is what its build prints), **stale** (the file differs — `check` lists what changed, by id), **missing** (no file yet), **broken** (`failed`: the build exits with an error, times out, or prints something that is not JSON), or **refused** (JSON, but not a graph of the version it claims). A file holds the graph formatted (sorted keys, indent 2), so it may differ from the build's raw output byte for byte: only `graph-builder check` says whether a file is current, never `cmp` or `diff`.
3. **Find every service and how its model can be exported.** A service is a package or application with a model of its own; libraries that only provide building blocks (adapters, plugins, a graph builder) are not services. For each service, find which of these it is:
   - **it exports already** — a command that prints its graph document to standard output (a module named like `build_graph`, a script). A graph that is only served over HTTP (a route such as `/graph-json`) or only built in code (`to_json()` on a graph builder) shows that the model can be exported, but a build cannot wait for a running server: treat that service as the next case and add an exporter that prints the same document;
   - **it has a model, and nothing exports it yet** — the service's code declares a model (domains, entities, operations, their links) that can be printed as a protocol graph, but no code does. The project may be in any language: the exporter is written in its own language, by its own means. For AOA, the first producer of the protocol, it is three lines: the service registers actions, entities or resources, and its graph is `create_node_graph_coordinator().to_json()` once the modules that register them are imported (see Example exporters);
   - **it has no producer** — no framework or code that can export its model as a protocol graph. Do not invent a graph for it: writing a description of the model by hand is not setup, and it would drift from the code. Record the service as `no producer` and go on.
   Also note what the project's own docs call its model, its graph or its architecture map, and any `graph.json` that already exists (check it with `graph-builder validate <file>`; step 4 tells whether it is current). The schema is the only test of "this is a graph": nothing else about the producer matters.
4. **Prove a build for each new, stale, broken or refused graph — in the temporary folder.** A build is a shell command that prints the graph to standard output and nothing else, run in a process of its own: importing two services in one process mixes their models.
   - For a service that **exports already**, the command calls what exists.
   - For a service with a **model and no exporter**, write a draft exporter in the temporary folder (the example below) and run it by its path, e.g. `uv run python <temporary folder>/build_graph.py`, from the folder the service's build will run in — with whatever the project's own commands need (extras, environment variables). In the repository it will become a module of the service named with a verb, `build_graph.py`, so it is never mistaken for the graph file it feeds; a module the project already has for this keeps its name.
   - For a **stale** graph, prove the existing command writes a valid replacement. For a **broken or refused** graph, find the cause and prove the correction.
   Prove each command the way CI will run it: write a temporary config in the temporary folder with one `[[graph]]` — `cwd` the absolute path of the folder the build runs in, `build` the command, `file` a path in the temporary folder (absolute paths are allowed in a config; relative ones start at the config's folder) — and run `graph-builder write --config <temporary config>`. The proof is its line `ok <name> (written)` and exit 0; then `graph-builder validate <that file>` gives the size, `ok 1.1: N nodes, M edges`. Anything else is not proven: say what the build printed and why it failed. When the service already has a graph file, also run `graph-builder check` on a temporary config whose `file` is that existing file: `ok <name>` means it is already current, and `check` writes nothing.

### A question, as the user should see it

Translate and adapt this illustrative card to observed facts; it is not a result from the current project:

> **2/4 · Services · game-back — save a map of this service?**
>
> `game-back` contains the game's model, but no command saves its map. I have checked a small exporter that can produce it from the code. Connecting it lets you review model changes alongside code changes.
>
> 1. **Connect it (recommended):** add `packages/game-back/game_back/build_graph.py`, the program that produces the map. You will review the generated map when the model changes. We will settle its location next.
> 2. **Leave it out for now:** add nothing for this service; its model changes will not be tracked by this setup.
>
> You can choose an option, describe another approach, or ask me to explain.

After option 2: “game-back stays outside this setup; I will skip its file-location question.” Continue with the next service, not an exporter or destination question for game-back.

### 2/4 Services

Keep a working decision record: service, observed state, proven build or blocker, include/defer, exporter, destination, update method, CI coverage, and whether each choice is settled or pending. It is working context, not a form for the user to fill. Never substitute a plausible example for an observed fact.

For each service, resolve choices in dependency order:

1. **Whether and how to include it.** For an existing valid configuration, keep its established scope. For a newly discovered service, explain what its map would contain and offer to include it or leave it out for now. If it needs an exporter, this is the same decision: explain the proven small program, its final path and what it enables. Do not separately ask to include a service and then ask permission for the exporter required to include it. If it has no producer, explain why a reliable map cannot yet be generated; leave it out and name the prerequisite. Never hand-author a graph or present an unproven exporter as ready.
2. **An existing problem, if any.** Explain the effect, not only the diagnostic label. A stale file describes an older model; a broken build cannot produce a map; a refused document does not meet its claimed format. Offer the proven correction or exclusion from automatic graph checks, explaining that exclusion loses coverage and leaves any old file untouched. If no correction is proven, identify the blocker; do not label “repair” as ready. A missing file is generated when applying the accepted configuration, without a separate question. A malformed config is a configuration blocker, not evidence that every graph is broken; prepare and show a repair before dependent choices.
3. **Where to save an included new graph.** Ask only after inclusion is settled, and only if its location is not already settled. Recommend the repository's convention, otherwise `graph.json` beside this service. Give at most one meaningful alternative plus free text; do not offer the same path twice. Explain that this is the saved model map reviewed with code changes. Keep an existing destination unless the user wants to move it. Do not overwrite an unrelated file or silently delete the old one.

If a service is deferred, skip all dependent questions for it. Move to the next service only when this one's applicable choices are settled. If no services remain included and none were already configured, finish with what is missing; do not create an empty config or ask about CI for nothing.

### 3/4 Updates and checks

First settle **how maps get refreshed**, then **how forgotten refreshes get detected**. Explain the difference when needed: updating writes a new map; checking compares the saved map with the code and reports a mismatch without fixing it.

**Updating.** Name the selected services and the project's existing check run. If it already updates their graphs correctly, keep it and say so; there is no compulsory repeat question. Otherwise recommend `graph-builder write` at the end of that run, only after every preceding check passed. Explain that a successful run then leaves changed graph files to review and commit with the model change, and also runs every selected graph build. Do not promise a duration you have not measured.

With no check run, explain the tradeoff between a small explicit update command/target following project conventions and running the command manually. Do not invent a full test pipeline or introduce a new hook framework as a default. An update script such as `update-aoa.sh` covers only changes made through that script: edits to a service's own model still need a refresh. If that extra integration is useful, ask about it separately, after the primary update method. A dependency update may change a graph; it does not necessarily do so.

**Checking.** Say what CI already covers. Reuse an adequate check without asking again. Otherwise offer a check in an existing suitable job, or a new workflow when the repository's actual hosting supports it, and an explicit “defer automatic checking” choice. Explain that a stale graph makes the check fail; it prevents merging only if repository rules require that check. Do not change those rules as part of setup. CI checks every included graph and never rewrites or commits them. Deferring CI leaves detection to a manual check; record this limitation. Do not offer GitHub Actions to a project on another host.

### 4/4 Review

Start with a short account of the user's choices in ordinary language. Then show one compact table; technical proof must not make the main table unreadable:

| Service | Now | After applying | Saved map |
|---|---|---|---|
| game-back | Model exists; no export command | Add the proven exporter and save the map | `packages/game-back/graph.json` |
| game-admin | Saved map is current | Keep its existing setup | `packages/game-admin/graph.json` |
| billing-worker | No graph producer | Leave out; requires a producer first | — |

These rows illustrate the shape only. Populate the real review from discovery and answers. Below the table, state when maps will update, what checks them, and any deferred/manual work. Include a clearly separated technical detail block with:

- every project file to create or change, its purpose and the proposed change; show meaningful diffs for existing files and the prepared content for new integration/exporter files;
- each final build command and working directory, the verified tool pin, and each command Apply will run;
- actual proof output and exit status per graph, distinguishing a temporary draft from the final module. Never invent counts or copy the illustrative output. Use both `graph-builder check` and `validate` for already configured valid graphs; keep failures visible.

Resolve implementation mechanics during discovery/preparation; they are not additional user preference questions. A scope change that needs a new decision returns to that decision. Ask **apply these changes**, **change a choice**, or **stop without applying** only once the proposal is concrete and reviewable. Do not repeat authorization already given for this exact reviewed plan. If the audit found everything current and correctly integrated and no changes are proposed, finish with the evidence; do not ask permission to do nothing.

### Apply and report

Apply only the reviewed choices, after the user's authorization:

1. Add accepted exporters from the proven drafts and use their final module commands.
2. Create or update `graph-builder.toml`, preserving unrelated entries and user edits.
3. Run `graph-builder write` from the actual project configuration. Temporary-draft success does not establish that the installed module works.
4. Add only the accepted CI and update integrations. Preserve failure propagation: the local write step runs only after other checks succeed; CI runs `check`, not `write`.
5. Run `graph-builder check`, inspect the diff and report the real outcome.

If implementation reveals a changed scope or an unproven dependency, pause the affected work and present the concrete new decision. An execution failure is not success: show the failed command and relevant output, say which files were already changed and what remains, and do not discard the user's edits. Stop retries when the same unresolved prerequisite remains. Keep the decision record for resuming; remove temporary files when no longer needed. Do not interpret stopping after a partial Apply as permission to revert project files.

Finish with the changed files, observed verification, and what the developer now does when changing a model. Include one actual command and its actual answer, and distinguish complete setup from deferred integration or a blocked build. Leave the diff for review; do not commit, push, open a pull request or merge. Explain that serving history from the main branch requires the graph file to reach that branch; a side branch has git history too, but is not yet part of that main-branch history.

Only if the user wants history served in Maxitor, explain the separate `repo-graph-port` setup: one `[[history]]` per graph (`repository`, `branch`, `graph_file`) and its GitHub App for a private repository. Do not make it an extra setup question by default.

### Operational invariants

- Never edit graph JSON by hand: its producer prints it and `graph-builder write` saves it.
- Prove builds with `graph-builder write` on a temporary config, never with a pipe to `validate -`: validation alone loses the producer's exit code. Use `set -o pipefail` if a pipe is needed for another purpose.
- Each service builds in its own process; loading two services together mixes registered models.
- CI only checks. Graph files are updated locally and reviewed with the code change.
- Existing numbered snapshots or an old history index are not automatically migrated or deleted. Point out their presence and let the user decide separately.

## Running graph-builder

`graph-builder` is the command of the `maxitor` package on PyPI — its base install, with no extra and nothing of AOA. Run it without installing, with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from maxitor graph-builder --version
```

Below, `graph-builder` means that whole command — or plain `graph-builder` when the project's own environment already has `maxitor` installed (then run it the way the project runs its tools, e.g. `uv run graph-builder`), or after `pip install maxitor`.

**Pin what exists.** A check must never change under the project's feet, so CI and the check run name one version — and it must be one that exists. Look before you pin:

```bash
git ls-remote --tags https://github.com/bystrovmaxim/aoa 'maxitor-v*'
git ls-remote https://github.com/bystrovmaxim/aoa refs/heads/main
```

- a tag `maxitor-v<version>` exists → `uvx --from "maxitor==<version>" graph-builder …`, and the CI action at `@maxitor-v<version>`;
- no tag yet → the commit of `main` the second command printed: `uvx --from "git+https://github.com/bystrovmaxim/aoa@<commit>#subdirectory=packages/maxitor" graph-builder …`, and the CI action at `@<commit>`. Say in the technical detail at Review that the pin is a commit until a release exists.

| Command | What it does | Exit |
|---|---|---|
| `graph-builder write [--config FILE]` | runs every build of the config, writes each file whose bytes changed | 0 ok, 1 a build failed or printed no graph, 2 config refused |
| `graph-builder check [--config FILE]` | runs every build, writes nothing, fails if a file is not what its build prints | 0 current, 1 stale / missing / failed / refused, 2 config refused |
| `graph-builder validate <file \| ->` | says whether one document is a graph: `ok 1.1: N nodes, M edges` or why not | 0 / 1 |
| `graph-builder skill` | prints this file | 0 |

`write` and `check` run each build themselves: they see its exit code, its output and the schema at once. `validate -` sees only what reaches it through a pipe — a build that prints a graph and then fails still pipes a valid graph — so never use a pipe into `validate -` as proof of a build.

## Example exporters

The exporter is the only part that knows the project; it is written in the project's language. An AOA service (Python):

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

A service in another language prints the same document with its own code — a Node script, a Java task, a 1C export:

```js
// scripts/export-graph.mjs — prints this service's model as an Open Gnomon Protocol graph
import { buildModelGraph } from "../src/model/graph.js";
process.stdout.write(JSON.stringify(buildModelGraph()));
```

Nothing else may be printed: standard output is the graph. Include only what this service declares and serves — shared parts it really serves belong in its graph, another service's own code does not.

## Example `graph-builder.toml`

```toml
graph_builder = "1.0"                      # the config's own format version

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
    # the project's own environment, the way its other jobs prepare it — the builds run in it
    - uses: actions/setup-node@v4        # or setup-java, or astral-sh/setup-uv + `uv sync`, …
    - run: npm ci
    - uses: bystrovmaxim/aoa/packages/maxitor/tools/graph_builder@<ref>   # the release tag if one exists, else a commit of main (Pin what exists)
```

As a new workflow, the job goes under `on: [push, pull_request]` and `jobs:` in `.github/workflows/graph-builder.yml`; a repository whose builds need submodules checks them out (`with: {submodules: true}`). The action installs uv (which fetches its own Python; the project needs none) and runs `graph-builder check` from the `maxitor` it belongs to: every build again, every graph checked against the protocol's schema. It does not prepare the project's environment — that is the steps before it. Its inputs: `config` (default `graph-builder.toml`) and `graph-builder` (how to run the command, when the project has its own).
