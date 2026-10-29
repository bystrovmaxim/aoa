# Tasks: Maxitor Reads a Graph's History from Its Repository

**Input**: Design documents from `specs/036-repo-graph-port/`

**Prerequisites**: plan.md, spec.md (US1–US5), research.md (R1–R11), data-model.md, contracts/ (actions.md, config.md, rename.md), quickstart.md

**Tests**: Required. Every new test is verified adversarially: break the code the way the test must catch, confirm that test fails and no other does, restore.

**Organization**: one phase = one commit. Commit 1 holds the design documents; commits 2–7 are #288's phases 1–6 (phase 6: running on the stand); #288's phase 7 is three commits (check run, documentation, changelog), commits 8–10. A commit is made only on the maintainer's word (constitution I). The full check run is run after code changes only, not after documentation edits.

**Issue checkboxes**: commit 2 → phase 1; 3 → 2; 4 → 3; 5 → 4; 6 → 5; 7 → 6; commits 8–10 → phase 7 (ticked after commit 10). Every tick carries its sha (`gh issue edit 288`, the body fetched and checked for length before it is written back).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US5)
- Every new module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every public action, resource, role and coordinator carries an AI-CORE block (IV); every class, function and method a one-line docstring (V). The code follows rules 41–66 (research R11): a file per class (54), constants inside the method that uses them (51), resources with meaningful methods only (52), environment only through declared context (63).
- Shorthand: `M` = `packages/maxitor`; `F` = `packages/maxitor/front`; `FS` = `packages/maxitor/front/src/maxitor/front`; `C` = `packages/maxitor/tools/repo_graph_port`; `CS` = `packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port`.
- Old specs and the past entries of every changelog keep their words.

---

## Phase 1: Setup — design documents (commit 1)

