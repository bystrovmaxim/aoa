# Implementation Plan: An entity reads its private attributes

**Branch**: `feature/issue-414-entity-private-attributes` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

## Summary

`BaseEntity.__getattr__` hands every name that is not a declared field to Pydantic's own lookup (R1).

## Constitution Check

I (instructed autonomously, one phase = one commit), II (English in code), VI (check run, documentation, changelog) — no violation.

## Phases

1. The fix (13.1). Tests: a private attribute on a full and a partial entity; a missing declared field; an unknown name. Adversarial: the hand-over removed.
2. Graph files and versions. 3. Closing check run. 4. Documentation: step 22 with a script and a notebook. 5. Changelog.
