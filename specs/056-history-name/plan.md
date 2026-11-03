# Implementation Plan: A history named after what was opened

**Branch**: `feature/issue-394-history-name` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

A public history is named after the folder of its graph file, and carries its full path, `owner/repo/<folder>`. The server takes both from the GitHub link it already parses; the open answer gains a `path` field; the version picker shows the name, the full path on hover, and copies the path on a click. The browser tab, the recent list and the log lines already read the history's title, so they follow.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14); TypeScript 5 with React 19 and MUI
**Primary Dependencies**: AOA actions (FastAPI adapter), Vitest with Testing Library
**Storage**: none (the name is taken from the link)
**Testing**: pytest (`packages/maxitor/web/tests`), Vitest (`packages/maxitor/web/client`)
**Target Platform**: Maxitor web: its server and its browser client
**Project Type**: web application (server + client in one level, `packages/maxitor/web`)
**Performance Goals**: opening a history costs nothing more (no request is added)
**Constraints**: the open answer only gains a field; nothing is renamed or removed
**Scale/Scope**: one server module, one action's result, one hook, one picker header

## Constitution Check

- I. The maintainer asked for every phase, the pull request, the merge once every check passes, the PyPI release and the stand's redeploy, without asking again (2026-11-04).
- II. English in code and history, no tool attribution: held.
- III–V. Module headers and AI-CORE blocks of the changed modules are kept true; one-line docstrings on new code.
- VI. The tail is the closing check run, the documentation, the changelog; the pull request opens whole, with `packages/maxitor/web/graph.json` rebuilt and the versions raised (`packages/maxitor/web/version.toml`, `maxitor` in `pyproject.toml`).
- API only through actions: the name travels in `OpenHistoryAction`'s result; no route is added.

Gates pass, before and after design.

## Project Structure

### Documentation (this feature)

```text
specs/056-history-name/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/open-history.md
└── tasks.md
```

### Source Code

```text
packages/maxitor/web/
├── maxitor/web/model/core/
│   ├── history_address.py          # PublicHistory: folder name as title, full path
│   ├── history_entry.py            # HistoryEntry.path
│   ├── history_reading.py          # fills path
│   └── actions/open_history_action.py  # result gains path
├── tests/test_history_name.py      # name and path rules
└── client/src/
    ├── api/history.ts              # path in the open answer
    ├── app/useOpenHistory.ts       # OpenHistory.path
    ├── app/App.tsx                 # passes path to the picker
    └── components/history/VersionPicker/  # name with hover and copy
docs/how-to/open-a-graph-history.md # where the name comes from
CHANGELOG.md
```

**Structure Decision**: everything lives in the Maxitor web level; no new module.

## Complexity Tracking

None.