- [X] T001 Prepare commit 1 with `specs/036-repo-graph-port/` only (spec, plan, research, data model, contracts, quickstart, `checklists/requirements.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify repo_graph_port and the front (#288)`.

---

## Phase 2: Maxitor's web part is `front` (commit 2) · US1 — #288 phase 1

**Goal**: one name for Maxitor's web part everywhere (FR-001 – FR-003, contracts/rename.md).

**Independent test**: quickstart §1; tests unchanged in count; the front's graph differs only in its ids' prefix.

- [X] T002 Baseline: `bash scripts/run_checks_with_log.sh` on the branch at `aa3f4e90`; record the `OK` count and wall time here. **Recorded**: 40 of 40 steps `OK`, no `FAIL`; wall time 62.5 s.
- [X] T003 [US1] `git mv M/app F`; `git mv F/src/maxitor/viewer FS`; the front's graph stays `F/graph.json`.
- [X] T004 [US1] Rename in every tracked file except `specs/` and past changelog entries: `packages/maxitor/app` → `packages/maxitor/front`, `maxitor/viewer` → `maxitor/front`, `maxitor.viewer` → `maxitor.front`, `maxitor[viewer]` → `maxitor[front]`, the extra `viewer` → `front` in `M/pyproject.toml` (and `all = ["maxitor[front]"]`), `maxitor-api` → `maxitor`; line 1 of every moved module. Covers code, tests, `F/client` (build output path), `F/Dockerfile`, `deploy/stand/docker-compose.yml`, `.claude/launch.json`, `.vscode/launch.json`, the workflows, the root `pyproject.toml` (workspace dev-mode dirs, mypy, vulture, pytest paths, tasks), `scripts/check_run.py` (`Pytest maxitor/front`), `scripts/package_boundaries.toml`, `graph-builder.toml` (build `python -m maxitor.front.build_graph`, file `packages/maxitor/front/graph.json`), README, docs, examples, `tests/`.
- [X] T005 [US1] The command: `M/pyproject.toml` `maxitor = "maxitor.front.launch:main"`; `FS/launch.py` renames `viewer()` → `main()` and its hint → `maxitor needs its front: pip install "maxitor[front]"`; its test and the smoke test follow.
- [X] T006 [US1] `tests/scripts/test_no_old_names.py`: also fails on `maxitor.viewer`, `maxitor/viewer`, `maxitor[viewer]`, `packages/maxitor/app`, `maxitor-api` (pinned-tag lines aside, as today).
- [X] T007 [US1] `uv lock`, `uv sync --all-extras --reinstall-package maxitor`; `graph-builder write`; the old graph with `maxitor.viewer` → `maxitor.front` equals `F/graph.json`; record here. **Recorded**: `graph-builder write` → `ok maxitor (written)`; the graph of `7d760694` with `maxitor.viewer` → `maxitor.front` is byte for byte `F/graph.json` (`cmp`); `.venv/bin/maxitor` exists, `maxitor-api` is gone; test functions 1634 before and after.
- [X] T008 [US1] Adversarial, full check run each time: (1) one `maxitor.viewer` left in an example → only the old-name test fails, naming it; (2) the `front` extra's dependencies dropped from `M/pyproject.toml` → only the smoke test's run of `maxitor` fails. Restore. Check run green; prepare commit 2: `refactor(maxitor): the web part is front (#288)`; tick #288 phase 1. **Recorded**: (1) `# maxitor.viewer` appended to `examples/step_26_maxitor/12_graph_file.py` → one `FAIL`, `Pytest tests/scripts`, naming `examples/step_26_maxitor/12_graph_file.py:102: maxitor.viewer` (38 `OK`; the graph write is skipped on a red run, by design); (2) `front = []` → one `FAIL`, `Package metadata`, `maxitor: missing required dependency(ies): ['aoa-action-machine', 'aoa-fastapi-adapter']` (38 `OK`) — not the smoke test as this task expected: the smoke test covers the install without the extra, so it passes. Restored; check run 40 of 40 `OK`, 65.8 s.

---

## Phase 3: Versions from git (commit 3) · US2 — #288 phase 2

**Goal**: a history's versions and their tags from a repository (FR-004 – FR-009, research R2–R4).

**Independent test**: quickstart §2.

- [X] T009 [US2] The core's package: `CS/__init__.py`, `CS/py.typed`, `CS/repo_graph_domain.py` (`RepoGraphDomain`); `M/pyproject.toml` extra `repo-graph-port = ["aoa-action-machine>=1.0.1a0", "PyJWT[crypto]>=2.8,<3", "httpx>=0.28,<1.0"]`, `front` includes it; hatch `only-include`, `sources`, `dev-mode-dirs` gain `tools/repo_graph_port/src`; root `pyproject.toml` paths (mypy, vulture, pytest); `C/pytest.ini`; a `Pytest maxitor/tools/repo_graph_port` step in `scripts/check_run.py`; `scripts/package_boundaries.toml` `[packages.repo_graph_port]` (`may_import = ["action_machine", "graph_builder"]`), `front` may import it, it may not import `front`; `scripts/check_package_boundaries.py` adds `repo_graph_port` to `CANONICAL` and lets a `[packages.*]` entry name a standalone owner (`graph_builder`) in `may_import` (research R10a). Break: `repo_graph_port` importing `maxitor.front` → the boundary check names it; restore. **Recorded**: the checker already let a `[packages.*]` entry name a standalone owner (`front` named `graph_builder`), so it only gained `repo_graph_port` in `CANONICAL`; `[standalone.graph_builder]` also forbids `maxitor.repo_graph_port`; `tests/scripts/test_package_boundaries.py` gained two tests (the core importing the front is named; the core may use `graph_builder`, the front the core). Break: a module of the core importing `maxitor.front.launch` → one `FAIL`, `Package import boundaries (production)`: `…/_probe.py:4: context 'repo_graph_port' must not import package 'maxitor' via 'maxitor.front.launch'` (39 `OK`); restored.
- [X] T010 [US2] `CS/resources/git_mirror.py` — `GitMirror` (research R3): `open(repository)` (a bare `--filter=blob:none` clone under the cache folder, or a local path as it is), `fetch(repository)` (one at a time per repository), `versions(repository, branch, path)` (`git log --first-parent --format=%H%x1f%cI%x1f%B%x1e -- <path>`, oldest first), `file_at(repository, sha, path)` (`git show`, bytes), `tags(repository)` (`git for-each-ref refs/tags`, `name` and commit), `is_ancestor(repository, a, b)`; every call `subprocess.run` with an argument list, no shell, a timeout. **Recorded**: `is_ancestor` is replaced by `first_parents(repository, branch)` (`git rev-list --first-parent`): on one first-parent chain, ancestor-or-self is the order of the chain, so placement needs no git call per tag. `file_at` returns `None` when the commit has no such file (`git ls-tree` first); `open`, `fetch` and `file_at` take `auth`, extra environment for that call only; a failure or timeout is `GitError` naming the git subcommand only.
- [X] T011 [US2] `CS/history_versions.py` (pure functions, no I/O): place tags on versions (data-model: "the newest version whose commit is an ancestor-or-self of the tag's commit; a tag off that chain is not placed"); a version's facts from its graph bytes — counts, or `refused` with the reason from `maxitor.graph_builder.schemas.check_graph`.
- [X] T012 [P] [US2] `C/tests/repo_builder.py` — a fixture that builds a git repository in a temporary folder: commits on `main`, branches merged with `--no-ff`, a commit made directly on `main`, a merge that does not touch the graph file, tags on a version's commit and on a later commit, a tag on a side branch, a graph that fails its schema, a `1.0` graph.
- [X] T013 [US2] `C/tests/test_versions.py`: exactly the first-parent commits that changed the file, oldest first; branch commits absent; the untouched merge absent; every tag placed as data-model says, the side-branch tag not placed; each version's file byte for byte; a refused graph carries its reason; the `1.0` graph counted. Adversarial: drop `--first-parent` → a branch commit appears and only these tests fail; place a later tag on the next version → only the tag test fails. Restore. Record here. **Recorded**: 8 tests pass. Breaks, full check run each: (1) `--first-parent` dropped → one `FAIL`, `Pytest maxitor/tools/repo_graph_port`, three tests of this file, the version test saying `a1 is listed as a version` (39 `OK`); (2) a later tag placed on the next version → one `FAIL`, the same step, only `test_tags_land_on_the_version_they_belong_to` (39 `OK`). Restored; check run 41 of 41 `OK` (one step more: the core's tests), 67.4 s.
- [X] T014 [US2] Check run green; prepare commit 3: `feat(repo-graph-port): versions and tags from git (#288)`; tick #288 phase 2.

