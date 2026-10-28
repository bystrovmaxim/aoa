# Research: A Service Keeps Its Current Graph in One File, by the Format of maxitor-gnomon

Decisions for [spec.md](spec.md), checked against the repository on 2026-10-28.

## R1. The package and where its files live

- **Decision**: `packages/maxitor-gnomon/`, distribution `maxitor-gnomon`, import package `maxitor_gnomon` at the top level (`src/maxitor_gnomon/`), built with hatchling like the others, `requires-python >= 3.12`, member of the uv workspace (`[tool.uv.workspace]` and `[tool.uv.sources]` in the root `pyproject.toml`). Dependencies: `jsonschema` only (already used by `aoa-action-machine`); TOML is read with the standard `tomllib`. The schema files ship inside the import package as data: `maxitor_gnomon/schemas/graph/1.0.json`, `…/1.1.json`, `maxitor_gnomon/schemas/config/1.0.json`, read with `importlib.resources`.
- **Rationale**: FR-001, FR-011. A top-level name, not `aoa.gnomon`, says in the import itself that the package is not part of AOA.

## R2. Keeping the package free of AOA

- **Decision**: `scripts/check_package_boundaries.py` gains a second kind of rule: a root that may import **nothing** from `aoa`. `scripts/package_boundaries.toml` gets `[standalone.gnomon] roots = ["packages/maxitor-gnomon/src/maxitor_gnomon"]`, and the checker fails on any `import aoa…` or `from aoa…` there. The packaging smoke test learns that `maxitor-gnomon`'s wheel ships `maxitor_gnomon/` and nothing under `aoa/`.
- **Rationale**: FR-001 (enforced, not promised); today both tools assume `packages/*/src/aoa/…`.

## R3. The schema by version, and AOA's `GRAPH_JSON_SCHEMA`

- **Decision**: `schemas/graph/1.1.json` is today's `graph_json_schema.json` byte for byte; `1.0.json` is that file at `f260e2e6`. Each file's `$id` names its version. `maxitor_gnomon.schemas`: `graph_schema(version) -> dict` and `check_graph(document) -> None`, the latter reading `schema_version` and raising a refusal that names a missing or unknown version, or the first schema error with its JSON path. In AOA, `graph_json_schema.py` keeps `GRAPH_JSON_SCHEMA` as `graph_schema("1.1")`, so its 15 users change nothing; `graph_json_schema.json` is deleted from AOA; `aoa-action-machine` depends on `maxitor-gnomon`.
- **Rationale**: FR-002 – FR-004; one source of the schema, and a published version never edited.
- **Alternatives considered**: AOA keeping its own copy. Rejected: two copies drift.

## R4. The config, `gnomon.toml`

- **Decision**: in a repository's root; `[[graph]]` tables with `name` (unique), `cwd` (default `.`), `build` (a shell command), `file` (unique); paths relative to the config's folder. `schemas/config/1.0.json` describes it, and a top-level `gnomon = "1.0"` key names the config's own version. `maxitor_gnomon.config.read_config(path) -> list[Graph]` refuses naming the graph and the field.
- **Rationale**: FR-005; a config version from day one keeps the config, too, on the road to an open format.

## R5. `gnomon write` and `gnomon check`

