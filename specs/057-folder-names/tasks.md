# Tasks: Maxitor's parts in folders named the way people call them

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md)

Each phase is one commit. After a phase only its own tests run.

## Phase 1: The port follows a file through a move (US2)

- [ ] T001 [US2] `GitMirror.earlier_paths(repository, branch, path)`: the paths `path` had before, newest first, from `git log --first-parent --follow --name-status`, in `packages/maxitor/tools/repo_graph_port/maxitor/repo_graph_port/resources/git_mirror.py`
- [ ] T002 [US2] `History.followed(graph_before, version_before)`: the history with found paths joined to its configured ones, no path twice, in `history.py`
- [ ] T003 [US2] `refreshed()` answers the followed history; the actions that call it read with what it answers, in `history_reading.py` and `actions/*.py`
- [ ] T004 [US2] Tests: a graph moved inside a merged pull request keeps its versions, each read at its own path; a moved version file keeps its numbers; a configured old path joins a found one; a file moved twice; a file never moved; in `packages/maxitor/tools/repo_graph_port/tests/`

## Phase 2: The folders move (US1, US3)

- [ ] T005 [US1] `git mv packages/maxitor/web packages/maxitor/maxitor-web`, `git mv packages/maxitor/tools/repo_graph_port packages/maxitor/tools/repo-graph-port`, `git mv packages/maxitor/tools/graph_builder packages/maxitor/tools/graph-builder`
- [ ] T006 [US3] Replace the three prefixes in every tracked file outside `CHANGELOG.md` and `specs/`; fix relative paths without the prefix (`packages/maxitor/pyproject.toml`, relative links, `scripts/check_run.py`)
- [ ] T007 [US3] `uv sync`, package build: the wheel holds the same modules as before
- [ ] T008 [US3] The search for old paths finds only `CHANGELOG.md` and `specs/`

## Phase 3: Graphs, versions, the closing check run

- [ ] T009 `graph-builder write`; versions: `repo-graph-port` and `maxitor` minor, `maxitor-web` and `graph-builder` patch; the closing check run taken to zero

## Phase 4: Documentation

- [ ] T010 Pages that show these paths use the new ones; `docs/how-to/run-the-repo-graph-port.md` says the port follows a moved file by itself and `graph_file_before` is for what git cannot see

## Phase 5: Changelog

- [ ] T011 One article, with the new path of the GitHub Action

## After the merge

- [ ] T012 A pull request in `bystrovmaxim/gameoffer` moves its workflow to `bystrovmaxim/aoa/packages/maxitor/tools/graph-builder@<merge commit>`; merged once its checks pass

## Dependencies

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → T012.