---

## Phase 4: The actions (commit 4) · US2, US4 — #288 phase 3

**Goal**: `describe`, `history`, `version` with their cache (FR-010, FR-017, contracts/actions.md, research R8–R9).

**Independent test**: the actions over a fixture repository; repeated reads.

- [X] T015 [US2] `CS/resources/version_cache.py` — `VersionCache`: per `(repository, sha)` the graph bytes and facts on disk, forever; per repository the tags and per `(repository, sha)` the pull request with the time they were read. **Recorded**: `VersionCache` keeps a version's bytes and facts by `(repository, sha)` on disk (written to a temporary name and renamed) and the time each repository was last fetched (in memory). The host's part — tags with releases and a version's pull request, with the time read — comes with the host in phase 6, where it is first used.
- [X] T016 [US2] `CS/actions/describe_history_action.py`, `history_action.py` (`after`), `version_action.py` — frozen `Params`/`Result`, logic in aspects, the mirror and the cache through `@depends`/connections; `history` fetches first when the mirror is older than the fallback interval (`MAXITOR_HISTORY_REFRESH_SECONDS`, default 600, through declared context); the mirrors and the cache live under `MAXITOR_HISTORY_CACHE` (default `~/.cache/maxitor/history`), through declared context. **Recorded**: the actions find a history through `HistoriesConfig`, written now with its `[[history]]` part (id, host, repository, branch, graph file; refused when out of shape); keys, `[github]` and rereading come in T019. `HistoryContext` declares `env.history_refresh_seconds` (`@env`); `MAXITOR_HISTORY_CACHE` is read where the port's server builds the resources (T023), not in an action. `VersionResult.graph` is the file's text; the port's route answers its bytes with `Cache-Control: immutable` (T023). A history on a host other than `local` is "not found" until phase 6. Every refusal is `HistoryNotFoundError("not found")`. `GitMirror.is_open` added.
- [X] T017 [P] [US4] `C/tests/test_actions.py`: the three answers on the fixture; `after` returns only later versions; a second `version` reads neither git nor the graph file again (a counting stand-in mirror); the fallback fetch happens only after the interval. Adversarial: key the cache by path instead of `sha` → only the repeated-read test fails. Restore. Record here. **Recorded**: 8 tests here, 16 in the core. Break, full check run: the cache keyed by the file's path instead of `sha` → one `FAIL`, `Pytest maxitor/tools/repo_graph_port` (39 `OK`), but three tests rather than the one this task expected: with that key every version after the first gets the first one's file, so every test that reads two versions sees it (the listing's counts, the repeated read, "each file once"). Restored; check run 41 of 41 `OK`, 63.6 s.
- [X] T018 Check run green; prepare commit 4: `feat(repo-graph-port): describe, history and version (#288)`; tick #288 phase 3.

---

## Phase 5: The port's own server, read keys and public links (commit 5) · US3 — #288 phase 4

**Goal**: the port runs as a service of its own; a key opens one history; public links need none (FR-004, FR-010 – FR-014, FR-019, contracts/actions.md, contracts/config.md, research R2, R6, R7, R9).

**Independent test**: quickstart §3.

- [X] T019 [US3] `CS/resources/histories_config.py` — `HistoriesConfig` whole: `[github]` and `[[history.keys]]` beside the `[[history]]` part of T016 (contracts/config.md); reread when the file's modification time changes; a key found only by its SHA-256; expiry honoured. **Recorded**: a broken file at runtime leaves the last accepted one in force; the id `public` is reserved; `__repr__` names the file only.
- [X] T020 [US3] `CS/history_reader_role.py` (`HistoryReaderRole`) and `CS/auth/` — `HistoryKeyCredentialExtractor` (header `X-Maxitor-History-Key`), `HistoryKeyAuthenticator` (hash, find, expiry; the key's `name` as `user_id`, the history id in the context), `HistoryKeyAuthCoordinator` (assembles a `HistoryContext`); wrong keys limited per client address per minute; the actions check the history against the context; every refusal `404 not found`, the limit `429`. **Recorded**: the reader is `HistoryReaderInfo(UserInfo)` with a `history` field; the coordinator never returns `None` — no key or a wrong key reads as a guest, so the action's one answer is "not found"; from the eleventh wrong key within a minute from one address, each further wrong key is `429`. Each read is logged as `History <id> listed for <name>`.
- [X] T021 [US3] Public links (contracts/actions.md, research R9): the actions accept `link=https://github.com/<owner>/<repo>/blob/<branch>/<path>` in place of an id, on the routes `/api/v1/history/public`, `/public/versions`, `/public/versions/{sha}`; no key (`GuestRole`), read anonymously, cached by the link's repository, branch and path; no session is kept. **Recorded**: the same three actions take `history` or `link` (exactly one); a public link is opened anonymously from `https://github.com/<owner>/<repo>.git`, and a repository that is missing or not public is "not found". Tests stand GitHub in with git's own `url.<folder>.insteadOf=https://github.com/`, set in the test's environment — no hook in the code.
- [X] T022 [US3] `CS/cli.py` — `repo-graph-port history key new|revoke|list|check` (contracts/config.md; exit codes 0/1/2). `CS/launch.py` — the command `repo-graph-port`: no arguments → serve; `history …` → the CLI; without the extra it names the extra, as `maxitor` does. `M/pyproject.toml`: `repo-graph-port = "maxitor.repo_graph_port.launch:main"`; the `repo-graph-port` extra gains `aoa-fastapi-adapter` and `uvicorn`; the `front` extra no longer includes it. `scripts/package_boundaries.toml`: the front's `may_import` drops `repo_graph_port`; `tests/scripts/test_package_boundaries.py` follows. **Recorded**: a wrong command line ends in argparse's own exit 2; the config is edited as text, so comments and order survive, and every edit is loaded and checked before it replaces the file.
- [X] T023 [US3] `CS/server.py` — `create_app()`: `FastApiAdapter` over the actions under `/api/v1/history/…` with the coordinator; `version` answered as the file's bytes, `application/json`, `Cache-Control: public, max-age=31536000, immutable`; the resources built from `MAXITOR_HISTORIES` and `MAXITOR_HISTORY_CACHE` (default `~/.cache/maxitor/history`), read where the server is built, not in an action; `/health`. `CS/build_graph.py` and `C/graph.json` — the port's own graph, a new entry in `graph-builder.toml`; `F/graph.json` does not change. **Recorded**: FastAPI refuses a `Response` class as a response model, so `VersionFileMiddleware` (transport) unwraps `{"graph": …}` into the file's bytes with `immutable`; `VersionParams` lists `sha` first (the adapter builds the endpoint's signature in field order). The port's graph: 46 nodes, 55 edges. **Moved**: the port sits in `packages/maxitor/tools/repo_graph_port/`, not `core/` (the maintainer, 2026-10-29: Maxitor talks to it as to a separate service); `core/` is gone, every path follows.
- [X] T024 [P] [US3] Tests `C/tests/test_keys.py` and `C/tests/test_server.py`: a key opens its history and not another of the same repository; unknown, revoked, expired → the same `404`; the limit → `429`; the config holds no key; the log of a test run, every refusal's body and the `repr` of the config, the coordinator and the resources hold the key's name and never the key (all searched for it); a public link opens with no key; `key new` prints a key once and writes only its hash; a repeated `history` with its `ETag` → `304`; `version` → the committed bytes with `immutable`. Adversarial: compare keys in plain text → only the hash test fails; log the header → only the log test fails. Restore. Record here. **Recorded**: 32 tests in the port. Breaks, full check run each: (1) `key new` also writes the key in plain text → one `FAIL`, `Pytest maxitor/tools/repo_graph_port`, only `test_key_new_prints_the_key_once_and_keeps_only_its_hash` (39 `OK`); (2) the coordinator prints the credentials it extracted → the same step, only `test_the_log_names_the_reader_never_the_key` (39 `OK`). Restored; pylint's two findings in `cli.py` (seven returns, a constant test) fixed by letting argparse exit; check run 41 of 41 `OK`, 66.6 s.
- [X] T025 Check run green; prepare commit 5: `feat(repo-graph-port): its own server, read keys and public links (#288)`; tick #288 phase 4.

---

## Phase 6: GitHub (commit 6) · US2, US4 — #288 phase 5

**Goal**: a private repository through the App; pull requests, releases; webhooks routed to the histories they change (FR-015, FR-018, FR-018a, research R5, R12).

**Independent test**: quickstart §4, against a stand-in host.

- [ ] T026 [US2] `CS/resources/github_host.py` — `GitHubHost`: `token_for(repository)` (App JWT RS256 via `PyJWT`, installation token kept in memory, renewed before its hour), `git_auth(repository)` — the token as an `Authorization` header passed to each git call through `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0=http.extraHeader`/`GIT_CONFIG_VALUE_0` in that call's environment; the remote URL holds no token (research R5, FR-024), `pull_request_of(repository, sha)`, `release_of(repository, tag)`, `verify_webhook(body, signature)` (HMAC-SHA256, constant-time compare); the App id, private key and webhook secret through declared context. A `github` history is opened in the mirror from `https://github.com/<owner>/<repo>.git`.
- [ ] T027 [US2] `history` fills each version's `pr` (or the commit's message) and each tag's `release` from the host; `VersionCache` gains the host's part deferred from T015: a repository's tags with their releases and a version's pull request, each with the time it was read, refreshed by a webhook or after the fallback interval.
- [ ] T028 [US4] `CS/actions/receive_host_event_action.py`, the route `POST /api/v1/history/events/github`, and `CS/webhook_signature_middleware.py` — an ASGI middleware on that route that checks `X-Hub-Signature-256` over the raw body before the adapter (research R9), `401` without reaching the action. Routing by research R12: `push` → the histories of that repository and branch, one fetch, new versions only where `GitMirror.changed(repository, before, after, path)` (`git log --first-parent before..after -- <path>`) is not empty, a whole recompute when `before` is zeros or not an ancestor; `create` of a tag → that repository's tags read again; `pull_request` edited or merged → the version whose commit is its `merge_commit_sha`, if any, gets its `pr` again; anything else → `204`, nothing done.
- [ ] T029 [P] [US4] `C/tests/stand_in_github.py` (a stand-in host over `httpx.MockTransport`) and `C/tests/test_github.py`: `pr` and `release` on versions; in a repository with two graph files, a push that changes one gives a new version to that history only and the other history reads nothing; a push that touches no graph file changes no history; a pull request whose merge commit is not a version changes nothing; a new version shows without waiting for the fallback interval; a bad signature → `401`, nothing done; the token is in no log, no error body and not in the mirror's `config` on disk (the file read and searched). Adversarial: skip the signature check → only the bad-signature test fails; refresh every history of the repository on a push → only the routing test fails; put the token in the remote URL → only the mirror-config test fails. Restore. Record here.
- [ ] T030 [US2] `C/Dockerfile` — `python:3.12-slim` with `git`, `--extra repo-graph-port`, `CMD ["repo-graph-port"]` on `0.0.0.0:8102`; the smoke test: a clean install without the extra, `repo-graph-port` names its extra and exits 2.
- [ ] T031 Check run green; prepare commit 6: `feat(repo-graph-port): GitHub, pull requests, releases and webhooks (#288)`; tick #288 phase 5.

