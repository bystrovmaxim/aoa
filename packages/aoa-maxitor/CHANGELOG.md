# Changelog

All notable changes to `aoa-maxitor` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] – 2026-07-09

### Fixed

- **Frontend built with relative API paths.** Removed hardcoded `VITE_MAXITOR_API_BASE_URL=https://aoa.run/maxitor` and `--base=/maxitor/` from CI build; frontend now uses `--base=/` and relative `/api/` paths, making the package deployable at any domain or IP without rebuilding.

## [1.1.2] – 2026-07-09

### Changed

- **Dependencies updated to current PyPI releases.** `aoa-action-machine>=1.0.1a0` (was `>=1.0.0a4`), `duckdb>=1.5,<2` (was `>=1.1,<2`), `httpx>=0.28,<1.0` (was `>=0.27,<1.0`).

## [1.1.1] – 2026-07-08

### Fixed

- **Dependency `aoa-action-machine` pinned to non-existent stable version.** Changed `==1.0.0` → `>=1.0.0a4` so the package installs correctly from PyPI where only alpha releases are available. Similarly tightened `aoa-fastapi-adapter>=1.0.0a0` → `>=1.0.0`.

## [1.1.0] – 2026-07-08

### Added

- **Bundled React SPA.** The compiled Vite frontend (`src/aoa/maxitor/static/`) is now included in the wheel via hatchling `artifacts`. `pip install aoa-maxitor` delivers both the API backend and the complete web UI — no Node.js required on the server.
- **`StaticFiles` mount.** `create_app()` now mounts the bundled SPA at `/` (after all API routes) using FastAPI `StaticFiles(html=True)`, enabling SPA client-side routing fallback. The mount is skipped gracefully if the static directory is absent (dev environment without a built frontend).
- **`uvicorn>=0.30` added to runtime dependencies.** Previously an implicit transitive dependency; now declared explicitly so `pip install aoa-maxitor` pulls a working ASGI server.

### Deployment note

The frontend is built with `--base=/maxitor/` and `VITE_MAXITOR_API_BASE_URL=https://aoa.run/maxitor`. Nginx should proxy `location /maxitor/ { proxy_pass http://127.0.0.1:8101/; }` — the prefix is stripped before reaching uvicorn.

## [1.0.1] – 2026-06-27

### Changed

- **Test suite relocated into the package (`packages/aoa-maxitor/tests/`).** Maxitor unit tests moved out of the shared root `tests/maxitor/` into the package's own `tests/` directory, so the package is self-contained: test dependencies are declared in its `[dependency-groups]` dev group and pytest is configured via its own `[tool.pytest.ini_options]` (`testpaths`, `asyncio_mode`, `pythonpath`). The skipped integration test `test_load_aoa_service_action_integration.py` lives in the package alongside the maxitor unit tests (skipped by default — it requires a running `aoa-examples` service). ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **`LoadAOAServiceAction` — five-aspect DuckDB loader for the AOA coordinator graph.** Accepts a bare base URL or full endpoint URL; empty/whitespace input rejected by Pydantic. Aspects in order: validate URL format → normalize to canonical `coordinator-json` endpoint → validate HTTP reachability → parse coordinator JSON structure → build `DuckDBGraphResource`. 24 unit tests cover all aspects and Pydantic validation; integration test included but skipped by default (`@pytest.mark.skip`). ([#78](https://github.com/bystrovmaxim/aoa/issues/78))
- **`POST /api/load` — on-demand graph loading endpoint.** Accepts `{"service_url": "..."}`, runs `LoadAOAServiceAction` + `GetLeftMenuSidebarDataAction`, and stores results in `app.state`. The server no longer auto-loads a graph on startup; the graph is loaded only when the user provides a URL. `GET /api/sidebar` returns an empty payload when no graph is loaded. ([#78](https://github.com/bystrovmaxim/aoa/issues/78))
- **Left sidebar: URL input with recent history.** When no graph is loaded, the sidebar shows an `AOA Service URL` text field with an inline load button. The last 10 successfully used URLs are persisted in `localStorage` and shown below the input as a quick-select list. ([#78](https://github.com/bystrovmaxim/aoa/issues/78))
- **Left sidebar: switch-service button.** When a graph is loaded, a thin-stroke swap-arrows icon button appears in the sidebar header next to the collapse toggle. Clicking it clears the loaded graph from local state and returns to the URL input screen. ([#78](https://github.com/bystrovmaxim/aoa/issues/78))

### Changed

- **`GetLeftMenuSidebarDataAction` rewritten as a four-aspect DuckDB pipeline; `networkx` dependency removed.** The action no longer depends on `networkx`. Four `@regular_aspect` methods build sidebar `NodeEntity` lists in stages — level-1 root bucket nodes → level-2 fixed diagram rows → level-2 interchange nodes from DuckDB → level-3 per-domain ERD and per-entity class/lifecycle rows — with a `@summary_aspect` assembling the final `Result`. String helpers `_diagram_view_label` and `_lifecycle_state_machine_row_title` are `@staticmethod` methods on the class; aspect-level unit tests added. Deleted files: `api/session.py`, `node_build.py`, `interchange_demo_coordinator.py`, `model/diagrams/actions/load_graph_action.py`. ([#78](https://github.com/bystrovmaxim/aoa/issues/78))
