# Quickstart: proving the capability works

A guide for validating the feature end to end. It names the scenarios, the commands and the expected outcomes; the detail of the model is in [data-model.md](./data-model.md) and the surfaces in [contracts/](./contracts/).

## Prerequisites

- The workspace is installed: `uv sync --extra dev` from the repository root.
- The package under test is the engine: `packages/aoa-action-machine`.

## Scenario 1 — one declaration, two answers (P1)

Declare an operation with a role requirement and one declared condition. Ask in advance, then execute, as a caller who satisfies the declaration and as one who does not.

**Expected**: the four answers follow from the declaration alone; the refusal produced by the question and the refusal produced by the execution name the same gate and the same reason.

**Proves**: FR-002, FR-004, FR-017, SC-006.

## Scenario 2 — a refusal that reveals nothing about the object (P2)

Declare the object check and answer `FORBIDDEN_OBJECT` for an object that does not exist, and for an object that belongs to another caller.

**Expected**: the two answers are identical in `kind`, `gate` and `reason`, and both came from one branch.

**Proves**: FR-011, FR-018, SC-003.

## Scenario 3 — a gate that cannot tell (P3)

Make one gate fail (inject a store that raises), then read the answer and the published events.

**Expected**: the answer is `undecided` and names the gate that could not tell; while the call executes, a failed-gate event is published carrying the failure's type, and asking in advance publishes no such event; neither the answer nor any event contains the text of the failure; the outcome is never cached or reused as a refusal.

**Proves**: FR-005, FR-006, FR-013, FR-015, SC-004, SC-007.

## Scenario 4 — a decision is answered, not published

Ask in advance, then execute, with an in-memory exporter attached.

**Expected**: no event about a decision on either path; asking in advance publishes only the object check's own before and after events; a run that ends in a refusal shows its `GlobalStart` without a `GlobalFinish` and no handler the operation declares for its failures is reached; a failed gate carries the request identity when the context has one, and none when it does not.

**Proves**: FR-013, FR-015, SC-001, SC-008.

## Scenario 5 — the declaration is not optional

Build a machine containing an operation with no access declaration.

**Expected**: assembling the graph fails, before any call is served.

**Proves**: FR-001, SC-005.

## Scenario 6 — rejected credentials are not guests

Present rejected credentials to an operation declared open to guests.

**Expected**: a refusal naming the identity gate, with no reason text invented.

**Proves**: FR-009, FR-013.

## Commands

```bash
# the engine's own suite
uv run --extra dev pytest packages/aoa-action-machine/tests -q

# the adapters, which must keep seeing a refusal come back as a refusal
uv run --extra dev pytest packages/aoa-fastapi-adapter/tests packages/aoa-mcp-adapter/tests -q

# the closing gate of the whole work
bash scripts/run_checks_with_log.sh
```

## Definition of done for the feature

- Every scenario above passes, and each one fails when the behaviour it checks is deliberately broken (the adversarial checks in issue #189).
- `bash scripts/run_checks_with_log.sh` exits clean, with its log in `archive/logs/check-all.txt`.
