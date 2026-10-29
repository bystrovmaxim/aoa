# Implementation Plan: Maxitor Reads a Graph's History from Its Repository

**Branch**: `feature/issue-288-repo-graph-port` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/036-repo-graph-port/spec.md` (issue #288, step 3 of 9 of #273)

## Summary

First, Maxitor's web part takes its name: `packages/maxitor/front/`, `maxitor.front`, `maxitor[front]`, the command `maxitor`. Then the core `maxitor.repo_graph_port` (`packages/maxitor/core/repo_graph_port/`) reads a graph's history from its repository: a partial git mirror gives the versions (first-parent commits that changed the graph file) and their graphs byte for byte; the GitHub host gives each version's pull request and each tag's release, through a GitHub App for a private repository and anonymously for a public one; read keys open one history each through an AOA auth coordinator; webhooks and a fallback fetch keep it fresh. Three actions — `describe`, `history`, `version` — and a webhook action are mounted in the front's server.

## Technical Context

**Language/Version**: Python ≥ 3.12; the front's client (TypeScript/React) only renamed paths.

**Primary Dependencies**: AOA (`aoa-action-machine`, `aoa-fastapi-adapter`); the `git` command; `PyJWT[crypto]` (the App's RS256 JWT); `httpx` (the host's REST API); `maxitor.graph_builder.schemas` (the protocol's schema check).

**Storage**: files — bare partial git mirrors and a per-`sha` cache under one cache folder; the histories config (TOML, `MAXITOR_HISTORIES`).

**Testing**: pytest; a git repository built per test in a temporary folder; a stand-in GitHub host; the boundary checker; the clean-install smoke test; the check run.

**Target Platform**: Maxitor's server (Linux container, macOS for development).

**Project Type**: web service (the front's server) plus a library core.

**Performance Goals**: a repeated `version` makes 0 host requests; an unchanged `history` costs a `304`; a history of a few hundred versions is listed within a second from the mirror.

**Constraints**: no key or token in logs, URLs or disk; one fetch per repository at a time; the core imports neither the front nor a tool.

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
| VI. Tail | Phase 7 is three commits: the check run, the documentation (the core's README, the front's README, an executed example with script and notebook covering every case, the stand's how-to, Russian drafts), the changelog article. | ✅ |
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
├── pyproject.toml                         # extras: front (includes repo-graph-port), repo-graph-port, all; command `maxitor`
├── front/                                 # was app/
│   ├── client/
│   ├── src/maxitor/front/                 # was maxitor/viewer; launch.py; api/app.py mounts the history routes
│   ├── graph.json                         # the front's graph, now with the core's actions
│   ├── Dockerfile                         # installs git; --extra front
│   └── tests/
├── core/
│   └── repo_graph_port/
│       ├── src/maxitor/repo_graph_port/
│       │   ├── __init__.py
│       │   ├── repo_graph_domain.py
│       │   ├── history_reader_role.py
│       │   ├── actions/                   # describe_history_action.py, history_action.py, version_action.py, receive_host_event_action.py
│       │   ├── resources/                 # git_mirror.py, github_host.py, histories_config.py, version_cache.py
│       │   ├── auth/                      # history_key_auth_coordinator.py (+ extractor, authenticator)
│       │   └── cli.py                     # maxitor history key new|revoke|list|check
│       └── tests/                         # fixtures: a git repository builder, a stand-in host
├── tools/graph_builder/
└── skills/
```

Outside: root `pyproject.toml` (workspace paths, mypy, vulture), `scripts/package_boundaries.toml` + checker, `scripts/check_run.py` (a pytest step for the core), `graph-builder.toml`, `.github/workflows/*`, `deploy/stand/docker-compose.yml`, `.claude/launch.json`, `.vscode/launch.json`, docs, examples, tests.

**Structure Decision**: the core in `core/`, shared by the front and later tools; the front only mounts it.

## Phases → commits

| # | Phase (issue #288) | Contents | Proof |
|---|---|---|---|
| 0 | Design documents | `specs/036-repo-graph-port/` | — |
| 1 | The web part is `front` | the rename (R1), old-name test extended, `.claude/launch.json` | tests unchanged in count; graph differs only by prefix; break: one `maxitor.viewer` left → the old-name test names it |
| 2 | Versions from git | `GitMirror`, the version list, tags placed, graphs checked and counted; the core's package, extra and boundaries | a fixture repository gives exactly the expected versions and tags; break: drop `--first-parent` → the test fails naming a branch commit |
| 3 | The actions | `describe`, `history` (`after`, `304`), `version` (`immutable`), the per-`sha` cache | repeated `version` makes 0 mirror reads; break: cache keyed by path → the test fails |
| 4 | Read keys and public links in Maxitor | config, auth coordinator, key CLI, the same "not found", the limit, routes in the front | a key opens one history; no key in the log; break: compare keys in plain text → the hash test fails |
| 5 | GitHub | `GitHubHost`: App token, token as a per-call git header, PRs, releases, webhooks (signature middleware), fallback fetch | stand-in host: PR and release on versions; a webhook refreshes at once; a bad signature is refused; no token in the mirror's `config` |
| 6 | Running on the stand | `deploy/stand/` with the histories config, cache volume and the App's secrets from the server's environment; read keys issued on the server (R10b) | the maintainer's private and public repositories answer live; a push shows at once; no token on the server |
| 7a–c | Tail | check run; documentation; changelog | examples run |

Adversarial verification in every test task.

## Complexity Tracking

No constitution violations.
