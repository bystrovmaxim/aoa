# Contract: the names users and tools rely on

## What a user sees

| Name | Before | After | Changes in |
|---|---|---|---|
| Distribution | `maxitor` | `maxitor` | never |
| Commands | `maxitor`, `graph-builder`, `repo-graph-port` | same | never |
| Extra | `maxitor[front]` | `maxitor[web]` | phase 3 |
| Import path | `maxitor.front` | `maxitor.web` | phase 3 |
| Entry point of `maxitor` | `maxitor.front.launch:main` | `maxitor.web.launch:main` | phase 3 |
| Message without the extra | `maxitor needs its front: pip install "maxitor[front]"` | `maxitor needs its web part: pip install "maxitor[web]"` | phase 3 |
| Schema `$id` | `.../tools/graph_builder/src/maxitor/graph_builder/config_schema.json` | `.../tools/graph_builder/maxitor/graph_builder/config_schema.json` | phase 2 |

There is no alias for the old names. The distribution has never been published.

## What must follow a path

For each move (phases 1 and 2):

| File | Entries |
|---|---|
| `packages/maxitor/pyproject.toml` | `only-include`, `artifacts`, `dev-mode-dirs`, `sources`, the comment above them |
| `pyproject.toml` | `mypy_path`, `typecheck` (ending at `/maxitor`, see R3), vulture paths, per-file ruff rules |
| `scripts/package_boundaries.toml` | roots |
| `packages/maxitor/<part>/pytest.ini` | `pythonpath = .` |
| `tests/scripts/test_schema_copies.py` | `graph_builder`'s three schema copies |
| `packages/aoa-action-machine/tests/support/isolated_entity_models.py` | the `sys.path` entry (`front`) |
| `packages/maxitor/front/tests/test_maxitor_names_no_kind_words.py` | the scanned folder (`front`) |
| `packages/maxitor/front/Dockerfile` | the `static` target (`front`) |
| `.gitignore` | the `static` folder (`front`) |
| `.github/workflows/publish.yml` | `--outDir ../maxitor/front/static` (`front`) |
| `examples/step_26_maxitor/05_full_graph_in_the_browser.{py,ipynb}` | `STATIC` and the `cp -R` text (`front`) |
| every moved module | line 1 |
| `config_schema.json` | `$id` (`graph_builder`) |

For the rename (phase 3), all of the `front` rows above, and:

| File | Entries |
|---|---|
| `packages/maxitor/pyproject.toml` | the extra, `all`, the `maxitor` script |
| `uv.lock` | regenerated for the extra |
| both Dockerfiles' `uv sync --extra` | `web` for the part's own image |
| `scripts/check_run.py` | `CLIENT`, the test package list |
| `scripts/run_checks_with_log.sh` | the client's folder |
| `scripts/check_package_metadata.py` | `AOA_ONLY_IN_EXTRA` |
| `graph-builder.toml` | the build module, the file |
| `.github/workflows/ci.yml`, `publish.yml` | the client's paths |
| `deploy/stand/docker-compose.yml` | the Dockerfile path |
| `.claude/launch.json`, `.vscode/launch.json` | paths and modules |
| `packages/maxitor/.../client/scripts/check-layout-determinism.ts` | the `uvicorn` target |
| `tests/packaging/test_wheel_install_smoke.py`, `front/tests/test_launch.py` | the expected message and the extra |
| `examples/`, `docs/reports/evidence/` | every `maxitor.front` import |

The search of SC-001 is the final word on this list.
