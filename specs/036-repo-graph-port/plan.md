# Implementation Plan: Maxitor Reads a Graph's History from Its Repository

**Branch**: `feature/issue-288-repo-graph-port` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/036-repo-graph-port/spec.md` (issue #288, step 3 of 9 of #273)

## Summary

First, Maxitor's web part takes its name: `packages/maxitor/front/`, `maxitor.front`, `maxitor[front]`, the command `maxitor`. Then the port `maxitor.repo_graph_port` (`packages/maxitor/tools/repo_graph_port/`), a service of its own at `https://repo-graph-port.aoa.run` and the only part of Maxitor that talks to GitHub, reads a graph's history from its repository: a partial git mirror gives the versions (first-parent commits that changed the graph file) and their graphs byte for byte; the GitHub host gives each version's pull request and each tag's release, through a GitHub App for a private repository and anonymously for a public one; read keys open one history each through an AOA auth coordinator; webhooks, routed by git to the histories they change, and a fallback fetch keep it fresh. Three actions — `describe`, `history`, `version` — and a webhook action are the routes of the port's own server; Maxitor reads them over HTTP.

## Technical Context

**Language/Version**: Python ≥ 3.12; the front's client (TypeScript/React) only renamed paths.

**Primary Dependencies**: AOA (`aoa-action-machine`, `aoa-fastapi-adapter`); the `git` command; `PyJWT[crypto]` (the App's RS256 JWT); `httpx` (the host's REST API); `maxitor.graph_builder.schemas` (the protocol's schema check).

**Storage**: files — bare partial git mirrors and a per-`sha` cache under one cache folder; the histories config (TOML, `MAXITOR_HISTORIES`).

**Testing**: pytest; a git repository built per test in a temporary folder; a stand-in GitHub host; the boundary checker; the clean-install smoke test; the check run.

**Target Platform**: the port's own server (Linux container beside Maxitor's on the stand, macOS for development).

**Project Type**: web service — the port, its own server over its actions.

**Performance Goals**: a repeated `version` makes 0 host requests; an unchanged `history` costs a `304`; a history of a few hundred versions is listed within a second from the mirror.

**Constraints**: no key or token in logs, URLs or disk; one fetch per repository at a time; the port imports neither the front nor a tool, and the front does not import the port; the App's secrets only in the port's container.

