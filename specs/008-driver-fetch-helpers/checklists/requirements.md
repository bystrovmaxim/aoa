# Specification Quality Checklist: A domain reads all rows and one value through the driver's protected helpers

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-18
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Type of feature, stated plainly**: an internal library change whose "users" are developers of domain resources and the library user who upgrades on 1.0.1a4. There is no end-user business flow, so the vocabulary is the library's own — contract, resource, driver, helper, wrapper, nested action, unit of work. The two checklist items about implementation details and non-technical stakeholders are read in that light, exactly as the specification before it read them: no language, driver library or file path appears as a requirement, while the member names and shapes in the issue do, because they *are* the contract this feature changes.
- **How this specification was written**: from issue [#222](https://github.com/bystrovmaxim/aoa/issues/222) and from the current working tree, not from the issue's line numbers. Verified before writing: the driver holds exactly two protected query helpers (`_execute` at `postgres_resource.py:229`, `_fetchrow` at `:252`) over one `_require_connection` (`:223`); the three contract modules carry no query member; `packages/aoa-demo`'s identity domain publishes exactly two operations (`read_person`, `record_login`) over `_read_person` and `_write_login`, so FR-015's two new private reads are genuinely new rather than a rename; the demo's fake connection answers only `execute` and `fetchrow`, so it must gain the two driver calls the new helpers make; `docs/extensions/postgresql.md` and `docs/how-to/authoring-resource.md` each list only the two existing helpers; the package version is `1.0.1a4` and the changelog's last heading is `## [Unreleased]`.
- **One prior decision is superseded, and the specification says so where it happens.** `specs/007-sql-contract-driver-helpers/spec.md` chose two helpers and left `_fetch`/`_fetchval` out because no caller existed. The issue's consumer (bystrovmaxim/gameoffer#72) and the demo's two new private reads are that caller now, so the pair is added; the Clarifications section records the earlier decision and what changed about its premise rather than quietly contradicting it.
- **The issue's vulture premise does not hold, and this is the second spec to record it.** `pyproject.toml` runs `vulture` at `min_confidence = 80`, and an unused method carries 60 %; an uncalled helper therefore would not fail the check run. NFR-3 and AC-6 are satisfied by the demo's callers and by the search over `packages/`, not by passing the check. The threshold is not lowered and no fake caller is added, and SC-009 states the caller as the real evidence.
- **Decisions taken while writing, each with its ground, each in Clarifications**: **(1) named parameters are refused by the annotation, not by a runtime guard** — the issue closes the message set at two, and `_execute`/`_fetchrow` carry the same annotation with no guard, so a guard on the new pair alone would split four helpers into two shapes. **(2) `_fetchval` cannot distinguish no row from a SQL `NULL`** — the driver cannot either, and a sentinel or an `_fetchval_or` would be exactly the speculative member the issue refuses; the docstring and the pages say it instead. **(3) The demo's demonstration is its suite, not a route** — adding an action, tool or screen would widen an additive library change into demo surface the issue does not ask for. **(4) The changelog stays under `## [Unreleased]` with no version bump**, following the maintainer's own correction recorded in #215 rather than the issue's "version" wording. **(5) Sites are named by member and page, never by line number**, because the issue's line numbers already drifted once.
- **Scope boundaries are drawn where the issue's own anti-requirements are**: no query member on the structural contract, the base resource or the wrapper (FR-013); no `executemany`, cursor, bulk copy, timeout, record class, pool or transactional helper; no behaviour change to the existing pair or the lifecycle (FR-014); no migration, since both new queries read a table the store already reads and the repository carries no schema for it.
- **The issue's acceptance list is carried rather than summarised**: AC-1 … AC-8 map to SC-003, SC-004, SC-001, SC-002, SC-005, SC-009, SC-011 and SC-010 respectively, so planning inherits each item; SC-012 adds the issue's NFR-1 in checkable form — a 1.0.1a4 subclass still valid, existing checks unedited.
- **Sections deliberately absent**: no separate `Dependencies` section, because the feature adds no dependency and must work with no database at all (FR-024). No version section, because the decision is that this feature introduces no version (FR-023).
- **Not this command's job**: the specification does not choose file layout, does not reserve tasks and does not write the documentation. `/speckit-plan` and `/speckit-tasks` follow; `/speckit-clarify` has nothing open, since no marker remains and every ambiguity the issue left is settled above.
- **Checklist result**: 16/16 items passing on the first pass; no item failed, so no iteration was needed.
- **Clarification round ran on 2026-10-18 and asked three questions, all answered and integrated** (`### Session 2026-10-18 — clarification` in the spec): the demo's demonstration is two private reads on the PostgreSQL store rather than public operations, an action or a route, with the driver-free base and the in-memory store unchanged (US4, FR-015 … FR-020, Key Entities, Out of scope, SC-007, SC-008, Assumptions rewritten); named parameters keep the annotated-tuple contract with no runtime guard, exactly as `_execute` and `_fetchrow` (FR-007 confirmed, no edit); and the changelog stays a single `### Added` article under `## [Unreleased]` with no version bump and no dated heading (FR-023 confirmed, no edit). Two of the three answers confirmed decisions already written; only the demo's shape changed. Checklist state after the round: 16/16, unchanged, so no marker moved.

- **After the plan and the tasks were written, the specification gained FR-025 and SC-013**: the page-and-count case must also ship as a runnable script under `examples/` and a notebook of the same case, because principle VI of the constitution requires every case twice and no other artifact carries that obligation. The clause is a process requirement rather than a new capability: it changes no shape in §1 of `data-model.md` and no code under `packages/`. Checklist state stays 16/16 — the two new requirements are covered by tasks T017 and T018 and by the plan's documentation design.