---

## Phase 7: Running on the stand (commit 7) · US5 — #288 phase 6

**Goal**: the port, its own container, serves the maintainer's real repositories live at `https://repo-graph-port.aoa.run` (FR-022 – FR-025, research R10b).

**Independent test**: at `https://repo-graph-port.aoa.run`, every configured history answers; a push shows at once; no token on the server; Maxitor's container holds no secret of the App.

- [ ] T032 [US5] Before this phase, ask the maintainer for: the GitHub App created and installed on their private repositories (Contents, Metadata and Pull requests read-only; no Callback URL, no Setup URL, no user authorization; webhook URL `https://repo-graph-port.aoa.run/api/v1/history/events/github`, active, with its secret; events Push, Create, Pull request), its App ID, the list of repositories (`owner/repo`, branch, path of each `graph.json`), how the stand is deployed (host, script), and the host's front-end route from `repo-graph-port.aoa.run` to the alias `dev_aoa_repo_graph_port` (the DNS name points at `194.67.66.48` since 2026-10-29). Check that each repository has its `graph.json` on its branch; report any that has none instead of configuring it.
- [ ] T033 [US5] `deploy/stand/docker-compose.yml`: a service `repo-graph-port` built from `C/Dockerfile`, on `127.0.0.1:${REPO_GRAPH_PORT_PORT:-8102}:8102`, health check on `/health`, `MAXITOR_HISTORIES` (a config file on the server, mounted read-only), `MAXITOR_HISTORY_CACHE` (a named volume), `GITHUB_APP_PRIVATE_KEY` and `GITHUB_WEBHOOK_SECRET` from the server's environment file given to this service only (`env_file`, not in the repository); `docker-compose.host.yml`: the alias `dev_aoa_repo_graph_port` on `up2y-net`; the `maxitor` service unchanged; a `histories.example.toml` beside them with the shape and no secret; the stand's README says what the maintainer puts where.
- [ ] T034 [US5] The histories config for the chosen repositories (no key yet): private ones by `owner/repo`, public ones left to links; `repo-graph-port history check` on the server passes for each.
- [ ] T035 [US5] Deploy the stand the way agreed in T032; issue a read key per private history with `repo-graph-port history key new` on the server and hand it to the maintainer only, never into the repository.
- [ ] T036 [US5] Verify at `https://repo-graph-port.aoa.run`, and record here with real answers (keys shown as dots): `history` and `version` for every configured repository — a private one with its key, refused without it; a public one by its link; a merge into one repository shows in its next `history` at once; a push that touches no graph file adds no version; the App's token is in no server log and in no mirror's `config`, and the App's private key and webhook secret are not in Maxitor's container (both searched on the server). Prepare commit 7: `feat(stand): the repo-graph-port service at repo-graph-port.aoa.run (#288)`; tick #288 phase 6.

