# Tasks: The logical data model

One phase = one commit, referencing (#479). After a phase only its own tests run; every new test is broken once on purpose.

- [x] T001 Phase 1: relations know no store — the boundary rules removed from `entity_resource_validator.py` and from the coordinator's re-check; tests of each link across two data sources; the step-24 examples that showed the refusal show the relation allowed
- [x] T002 Phase 2: a data source required for a resource that stores an entity, at model build and graph build; `InMemoryDataSource`, `ExternalServiceDataSource`; `PostgresResource` takes only `data_source=`; every test, example, adapter model and demo resource names a data source; tests of each refusal and each kind
- [x] T003 Phase 3: one resource per domain and data source, at model build and graph build; the demo's messaging resources become one; tests
- [x] T004 Phase 4: the graph at protocol 1.8 — schema copy, `schema_version`, Maxitor pinned to the gnomon commit in the dependencies and CI; the graph tests
- [x] T005 Phase 5: rebuild the graph files, raise the versions
- [ ] T006 Phase 6: the closing check run on the pull request, taken to zero
- [ ] T007 Phase 7: documentation — the data source page with the frame on the connection policy; the pages on relations and resources; the PostgreSQL page
- [ ] T008 Phase 8: changelog
