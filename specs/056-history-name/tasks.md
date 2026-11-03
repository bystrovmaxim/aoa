# Tasks: A history named after what was opened

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/open-history.md](contracts/open-history.md)

Each phase is one commit. After a phase only its own tests run.

## Phase 1: Server — the name and the full path (US1, US2)

- [ ] T001 [US1] `PublicHistory` keeps the graph file's `path` from the link; `title` is its last folder, or `repo` at the root; a new `full_path` is `owner/repo/<folder>`, `owner/repo` at the root, in `packages/maxitor/web/maxitor/web/model/core/history_address.py`
- [ ] T002 [US1] `PrivateHistory.full_path` is its `name` (the address without the key), in the same file
- [ ] T003 [US1] `HistoryEntry` gains `path`; `open_history` fills it from `history.full_path`, in `packages/maxitor/web/maxitor/web/model/core/history_entry.py` and `history_reading.py`
- [ ] T004 [US1] `OpenHistoryAction`'s result gains `path`, and `title`'s description says it is the folder, in `packages/maxitor/web/maxitor/web/model/core/actions/open_history_action.py`
- [ ] T005 [US1] Tests in `packages/maxitor/web/tests/test_history_name.py`: a nested folder (`packages/aoa-demo/graph.json` → `aoa-demo`, `bystrovmaxim/aoa/packages/aoa-demo`); a deeper one (`packages/maxitor/tools/repo_graph_port/graph.json`); the root (`graph.json` → `gameoffer`, `bystrovmaxim/gameoffer`); a link with `version_link` keeps the graph's folder; a private history (id, address without the key); the open answer carries `title` and `path`
- [ ] T006 [US2] Existing tests that expected `owner/repo` as the title follow the folder name

## Phase 2: Client — the name, hover and copy (US1, US2)

- [ ] T007 [US1] `path` in the open answer type, in `packages/maxitor/web/client/src/api/history.ts`, and in `OpenHistory`, in `src/app/useOpenHistory.ts`
- [ ] T008 [US1] `VersionPicker` takes `path`: the name is a button in a tooltip showing the path; a click or Enter copies it; the tooltip says `Copied` for 1.5 s, or `Not copied` when the clipboard refuses, in `src/components/history/VersionPicker/VersionPicker.tsx`; `App.tsx` passes `shown.path`
- [ ] T009 [US1] Tests in `src/components/history/VersionPicker/VersionPicker.test.tsx`: the header shows the name and no path line; hover shows the path; a click writes the path to the clipboard and says `Copied`; a refused clipboard says `Not copied`
- [ ] T010 [US2] Tests and fixtures that build an open answer gain `path`

## Phase 3: The closing check run

- [ ] T011 `graph-builder write` for `packages/maxitor/web/graph.json`; versions raised (`packages/maxitor/web/version.toml`, `maxitor` in `packages/maxitor/pyproject.toml`); the closing check run taken to zero

## Phase 4: Documentation

- [ ] T012 `docs/how-to/open-a-graph-history.md` (and its `.ru_draft.md`) says the history is named after its graph file's folder, shows its full path on hover and copies it on a click; `packages/maxitor/web/client/src/components/history/VersionPicker/README.md` follows

## Phase 5: Changelog

- [ ] T013 One article in `CHANGELOG.md`

## Dependencies

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5. Within a phase, tests follow the code they check.
