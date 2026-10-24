# US4 Evidence: Preserved Compatibility

**Task**: T034 (Procedure 6 — US4)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`

## What landed

The complete-declaration, reciprocal-inverse and dictionary changes add **no** ownership or
container-pair matrix, no instance-level uniqueness, and no storage constraints or cascades.
Existing field-declaration and specialization/classifier refusals are retained, and the
accepted unchanged-inheritance endpoint behavior is retained. This is verified against the
pre-change baseline in `compatibility-baseline.json`, not derived from the changed code.

## Commands and results

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/graph/test_relationship_compatibility_regressions.py -q
```

```text
3 passed
```

## Classification

| Outcome | Classification |
| --- | --- |
| A complete reciprocal pair passes for `CompositeOne↔CompositeOne`, `CompositeMany↔CompositeOne`, `CompositeOne↔AssociationMany`, `AggregateOne↔AggregateOne`, `CompositeOne↔AggregateOne`, `AssociationOne↔AssociationMany` | Retained (no matrix; the removed matrix is not re-introduced) |
| Unchanged inherited `Base.items` ↔ `Item.owner` keeps the base declaring owner | Retained |
| Bare entity / `NoRelation` / bare dictionary / state refusals | Retained (the new rule is stricter in the specified ways only) |
| Specialization classifier membership/coverage rules | Retained (`entity_specialization_validator.py` unchanged except the reciprocal `Inverse` marker check) |

## Review of the three validators

- `entity_field_validator.py`: no matrix, uniqueness, storage or cascade logic (grep found
  none). It refuses incomplete shapes and counts direction markers only.
- `entity_inverse_validator.py`: no matrix; it compares canonical `(declaring_owner,
  field_name)` endpoints and refuses only non-reciprocal/one-sided pairs.
- `entity_specialization_validator.py`: only the existing classifier-code uniqueness
  (`_validate_codes_unique`) and the new reciprocal `Inverse` marker check; "No database
  constraints are generated" remains true.

No acceptance/refusal in the feature is justified by the discarded matrix. The docstring-only
claims recorded in `compatibility-baseline.json` (ownership pair matrix, inverse-existence
proof) remain `implemented: false` in the baseline and are enforced only where the feature
specifies them (reciprocity), never as a matrix.
