# Research: The Protocol in a Folder with No Code; Maxitor as One Package with Extras

Decisions taken while planning #286. Each one: what was chosen, why, and what was rejected.

## R1. How a Python package carries the protocol's schemas

**Decision**: each Python package keeps a committed copy of the schemas it needs beside its code — `aoa-action-machine` the one it produces (`1.1`), `maxitor` every version its `gnomon` command reads (`1.0`, `1.1`). A test in the check run compares every copy with the protocol folder's file byte for byte and fails naming both files.

**Rationale**: tried on 2026-10-29 with hatchling: `force-include` of `../open-gnomon-protocol/graph` works when the sdist is built, but `uv build` then builds the wheel *from the sdist*, where the sibling folder does not exist, and the build fails. Making it work needs two mappings (sdist into `src/…`, wheel none) plus a fallback for editable installs, which never see force-included files — the reason `maxitor_gnomon/shipped.py` exists today. A committed copy works the same in an editable install, an sdist and a wheel, needs no build trick and no `shipped.py`, and the byte-for-byte test makes drift impossible to merge. The spec (FR-004, FR-009) says "byte for byte the folder's file, proved by the check run" accordingly.

**Alternatives rejected**: force-include in both targets (fails as above); a custom hatch build hook that copies the files (more code, and still blind in editable installs); reading the schema over the network by its `$id` (a check must work offline and pinned).

## R2. Where the protocol lives, and its `$id`

**Decision**: `packages/open-gnomon-protocol/` with `README.md`, `CHANGELOG.md`, `graph/1.0.json`, `graph/1.1.json`; no `pyproject.toml`, not a workspace member, no `src/`. `$id` becomes `https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/open-gnomon-protocol/graph/<v>.json`. The config schema (`config/1.0.json`) leaves the protocol for `maxitor.gnomon`.

**Rationale**: the issue (1.1). A raw address returns the JSON itself, so a validator can fetch a schema by its `$id`; a `blob/` address returns a web page. The config is how the `gnomon` command reads a repository, not the language of the graph.

**Alternatives rejected**: keeping `blob/` addresses (not fetchable); a version-pinned tag in `$id` (the address would change with every release of the folder, while a published schema file never does).

## R3. The package's layout and the import rename

**Decision**: `packages/maxitor/` with `src/maxitor/{__init__.py, gnomon/, viewer/, skills/}`, `client/`, `graphs/viewer.json`, `action.yml`, `tests/{gnomon,viewer}/`. `aoa.maxitor` → `maxitor.viewer` and `aoa/maxitor` → `maxitor/viewer` everywhere outside old specs; `maxitor_gnomon` → `maxitor.gnomon`. The move is done with `git mv` so history follows the files.

**Rationale**: the issue (1.2). 1 366 mentions of `aoa.maxitor` inside the viewer and about 40 files outside it (examples, docs evidence, `.vscode/launch.json`, `.claude/launch.json`, `gnomon.toml`, workflows) are a mechanical rename; doing it in one commit per part keeps each commit testable.

