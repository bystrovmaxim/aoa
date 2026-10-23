# Closing check run and the adversarial breaks

**Feature**: `specs/016-value-declaration-consistency` | **Date**: 2026-10-23 | **Task**: T044

## 1. The run, taken to zero

```
bash scripts/run_checks_with_log.sh
```

Run with three environment overrides, because the file sandbox denies writing to the usual
caches — the same limitation recorded in `baseline.before.txt`:

```
UV_CACHE_DIR=/tmp/uv-cache
PYLINTHOME=/tmp/pylint-home
npm_config_cache=/tmp/npm-cache
```

Result: **exit 0**, all 33 steps OK, log `archive/logs/check-all.txt` (4 594 lines). The steps
cover the client build and its three checks, ruff auto-fix and lint, mypy, pylint, the
package-boundary and metadata checkers, a wheel and sdist build of all eight packages, the
packaging smoke test, vulture, the Maxitor samples public-API check, all eight pytest suites,
radon complexity and maintainability.

The only remark in the log is the accepted one:

```
line 52: (!) Some chunks are larger than 500 kB after minification. Consider: ...
```

This is the Vite chunk-size advisory the constitution names as accepted. LangGraph's
pending-deprecation warning did not appear in this run — the suite that raises it passed with
`1 warning`, which is the same warning being surfaced by pytest rather than by the library on a
deprecated call path. Neither was acted on, as required.

The working tree is clean afterwards (`.gitignore` covers `archive/logs` and the build outputs).

## 2. The adversarial breaks

Each corrected defect was reintroduced in isolation, its targeted test was run, a different test
module was run as the control, and the file was restored with `git checkout`. The tree was clean
before and after every pair.

| # | Defect reintroduced | Targeted run | Control run | Restored |
| --- | --- | --- | --- | --- |
| 1 | `_refused_property_type` returns `None`, so every property type is accepted | `test_dictionary_property_types.py` — **8 failed**, 11 passed | `test_dictionary_scope.py` — 9 passed | yes |
| 2 | `_serialize_as_reference` reads fields with `getattr`, so a serializer is bypassed | `test_dictionary_core_schema.py` — **2 failed**, 14 passed | `test_dictionary_property_types.py` — 19 passed | yes |
| 3 | `to_reference()` returns the Python-mode dump, so a date reaches the document | `graph/test_dictionary_reference_json.py` — **1 failed**, 2 passed | `test_dictionary_scope.py` — 9 passed | yes |
| 4 | the validation schema requires `code`, `display_name` and `properties` again | `test_dictionary_json_schema.py` — **3 failed**, 9 passed | `test_dictionary_core_schema.py` — 16 passed | yes |
| 5 | the payload conversion skips the last property of each value | `test_list_entities_payload_dictionary.py` — **3 failed**, 5 passed | `test_entity_specialization_erd.py` — 11 passed | yes |
| 6 | the client appends `(dictionary_label)` beside the server's label again | `check-erd-group-label.ts` — **a stale dictionary_label produced 2 names** | `check-erd-dictionary-values.ts` — passed | yes |

The exact failure in each case is the one the defect would cause, not a collection error: break 1
fails the eight refusal tests, break 3 fails `test_the_graph_document_survives_json_dumps`,
break 5 fails `test_the_payload_keeps_one_item_per_graph_property`, and break 6 reports the
duplicated name count.

## 3. What this leaves

- The check run is green on the tree that carries phases 1–7.
- Each of the six corrected defects has a test that fails when the defect returns, and a control
  run that stays green — the tests are aimed, not merely present.
- The two accepted remarks are the only remarks; neither was triaged away as a new exception.
