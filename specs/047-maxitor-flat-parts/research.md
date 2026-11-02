# Research: Maxitor parts one level shallower, and `front` named `web`

Everything below was checked against the code on 197415c3. Nothing was left open.

## R1. The wheel builds the same from the flat shape

**Decision**: point `only-include`, `sources`, `artifacts` and `dev-mode-dirs` at `<part>/maxitor` and `<part>`.

**Rationale**: a trial build of both shapes, in a throwaway copy with a stand-in `static/index.html`, gave wheels with the identical list of 176 files. The flat wheel has no `tests/`, `client/`, `Dockerfile`, `graph.json`, `pytest.ini` or `action.yml`, and it does carry `maxitor/front/static/`.

**Alternatives considered**: keeping the folders and remapping them at build time. Rejected, as in the issue: mypy, pytest, vulture and the editable install read the real folders.

## R2. What dropping `src/` really costs

**Decision**: accept it, and record it. The issue says `src/` "buys nothing"; that is nearly true, not fully.

**Rationale**: `src/` kept a part's `tests/` and its top-level scripts off the import path. Without it, the editable install puts each part's outer folder on `sys.path`, so five `tests` packages and `front/collect_python_files.py` become importable by name.

Nothing depends on that today: `from tests` / `import tests` appears 0 times in `packages/maxitor` and `tests/`. The check run starts one pytest process per part, and each part's tests are packages, so pytest puts that part's folder first. The risk is limited to a future `import tests` in one process resolving to the wrong part. The wheel is not affected (R1).

**Alternatives considered**: renaming every `tests/` to a unique name. Rejected: it is a large change against a risk nothing triggers.

## R3. The type-check target must stop at the code

**Decision**: the `typecheck` task names `packages/maxitor/<part>/maxitor`, while `mypy_path` and pytest's `pythonpath` name `packages/maxitor/<part>`.

**Rationale**: `mypy packages/maxitor/front/src` read code only. A mechanical `s#/src##` would give `mypy packages/maxitor/front`, which also reads `tests/` and `client/`. So the path edit cannot be one blind substitution.

**Alternatives considered**: `exclude` patterns in the mypy configuration. Rejected: naming the code is simpler than excluding the rest.

## R4. Every place that names a moved path

**Decision**: the list in [contracts/names.md](contracts/names.md), on top of the one in the issue.

Found beyond the issue's list, by search:

| Place | What it holds |
|---|---|
| `.github/workflows/publish.yml:134,139` | the client's folder and its relative `--outDir` |
| `.github/workflows/ci.yml:34` | the client's lockfile path |
| `packages/aoa-action-machine/tests/support/isolated_entity_models.py:65` | a `sys.path` entry, in another package |
| `packages/maxitor/core/*/pytest.ini` | `pythonpath = src` in the two parts the issue did not know |
| `examples/step_26_maxitor/05_full_graph_in_the_browser.{py,ipynb}` | a runtime `STATIC` path |
| `deploy/stand/docker-compose.yml:28` | the Dockerfile path |
| `graph-builder.toml:12-13` | the build module and the graph file |
| `scripts/check_package_metadata.py:68` | the extra `front` |
| `packages/maxitor/front/client/scripts/check-layout-determinism.ts:182` | the `uvicorn maxitor.front...` target |
| `.claude/launch.json`, `.vscode/launch.json` | run configurations |
| `packages/maxitor/front/src/maxitor/front/launch.py:28` | the message a user sees |
| `uv.lock` | the extra's name; the Dockerfiles run `uv sync --frozen`, so a stale lock breaks the image build |

`check-layout-determinism.ts` runs only in `check_before_pr.sh`, so `check_before_commit.sh` does not catch a miss there. The search of SC-001 does.

## R5. The graph's reverse replacement is exact

**Decision**: SC-004 is checked by replacing `maxitor.web` with `maxitor.front` in `web/graph.json` and comparing bytes.

**Rationale**: `maxitor.front` is the only `maxitor.*` prefix in that file (2074 occurrences), and `.web` occurs 0 times today, so the reverse replacement cannot hit anything else. No other id sorts between the two names, so the order of the file does not change. The file has no hash or build stamp, only `edges`, `nodes` and `schema_version`.

This holds only if phase 3 changes no text that feeds the graph, which sets R6.

## R6. Identifiers change, prose in code does not

**Decision**: phase 3 changes the names `maxitor.front`, `maxitor[front]`, `packages/maxitor/front` and the extra `front`. Comments and docstrings that say "the front" in plain words stay in this work. READMEs and `docs/` are updated in phase 4. The message in `launch.py` is an exception, because a user reads it.

**Rationale**: docstrings can feed the graph's descriptions, and SC-004 must stay a mechanical proof.

**Alternatives considered**: rewording all prose in code in phase 3. Rejected: it mixes a rename with a text edit and loses the proof.

The message becomes `maxitor needs its web part: pip install "maxitor[web]"`, and `FRONT_HINT` becomes `WEB_HINT`.

## R7. Import order changes with the name

**Decision**: let the check run's `ruff check --fix` reorder imports in phase 3, and review the result.

**Rationale**: `maxitor.web` sorts after `maxitor.repo_graph_port`, where `maxitor.front` sorted before it. The change is in the import blocks only.

## R8. Phase 1 mixes shapes for one commit

**Decision**: accepted. After phase 1, `front` is flat and the other four parts still have `src/`.

**Rationale**: each part has its own entries in every configuration, so the two shapes do not interfere, and the check run can be green on each commit.

## R9. Principle III names `packages/*/src`

**Decision**: the moved modules keep the header, and the constitution's wording is left to the maintainer. Line 1 names the new path.
