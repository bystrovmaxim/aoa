# Quickstart: prove the lifecycle catalogue end to end

**Feature**: `specs/014-lifecycle-status-catalog` | **Date**: 2026-10-22

This guide lists the runnable checks for the feature. It does not repeat the contracts; it points at them: [state-declaration-contract.md](./contracts/state-declaration-contract.md) and [lifecycle-axis-contract.md](./contracts/lifecycle-axis-contract.md).

## Prerequisites

```bash
git switch feature/issue-237-state-catalog-and-lifecycle-checks
uv sync --extra dev
```

The corpus is measured on `main` after #210: 55 axes, 64 state types, 0 uncovered statuses.

## 1. The state type and its catalogue

```bash
uv run python examples/step_22_lifecycle/22_status_fields.py
```

Expected: every status prints `model_dump()` with `code`, `display_name`, `sort_order`, `color`, `fill_color` and `requires_receipt`; the omitted fields show their defaults; `members`, `codes()` and `by_code("paid")` answer; `entity_type` is the state type.

The same case runs cell by cell in `22_status_fields.ipynb`.

## 2. The axis and the runtime

```bash
uv run python examples/step_22_lifecycle/02_lifecycle_axis.py
```

Expected: the axis builds from `Lifecycle[OrderStateEntity]`; `OrderLifecycle(current_state="draft").current_status` is the declared `DRAFT`; the transitions are the template's.

## 3. The foreign refusal

```bash
uv run python examples/step_22_lifecycle/15_foreign_status.py
```

Expected: `ForeignStateError: <axis>: status 'ghost' (OtherStateEntity) is not a declared status of OrderStateEntity. Allowed: ['draft', 'paid', 'cancelled'].`

The twin case is its own example:

```bash
uv run python examples/step_22_lifecycle/21_twin_instance.py
```

Expected: `ForeignStateError` saying `status 'draft' is a different instance from the one declared on OrderStateEntity; use OrderStateEntity.DRAFT.`

## 4. The missing refusal

```bash
uv run python examples/step_22_lifecycle/20_missing_status.py
```

Expected: `MissingStateError: <axis>: status(es) ['cancelled'] of OrderStateEntity do not appear in the lifecycle. Declare every status.`

A member used only in `.to(...)` is covered by the same example's second part.

## 5. The field errors

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_state_entity.py -q -k "field or default or duplicate"
```

Expected: green. The cases are a misspelled field (`Extra inputs are not permitted`), a missing `code` (`Field required`), a wrong type (`Input should be a valid integer`), a coercible `"42"` accepted as `int`, and a duplicate code refused.

## 6. The plain escape

```bash
uv run python examples/step_22_lifecycle/23_plain_lifecycle.py
```

Expected: a `Lifecycle` subclass with no type parameter builds and is unchecked; the template's behaviour is today's.

## 7. The automated checks

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_catalog_checks.py -q
uv run --extra dev pytest packages/aoa-action-machine/tests -q
uv run --extra dev mypy packages/
```

Expected: the three refusals are each a dedicated failing-before, passing-after test; the full suite is green; `mypy --strict` is clean with no new `# type: ignore`.

## 8. The migration evidence

```bash
uv run python specs/014-lifecycle-status-catalog/evidence/scan_lifecycle_catalog.py --out specs/014-lifecycle-status-catalog/evidence/scan.after.json
uv run python specs/014-lifecycle-status-catalog/evidence/compare_baselines.py \
  specs/014-lifecycle-status-catalog/evidence/baseline.before.json \
  specs/014-lifecycle-status-catalog/evidence/baseline.after.json
grep -rn "StateVocabulary" --include=*.py packages examples | wc -l
```

Expected: 0 axes on `StateVocabulary`; 0 uncovered statuses; 0 differences in the baseline (statuses, labels, transitions, demo state rows, entity field types); the grep prints `0`.

## 9. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

Expected: exit 0. The only remarks left are the two the constitution accepts: the Vite chunk-size advisory and the LangGraph pending-deprecation warning.

## 10. What to do when a scenario fails

- A status field is missing or wrong: the error is at class creation, not at runtime; read the `ValidationError`'s field name.
- A twin is accepted: the identity check is broken; the twin test must fail first.
- A missing status is accepted: the coverage check is broken; the missing test must fail first.
- The catalogue is empty on a type that declares statuses: the conversion hook did not run; check `__pydantic_init_subclass__` and `ignored_types`.
- A bare `Lifecycle` annotation fails mypy: parameterise it (`Lifecycle[BaseStateEntity]`), never suppress it.
