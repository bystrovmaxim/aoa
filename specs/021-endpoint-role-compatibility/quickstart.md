# Quickstart: Endpoint Role Compatibility

Runnable validation scenarios that prove the feature end to end. Prerequisite: the feature is
implemented and the workspace is set up (`uv sync --extra dev`).

Run the package's validator tests:

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/validators -q
```

Run a single scenario file:

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/graph/validators/test_role_compatibility_matrix.py -q
```

## Scenarios

- **S1 — Matrix cells.** All 64 directed role combinations produce exactly 22 acceptances and 42
  refusals. See `test_role_compatibility_matrix.py`.
- **S2 — Symmetry.** Reversing each record keeps the verdict and retains the endpoint roles and
  One/Many values. See `test_role_compatibility_matrix.py`.
- **S3 — Assembly.** Actual reciprocal declarations through `NodeGraphCoordinator.build()` for every
  permitted family and every prohibited family. See `test_role_compatibility_assembly.py`.
- **S4 — Specialization axis.** A complete valid classified axis passes; same-role and
  ordinary-role mismatches refuse with the "pair exclusively" message. See
  `test_role_compatibility_specialization.py`.
- **S5 — NoInverse table.** The five declaration shapes of `contracts/noinverse-contract.md`, each
  with its required result. See `test_role_compatibility_noinverse.py`.
- **S6 — Diagnostics.** The exact exception type, text and failure boundary for each refusal family,
  including an earlier check firing first. See `test_role_compatibility_diagnostics.py`.
- **S7 — Dictionary.** All six ordinary dictionary containers across values, empty/nullable cases,
  input/export in both schema modes and graph projection. See `test_role_compatibility_dictionary.py`.
- **S8 — No bypass.** Cross-module rebuilding, graph exclusion, `NoGraphEdge`, hidden edges,
  inherited fields, overrides and delayed type resolution must not bypass the check. See
  `test_role_compatibility_bypass.py`.
- **S9 — Adversarial.** The five FR-027 mutations each fail their targeted check while a valid
  neighbouring control passes. See `test_role_compatibility_adversarial.py`.

## Teaching scenarios

Each scenario has a script and a matching notebook under `examples/step_21_relations/`; run each in
a fresh process so a deliberately invalid declaration cannot contaminate another example's model
discovery:

```bash
uv run python examples/step_21_relations/68_role_plain_associations.py
uv run python examples/step_21_relations/69_role_aggregation.py
uv run python examples/step_21_relations/70_role_composition.py
uv run python examples/step_21_relations/71_role_specialization.py
uv run python examples/step_21_relations/72_role_dictionary.py
```

## Closing check run

```bash
bash scripts/run_checks_with_log.sh
```

The run must be green with only the two accepted third-party remarks the constitution names.
