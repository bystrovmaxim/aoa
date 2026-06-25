# Changelog

All notable changes to `aoa-maxitor` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