- **Decision**: one console script, `gnomon`, with two subcommands; `--config` defaults to `gnomon.toml` in the current folder. For each graph: run `build` with `bash -c` in its `cwd`, as its own process, with a time limit of 300 s; read standard output; parse JSON; `check_graph`; serialise as `json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`. `write` writes the file only if its bytes differ (so an unchanged graph does not even touch the file's time); `check` writes nothing and compares. Graphs of one config run one after another. Exit codes: 0 — all current (or written); 1 — a file is stale, missing or a build failed; 2 — the config is refused.
- **Rationale**: FR-006 – FR-009, FR-007's "same bytes". 300 s is generous: the demo builds in about 2 s with its imports.

## R6. Naming the differences

- **Decision**: `check` parses the file and the new document and compares them generically: at the top level by key; inside arrays of objects that all carry an `id`, by `id` (added, removed, changed); inside objects by key, recursively; other values by equality. Each difference is one line — `edges[id=…].target_id: A → B`, `nodes[id=…]: added`, `schema_version: 1.0 → 1.1` — at most 20 lines, then "… and N more". When the parsed documents are equal but the bytes differ, it says that only the formatting differs. Every failure ends with the command that fixes it: `gnomon write --config …`.
- **Rationale**: FR-008; generic by `id`, so no knowledge of AOA's node or edge types.

## R7. The demo's and Maxitor's graphs

- **Decision**: two small modules print a graph and nothing else: `aoa.demo.graph_json` (imports the demo's sample modules and prints `build_registered_interchange_coordinator().to_json()`) and `aoa.maxitor.graph_json` (imports Maxitor's application module and prints `create_node_graph_coordinator().to_json()`, the graph Maxitor's machine is built with). The root `gnomon.toml` lists `demo` → `packages/aoa-demo/graph.json` and `maxitor` → `packages/aoa-maxitor/graph.json`, each built as `uv run --extra dev python -m …`, each in its own process. Both packages' sdists exclude `graph.json` (the demo's is about 4.5 MB).
- **Rationale**: FR-010, SC-004; a module per graph keeps the config short and the build reproducible.

## R8. The check run's last step

- **Decision**: `scripts/check_run.py` gets the package's steps (its wheel build, its pytest, its paths in mypy and vulture, the boundary rule) and one more step, `Graph files (gnomon write)`, with a new field `only_if_all_passed`: it starts after every other step has ended, and only if all of them passed; otherwise its log block says `SKIPPED Graph files (gnomon write): N step(s) failed`, and it counts neither as `OK` nor as `FAIL`. Like Ruff's auto-fix, it may change files, and the run stays green.
- **Rationale**: FR-010 as the maintainer decided: no graph is built for a run that already failed.

## R9. Documentation

- **Decision**: (1) `packages/maxitor-gnomon/README.md` — what the package is and its name; the graph document and matching by `id`; schema versions and the rule that a published version never changes; `gnomon.toml` field by field; `gnomon write`, `check`, `validate`, `skill` with real output; "How a graph travels with a pull request" (FR-012a); three ways to start (FR-012f); and the Russian draft beside it. (2) `docs/tutorials/step-00-get-started.md`: after Installation option A, a short section "Save your graph from day one" — why, and the three ways to start, linking to the package's README; in "Repository structure", `maxitor-gnomon/` in the `packages/` tree, marked as independent of AOA, and the stale "three packages" wording fixed. (3) `docs/tutorials/step-26-maxitor.md`: a section "The graph saved with every change" after "Every edge has an id" — the demo's and Maxitor's `graph.json` and `gnomon.toml`, the PR flow, `gnomon check`'s real output. (4) The root `README.md` packages table and a line under "VII Maxitor" in `docs/index.md`. (5) `examples/step_26_maxitor/12_graph_file.py` and its executed notebook, every case (FR-013), writing only to a temporary folder. Russian drafts beside each changed page.
- **Rationale**: Principle VI. Unlike #279's shell-only cases, most cases here are library calls whose results are worth seeing step by step (a schema check, differences by id), so the script and notebook of VI.5 are worth having; the get-started chapter is where a project should learn to save its graph from its first day.

## R10. The `gnomon-setup` skill, `gnomon validate` and `gnomon skill`

- **Decision**: the skill is one file, `src/maxitor_gnomon/skills/gnomon-setup/SKILL.md` — inside the import package, so it ships in the wheel, versions with the commands it drives, and `gnomon skill` can print it. Front matter: name `gnomon-setup`, a description that makes agents pick it for "set up / check graph history". Body: (1) "If you read this from a link": save this file as `.claude/skills/gnomon-setup/SKILL.md`, `.cursor/skills/gnomon-setup/SKILL.md` or `.dsh/skills/gnomon-setup/SKILL.md` (whichever this agent uses), then go on at once; (2) how to run `gnomon` — from git before publication, pinned to a commit in CI, from PyPI after; (3) **Setup**, as numbered steps: read `gnomon.toml` if any; for each configured graph run its build, `gnomon validate -` its output, compare with its file (`gnomon check`); search the repository for every other place that produces a graph document (code or endpoints emitting JSON with `schema_version`, `nodes`, `edges`; what the project's docs call its graph); draft a build command for each, run it in a process of its own and prove it with `gnomon validate -`; for each graph propose where its file goes — first places that follow the repository's conventions (folders that already hold generated or exported files, existing graph files, the service's own folder), then the standard `<service folder>/graph.json`, or a place the user names; show one table — service, folder, command, proof, proposed file and alternatives, state (current / stale / broken / new / refused); ask which to keep, add, fix or drop and where each file goes; then apply: edit `gnomon.toml`, `gnomon write`, add `gnomon check` to the CI the project uses (asking which if several), run `gnomon check`; stop without committing. Everything the skill needs — an example `gnomon.toml`, the CI step — is inside the file.
- **`gnomon validate <file | ->`** prints `ok 1.1: 3213 nodes, 4841 edges` or the refusal, exit 0 / 1; **`gnomon skill`** prints the skill file.
- **The README's three ways to start**: by hand (Get started), from the command line (`… gnomon skill > <agent skills folder>/gnomon-setup/SKILL.md`, then "run Setup"), and a one-sentence prompt with the skill's raw link (`raw.githubusercontent.com/…/SKILL.md`, not the HTML page).
- **Rationale**: FR-012c–f. The schema is the only test of "this is a graph", so the skill stays generic; one command for first and later setup means the same skill also audits.
- **How it is checked**: in this repository (Setup with no config finds the demo and Maxitor; again reports them current; with one entry broken reports it), and by the maintainer on gameoffer in each of the three ways (SC-007).
