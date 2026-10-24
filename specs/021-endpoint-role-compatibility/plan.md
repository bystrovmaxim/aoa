# Implementation Plan: Endpoint Role Compatibility

**Branch**: `codex/issue-261-complete-relationships` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification in [spec.md](spec.md) and [issue #261](https://github.com/bystrovmaxim/aoa/issues/261).

## Summary

A new role-pair compatibility check runs when a real project assembles its model, before graph
publication. For every explicitly paired relationship it maps each endpoint's container to one of the
eight public roles — `AssociationOne`, `AssociationMany`, `AggregateOne`, `AggregateMany`,
`CompositeOne`, `CompositeMany`, `Specialization`, `Generalization` — and validates the pair against
the symmetric 8×8 matrix. Twelve unordered combinations are permitted and twenty-four are refused;
ownership/ownership pairs (aggregate/aggregate, composite/composite, aggregate/composite) and any
specialization/generalization endpoint paired with an ordinary role are the newly refused families.
A refused pair raises one new public exception naming both owner classes and fields, both resolved
roles, the violated rule and the permitted correction.

The dictionary-specific `AssociationOne`-only rule is removed: all six ordinary containers are legal
for dictionary targets, with to-one and to-many value resolution, transport and graph projection.
The repository's tests, teaching scenarios and reference documentation are brought to the matrix.

Research and design below are workflow procedures, not repository commit phases. This command
performs no commits and creates no implementation task list; `/speckit-tasks` produces that.

## Technical Context

**Language/Version**: Python >=3.12 (local interpreter 3.12.x). No new dependency, no new package.

**Primary Dependencies**: existing Pydantic >=2 (local 2.12.x), pytest (local 8.4.x), the existing
`aoa-action-machine` entity/relation/graph machinery. `aoa-maxitor` and the adapters are consumers
of the graph export and are not modified.

**Storage**: none introduced. Declaration validation reads descriptors, never database rows. A
dictionary value resolves to the canonical declared member in memory; no persistence change.

**Testing**: pytest per package (`uv run --extra dev pytest packages/<pkg>/tests -v`), the
repository's closing runner `scripts/run_checks_with_log.sh`, and executed example scripts and
notebooks for the teaching scenarios.

**Target Platform**: the existing Python library environments; no runtime platform change.

**Project Type**: public library package (`aoa-action-machine`) plus teaching material (`examples/`)
and the reference documentation.

**Performance Goals**: none invented. The matrix check is a constant-time lookup over two resolved
roles per reciprocal pair, added to a build pass that already walks every declared field. No new
quadratic pass: reciprocity resolution already pairs fields, and the matrix check reuses that pairing.

**Constraints**: Python only, no new dependency; the whole repository including `aoa-demo` must be
green because the closing runner covers it; English in code, tests, docs and the changelog; the work
is prepared and shown but never committed, pushed, opened or merged without the maintainer's word
(Principle I); the constitution is read, not amended.

**Scale/Scope**: one source package touched (`aoa-action-machine`); its graph validators, domain
exceptions and relation/dictionary value code; one new validator module and one new exception type;
five teaching scenario scripts and their notebooks; reference and how-to/tutorial documentation; one
changelog article.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS.*

| Principle | Design evidence |
| --- | --- |
| I — the maintainer decides | The branch already exists at the maintainer's instruction. This plan and every phase below are prepared work; no commit, push, pull request or merge happens without a separate explicit instruction. |
| II — English in commits and code | Every artifact, docstring, test name, docstring example and changelog line written by this feature is English. |
| III — module headers | The new validator opens with the relative-path first line, a `Name — purpose.` title, `PURPOSE` and `ARCHITECTURE / DATA FLOW` sections, and a `"""` on its own line. |
| IV — AI-CORE blocks | The new public exception carries a `ROLE`/`CONTRACT`/`INVARIANTS` block; the matrix table (a module-level constant) carries no block, because a table is not a class or a function. |
| V — short docstrings | Every new class, function and method carries the one-line purpose. |
| VI — check run, then documentation, then changelog | Reserved as C1, C2, C3 below, in that order, and no work package absorbs them. |
| Adversarial verification | The five mutations of FR-027 run against a temporary copy with valid neighbouring controls; a mutation that does not fail its check means the test is wrong. |
| Governing text | The constitution is read and cited, never edited in this change. |

## Project Structure

### Documentation (this feature)

```text
specs/021-endpoint-role-compatibility/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── role-pair-matrix.md
    ├── noinverse-contract.md
    └── dictionary-transport.md
```

[tasks.md](tasks.md) is generated by `/speckit-tasks`; it is not produced here.

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── domain/
│   ├── relation_containers.py            # six ordinary containers; RelationType enum
│   ├── specialization_containers.py      # Specialization / Generalization containers
│   ├── enum_entity.py                    # dictionary catalogue + value resolution
│   └── exceptions.py                     # new RoleCompatibilityError (working name)
├── graph/
│   ├── core/node_graph_coordinator.py    # build(): call the new validator
│   ├── nodes/entity_graph_node.py        # per-node build: call the new validator
│   ├── edges/entity_reference_graph_edge.py   # dictionary reference projection
│   └── validators/
│       ├── entity_field_validator.py     # remove AssociationOne-only dictionary rule
│       ├── entity_inverse_validator.py   # reciprocity (existing; unchanged contract)
│       └── entity_role_compatibility_validator.py   # NEW: matrix check
└── tests/action_machine/graph/validators/        # 64-combination + symmetry + NoInverse + dictionary
examples/step_21_relations/                       # teaching scenarios 1–5, scripts + notebooks
docs/{reference,intents-and-invariants.md,how-to,CHANGELOG.md}
```

**Structure Decision**: add one validator and one exception; do not rebuild the resolver. The existing
`ResolvedEntityField` already carries `container`, `relation_kind`, `cardinality`, `targets`,
`has_inverse`, `inverse_entity`, `inverse_field`, `is_relation`, `is_specialization` and
`is_generalization`, so the new validator consumes the same normalized view the field and inverse
validators already share. The matrix lives as a module-level constant in the new validator, not as
new public API.

## Scope and unchanged behavior

- Unchanged: the completeness pass (every entity-valued field needs a supported container, exactly
  one direction marker, a nonblank `Field` description, explicit requiredness/nullability); the
  reciprocal-inverse contract (both endpoints name each other); `State`'s `Lifecycle` contract; the
  specialization validator's classifier/alternative/closure/cycle checks; the interchange graph's
  wire shape; historical graph import support.
- Changed deliberately: ownership/ownership pairs (aggregate/aggregate, composite/composite,
  aggregate/composite) and specialization/generalization paired with an ordinary role are refused at
  model assembly (FR-004, FR-005); the dictionary `AssociationOne`-only rule is removed (FR-016).
- Changed as a consequence: the field validator's dictionary refusals (`_dictionary_container_refusal`,
  `_dictionary_inverse_refusal`) are replaced by the general six-container rule and the general
  endpoint-pair rule; to-many dictionary values gain transport and export support (FR-017, FR-018).
- Out of scope: editing the constitution, Russian documents/drafts, the excluded package,
  `CompositionOne`/`CompositionMany` aliases, database cascades, ownership uniqueness or storage
  constraints, and — until separately authorized — committing, pushing, opening a pull request or
  merging.

## Design and implementation work packages

The packages below are the design view; [tasks.md](tasks.md) realises them as ordered tasks.
W1 is the foundational procedure (the validator cannot be wired before the matrix and exception
exist); W2–W3 are the dictionary procedures; W4 is the package's own tests; W5 is the teaching
scenarios.

### W1 — Role-pair compatibility validator and exception (FR-004…FR-009, FR-013, FR-014)

A new `graph/validators/entity_role_compatibility_validator.py` exposes
`validate_entity_role_compatibility(entities=None)`. It walks every declared `@entity` class (the
same `_all_declared_entity_classes` walk the inverse validator uses), and for each field that is a
reciprocal endpoint (`has_inverse` and `is_relation`/`is_specialization`/`is_generalization`) it:

1. resolves the reverse field on the target (the same `_reverse_field` resolution the inverse
   validator uses, compared by `(declaring_owner, field_name)` identity);
2. maps each endpoint's `container` to its role — the six ordinary container classes plus
   `Specialization`/`Generalization`;
3. consults the symmetric matrix constant ([contracts/role-pair-matrix.md](contracts/role-pair-matrix.md));
4. on a refused cell, raises the new exception naming both owner classes and fields, both resolved
   roles, the violated rule and the permitted correction.

The matrix constant encodes the family rule (association pairs with any ordinary role; aggregate and
composite pair only with association; specialization/generalization pair only with each other), so
One/Many cardinality never changes a verdict. The check runs after `validate_entity_inverses()` and
before node gathering in `NodeGraphCoordinator.build()`, and beside `validate_entity_inverses()` in
`entity_graph_node.py`, mirroring where the existing passes already run; `NoGraphEdge`, excluded
hosts, inherited fields and delayed type resolution cannot bypass it because it reads resolved
descriptors, not graph edges.

The new exception `RoleCompatibilityError` (one new public type; the maintainer's confirmed answer to the
clarification question) lands in `domain/exceptions.py` with an AI-CORE block and the message contract of
[contracts/role-pair-matrix.md](contracts/role-pair-matrix.md#diagnostics): an ownership/ownership
refusal says the reverse of an ownership endpoint must be `AssociationOne`/`AssociationMany`; a
specialization/ordinary-role refusal says `Specialization` and `Generalization` pair exclusively with
each other. `EntityFieldDeclarationError` and `SpecializationDeclarationError` keep their existing
checks and fire first when their subject fails.

### W2 — Remove the dictionary `AssociationOne`-only rule (FR-016)

`entity_field_validator.py` stops refusing a dictionary target that is not `AssociationOne` with
`NoInverse`. The three refusals — `_dictionary_container_refusal`, `_dictionary_inverse_refusal`, and
the `if resolved.container is not AssociationOne` branch — are deleted or rewritten to the general
rule: any of the six ordinary containers is a legal dictionary relationship under the same
full-declaration and endpoint-pair rules as any other target. A reciprocal dictionary endpoint (a
field on the dictionary side naming back) is now judged by the general matrix and inverse rules, not
a dictionary-only `NoInverse` prohibition. The module header and the refusal text that names
`AssociationOne[...] | None, NoInverse()` are rewritten to name the six containers.

### W3 — To-many dictionary values, transport and graph projection (FR-017, FR-018, FR-019)

`relation_containers.py` gains to-many dictionary value support beside the existing to-one path:
to-one resolves one identifier to the canonical declared member; to-many resolves every identifier
in input order and retains the declared container class; unknown, blank or incorrectly typed codes
and foreign, fabricated or mismatched supplied members are refused with item paths; results normalize
into immutable containers without mutating the caller's input. Empty selection, explicit absence,
omission and loaded/unloaded states are each specified and tested distinctly.

Transport and export follow the existing to-one dictionary contract and gain the equivalent to-many
input/export form and both schema modes. Graph projection keeps the declared role family,
cardinality, endpoint direction, description and dictionary hint; a dictionary relationship is not
forced into association/one and no duplicate relationship arrow is emitted. Historical graph import
support is preserved independently of the source declaration rule.

### W4 — The package's own tests (FR-024…FR-027)

Tests cover all sixty-four directed role combinations (exactly twenty-two accepted, forty-two
refused) and assert symmetry with endpoint roles and One/Many values retained when records are
reversed. Actual reciprocal declarations exercise public model assembly for every permitted family
and every prohibited family, including a valid `Specialization`/`Generalization` case with its
classifier/alternative requirements. The NoInverse table is covered end to end: one unpaired
`NoInverse` field; two mutually resolving `Inverse` markers; an `Inverse` targeting a `NoInverse`
field refused in both orders; two `NoInverse` fields accepted as independent relationships; `NoInverse`
on `Specialization` and on `Generalization` refused with a valid reciprocal control. All six ordinary
dictionary containers are covered across runtime values, empty/nullable cases, input/export, both
schema modes, graph projection and affected consumers. The five adversarial mutations of FR-027 run
in isolation, each failing its intended check while valid neighbouring controls pass.

### W5 — Teaching scenarios and notebooks (FR-022, FR-023)

Five numbered scripts under `examples/step_21_relations/`, each with a matching notebook, a main
function, clear assertions, expected-error handling and real output, executed in a fresh process so
a deliberately invalid declaration cannot contaminate another example's model discovery:

1. plain associations — `AssociationOne`/`AssociationOne`, `AssociationOne`/`AssociationMany`,
   `AssociationMany`/`AssociationMany`, with each field's cardinality explained;
2. aggregation — `AggregateOne`/`AssociationMany`, `AggregateMany`/`AssociationOne`, a refused
   aggregate/aggregate pair and its corrected reverse association;
3. composition — `CompositeMany`/`AssociationOne`, `CompositeOne`/`AssociationMany`, refused
   composite/composite and composite/aggregate pairs and corrected alternatives;
4. specialization/generalization — a complete valid classified axis and representative same-role and
   ordinary-role mismatch refusals with otherwise valid declarations;
5. dictionary endpoints — complete to-one and to-many selections across the ordinary relation
   families, canonical identity, invalid values, transport, graph kind/cardinality and permitted
   reciprocal roles where present.

## Closing tasks reserved for `/speckit-tasks`

Exactly three tail tasks, in this order, and no work package may absorb them.

1. **C1 — The check run, taken to zero.** `bash scripts/run_checks_with_log.sh`, every remark fixed,
   including the demo package, Ruff/mypy/pylint/vulture/Radon and the packaging smoke. The two
   accepted third-party remarks stay. A failing check is repaired, not triaged.
2. **C2 — The documentation.** Written after the code is settled: the reference gains the eight role
   definitions, the symmetric 8×8 matrix, the twelve permitted combinations, the three rules, the
   NoInverse table, the failure boundary and migration, and the dictionary rules (FR-020); affected
   how-to pages and tutorials drop the former dictionary single-selection-only rule and the former
   claim that all ownership/ownership pairs are permitted (FR-021). Every case appears as a script
   and a notebook, every example is executed with its output recorded, local links and anchors are
   checked, and a Russian draft sits beside each page written (drafts stay outside the commit).
3. **C3 — The changelog, one article.** `docs/CHANGELOG.md` gains a single readable piece about what
   the work created — the matrix, the refused families, the dictionary change — in plain words with
   the nuances a user has to know, and no per-file account.

## Verification design

[quickstart.md](quickstart.md) holds the runnable scenarios S1–S9; this section says what they
partition.

- **Matrix**: sixty-four directed combinations, twenty-two accepted and forty-two refused, plus
  symmetry and retained One/Many values on reversal.
- **Assembly**: actual reciprocal declarations through `NodeGraphCoordinator.build()` for every
  permitted family and every prohibited family, and a valid specialization axis.
- **NoInverse**: the five-row table, including `NoInverse` on `Specialization`/`Generalization`
  refused and two independent one-way fields not collapsed.
- **Dictionary**: six ordinary containers across values, empty/nullable, input/export, both schema
  modes, graph projection, canonical identity and invalid codes.
- **Diagnostics**: the exact exception type, text and failure boundary for each refusal family.
- **Adversarial**: the five mutations of FR-027, each failing its check while its control passes.

## Research and design gates

- Research complete: [research.md](research.md) records each decision with the file and line that
  justified it and the alternative rejected.
- Data view: [data-model.md](data-model.md) defines the endpoint role, the reciprocal pair, the
  matrix and the declaration error.
- Interfaces: [role-pair matrix](contracts/role-pair-matrix.md),
  [NoInverse contract](contracts/noinverse-contract.md),
  [dictionary transport](contracts/dictionary-transport.md).
- The single open question (the exception type) is resolved: one new public type, `RoleCompatibilityError`,
  recorded in the specification's Clarifications.
- No gate failure.

## Complexity Tracking

No constitutional exception is introduced. The change is additive but small: one validator module, one
public exception type, one matrix constant, and a widened dictionary rule. No dependency is added, no
new public name beyond the exception is created, and no second relationship layer replaces the
existing field/inverse/specialization passes. The single deliberate behaviour change — ownership/
ownership pairs stop being permitted — is named in the specification, the plan, the tests and the
changelog rather than absorbed quietly.
