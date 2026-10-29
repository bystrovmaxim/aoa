# Research: The Protocol in a Folder with No Code; Maxitor as One Package with Extras

Decisions taken while planning #286. Each one: what was chosen, why, and what was rejected.

## R1. How a Python package carries the protocol's schemas

**Decision**: each Python package keeps a committed copy of the schemas it needs beside its code — `aoa-action-machine` the one it produces (`1.1`), `maxitor` every version its `graph-builder` command reads (`1.0`, `1.1`). A test in the check run compares every copy with the protocol folder's file byte for byte and fails naming both files.

**Rationale**: tried on 2026-10-29 with hatchling: `force-include` of `../open-gnomon-protocol/graph` works when the sdist is built, but `uv build` then builds the wheel *from the sdist*, where the sibling folder does not exist, and the build fails. Making it work needs two mappings (sdist into `src/…`, wheel none) plus a fallback for editable installs, which never see force-included files — the reason `maxitor_gnomon/shipped.py` exists today. A committed copy works the same in an editable install, an sdist and a wheel, needs no build trick and no `shipped.py`, and the byte-for-byte test makes drift impossible to merge. The spec (FR-004, FR-009) says "byte for byte the folder's file, proved by the check run" accordingly.

**Alternatives rejected**: force-include in both targets (fails as above); a custom hatch build hook that copies the files (more code, and still blind in editable installs); reading the schema over the network by its `$id` (a check must work offline and pinned).

## R2. Where the protocol lives, and its `$id`

**Decision**: `packages/open-gnomon-protocol/` with `README.md`, `CHANGELOG.md`, `graph/1.0.json`, `graph/1.1.json`; no `pyproject.toml`, not a workspace member, no `src/`. `$id` becomes `https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/open-gnomon-protocol/graph/<v>.json`. The config schema (`config/1.0.json`) leaves the protocol for `maxitor.graph_builder`.

**Rationale**: the issue (1.1). A raw address returns the JSON itself, so a validator can fetch a schema by its `$id`; a `blob/` address returns a web page. The config is how the `graph-builder` command reads a repository, not the language of the graph.

**Alternatives rejected**: keeping `blob/` addresses (not fetchable); a version-pinned tag in `$id` (the address would change with every release of the folder, while a published schema file never does).

## R3. The package's layout and the import rename

**Decision**: `packages/maxitor/` with `src/maxitor/{__init__.py, gnomon/, viewer/, skills/}`, `client/`, `app/graph.json`, `action.yml`, `tests/{gnomon,viewer}/`. `aoa.maxitor` → `maxitor.viewer` and `aoa/maxitor` → `maxitor/viewer` everywhere outside old specs; `maxitor_gnomon` → `maxitor.graph_builder`. The move is done with `git mv` so history follows the files.

**Rationale**: the issue (1.2). 1 366 mentions of `aoa.maxitor` inside the viewer and about 40 files outside it (examples, docs evidence, `.vscode/launch.json`, `.claude/launch.json`, `graph-builder.toml`, workflows) are a mechanical rename; doing it in one commit per part keeps each commit testable.