**Alternatives rejected**: keeping `aoa.maxitor` as the import of a package named `maxitor` (two names for one thing — the offers constitution's rule 1, one term one name).

## R4. Extras and the commands without them

**Decision**:

| Extra | Dependencies |
|---|---|
| none | `jsonschema>=4.17,<5`, `jsonschema-rs>=0.60,<1` |
| `viewer` | `aoa-action-machine`, `aoa-fastapi-adapter>=1.3.0`, `duckdb>=1.5,<2`, `httpx>=0.28,<1.0`, `uvicorn>=0.30`, `websockets>=15` |
| `all` | `maxitor[viewer]` (and later `repo-graph-port`, #288) |

Commands: `gnomon = "maxitor.gnomon.cli:main"`, `maxitor-api = "maxitor.launch:viewer"`. `maxitor/launch.py` imports nothing heavy at module level; `viewer()` imports the server and, on `ModuleNotFoundError` for a dependency of the extra, prints `maxitor-api needs the viewer: pip install "maxitor[viewer]"` to standard error and exits 2.

**Rationale**: the issue (1.2): a command whose extra is missing names it. One small launcher keeps the rule in one place; the viewer's own code stays free of install checks.

**Alternatives rejected**: catching `ImportError` inside `maxitor.viewer` (the import fails before any code of the viewer runs); a separate `maxitor-viewer` distribution (the maintainer chose one package).

## R5. Boundaries inside the package

**Decision**: `scripts/package_boundaries.toml` describes the parts by their roots:

- `[packages.maxitor]` — roots `packages/maxitor/src/maxitor/viewer`, import prefixes `maxitor.viewer`, `may_import = ["action_machine", "gnomon"]`;
- `[standalone.gnomon]` — roots `packages/maxitor/src/maxitor/gnomon`, and a new key `forbid = ["maxitor.viewer"]` beside the existing ban on `aoa`;
- `gnomon` joins the canonical names so `maxitor.gnomon` imports from the viewer resolve.

`check_package_boundaries.py` learns `forbid` and the nested import prefix (`maxitor.viewer`, `maxitor.gnomon`, today it resolves only `aoa.<name>` and `<name>`).

**Rationale**: FR-013/014; the check run already runs this checker, so the rule costs no new step. The existing `import_prefixes = ["maxitor", …]` for the viewer would swallow `maxitor.gnomon`, so it narrows to `maxitor.viewer`.

**Alternatives rejected**: an import-linter dependency (a second tool for what the existing checker does with two small additions).

## R6. One graph per service

**Decision**: `graphs/viewer.json`, built by `python -m maxitor.viewer.build_graph`, which imports `maxitor.viewer.api.app` only. `gnomon.toml`'s Maxitor entry is renamed `viewer` and points there.

**Rationale**: FR-011; the offers constitution's rule 60 (a service's graph comes from its own code). The viewer is today the package's only service; `repo_graph_port` (#288) will run inside it and join its graph.

## R7. Version and changelog

**Decision**: `maxitor` starts at `3.0.0`, continuing the viewer's line (`aoa-maxitor` 2.3.0): its import changes, which is breaking. `packages/maxitor/CHANGELOG.md` continues `aoa-maxitor`'s; `maxitor-gnomon`'s single `0.1.0` entry is kept below a line saying it joined. The repository's `docs/CHANGELOG.md` gets the one article (Principle VI).

**Rationale**: the spec's assumption left the number to the plan; the viewer is the larger and older part and its users are the ones whose import changes.

## R8. The CI action

**Decision**: a composite action, `packages/maxitor/action.yml`, used as `uses: bystrovmaxim/aoa/packages/maxitor@<ref>`. Inputs: `config` (default `gnomon.toml`), `sync` (default `uv sync --all-extras`: the command that installs the project's environment, since builds run in it), `version` (default: the action's own ref's `maxitor`). Steps: `astral-sh/setup-uv`, the `sync` command, `uvx --from "maxitor==<version>" gnomon check --config <config>` — or, in this repository, the workspace's own `gnomon`.

**Rationale**: FR-016; GitHub runs an action from a repository subfolder by `owner/repo/path@ref`. Builds need the project's environment, which only the project knows how to install, hence the `sync` input.

## R9. The preview config

**Decision**: `.claude/launch.json`'s `maxitor-api` runs `uv run --extra dev uvicorn maxitor.viewer.api.app:app --host 127.0.0.1 --port 8000` (phase 1 commits the `--extra dev` fix with the current import; phase 3 renames the import and the client path).

**Rationale**: FR-018; the maintainer's decision of 2026-10-28.

## R10. Rules the code is written by

The maintainer decided (2026-10-29) that Maxitor follows the AOA development rules of the offers project's constitution, rules 41–66, beside this repository's own constitution. For this change, which moves code rather than writing new actions, the ones that bite are 54 (a file named after its class — the new `launch.py` holds functions, no class) and 60 (R6). Rules 41–53 and 55–66 are untouched: no action, resource, adapter or context changes here.
