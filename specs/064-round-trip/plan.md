# Implementation Plan: What goes out comes back in

**Branch**: `feature/issue-409-round-trip` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: issue #409, step 5 of 8 of #399.

## Summary

The graph build refuses a Params or Result without a JSON Schema in either mode and names the field (R1); one comparison of observable state returns the first difference (R2); the run of every example reads back every Result it builds (R3), and a demo test reads back a sample of every demo Result class (R4).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14) · **Primary Dependencies**: Pydantic 2.14 · **Testing**: pytest per package and the repository's example tests · **Project Type**: library monorepo

**Constraints**: `==` unchanged; the examples run once

**Scale/Scope**: `graph/validators/json_form_validator.py` (new), `graph/core/node_graph_coordinator.py`, `model/observable_state.py` (new), `model/__init__.py`; `tests/examples/round_trip_runner.py` (new), `tests/examples/test_examples_run.py`; tests; `aoa-demo/tests/model/test_result_round_trip.py` (new); the pages on the checks and on Params and Result

## Constitution Check

| Principle | How |
| --- | --- |
| I | The maintainer instructed the whole task, PR and merge; one phase = one commit |
| II | English in code and history; Russian only in `*_draft.md` |
| III–V | The new modules get their headers; touched modules update notes |
| VI | Phases 4–6: check run, documentation, changelog |

No violation.

## Phases

One phase = one commit.

1. **Build check** (8.1) — R1. Tests: a Result field and a Params field of a plain class refused and named; a field failing only in serialization mode refused; `JsonSchemaValue` and a projection pass. Adversarial: the validator not called; only validation mode checked.
2. **Observable state and read-back** (8.2) — R2–R4. Tests: the comparison's pairs; AOA's value types read back; the examples' runner; the demo's Result classes. Adversarial: a relation read back as not loaded (the issue's break); the loaded-state rule removed from the comparison; the runner's recording disabled.
3. **Versions**.
4. **Closing check run**.
5. **Documentation** — the page on the checks, the page on Params and Result; #401 sections 3 and 4.8.
6. **Changelog**.
