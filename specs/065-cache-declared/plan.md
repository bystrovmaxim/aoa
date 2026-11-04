# Implementation Plan: The cache is declared like an access check

**Branch**: `feature/issue-412-cache-declared` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: issue #412, step 6 of 8 of #399.

## Summary

Four declarations replace the four cache methods of `BaseAction` (R1–R3); key and write come together (R2); tag types are declared and checked (R4); the graph shows the declarations and the entities they tag, and refuses dead invalidations and dead tags (R5); the protocol, the builder and Maxitor follow (R6).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14) · **Testing**: pytest per package; the examples' tests · **Project Type**: library monorepo

**Scale/Scope**: `intents/cache/` (new), `model/base_action.py`, `runtime/action_product_machine.py`, `graph/nodes/cache_graph_node.py`, `graph/edges/cache_graph_edge.py`, `graph/edges/cache_tag_graph_edge.py`, `graph/nodes/action_graph_node.py`, `graph/validators/cache_tags_validator.py`, `graph/core/node_graph_coordinator.py`, `graph/graph_json_schema.json`; `open-gnomon-protocol/graph/1.4.json`; graph-builder schemas; Maxitor's DuckDB store; tests, examples, docs (R7)

## Constitution Check

| Principle | How |
| --- | --- |
| I | The maintainer instructed every #399 task autonomously, PRs merged; one phase = one commit |
| II | English in code and history; Russian only in `*_draft.md` |
| III–V | New modules get headers and AI-CORE blocks |
| VI | Phases 6–8: check run, documentation, changelog |

No violation.

## Phases

One phase = one commit.

1. **Declarations** (11.1, 11.6) — R1–R3. Tests: each rule of 11.1; a run through the machine (hit, ctx, read returning `None`, invalidate before write, not inherited); old names refused; `BaseAction` without the methods. Adversarial: the suffix check removed; the old-name check removed; the machine calling an inherited declaration.
2. **Pairing** (11.2). Tests: key alone, write alone, read without the pair refused; invalidate alone accepted. Adversarial: the pairing check removed.
3. **Tag types** (11.4) — R4. Tests: declared, undeclared, type-less tags; empty invalidate tags; a non-entity tag type. Adversarial: the call-time check removed.
4. **Graph** (11.3, 11.5) — R5, R6. Tests: nodes, edges, dead invalidation, dead tag; the 1.4 schema; Maxitor's tables. Adversarial: the validator not called; an edge left out.
5. **Graph files and versions**.
6. **Closing check run**.
7. **Documentation** — step 8, the reference, the examples that cache; #411 part I.
8. **Changelog**.
