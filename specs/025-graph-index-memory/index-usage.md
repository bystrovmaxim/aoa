# Index Usage: Which Diagram Query Reads Through Which Index

**Measured**: 2026-10-26, DuckDB 1.5.6, with `python -m tests.graph_build_metrics <graph> --explain`.

## 1. Method

The helper runs every diagram action and the sidebar build with a recording proxy around the built graph's DuckDB connection. Both paths into the database are recorded: `execute_fetch_dicts` and the direct `duck.service.execute(...)` in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action.py:153`. Every recorded statement is then repeated under `EXPLAIN (FORMAT JSON)` with its parameters inlined as literals, and the plan is searched for the 21 primary-key names and the 64 index names read from `duckdb_constraints()` and `duckdb_indexes()`.

Parameterized queries run for every domain or lifecycle, so the table covers the reference graph's 96 statements (72 distinct plans) and the demo's 941 statements (823 distinct plans). The direct `list-entities` query (`SELECT COALESCE(NULLIF(name, ''), label, id) FROM domain WHERE id = ?`) is among the recorded statements; it appears once per domain.

## 2. Result

All 85 rows are empty: no plan of any diagram query or of the sidebar build reads through any index or primary key.

| Structure | Kind | Table | Reference graph | Demo graph |
|---|---|---|---|---|
| `access_decide_id_pkey` | primary key | `access_decide` | — | — |
| `action_id_pkey` | primary key | `action` | — | — |
| `application_id_pkey` | primary key | `application` | — | — |
| `checker_id_pkey` | primary key | `checker` | — | — |
| `compensator_id_pkey` | primary key | `compensator` | — | — |
| `domain_id_pkey` | primary key | `domain` | — | — |
| `entity_id_pkey` | primary key | `entity` | — | — |
| `entity_field_id_pkey` | primary key | `entity_field` | — | — |
| `error_handler_id_pkey` | primary key | `error_handler` | — | — |
| `field_id_pkey` | primary key | `field` | — | — |
| `lifecycle_id_pkey` | primary key | `lifecycle` | — | — |
| `params_id_pkey` | primary key | `params` | — | — |
| `property_field_id_pkey` | primary key | `property_field` | — | — |
| `regular_aspect_id_pkey` | primary key | `regular_aspect` | — | — |
| `required_context_id_pkey` | primary key | `required_context` | — | — |
| `resource_id_pkey` | primary key | `resource` | — | — |
| `result_id_pkey` | primary key | `result` | — | — |
| `role_id_pkey` | primary key | `role` | — | — |
| `sensitive_id_pkey` | primary key | `sensitive` | — | — |
| `state_id_pkey` | primary key | `state` | — | — |
| `summary_aspect_id_pkey` | primary key | `summary_aspect` | — | — |
| `ix_access_decide_edges_source` | index | `access_decide_edges` | — | — |
| `ix_access_decide_edges_target` | index | `access_decide_edges` | — | — |
| `ix_application_edges_source` | index | `application_edges` | — | — |
| `ix_application_edges_target` | index | `application_edges` | — | — |
| `ix_check_roles_edges_source` | index | `check_roles_edges` | — | — |
| `ix_check_roles_edges_target` | index | `check_roles_edges` | — | — |
| `ix_compensate_edges_source` | index | `compensate_edges` | — | — |
| `ix_compensate_edges_target` | index | `compensate_edges` | — | — |
| `ix_connection_edges_source` | index | `connection_edges` | — | — |
| `ix_connection_edges_target` | index | `connection_edges` | — | — |
| `ix_depends_edges_source` | index | `depends_edges` | — | — |
| `ix_depends_edges_target` | index | `depends_edges` | — | — |
| `ix_domain_edges_source` | index | `domain_edges` | — | — |
| `ix_domain_edges_target` | index | `domain_edges` | — | — |
| `ix_entity_field_edges_source` | index | `entity_field_edges` | — | — |
| `ix_entity_field_edges_target` | index | `entity_field_edges` | — | — |
| `ix_entity_reference_edges_source` | index | `entity_reference_edges` | — | — |
| `ix_entity_reference_edges_target` | index | `entity_reference_edges` | — | — |
| `ix_entity_relation_edges_source` | index | `entity_relation_edges` | — | — |
| `ix_entity_relation_edges_target` | index | `entity_relation_edges` | — | — |
| `ix_entity_schema_edges_source` | index | `entity_schema_edges` | — | — |
| `ix_entity_schema_edges_target` | index | `entity_schema_edges` | — | — |
| `ix_entity_specialization_edges_source` | index | `entity_specialization_edges` | — | — |
| `ix_entity_specialization_edges_target` | index | `entity_specialization_edges` | — | — |
| `ix_entity_view_edges_source` | index | `entity_view_edges` | — | — |
| `ix_entity_view_edges_target` | index | `entity_view_edges` | — | — |
| `ix_field_edges_source` | index | `field_edges` | — | — |
| `ix_field_edges_target` | index | `field_edges` | — | — |
| `ix_generic_params_edges_source` | index | `generic_params_edges` | — | — |
| `ix_generic_params_edges_target` | index | `generic_params_edges` | — | — |
| `ix_generic_result_edges_source` | index | `generic_result_edges` | — | — |
| `ix_generic_result_edges_target` | index | `generic_result_edges` | — | — |
| `ix_lifecycle_contains_state_edges_source` | index | `lifecycle_contains_state_edges` | — | — |
| `ix_lifecycle_contains_state_edges_target` | index | `lifecycle_contains_state_edges` | — | — |
| `ix_lifecycle_edges_source` | index | `lifecycle_edges` | — | — |
| `ix_lifecycle_edges_target` | index | `lifecycle_edges` | — | — |
| `ix_lifecycle_transition_edges_source` | index | `lifecycle_transition_edges` | — | — |
| `ix_lifecycle_transition_edges_target` | index | `lifecycle_transition_edges` | — | — |
| `ix_on_error_edges_source` | index | `on_error_edges` | — | — |
| `ix_on_error_edges_target` | index | `on_error_edges` | — | — |
| `ix_parent_action_edges_source` | index | `parent_action_edges` | — | — |
| `ix_parent_action_edges_target` | index | `parent_action_edges` | — | — |
| `ix_parent_domain_edges_source` | index | `parent_domain_edges` | — | — |
| `ix_parent_domain_edges_target` | index | `parent_domain_edges` | — | — |
| `ix_parent_entity_edges_source` | index | `parent_entity_edges` | — | — |
| `ix_parent_entity_edges_target` | index | `parent_entity_edges` | — | — |
| `ix_parent_role_edges_source` | index | `parent_role_edges` | — | — |
| `ix_parent_role_edges_target` | index | `parent_role_edges` | — | — |
| `ix_property_edges_source` | index | `property_edges` | — | — |
| `ix_property_edges_target` | index | `property_edges` | — | — |
| `ix_regular_aspect_edges_source` | index | `regular_aspect_edges` | — | — |
| `ix_regular_aspect_edges_target` | index | `regular_aspect_edges` | — | — |
| `ix_required_context_edges_source` | index | `required_context_edges` | — | — |
| `ix_required_context_edges_target` | index | `required_context_edges` | — | — |
| `ix_result_checker_edges_source` | index | `result_checker_edges` | — | — |
| `ix_result_checker_edges_target` | index | `result_checker_edges` | — | — |
| `ix_sensitive_edges_source` | index | `sensitive_edges` | — | — |
| `ix_sensitive_edges_target` | index | `sensitive_edges` | — | — |
| `ix_state_kind` | index | `state` | — | — |
| `ix_state_lifecycle` | index | `state` | — | — |
| `ix_state_edges_source` | index | `state_edges` | — | — |
| `ix_state_edges_target` | index | `state_edges` | — | — |
| `ix_summary_aspect_edges_source` | index | `summary_aspect_edges` | — | — |
| `ix_summary_aspect_edges_target` | index | `summary_aspect_edges` | — | — |

