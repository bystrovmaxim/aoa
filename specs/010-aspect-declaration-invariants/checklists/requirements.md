# Specification Quality Checklist: An aspect declaration's signature is an invariant, not a convention

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

- **The deliberate exceptions to "no implementation details" are names that are themselves the contract.** The parameter names are what a developer writes, what the engine binds to by position, and the text every refusal quotes; a specification that called them "four values in the order the machine passes them" could not be tested, because the defect is precisely a name that differs from the one the machine uses. The same holds for the three error names in FR-019: they are the public surface a caller catches, and the clarification above decided their number. Nothing else in the specification names a module, a class or a function.
- **The two decisions that a maintainer may want to revisit** are recorded under Clarifications rather than left open: all four decorators in scope, and a hard refusal with the corpus migrated inside the change rather than a warning window. Both are argued there; both change the size of the work substantially, and neither was put to the maintainer as a question in the clarification session — they are the two places where the specification guessed, and it says so.
- **The mechanism for FR-011 is now settled by clarification** — both moments: the declared annotation at assembly, the returned instance at run time. It was deliberately open while the specification was first written, and the two acceptance paths are now separate scenarios so that a check cannot satisfy one and call the other done.
- **The public surface deliberately grows by two names** (FR-019): the signature's error and the duplicate summary's. The third rule — the summary's answer — revives `ActionResultTypeError`, which is public already and raised nowhere today. That is a vocabulary commitment, taken by decision rather than by default, and it is the reason the specification states explicitly (FR-021) that the new errors must stay catchable by the family type the existing handlers already catch.
- **The count of non-conforming declarations** was measured with a syntax-tree scan on 2026-10-18 and corrected twice: **499**, not the 211 or the 523 written before. The first figure counted only the two decorators the issue's table names and only `.py` files; the second judged every declaration against the summary's name list, which counted each `@on_error` and `@compensate` method as misnamed. The scan in `evidence/scan_corpus.py` — judging each decorator against its own contract and separating the fixtures that are wrong on purpose — gives 499 non-conforming, **19 deliberate** (`pytest.raises` fixtures, which stay wrong) and **480 to migrate**. It is an estimate of work, not a requirement: SC-003 asks for the unintentional sites to reach zero, whatever the number turns out to be once the rules land.
- **One claim in the issue did not survive measurement and the specification records it**: the error handler's result is not validated today — `ActionResultTypeError` is imported and caught in `error_handler_executor.py` and raised nowhere in the package. This change does not add that validation; FR-012 and SC-007 speak only of the cached result's refusal, which does exist. A reader who trusts the issue on that point would expect a check that is not there.
