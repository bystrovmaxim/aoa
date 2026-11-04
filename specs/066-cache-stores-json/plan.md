# Implementation Plan: The cache stores JSON

**Branch**: `feature/issue-410-cache-stores-json` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: issue #410, step 7 of 8 of #399.

## Summary

The store keeps bytes (R1); the machine writes JSON, reads it back and compares before storing (R2), and reads a new Result on every hit, dropping an entry that no longer reads (R3); a test proves rule 2 on a real hit (R4).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14) · **Testing**: pytest · **Scale/Scope**: `runtime/cache_entry.py`, `runtime/cache_coordinator.py`, `runtime/action_product_machine.py`, `exceptions/cache_serialization_error.py` (new); tests; the how-to example and page; tutorial step 8

## Constitution Check

| Principle | How |
| --- | --- |
| I | The maintainer instructed every #399 task autonomously, PRs merged; one phase = one commit |
| II | English in code and history; Russian only in `*_draft.md` |
| VI | Phases 6–8: check run, documentation, changelog |

No violation.

## Phases

1. **Bytes** (9.1) — R1, R3's read. Tests: a hit gives a new Result; `put` receives bytes; `@cache_read` gets the new Result with the stored metadata. Adversarial: the store keeps the Result object again.
2. **The write's read-back** (9.2) — R2. Tests: the three kinds; nothing stored; subclass of `CacheContractError`. Adversarial: the comparison skipped.
3. **Stale entries** (9.3) — R3. Tests: unreadable bytes → invalidate, run, `@cache_read` not called, next run hits. Adversarial: the read error propagated.
4. **Rule 2 on a real hit** — R4. Adversarial: `entities` removed from the stored JSON.
5. **Versions**. 6. **Closing check run**. 7. **Documentation** — step 8, the cache adapter how-to and its example; #401 section 4.9. 8. **Changelog**.
