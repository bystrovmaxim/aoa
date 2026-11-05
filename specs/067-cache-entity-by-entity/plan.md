# Implementation Plan: A collection is cached entity by entity

**Branch**: `feature/issue-413-cache-entity-by-entity` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: issue #413, step 8 of 8 of #399.

## Summary

`layout=CacheLayout.ENTITIES` and `@cache_entity_key` (R1); entity entries under a shared namespace, a collection entry of keys (R2); write, hit and miss (R3); `get_entries` (R4); the graph and protocol 1.5 (R5).

## Technical Context

Python 3.12 (CI also 3.14) · pytest · `intents/cache/`, `runtime/action_product_machine.py`, `runtime/cache_coordinator.py`, `runtime/cache_entity.py` (new), graph nodes, edges and validator, `open-gnomon-protocol/graph/1.5.json` and copies, Maxitor's store; tests; the how-to example; tutorial step 8

## Constitution Check

| Principle | How |
| --- | --- |
| I | The maintainer instructed every #399 task autonomously, PRs merged; one phase = one commit |
| II | English in code and history; Russian only in `*_draft.md` |
| VI | Phases 7–9: check run, documentation, changelog |

No violation.

## Phases

1. Declarations, rules, graph and protocol 1.5 (12.7.1–3). Adversarial: the pairing removed; the entity-field check removed.
2. The write (12.1, 12.2). Adversarial: entity entries untagged.
3. The hit (12.2, 12.3, 12.5). Adversarial: a missing entity skipped instead of a miss.
4. `get_entries` (12.7.4). Adversarial: one call per key.
5. The machine test (12.1, 12.4). Adversarial: one entity entry removed — a miss, not a shorter list.
6. Versions. 7. Closing check run. 8. Documentation (#411 part II). 9. Changelog.
