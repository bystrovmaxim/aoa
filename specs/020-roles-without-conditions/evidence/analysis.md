# Analysis — spec, plan and tasks against each other

**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md) | **Date**: 2026-10-24

Read-only cross-artifact pass over the three core artifacts and the constitution, then the findings
were resolved at the maintainer's instruction. Each row records what was found and what changed.

## Findings

| ID | Category | Severity | Location | Finding | Resolution |
| --- | --- | --- | --- | --- | --- |
| B1 | Ambiguity | HIGH | spec.md Clarifications, second bullet | The clarification said the four example pages keep their numbers **and** that "page numbers do not move", while plan R12 and T027 rename four suffixes. A reader could not tell whether names were frozen. | The bullet now separates the two: numbers stay, the four suffixes that name the removed mechanism move, and the tutorial links are rewritten in the same phase. |
| E1 | Coverage | HIGH | tasks.md (whole file) vs SC-001 | SC-001 is a search with a recorded result, and no task ran it. The requirement had zero verification. | Folded into T030 as its closing step: the search over source, tests, examples and documentation, recorded in `evidence/no-removed-names.md`, a hit sending the page back rather than being explained away. SC-001 also names the two pages allowed to carry a removed word once. |
| E3 | Coverage | HIGH | tasks.md T020 vs FR-017 | The timing consequence — a migrated condition now refuses inside the run — was stated only in documentation prose, with no test making it visible. A prose claim with no observation is a claim. | T020 now asserts the event sequence: the run's start is published before the object refusal. |
| F1 | Inconsistency | HIGH | plan.md Scale/Scope, research.md R13 | "17 test modules migrated (15 + 2)" was arithmetically false: of the seventeen that name the mechanism, one is replaced and one deleted, and one further module outside the seventeen is deleted with the exception it tested. | Both files now state the exact split, and say why the exception module does not appear in the search that found the seventeen. |
| F2 | Inconsistency | HIGH | tasks.md T008, dependency block, parallel examples | T008 carried `[P]` while editing the same `intents/check_roles/__init__.py` as T007; and the dependency block drew T004→…→T010 as a chain that contradicted the `[P]` markers on T005/T006/T008/T009. | T008 lost `[P]` and now follows T005/T006/T007; the dependency block shows the real shape (T004, then a parallel batch, then T008, then T010), and the parallel-examples list matches it. |
| E2 | Coverage | MEDIUM | tasks.md T030 vs FR-016, SC-008 | SC-008 asks that an author convert each of four shapes from the migration section alone, but T030 only said "the migration section" without naming what it must carry. | T030 names all four before/after pairs and requires them in that section. |
| C1 | Underspecification | MEDIUM | tasks.md T001 | The baseline covered three of eight packages without saying why, so a later failure in another package could not be told apart from a pre-existing one. | T001 now says the three are the affected ones and records that T029 covers the other five. |
| B2 | Ambiguity | MEDIUM | quickstart.md S2 | The `-k "migration or removed"` selector could collect nothing and still exit green on an empty run. | S2 now names the test module it runs. |
| F3 | Inconsistency | MEDIUM | plan.md work packages vs tasks.md procedures | The plan's W1–W6 and the task file's Procedures 1–8 were not mapped, so a reader had to infer which task realises which package. | The plan's work-package section now maps W1–W4 to T004–T010, W5 to T011–T024 and W6 to T025–T028. |
| A1 | Duplication | LOW | spec.md SC-002, SC-004 | Both speak to "no answer carries a word outside the three"; SC-002 counts refused forms, SC-004 covers produced decisions. Overlapping but not contradictory. | Left as is: one is about declarations, the other about answers. Recorded so a later reader does not merge them by accident. |
| F4 | Inconsistency | LOW | data-model.md | The specification says "object rule"; the code says "object check" in `object_gate` and `get_access_decide_graph_node`. | Recorded in the data model as one concept under two names, with neither renamed by this feature. |

## Coverage

| Requirement | Has task? | Task IDs |
| --- | --- | --- |
| FR-001 accepted declaration forms | yes | T004, T011 |
| FR-002 removed names, migration message | yes | T007, T008, T012 |
| FR-003 role step answers one word | yes | T005, T013 |
| FR-004 three words, stored word refused | yes | T009, T018 |
| FR-005 order and every stated count | yes | T009, T010, T019, T030 |
| FR-006 dead code removed with its last user | yes | T008, T029 |
| FR-007 `@access_decide` carries the rule | yes | T015, T016 |
| FR-008 no repetition of the declared role check | yes | T016, T017 |
| FR-009 optional object rule, both paths | yes | T015, T021 |
| FR-010 one edge per distinct role | yes | T006, T022 |
| FR-011 `AccessDecide` node and its companions | yes | T023 |
| FR-012 role outcomes preserved | yes | T013 |
| FR-013 sentinel inside a choice | yes | T005, T011, T013 |
| FR-014 repository declarations migrated | yes | T025–T028 |
| FR-015 documentation rewritten, cases twice, drafts | yes | T030 |
| FR-016 migration stated for an author | yes | T030 |
| FR-017 the timing consequence is stated | yes | T010, T020, T030 |
| FR-018 five adversarial checks | yes | T014, T021, T025 |
| FR-019 three closing tasks, in order | yes | T029, T030, T031 |
| FR-020 exclusions | n/a | scope statement; no task is the correct coverage |
| SC-001 no occurrences, search recorded | yes | T030 |
| SC-002 every form accepted and refused | yes | T011, T012 |
| SC-003 role tests keep their outcomes | yes | T001, T013 |
| SC-004 three words anywhere | yes | T018 |
| SC-005 demo and pages execute, docs clean | yes | T024, T028, T030 |
| SC-006 mutations caught, no duplicated role check | yes | T014, T017, T021, T025 |
| SC-007 check run green | yes | T029 |
| SC-008 four shapes convertible from the migration section | yes | T030 |

Unmapped tasks: none. Every task belongs to a procedure whose story or closing role is stated, and
T004–T010 are the foundational removal that no single story owns.

## Constitution alignment

PASS, with one recorded reading rather than a deviation: Principle VI orders the check run before the
documentation, and the example scripts are executable code that uses the removed API. They are
migrated as code in T027/T028 and their prose is written in T030; the check run does not execute
examples, so C1's green result does not depend on the choice. Principles I–V are satisfied by the
task text: no commit is authorized, all artifacts are English, touched modules keep their headers,
AI-CORE blocks are rewritten rather than deleted, and new callables carry one-line docstrings.
Exactly three closing tasks exist and no earlier task absorbs them.

## Metrics

- Requirements: 20 functional, 8 success criteria — 28 total.
- Tasks: 31 (setup 3, foundational 7, US1 4, US2 3, US3 4, US4 3, US5 4, closing 3).
- Coverage: 27 of 27 applicable requirements have at least one task (FR-020 is a scope statement) — 100 %.
- Critical issues: 0. High: 5, all resolved. Medium: 4, all resolved. Low: 2, one noted in the data model, one left deliberately.
- After the fixes the three artifacts agree on: the number of renamed pages, the number of touched test modules, the dependency order of the foundational procedure, and the tasks that verify each success criterion.
