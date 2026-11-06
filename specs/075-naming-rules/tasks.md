# Tasks: Every base class names its descendants

One phase = one commit, referencing (#486). After a phase only its own tests run; every new test is broken once on purpose.

- [ ] T001 [US1] Phase 1: resource kinds and wrappers — only the three kind bases inherit `BaseResource`; the kind suffix and the wrapper suffix; the wrapper targets at model build; `SqlStorage`, `PostgresStorage`, `SqlStorageWrapper`; `SocketChannelController`, `LangGraphControllerWrapper`, `OcelStorage`, `InMemoryOcelStorage`, `OcelStorageWrapper`; every core and package test, example and notebook resource follows; tests for each refusal
- [ ] T002 [US3] Phase 2: the demo's resources take their kind's names
- [ ] T003 [US2] Phase 3: observers — `Plugin` → `BasePlugin`, the `Plugin` and `Logger` rules; every plugin and logger follows; tests
- [ ] T004 [US2] Phase 4: `Params` and `Result`, with `StubParams` and `StubResult`; tests
- [ ] T005 [US2] Phase 5: `Lifecycle`, `Adapter`, `Coordinator`, `PluginEvent`, `GraphNode`, `GraphEdge`, `Inspector`, `Machine`, `RouteRecord`; tests
- [ ] T006 [US2] Phase 6: the `on_` prefix of `@on` handlers; tests
- [ ] T007 Phase 7: rebuild the graph files, raise the versions
- [ ] T008 Phase 8: the closing check run on the pull request, taken to zero
- [ ] T009 Phase 9: documentation — the naming rules in one place; every page with a renamed class
- [ ] T010 Phase 10: changelog