**Alternatives rejected**: keeping `aoa.maxitor` as the import of a package named `maxitor` (two names for one thing — the offers constitution's rule 1, one term one name).

## R4. Extras and the commands without them

**Decision**:

| Extra | Dependencies |
|---|---|
| none | `jsonschema>=4.17,<5`, `jsonschema-rs>=0.60,<1` |
| `viewer` | `aoa-action-machine`, `aoa-fastapi-adapter>=1.3.0`, `duckdb>=1.5,<2`, `httpx>=0.28,<1.0`, `uvicorn>=0.30`, `websockets>=15` |
| `all` | `maxitor[viewer]` (and later `repo-graph-port`, #288) |

Commands: `graph_builder = "maxitor.graph_builder.cli:main"`, `maxitor-api = "maxitor.launch:viewer"`. `maxitor/launch.py` imports nothing heavy at module level; `viewer()` imports the server and, on `ModuleNotFoundError` for a dependency of the extra, prints `maxitor-api needs the viewer: pip install "maxitor[viewer]"` to standard error and exits 2.

**Rationale**: the issue (1.2): a command whose extra is missing names it. One small launcher keeps the rule in one place; the viewer's own code stays free of install checks.

**Alternatives rejected**: catching `ImportError` inside `maxitor.viewer` (the import fails before any code of the viewer runs); a separate `maxitor-viewer` distribution (the maintainer chose one package).

## R5. Boundaries inside the package

**Decision**: `scripts/package_boundaries.toml` describes the parts by their roots:

- `[packages.maxitor]` — roots `packages/maxitor/app/src/maxitor/viewer`, import prefixes `maxitor.viewer`, `may_import = ["action_machine", "graph_builder"]`;
- `[standalone.graph_builder]` — roots `packages/maxitor/tools/graph_builder/src/maxitor/graph_builder`, and a new key `forbid = ["maxitor.viewer"]` beside the existing ban on `aoa`;
- `graph-builder` joins the canonical names so `maxitor.graph_builder` imports from the viewer resolve.

`check_package_boundaries.py` learns `forbid` and the nested import prefix (`maxitor.viewer`, `maxitor.graph_builder`, today it resolves only `aoa.<name>` and `<name>`).

**Rationale**: FR-013/014; the check run already runs this checker, so the rule costs no new step. The existing `import_prefixes = ["maxitor", …]` for the viewer would swallow `maxitor.graph_builder`, so it narrows to `maxitor.viewer`.

**Alternatives rejected**: an import-linter dependency (a second tool for what the existing checker does with two small additions).

## R6. One graph per service

**Decision**: `app/graph.json`, built by `python -m maxitor.viewer.build_graph`, which imports `maxitor.viewer.api.app` only. `graph-builder.toml`'s Maxitor entry is renamed `viewer` and points there.

**Rationale**: FR-011; the offers constitution's rule 60 (a service's graph comes from its own code). The viewer is today the package's only service; `repo_graph_port` (#288) will run inside it and join its graph.

## R7. Version and changelog

**Decision**: `maxitor` starts at `3.0.0`, continuing the viewer's line (`aoa-maxitor` 2.3.0): its import changes, which is breaking. `packages/maxitor/CHANGELOG.md` continues `aoa-maxitor`'s; `maxitor-gnomon`'s single `0.1.0` entry is kept below a line saying it joined. The repository's `docs/CHANGELOG.md` gets the one article (Principle VI).

**Rationale**: the spec's assumption left the number to the plan; the viewer is the larger and older part and its users are the ones whose import changes.

## R8. The CI action

**Decision**: a composite action, `packages/maxitor/tools/graph_builder/action.yml`, used as `uses: bystrovmaxim/aoa/packages/maxitor/tools/graph_builder@<ref>`. Inputs: `config` (default `graph-builder.toml`), `sync` (default `uv sync --all-extras`: the command that installs the project's environment, since builds run in it), `version` (default: the action's own ref's `maxitor`). Steps: `astral-sh/setup-uv`, the `sync` command, `uvx --from "maxitor==<version>" graph-builder check --config <config>` — or, in this repository, the workspace's own `graph-builder`.

**Rationale**: FR-016; GitHub runs an action from a repository subfolder by `owner/repo/path@ref`. Builds need the project's environment, which only the project knows how to install, hence the `sync` input.

## R9. The preview config

**Decision**: `.claude/launch.json`'s `maxitor-api` runs `uv run --extra dev uvicorn maxitor.viewer.api.app:app --host 127.0.0.1 --port 8000` (phase 1 commits the `--extra dev` fix with the current import; phase 3 renames the import and the client path).

**Rationale**: FR-018; the maintainer's decision of 2026-10-28.

## R10. Rules the code is written by

The maintainer decided (2026-10-29) that Maxitor follows the AOA development rules of the offers project's constitution, rules 41–66, beside this repository's own constitution. For this change, which moves code rather than writing new actions, the ones that bite are 54 (a file named after its class — the new `launch.py` holds functions, no class) and 60 (R6). Rules 41–53 and 55–66 are untouched: no action, resource, adapter or context changes here.

## R11. The layout by kind (the maintainer's correction, 2026-10-29)

**Decision**: one pip package, `maxitor`, whose folder is laid out by kind, not by Python's needs: `app/` holds the application and only it (front, server `maxitor.viewer`, `graph.json`, Dockerfile, tests); `tools/<name>/` holds each tool with its own `src/` and `tests/` (`tools/graph_builder/`, with its CI `action.yml`; `tools/gateway/` later, with its own `graph.json`); `skills/` holds the skills, apart from the code; `core/` will hold the code the application and the tools share (`core/repo_graph_port`, #288). `maxitor` is a namespace package: hatch's `sources` maps `app/src` and `tools/graph_builder/src` onto the wheel's root, `force-include` puts `skills/` at `maxitor/skills`, and `dev-mode-dirs` lists both `src` folders for the editable install. A service keeps `graph.json` in its own folder. This supersedes the single `src/maxitor/` of R3, `graphs/viewer.json` of R6, and the action's path in R8.

**Rationale**: commits 4–6 had made the application's folder the package's folder, so the command, the skill and the CI action ended up inside the application. A new tool now means one folder under `tools/`, one line in `pyproject.toml`, and its boundary rule; the application is not touched. Tried in a scratch project before the move: the wheel built through the sdist holds `maxitor/viewer`, `maxitor/graph_builder` and `maxitor/skills`; the editable install imports both parts and carries a copy of the skills (it is refreshed by `uv sync --reinstall-package maxitor`).
