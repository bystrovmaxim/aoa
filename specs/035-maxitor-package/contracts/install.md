# Contract: installing `maxitor`

| Install | Brings | `graph-builder` | `maxitor-api` |
|---|---|---|---|
| `pip install maxitor` | `jsonschema`, `jsonschema-rs` and their own dependencies | works | exits 2, stderr: `maxitor-api needs the viewer: pip install "maxitor[viewer]"` |
| `pip install "maxitor[viewer]"` | + `aoa-action-machine`, `aoa-fastapi-adapter`, `duckdb`, `httpx`, `uvicorn`, `websockets` | works | serves Maxitor as `aoa-maxitor` 2.3.0 did |
| `pip install "maxitor[all]"` | everything above | works | works |

Guarantees:

1. A no-extra install contains no distribution named `aoa-*` and none of `fastapi`, `uvicorn`, `duckdb`, `httpx`, `websockets` (checked in a clean venv by `tests/packaging/test_wheel_install_smoke.py`).
2. Every install contains the whole wheel: `maxitor.viewer` and its built front are present even without `[viewer]`; only their dependencies are not.
3. `graph-builder --version` prints `graph-builder <maxitor version>`; `graph-builder skill` prints `graph-builder-setup`'s `SKILL.md`.
4. Running without installing: `uvx --from maxitor graph-builder check`; pinned: `uvx --from "maxitor==3.0.0" graph-builder check`.
5. Python API for the command: `from maxitor.graph_builder.schemas import check_graph, graph_schema`, `from maxitor.graph_builder.config import read_config` — same behaviour as `maxitor_gnomon`'s.
