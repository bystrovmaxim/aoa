# Changelog

All notable changes to `aoa-maxitor` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`LoadAOAServiceAction` — five-aspect DuckDB loader for the AOA coordinator graph.** Accepts a bare base URL or full endpoint URL; empty/whitespace input rejected by Pydantic. Aspects in order: validate URL format → normalize to canonical `coordinator-json` endpoint → validate HTTP reachability → parse coordinator JSON structure → build `DuckDBGraphResource`. 24 unit tests cover all aspects and Pydantic validation; integration test included but skipped by default (`@pytest.mark.skip`). ([#78](https://github.com/bystrovmaxim/aoa/issues/78))

### Changed

- **`GetLeftMenuSidebarDataAction` rewritten as a four-aspect DuckDB pipeline; `networkx` dependency removed.** The action no longer depends on `networkx`. Four `@regular_aspect` methods build sidebar `NodeEntity` lists in stages — level-1 root bucket nodes → level-2 fixed diagram rows → level-2 interchange nodes from DuckDB → level-3 per-domain ERD and per-entity class/lifecycle rows — with a `@summary_aspect` assembling the final `Result`. String helpers `_diagram_view_label` and `_lifecycle_state_machine_row_title` are `@staticmethod` methods on the class; aspect-level unit tests added. Deleted files: `api/session.py`, `node_build.py`, `interchange_demo_coordinator.py`, `model/diagrams/actions/load_graph_action.py`. ([#78](https://github.com/bystrovmaxim/aoa/issues/78))
