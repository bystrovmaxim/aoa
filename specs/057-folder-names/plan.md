# Implementation Plan: Maxitor's parts in folders named the way people call them

**Branch**: `feature/issue-395-folder-names` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Two changes, in this order. First the graph port learns to follow a graph file and a version file through a move: `GitMirror.earlier_paths` asks `git log --first-parent --follow --name-status` for the paths a file had, and `refreshed()` answers the history with those paths joined to the ones its config lists; the reading of a version already takes the first of a history's paths that exists at that commit. Then the three folders move with `git mv`, and every reference outside `CHANGELOG.md` and `specs/` follows.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14), git ≥ 2.30; TypeScript for the client (paths only)
**Primary Dependencies**: AOA actions; hatchling for the `maxitor` package; Docker for the stand
**Storage**: the port's mirror and version cache (unchanged; a version is cached by its commit)
**Testing**: pytest per level, Vitest, the closing check run, `scripts/check_before_pr.sh`
**Target Platform**: the repository, its CI, the stand on `up2y-prod`
**Project Type**: monorepo
**Performance Goals**: one more `git log` per refresh of a history
**Constraints**: import names, commands, extras and published modules do not change
**Scale/Scope**: about 330 files name the old paths; most only in their module header line

## Constitution Check

- I. The maintainer asked for every phase, the pull request, its merge once every check passes, then PyPI and the stand after both #394 and #395 (2026-11-04).
- II. English, no tool attribution: held.
- III–V. Module headers follow their files' new paths; new functions get one-line docstrings; AI-CORE blocks of the changed resources are kept true.
- VI. The tail: closing check run, documentation, changelog; the pull request opens whole, graphs rebuilt, versions raised.

Gates pass.

## Project Structure

```text
packages/maxitor/
├── maxitor-web/                      # was web/
└── tools/
    ├── repo-graph-port/              # was repo_graph_port/
    │   └── maxitor/repo_graph_port/
    │       ├── resources/git_mirror.py   # earlier_paths
    │       ├── history.py                # History.followed(...)
    │       └── history_reading.py        # refreshed() answers the followed history
    └── graph-builder/                # was graph_builder/
```

Also: `pyproject.toml` (root and `packages/maxitor`), `graph-builder.toml`, `version.toml` (root), `.github/workflows/*`, `scripts/*`, `tests/scripts/*`, `deploy/stand/*`, docs, examples, notebooks, READMEs.

## Complexity Tracking

None.