**Scale/Scope**: the rename touches about 200 files (the sweep of #286); the core is new, about a dozen modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Each phase is a commit made only on the maintainer's word; no push, PR or merge without it. | ✅ |
| II. English | Code, docs, commits in English; only `tasks.ru_draft.md` and documentation `*.ru_draft.md` in Russian. | ✅ |
| III. Module headers | Every new module opens with its path, title and `PURPOSE` / `ARCHITECTURE / DATA FLOW`; renamed modules get their new path on line 1. | ✅ |
| IV. AI-CORE blocks | Every public action, resource and coordinator carries one. | ✅ |
| V. Short docstrings | Every class, function and method. | ✅ |
| VI. Tail | Phase 7 is three commits: the check run, the documentation (the core's README, the front's README, an executed example with script and notebook covering every case, the port's how-to, Russian drafts), the changelog article. | ✅ |
| Final step: the check run | Taken to zero; the two accepted remarks stay. | ✅ |

**The offers project's AOA rules 41–66** (research R11): actions with frozen contracts and aspects, resources with meaningful methods on the store directly (`GitMirror`, `GitHubHost`, `HistoriesConfig`), access through an auth coordinator and roles (R6), keys and tokens sensitive, environment through declared context, the front's graph from its own code. ✅

No violations; Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/036-repo-graph-port/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── actions.md        # describe, history, version, the webhook: inputs, results, refusals
│   ├── config.md         # the histories config and the key commands
│   └── rename.md         # what `front` replaces, everywhere
├── checklists/requirements.md
└── tasks.md (+ tasks.ru_draft.md)
```

### Source Code

```text
packages/maxitor/
├── pyproject.toml                         # extras: front, repo-graph-port, all; commands `maxitor`, `repo-graph-port`
├── front/                                 # was app/
│   ├── client/
│   ├── src/maxitor/front/                 # was maxitor/viewer; launch.py
│   ├── graph.json                         # the front's graph, unchanged but for the rename
│   ├── Dockerfile                         # --extra front
│   └── tests/
├── tools/
│   ├── graph_builder/
│   └── repo_graph_port/                   # a service of its own, moved from core/ on 2026-10-29
│       ├── src/maxitor/repo_graph_port/
│       │   ├── __init__.py
│       │   ├── repo_graph_domain.py
│       │   ├── history_reader_role.py
│       │   ├── actions/                   # describe_history_action.py, history_action.py, version_action.py, receive_host_event_action.py
│       │   ├── resources/                 # git_mirror.py, github_host.py, histories_config.py, version_cache.py
│       │   ├── auth/                      # history_key_auth_coordinator.py (+ extractor, authenticator)
│       │   ├── server.py                  # create_app(): FastApiAdapter over the actions, the webhook middleware
│       │   ├── launch.py                  # the command `repo-graph-port`: serve, or `history key …`
│       │   ├── build_graph.py             # the port's graph for graph-builder
│       │   └── cli.py                     # repo-graph-port history key new|revoke|list|check
│       ├── graph.json                     # the port's own graph
│       ├── Dockerfile                     # installs git; --extra repo-graph-port
│       └── tests/                         # fixtures: a git repository builder, a stand-in host
└── skills/
```

Outside: root `pyproject.toml` (workspace paths, mypy, vulture), `scripts/package_boundaries.toml` + checker, `scripts/check_run.py` (a pytest step for the core), `graph-builder.toml`, `.github/workflows/*`, `deploy/stand/docker-compose.yml` and `docker-compose.host.yml` (the port's service), `.claude/launch.json`, `.vscode/launch.json`, docs, examples, tests.

**Structure Decision**: the port in `tools/repo_graph_port/`, beside `graph_builder` — a service of its own with its own server, graph and image, not a core the front embeds (it was in `core/` until 2026-10-29); the front reads it over HTTP and does not import it.

## Phases → commits

| # | Phase (issue #288) | Contents | Proof |
|---|---|---|---|
| 0 | Design documents | `specs/036-repo-graph-port/` | — |
| 1 | The web part is `front` | the rename (R1), old-name test extended, `.claude/launch.json` | tests unchanged in count; graph differs only by prefix; break: one `maxitor.viewer` left → the old-name test names it |
| 2 | Versions from git | `GitMirror`, the version list, tags placed, graphs checked and counted; the core's package, extra and boundaries | a fixture repository gives exactly the expected versions and tags; break: drop `--first-parent` → the test fails naming a branch commit |
| 3 | The actions | `describe`, `history` (`after`, `304`), `version` (`immutable`), the per-`sha` cache | repeated `version` makes 0 mirror reads; break: cache keyed by path → the test fails |
| 4 | The port's server, read keys and public links | `server.py`, `launch.py`, the command `repo-graph-port`, the port's `graph.json`; config, auth coordinator, key CLI, the same "not found", the limit; the front no longer depends on the port | a key opens one history; no key in the log; `304` and `immutable` on the wire; break: compare keys in plain text → the hash test fails |
| 5 | GitHub | `GitHubHost`: App token, token as a per-call git header, PRs, releases, webhooks (signature middleware) routed to the histories they change (R12), fallback fetch | stand-in host: PR and release on versions; a push refreshes only the history whose file it changed; a bad signature is refused; no token in the mirror's `config` |
| 6 | Running on the stand | the port's container in `deploy/stand/` at `repo-graph-port.aoa.run`, with the histories config, cache volume and the App's secrets from its own environment file; read keys issued on the server (R10b) | the maintainer's private and public repositories answer live; a push shows at once; no token on the server; Maxitor's container holds no secret of the App |
| 7a–c | Tail | check run; documentation; changelog | examples run |

Adversarial verification in every test task.

## Complexity Tracking

No constitution violations.