## 3. Finding

No diagram answer depends on an index. The result is stronger than the hypothesis: on DuckDB 1.5.6 the planner did not choose an ART index scan for any read in these graphs. A separate probe confirmed it is not a property of these small graphs: equality, `IN` and `BETWEEN` filters on an indexed column, and a join with a dynamic filter, planned `SEQ_SCAN` on tables of 200 000 and 2 000 000 rows, in both an in-memory and a file database, with `index_scan_max_count` and `index_scan_percentage` raised. The 38.0 MiB of `ART_INDEX` on the reference graph and 57.5 MiB on the demo are therefore constraint structures plus pure overhead for every read Maxitor makes.

## 4. Decision

- **Phase 5 removes all 21 `PRIMARY KEY` constraints and all 64 `CREATE INDEX` statements.** No structure is kept for the timing bound of FR-007: none is used, so none can make a query faster.
- **The primary keys must go with the indexes.** Removing only the 64 indexes makes the reference graph larger, not smaller (43.5 → 50.7 MiB, R1); only the "nothing" variant reaches the memory target.
- **Phase 4 is required.** Once the primary keys go, the duplicate-id check is the only thing that refuses a graph with the same node `id` twice in one table.
- This is the "nothing" variant of research R1: 13.38 MiB on the reference graph, 43.51 → 13.38, and 54.3 → 22.0 MiB per graph in the process figure.

## 5. Adversarial check

The planned check of T010 — add `ix_tmp` on `domain(label)`, query by `label`, and see `--explain` report it as used — cannot be shown on DuckDB 1.5.6: the index is never chosen (see §3). Instead, the detector itself was checked against a synthetic `INDEX_SCAN` plan naming `ix_tmp`, and it reports `ix_tmp`; the same code raises if a plan contains an `INDEX` operator that names no catalogue structure, so a silent "unused" cannot hide an index scan. The negative control (adding the index and querying the column) is recorded as evidence: the answer is `SEQ_SCAN`, not an index scan.
