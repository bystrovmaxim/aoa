# Specification Quality Checklist: A role's mode is refused where it is declared, not where it is read

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-19
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

- **The deliberate exceptions to "no implementation details" are names that are themselves the contract.** The four member names and the error name are what a developer writes, what the refusal quotes and what a caller catches; a specification that called the members "the four lifecycle values" could not be tested, because the defect is a spelling that differs from the one the package accepts. The same holds for `_role_mode_info["mode"]`: an acceptance item in the issue asserts on that entry, and a test that cannot name it cannot check that a member was stored unchanged. Nothing else in the specification names a module, a class or a function; the two paths quoted (`intents/access_control/roles.py`) appear only in the measured context, as evidence for the claim about who reads the value.
- **One measured correction is recorded rather than smoothed over.** The issue says 67 call sites and lists `BaseRole` among the roles declared `ALIVE`; the scan of 2026-10-19 finds 69 sites, and `BaseRole` carries `@exclude_graph_model` and no `@role_mode` — it is never asked for a mode. The Assumptions section states both, because a plan that trusts the issue would edit a file that has nothing to edit and would budget for two fewer sites than exist.
- **The decisions a maintainer may want to revisit are under Clarifications, not left open.** Three of them change the shape of the result: the refusal uses the existing error rather than a new one, the argument is refused rather than coerced, and the four names are listed in enum-definition order. Each is argued there. None was put to the maintainer as a question, because each has a default the issue itself already points at.
- **The boundary is stated three times on purpose** — in Context, in Clarifications and in FR-011 — because it is the one thing this change is most likely to get wrong in the other direction: a developer told "the decorator now validates the mode" may reasonably conclude that `UNUSED` should be refused there too. It is not, and the three context rules keep the errors and warnings they raise today.
- **No clarification marker was needed.** The issue answers the questions this feature would otherwise ask — which error, which moment, which set, what stays at the consumers — and the two facts it got wrong are measurements, not decisions, so there was nothing to put to the maintainer.
