# Tasks: Every base class names its descendants

One phase = one commit, referencing (#486). After a phase only its own tests run; every new test is broken once on purpose.

- [x] T001 [US1] Phase 1: resource kinds and wrappers — only the three kind bases inherit `BaseResource`; the kind suffix and the wrapper suffix; the class-method wrapper contract and every reachable target at model build (including inheritance, `None`, cycles, invalid descriptors/results/kinds and getter errors); ancestry-based kind identity, spoofing refusal and mixed-kind refusal; `SqlStorage`, `PostgresStorage`, `SqlStorageWrapper`; `SocketChannelController`, `LangGraphControllerWrapper`, `OcelStorage`, `InMemoryOcelStorage`, `OcelStorageWrapper`; every core and package override, import, test, example and notebook resource follows; modules named after renamed classes follow too; tests for each refusal
- [x] T002 [US3] Phase 2: the demo's resources take their kind's names
- [x] T003 [US2] Phase 3: observers — `Plugin` → `BasePlugin`, `plugin/core/plugin.py` → `base_plugin.py`, the `Plugin` and `Logger` rules; every plugin and logger follows; tests
- [x] T004 [US2] Phase 4: `Params` and `Result`, with `StubParams` and `StubResult`, modules `stub_params.py` and `stub_result.py`, direct imports and public exports; tests
- [x] T005 [US2] Phase 5: `Lifecycle`, `Adapter`, `Coordinator`, `PluginEvent`, `GraphNode`, `GraphEdge`, `Inspector`, `Machine`, `RouteRecord`; tests
- [x] T007 Phase 7: rebuild the graph files, raise the versions
- [x] T008 Phase 8: take every locally runnable closing check to zero, including `graph-builder check`; retain evidence from phase checks without unnecessary repetition; the PR CI closing run happens after T010 and PR authorization
- [x] T009 Phase 9: documentation — the naming rules and migration in one place; update every affected page; write and execute a script and matching notebook covering each case in the plan’s Verification and documentation section, including every refusal; record exact outputs; keep old identifiers only in labelled migration explanations and historical material
- [x] T010 Phase 10: one plain-language changelog article describing the resulting capabilities and migration nuances, written last

## Scope exclusion

T006 is withdrawn on the maintainer’s explicit instruction. Handler names, the existing `on_` rule, its validation and `NamingPrefixError` are not changed. Later task IDs are retained so prior references remain valid.

## Traceability and order

| Requirement | Tasks |
|---|---|
| FR-001 | T001 |
| FR-002 | T003, T004, T005 |
| FR-003 | Scope guard only: @on validation and NamingPrefixError remain unchanged |
| FR-004 | T001–T005, T009 |
| FR-005 | T007 |
| FR-006 | T009, T010 |
| SC-001 | T001–T005: positive and refusal cases, with adversarial verification |
| SC-002 | T001–T005, T008, T009 |
| SC-003 | T008 local preparation; CI after T010 and authorized PR creation |

T001 → T002 → T003 → T004 → T005 → T007 → T008 → T009 → T010. The last three tasks remain checks, documentation, changelog. No task authorizes a commit, push or PR. A phase is ready for its commit only after its scoped verification; it is not marked complete before that authorized commit.

## Delivery

On the maintainer's instruction the phases land as one commit. Each phase was verified on its own before it: its tests, and a deliberate break of each new rule that only its own tests caught.
