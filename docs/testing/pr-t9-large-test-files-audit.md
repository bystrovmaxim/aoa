# PR-T9 — Large test files audit (`tests/`)

**Criterion:** Python files under `tests/` with **more than 400 lines** (soft limit from plan `008.md`).

**Generated:** snapshot for PR-T9. Re-run:

```bash
python3 -c "
from pathlib import Path
root = Path('tests')
for p in sorted(root.rglob('*.py')):
    n = sum(1 for _ in p.open(encoding='utf-8', errors='replace'))
    if n > 400:
        print(f'{n:5d}  {p}')
"
```

**Count:** 22 files exceed 400 lines (including shared fixtures under `scenarios/domain_model/`).

---

## Summary table

| Lines | Current path | Proposed split / notes (PR-T10+) |
| -----: | ------------ | ---------------------------------- |
| 886 | `tests/scenarios/domain_model/compensate_actions.py` | Shared **fixture** module (not `test_*.py`). Split by concern: e.g. `compensate_actions_orders.py`, `compensate_actions_payment.py`, or one file per action family; re-export from `compensate_actions.py` for stable imports. |
| 857 | `tests/intents/logging/test_log_coordinator.py` | One module per `Test*` group: `test_log_coordinator_substitution.py` (`TestVariableSubstitution`), `test_log_coordinator_iif.py`, `test_log_coordinator_broadcast.py`, `test_log_coordinator_params.py`, `test_log_coordinator_nested.py`, `test_log_coordinator_errors.py`; shared fixtures/helpers in same package `conftest.py` or `_log_coordinator_helpers.py`. |
| 735 | `tests/scenarios/graph_with_runtime/test_coordinator_graph.py` | Split by coordinator facet: e.g. `test_coordinator_graph_nodes.py` (`TestBasicNodes`, `TestDependenciesAndConnections`, …), `test_coordinator_graph_structure.py` (`TestRecursiveCollection`, `TestCycleDetection`), `test_coordinator_graph_api.py` (`TestPublicAPI`, `TestInvalidation`), `test_coordinator_graph_build_cache.py` (`TestCoordinatorBasic`); keep shared imports in `_coordinator_graph_fixtures.py` if needed. |
| 645 | `tests/intents/plugins/conftest.py` | **Fixture** module: extract plugin classes into `tests/intents/plugins/_test_plugins/` (one module per plugin cluster) and keep `conftest.py` as pytest wiring only. |
| 582 | `tests/intents/logging/test_base_logger.py` | Split by theme (filtering vs write API vs edge cases) after skimming `Test*` classes; target 2–3 files ~200–300 LOC each. |
| 580 | `tests/runtime/test_machine_plugins.py` | `test_machine_plugins_events_count.py`, `test_machine_plugins_events_types.py`, `test_machine_plugins_events_data.py`, `test_machine_plugins_isolation.py` (mirrors existing `Test*` blocks). |
| 568 | `tests/intents/logging/test_variable_substitutor.py` | Split internal method groups / error paths into `test_variable_substitutor_core.py` + `test_variable_substitutor_edges.py` (or by `Test*` class). |
| 541 | `tests/runtime/test_machine_nested.py` | `test_machine_nested_basic.py`, `test_machine_nested_nest_level.py`, `test_machine_nested_context.py` (or by scenario). |
| 524 | `tests/intents/context/test_context.py` | Split by `Test*` / topic: construction, validators, `resolve`, immutability. |
| 518 | `tests/intents/checkers/test_result_date_checker.py` | Parametrize shared cases first; then split date-format vs min/max vs error paths if still large. |
| 509 | `tests/intents/logging/test_console_logger.py` | Split layout/color vs streaming vs error handling sections. |
| 506 | `tests/intents/checkers/test_result_instance_checker.py` | Split tuple-of-types vs single type vs error paths. |
| 491 | `tests/scenarios/dependencies/test_dependency_factory_core_machine.py` | `test_dependency_factory_core_machine_resolve.py` vs `test_dependency_factory_core_machine_domain.py` (`TestDomainIntegration`); shared mocks at bottom module or conftest. |
| 486 | `tests/intents/logging/test_debug_filter.py` | Split filter grammar vs integration with coordinator/logger. |
| 465 | `tests/adapters/mcp/test_mcp_handler.py` | Split handler lifecycle vs tool invocation vs error paths; optional `test_mcp_handler_graph.py` if coordinator sections dominate. |
| 451 | `tests/runtime/binding/test_action_result_runtime_validation.py` | `test_action_result_binding_summary.py`, `test_action_result_binding_on_error.py`, `test_action_result_binding_forward_ref.py` (by decorator concern). |
| 446 | `tests/intents/context/test_context_view.py` | Split read-only view vs `context_requires` integration vs error mapping. |
| 438 | `tests/scenarios/intents_with_runtime/test_bench_run_compensator.py` | Split bench harness tests vs compensator-specific integration classes. |
| 436 | `tests/intents/compensate/test_saga_events.py` | Split by event phase (before/after aspect, global, error) or by `Test*` class group. |
| 432 | `tests/resources/test_wrapper_sql_connection_manager.py` | `test_wrapper_sql_transactions.py`, `test_wrapper_sql_execute.py`, `test_wrapper_sql_wrap_connections.py` (matches section headers in file). |
| 405 | `tests/runtime/test_machine_roles.py` | `test_machine_roles_specs.py` (None/Any/single/list) vs `test_machine_roles_bench.py` (`TestRolesWithBench`). |
| 402 | `tests/model/test_base_schema_resolve.py` | Split `resolve` happy-path vs missing keys vs type coercion sections. |

---

## Execution notes (PR-T10+)

- Prefer **one PR per source file** (or per small package like `tests/intents/logging/`) to keep review small.
- After each split: `uv run pytest tests/` and `uv run ruff check` on touched paths.
- Update this table with **done** checkmarks or remove rows when every successor file is **≤400** lines (or consciously waived with reason).

---

## Files intentionally out of scope

- `tests/**/__init__.py` docstrings can be long; only split if they harm navigation (none currently >400 in the 22-file list).
- Very small smoke files stay as-is even if they grow slightly later.
