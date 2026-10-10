# Quickstart: validating the access cascade demonstrator

Runnable validation for the feature end to end: the model builds, every shape is in the drawing, and the recorded evidence lands in `contracts/`.

## Prerequisites

- Repository environment: `uv` with the dev extra (same as the acceptance gate).
- Node toolchain for the Maxitor client build (see `scripts/run_checks_with_log.sh` for the client build step).

## 1. The model still builds

```bash
uv run --extra dev pytest packages/aoa-demo/tests/ -q
```

**Expected**: zero failures. This is the acceptance gate (FR-012). The new `access_cascade` domain is registered through the two module lists and must not disturb the existing demo content (FR-014).

## 2. The runnable proofs pass

The shape tests live in `packages/aoa-demo/tests/model/test_access_cascade_shapes.py`. Run them explicitly to read the proofs:

```bash
uv run --extra dev pytest packages/aoa-demo/tests/model/test_access_cascade_shapes.py -q
```

**Expected**, one assertion group per proof:

- **Early stop (FR-008)**: running `EarlyStopShapeAction` as a caller who fails `CHECK_ROLES` returns a refusal naming `CHECK_ROLES`, and the object-rule probe counter is zero — the declared `@access_decide` was provably not reached.
- **Refusal as an answer (FR-009)**: asking `machine.check_access_decide` about `QuestionPathShapeAction` returns a refusal answer — no exception — and no aspect of the operation ran.

## 3. The drawing shows the shapes

1. Build the Maxitor client (the repository check script does the same).
2. Run the demo app and load the model (the demo's `interchange_demo_coordinator`).
3. Open the use-case diagram for the `access_cascade` domain.

**Expected**, checked by eye against `contracts/access-shapes.md`:

- an operation with a single role edge (role check alone);
- a role edge with a refusing condition (`when=`);
- a shared guard refusing everyone alike (`guard=`);
- an operation with a declared object-rule node (`@access_decide`);
- roles of all three levels — system, application, domain;
- a role chain several levels deep (`parent_role` edges), not isolated role nodes;
- two role edges into one operation from different branches;
- the asked-about operation labelled as such;
- the `NoInverse` one-sided boundary on `CascadeBoundaryEntity`.

## 4. Record the evidence

1. The generated DOT sources are already produced by the Maxitor client's own builders and recorded as `specs/003-access-cascade-demonstrator/contracts/access-shapes.dot` (use-case diagram) and `access-shapes-erd.dot` (ERD slice), with the WASM-rendered `access-shapes.svg` / `access-shapes-erd.svg` beside them.
2. Capture the two diagrams from the built Maxitor client as `access-shapes.png` and `access-shapes-erd.png` in the same directory.
3. Verify against the table in `contracts/access-shapes.md` — every shape on the list must be identifiable by sight (SC-001), and every label must name its shape, never a business claim (FR-011, SC-003).

The artifacts are committed with the change (FR-013, SC-004).