---

## Phase 8: Closing — check run, documentation, changelog (commits 8–10) — #288 phase 7

- [ ] T037 Closing check run to zero; record against T002. Commit 8 only if the run changed files: `chore(checks): the closing check run of #288 (#288)`.
- [ ] T038 Documentation: `C/README.md` (the port as a service: running it, the config, the keys, the App, the webhooks and which histories they change, the cache) and its `README.ru_draft.md`; `M/README.md` (the parts table: `front`, the `repo-graph-port` service and its extra) and its draft; `examples/step_26_maxitor/14_graph_history.py` and `.ipynb` — the port's server run in the example over a repository the example builds, with the stand-in host: versions with their pull requests, a tag on the version before it with its release, a refused version, one version's graph, `after`, a repeated read answered `304`, a public link with no key, a key opening one history and refusing another, the limit on wrong keys (`429`), a push that changes one of two graph files — every case executed (Principle VI); the port's setup as a how-to page (`docs/how-to/run-the-repo-graph-port.md` and its draft): the App, the environment, the config, keys, the webhook; the tutorial's step 26 points at it. Commit 9: `docs(repo-graph-port): reading a graph's history (#288)`.
- [ ] T039 Changelog: one article in `docs/CHANGELOG.md` — Maxitor's web part is `front` (`pip install "maxitor[front]"`, `maxitor`), and a new service, `repo-graph-port`, reads a service's graph history from its repository: what a version is, keys, public links, the webhook, what a user configures. The package's `CHANGELOG.md` entry. Commit 10: `docs(changelog): the repo-graph-port service reads a graph's history (#288)`; tick #288 phase 7.

---

## Dependencies & Execution Order

- Commit order is fixed: 1 → 2 → … → 10; each leaves the check run green.
- US1 (commit 2) first: every later path names `front`.
- Commit 3 (versions) before 4 (actions); the port's server and keys (5) need the actions; GitHub (6) needs the server for its webhook; the stand (7) needs GitHub and the maintainer's App.

## Parallel Opportunities

- T012 (the fixture) beside T010–T011.
- T017, T024, T029 (tests) beside the code of their phase once its interfaces exist.
- T033 (the stand's files) while the maintainer prepares the App (T032).

## Implementation Strategy

No MVP cut: the issue ships whole, commit by commit; between any two commits the repository works and the check run is green.
