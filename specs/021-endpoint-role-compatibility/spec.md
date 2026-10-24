# Feature Specification: Endpoint Role Compatibility

**Feature Branch**: `codex/issue-261-complete-relationships`

**Created**: 2026-10-24

**Status**: Draft — ready for planning; implementation not started

**Input**: Maintainer instruction to run `/speckit-specify` for [issue #261](https://github.com/bystrovmaxim/aoa/issues/261): validate the eight endpoint roles through an exact compatibility matrix, complete declarations, documentation and runnable examples.

## Clarifications

Issue #261 states the role-pair policy in full — the eight roles, the three compatibility rules, the complete 8×8 matrix, the twelve permitted and twenty-four prohibited unordered combinations, the NoInverse contract and the dictionary rules — so no clarification question is required for the policy itself.

### Session 2026-10-24

- Q: Should all role-compatibility refusals raise one new public exception type or reuse the existing `EntityFieldDeclarationError`/`SpecializationDeclarationError`? → A: One new public exception type (`RoleCompatibilityError`) for all compatibility refusals, with `EntityFieldDeclarationError` and `SpecializationDeclarationError` kept for their existing checks. No existing exception type becomes unused: the new type is additive, and only the removed dictionary `AssociationOne`-only refusal helpers (which raised `EntityFieldDeclarationError`) are deleted with their rule.

### Decisions taken without a question

These follow from the issue text and are recorded here so planning does not re-open them.

- **The matrix is the complete role-pair policy.** Compatibility is read from the matrix alone. No additional pair restriction is inferred from entity stereotypes or from One/Many cardinality.
- **No aliases.** The public names are `CompositeOne` and `CompositeMany`; `CompositionOne`/`CompositionMany` are not introduced as part of this work.
- **This specification supersedes two earlier wordings.** It replaces the former rule that every ordinary container pairs with every other ordinary container, and it supersedes the dictionary-specific `AssociationOne`-only and `NoInverse`-only restrictions introduced by #259.
- **Tests do not satisfy the enforcement deliverable.** The compatibility check must fire when a real project assembles its model, before graph publication; isolated engine tests are additional, not a substitute.

## Role Compatibility Matrix (normative)

Rows and columns are the roles declared on the two endpoints. "Allowed" means the role pair passes the compatibility check; all other declaration, inverse and classifier checks still apply.

| Role | AssociationOne | AssociationMany | AggregateOne | AggregateMany | CompositeOne | CompositeMany | Specialization | Generalization |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| AssociationOne | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed | Refused | Refused |
| AssociationMany | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed | Refused | Refused |
| AggregateOne | Allowed | Allowed | Refused | Refused | Refused | Refused | Refused | Refused |
| AggregateMany | Allowed | Allowed | Refused | Refused | Refused | Refused | Refused | Refused |
| CompositeOne | Allowed | Allowed | Refused | Refused | Refused | Refused | Refused | Refused |
| CompositeMany | Allowed | Allowed | Refused | Refused | Refused | Refused | Refused | Refused |
| Specialization | Refused | Refused | Refused | Refused | Refused | Refused | Refused | Allowed |
| Generalization | Refused | Refused | Refused | Refused | Refused | Refused | Allowed | Refused |

There are 12 permitted unordered combinations and 24 prohibited unordered combinations, counting a same-role pair once. Equivalently, the full directed 8×8 matrix contains 22 permitted and 42 prohibited cells.

### All 12 permitted unordered combinations

1. AssociationOne ↔ AssociationOne
2. AssociationOne ↔ AssociationMany
3. AssociationMany ↔ AssociationMany
4. AssociationOne ↔ AggregateOne
5. AssociationOne ↔ AggregateMany
6. AssociationMany ↔ AggregateOne
7. AssociationMany ↔ AggregateMany
8. AssociationOne ↔ CompositeOne
9. AssociationOne ↔ CompositeMany
10. AssociationMany ↔ CompositeOne
11. AssociationMany ↔ CompositeMany
12. Specialization ↔ Generalization

### All 24 prohibited unordered combinations

1. AggregateOne ↔ AggregateOne
2. AggregateOne ↔ AggregateMany
3. AggregateOne ↔ CompositeOne
4. AggregateOne ↔ CompositeMany
5. AggregateMany ↔ AggregateMany
6. AggregateMany ↔ CompositeOne
7. AggregateMany ↔ CompositeMany
8. CompositeOne ↔ CompositeOne
9. CompositeOne ↔ CompositeMany
10. CompositeMany ↔ CompositeMany
11. Specialization ↔ Specialization
12. Generalization ↔ Generalization
13. AssociationOne ↔ Specialization
14. AssociationMany ↔ Specialization
15. AggregateOne ↔ Specialization
16. AggregateMany ↔ Specialization
17. CompositeOne ↔ Specialization
18. CompositeMany ↔ Specialization
19. AssociationOne ↔ Generalization
20. AssociationMany ↔ Generalization
21. AggregateOne ↔ Generalization
22. AggregateMany ↔ Generalization
23. CompositeOne ↔ Generalization
24. CompositeMany ↔ Generalization

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assemble a model and enforce the role-pair matrix before publication (Priority: P1)

An author assembles a model whose reciprocal endpoints declare two roles. Before the graph is published, the two resolved roles are validated against the symmetric compatibility matrix; a permitted pair proceeds and a prohibited pair blocks publication with an actionable error.

**Why this priority**: This is the first mandatory deliverable and the reason the issue exists. A matrix that lives only in documentation or in isolated tests does not stop a real project from assembling and publishing an invalid model.

**Independent Test**: Assemble a model for each of the twelve permitted unordered combinations and confirm publication; assemble a model for each of the twenty-four prohibited unordered combinations and confirm each is refused before graph publication. Repeat the same pairs with the endpoints inspected in the opposite order and confirm the acceptance or refusal is unchanged.

**Acceptance Scenarios**:

1. **Given** two endpoints whose resolved roles form one of the twelve permitted unordered combinations, **When** the model is assembled through a public publication entry point, **Then** the pair passes the compatibility check and the graph is published.
2. **Given** two endpoints whose resolved roles form one of the twenty-four prohibited unordered combinations, **When** the model is assembled, **Then** the pair is refused with a declaration error naming both owner classes and fields, both resolved roles, the violated rule and a permitted correction — and the graph is never published.
3. **Given** a permitted pair and a prohibited pair that differ only in which endpoint is inspected first, **When** each is assembled, **Then** swapping the endpoints preserves the acceptance or refusal; the roles stay attached to their declared endpoints and neither the ownership meaning nor the One/Many value is exchanged.
4. **Given** an `AggregateOne`/`AggregateMany`, a `CompositeOne`/`CompositeMany` and an `Aggregate`/`Composite` pair, **When** each is assembled, **Then** all three are refused regardless of cardinality, because an ownership endpoint's reverse must be an `AssociationOne` or `AssociationMany`.
5. **Given** both `CompositeOne`/`AssociationMany` and `CompositeMany`/`AssociationOne`, **When** each is assembled, **Then** both are accepted — One and Many describe cardinality and neither add nor remove compatibility between role families.

---

### User Story 2 - Declare every relationship completely, reciprocal or intentionally one-way (Priority: P1)

Every entity-valued field on Core, Assoc, Detail, Spec and Enum carries a complete declaration, and the author states explicitly whether the relationship is reciprocal (two `Inverse` markers) or intentionally one-way (a `NoInverse` marker with no reverse field). State keeps its separate Lifecycle contract.

**Why this priority**: Complete declarations remain mandatory, and the role-pair matrix only applies to the two endpoints of an explicitly paired relationship. Without an exact reciprocal-versus-unpaired contract the matrix has nothing stable to validate.

**Independent Test**: Assemble the four declaration shapes in the NoInverse table — one unpaired `NoInverse` field, two mutually resolving `Inverse` markers, an `Inverse` pointing at a `NoInverse` field, and two `NoInverse` fields referring to each other's entity types — and confirm each produces its required result.

**Acceptance Scenarios**:

1. **Given** a complete reciprocal pair — each field carrying a supported container, exactly one `Inverse` marker, a nonblank `Field` description, and explicit requiredness/nullability — **When** the model is assembled, **Then** both endpoints name each other and the pair is validated against the matrix.
2. **Given** one ordinary field with `NoInverse` and no reverse field, **When** the model is assembled, **Then** it is accepted as an intentionally one-way relationship; `NoInverse` is a declaration of absence, not a marker for skipping one endpoint of a reciprocal pair.
3. **Given** an `Inverse` that points at a field marked `NoInverse`, **When** the model is assembled, **Then** it is refused — an unpaired field cannot be the reverse endpoint of a paired field — regardless of which endpoint is inspected first.
4. **Given** two fields marked `NoInverse`, even when their entity types refer to each other, **When** the model is assembled, **Then** they are accepted as two independent one-way relationships, never collapsed into one reciprocal pair and never given inverse metadata.
5. **Given** `Specialization` or `Generalization` marked `NoInverse`, **When** the model is assembled, **Then** it is refused; these roles require a reciprocal `Specialization`/`Generalization` pair with `Inverse` on both endpoints.
6. **Given** a bare entity, a raw entity collection, arbitrary metadata around a bare entity, `NoRelation`, a hidden graph edge or a model excluded from graph display, **When** the model is assembled, **Then** none of these substitutes for a complete relationship declaration, and hiding or excluding a declaration does not bypass validation.

---

### User Story 3 - Pair specialization and generalization exclusively (Priority: P1)

A paired inheritance relationship contains exactly one `Specialization` endpoint and exactly one `Generalization` endpoint, and neither role pairs with any of the six association, aggregate or composite roles. Existing classifier membership, alternative coverage and specialization semantics are preserved alongside the new compatibility check.

**Why this priority**: Inheritance is the one axis where the roles are not drawn from the six ordinary containers, and its refusals are the most likely to be misunderstood if the rule is not exact.

**Independent Test**: Assemble a complete valid classified axis; then assemble a `Specialization`/`Specialization` pair, a `Generalization`/`Generalization` pair, and each `Specialization` or `Generalization` paired with an ordinary role, each with otherwise valid declarations, and confirm each refusal states that the two roles pair exclusively with each other.

**Acceptance Scenarios**:

1. **Given** one `Specialization` endpoint and one `Generalization` endpoint, **When** the model is assembled, **Then** the pair passes the compatibility check, and the existing classifier-membership and alternative-coverage checks still apply.
2. **Given** `Specialization`/`Specialization` or `Generalization`/`Generalization`, **When** the model is assembled, **Then** the pair is refused.
3. **Given** a `Specialization` or `Generalization` paired with any of `AssociationOne`, `AssociationMany`, `AggregateOne`, `AggregateMany`, `CompositeOne` or `CompositeMany`, **When** the model is assembled, **Then** the pair is refused with a message explaining that `Specialization` and `Generalization` pair exclusively with each other.
4. **Given** a dictionary used as a specialization classifier, **When** the model is assembled, **Then** its classifier semantics are preserved and it is not treated as a relationship endpoint subject to this matrix.

---

### User Story 4 - Read a refusal that names both endpoints and the fix (Priority: P2)

A prohibited pair produces one consistent public exception that identifies both owner classes and field names, both resolved endpoint roles, the violated rule, and the permitted correction appropriate to that rule. A newly refused ownership/ownership pair is presented as a migration, never silently rewritten.

**Why this priority**: The failure boundary is a product contract. An author who sees a refusal must be able to correct the declaration without reading the implementation.

**Independent Test**: Trigger each distinct refusal family and read the message; confirm it names the two owners and fields, both roles, the rule, and the correction — and that a `CompositeMany`/`CompositeOne` refusal says the reverse of an ownership endpoint must be an association, never that all Many relationships are prohibited.

**Acceptance Scenarios**:

1. **Given** a `CompositeMany`/`CompositeOne` pair, **When** the model is assembled, **Then** the refusal says both endpoints carry ownership roles and the reverse of an ownership endpoint must be `AssociationOne` or `AssociationMany`, and it does not claim all Many relationships are prohibited.
2. **Given** a specialization/ordinary-role pair, **When** the model is assembled, **Then** the refusal explains that `Specialization` and `Generalization` pair exclusively with each other.
3. **Given** an ownership/ownership pair that was previously accepted, **When** the model is assembled, **Then** the refusal states which endpoint to change to `AssociationOne` or `AssociationMany` according to the intended domain meaning, and it does not silently rewrite declarations or invent database cascades, ownership uniqueness or storage constraints.
4. **Given** a declaration that fails an earlier check (a missing marker, an unresolved type, an absent reverse endpoint), **When** the model is assembled, **Then** the earlier check fires first and the reported boundary is accurate — compatibility tests use otherwise valid declarations so they actually reach the role-pair rule.

---

### User Story 5 - Use all six ordinary containers for dictionary targets (Priority: P2)

A dictionary target accepts every ordinary container under the same full-declaration and endpoint-pair rules as any other target. To-one and to-many dictionary selections resolve values, reject invalid ones, and round-trip through transport and graph export without forcing every dictionary relationship into association/one.

**Why this priority**: The dictionary-specific `AssociationOne`-only rule is obsolete and is removed in this issue; keeping it would contradict the matrix, and value support must be implemented, not merely un-refused.

**Independent Test**: For each of the six ordinary containers with a dictionary target, assemble a complete declaration, exercise to-one and to-many runtime values, empty/nullable cases, input/export in both schema modes, and graph projection, and confirm a permitted reciprocal dictionary role is accepted under the general matrix.

**Acceptance Scenarios**:

1. **Given** an `AssociationMany[D]` dictionary field, **When** the model is assembled, **Then** it is supported — the former `AssociationOne`-only restriction is gone.
2. **Given** `AggregateOne`/`AggregateMany`/`CompositeOne`/`CompositeMany` with a dictionary target, **When** the model is assembled, **Then** they are not rejected simply because the target is `Enum`.
3. **Given** a to-one dictionary container, **When** it is resolved, **Then** the identifier resolves to the canonical declared member; unknown, blank or incorrectly typed codes and foreign, fabricated or mismatched supplied members are refused with item paths where applicable.
4. **Given** a to-many dictionary container, **When** it is resolved, **Then** every identifier is resolved in input order and the declared container class is retained; the result is normalized into an immutable container without mutating the caller's input.
5. **Given** empty selection, explicit absence, omission, and loaded/unloaded states, **When** each is exercised, **Then** each is specified and tested distinctly rather than conflated.
6. **Given** the graph export of a dictionary relationship, **When** it is read, **Then** the declared role family, cardinality, endpoint direction, description and dictionary hint are preserved, no dictionary relationship is forced into association/one, and no duplicate relationship arrow is emitted; historical graph import remains supported independently of the source declaration rule.

---

### User Story 6 - Read the matrix and its rules in the reference documentation (Priority: P2)

A reader of the public relationship reference finds the definitions of all eight roles, the complete symmetric 8×8 matrix, the twelve permitted combinations, the three rules, the NoInverse table, the failure boundary and the dictionary rules — with the obsolete claims removed.

**Why this priority**: The matrix is policy, and policy that only lives in an issue or in code is not documented. Contradictory current claims must disappear or readers will apply the old rules.

**Independent Test**: Read the reference and each affected how-to page and tutorial section; confirm every claim matches the matrix, every illustrated pair shows both endpoints with complete declarations, and no page still states the former dictionary single-selection-only rule or the former claim that all ownership/ownership pairs are permitted.

**Acceptance Scenarios**:

1. **Given** the relationship reference, **When** it is read, **Then** it defines all eight roles and distinguishes ownership meaning from cardinality, and states the three compatibility rules covering every prohibited family.
2. **Given** the same reference, **When** it is read, **Then** it shows the complete symmetric 8×8 matrix and all twelve permitted unordered combinations, and both endpoints of each illustrated pair carry complete `Annotated` declarations.
3. **Given** the reference's inverse section, **When** it is read, **Then** it explains reciprocal `Inverse` versus an intentionally unpaired `NoInverse` field, includes the complete NoInverse table, two independent one-way fields, and the prohibition on `NoInverse` for `Specialization`/`Generalization`.
4. **Given** the reference's failure-boundary section, **When** it is read, **Then** it states the exact diagnostics and the migration of prohibited pairs, and links to the runnable scenarios and their executed notebooks.
5. **Given** every affected how-to page, tutorial section and the reference table, **When** they are read, **Then** no contradictory current claim remains; historical changelog entries stay identifiable as historical behaviour, while current guidance states the matrix.

---

### User Story 7 - Run the teaching scenarios and their notebooks (Priority: P3)

A learner works through coherent topics — plain associations, aggregation, composition, specialization/generalization, and dictionary endpoints — each as a numbered script with a matching notebook, a main function, clear assertions, expected-error handling and real output, executed in a fresh process.

**Why this priority**: The runnable examples are the third mandatory deliverable and make the matrix learnable; a matrix of sixty-four cells is not taught one file per cell but through grouped, corrected scenarios.

**Independent Test**: Execute each numbered script and its matching notebook in a fresh process, confirm they complete and print real output, and confirm the script and notebook results agree; copy any documentation code into clean files and execute it; check local links and section anchors.

**Acceptance Scenarios**:

1. **Given** the plain-associations scenario, **When** it runs, **Then** it demonstrates `AssociationOne`/`AssociationOne`, `AssociationOne`/`AssociationMany` and `AssociationMany`/`AssociationMany` and explains what each field's cardinality means.
2. **Given** the aggregation scenario, **When** it runs, **Then** it demonstrates `AggregateOne`/`AssociationMany` and `AggregateMany`/`AssociationOne`, a refused `Aggregate`/`Aggregate` pair, and its corrected reverse association.
3. **Given** the composition scenario, **When** it runs, **Then** it demonstrates `CompositeMany`/`AssociationOne` and `CompositeOne`/`AssociationMany`, refused `Composite`/`Composite` and `Composite`/`Aggregate` pairs, and corrected alternatives.
4. **Given** the specialization scenario, **When** it runs, **Then** it demonstrates a complete valid classified axis and representative same-role and ordinary-role mismatch refusals with otherwise valid declarations.
5. **Given** the dictionary scenario, **When** it runs, **Then** it demonstrates complete to-one and to-many selections across the ordinary relation families, canonical identity, invalid values, transport, graph kind/cardinality, and permitted reciprocal roles where present.
6. **Given** any scenario that groups a refusal with its corrected declaration, **When** it runs in a fresh process, **Then** a deliberately invalid declaration never contaminates another example's model discovery.

---

### Edge Cases

- Compatibility is symmetric: reading a reverse directed record must not rename or exchange the ownership meaning of a `Specialization` or `Generalization` container, and One/Many values stay attached to the endpoint that declared them.
- Two fields whose entity types refer to each other, share names, or contain matching instance identifiers are **not** inferred to be a reciprocal pair; reciprocal pairing is declared explicitly through `Inverse`, and a `NoInverse` declaration must not be targeted by any other field's `Inverse`.
- Field-only `Inverse(field_name="...")` and concrete `Inverse(Target, "...")` receive equivalent compatibility checks, and a supplied concrete target must match the resolved target.
- Cross-module declarations keep working without circular imports; compatibility of inherited endpoints uses resolved endpoint identity rather than matching short class names, and graph exclusion, `NoGraphEdge`, inherited fields, overrides and delayed type resolution must not bypass a check.
- `State` keeps its separate `Lifecycle` declaration contract and is outside the relationship-compatibility matrix.
- A dictionary used as a specialization classifier is distinct from a relationship endpoint and keeps classifier semantics.
- Custom property serializers and typed exported-property schemas are retained for dictionary relationships; no unsupported uniqueness or cardinality restriction is added.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The compatibility domain MUST contain exactly these eight endpoint roles: `AssociationOne`, `AssociationMany`, `AggregateOne`, `AggregateMany`, `CompositeOne`, `CompositeMany`, `Specialization`, `Generalization`. The public names MUST be `CompositeOne` and `CompositeMany`; no `CompositionOne`/`CompositionMany` alias MAY be introduced.
- **FR-002**: Every entity-valued field on Core, Assoc, Detail, Spec and Enum MUST carry a complete declaration — a supported relationship container, exactly one direction marker (`Inverse` or `NoInverse`), a nonblank assignment-side `Field` description, and explicit requiredness and nullability. `State` MUST keep its separate `Lifecycle` contract.
- **FR-003**: Bare entities, raw entity collections, arbitrary metadata around a bare entity and `NoRelation` MUST NOT substitute for a complete relationship declaration. Hiding a graph edge or excluding a model from graph display MUST NOT bypass declaration validation.
- **FR-004**: A paired inheritance relationship MUST contain exactly one `Specialization` endpoint and exactly one `Generalization` endpoint. `Specialization` MUST pair only with `Generalization` and vice versa; same-role pairs and pairing either with the six ordinary roles MUST be refused.
- **FR-005**: For a pair drawn from the six ordinary roles, at most one endpoint MAY be an ownership role (`Aggregate*` or `Composite*`); if one endpoint is ownership, the other MUST be `AssociationOne` or `AssociationMany`; if neither is ownership, both MUST be `AssociationOne` or `AssociationMany`. `Aggregate`/`Aggregate`, `Composite`/`Composite` and `Aggregate`/`Composite` MUST be refused regardless of cardinality or inspection order.
- **FR-006**: One and Many MUST describe cardinality only and MUST NOT add or remove compatibility between role families. Compatibility MUST be symmetric: swapping the endpoints MUST preserve acceptance or refusal, and the roles MUST stay attached to their declared endpoints.
- **FR-007**: The full 8×8 matrix MUST be the single source of truth for role-pair compatibility. Exactly twelve unordered combinations MUST be permitted and exactly twenty-four MUST be prohibited; equivalently, of the sixty-four directed cells, exactly twenty-two MUST be accepted and forty-two MUST be refused by the compatibility rule.
- **FR-008**: Compatibility MUST be enforced when a real project assembles its model, before graph publication. For a reciprocal pair the assembly MUST (1) resolve each container and role after forward annotations are rebuilt, (2) resolve each `Inverse` to the actual reverse endpoint, (3) verify both endpoints name each other under the reciprocal inverse contract, (4) validate the two roles against the symmetric matrix, and (5) only then allow graph publication.
- **FR-009**: Field-only `Inverse(field_name="...")` and concrete `Inverse(Target, "...")` MUST receive equivalent compatibility checks, and a supplied concrete target MUST match the resolved target. Cross-module declarations MUST work without circular imports, and inherited endpoint compatibility MUST use resolved endpoint identity rather than matching short class names.
- **FR-010**: `NoInverse` MUST mean the field has no reverse field constituting the other endpoint of the same relationship, and MUST be permitted on each of the six ordinary containers. A `NoInverse` declaration MUST NOT be targeted by any other field's `Inverse`, and MUST be refused when an `Inverse` points at it, regardless of which endpoint is inspected first.
- **FR-011**: Two fields marked `NoInverse`, even when they refer to each other's entity types, MUST be accepted as two independent one-way relationships and MUST NOT acquire inverse metadata or be collapsed into one paired relationship. Reciprocal pairing MUST be declared explicitly through `Inverse`.
- **FR-012**: `Specialization` and `Generalization` MUST NOT be marked `NoInverse`; they MUST require each other, reciprocal `Inverse` markers on both endpoints, and the existing classifier/alternative checks. `NoInverse` MUST NOT replace either direction of that pair.
- **FR-013**: A prohibited pair MUST produce one consistent public exception that identifies both owner classes and field names, both resolved endpoint roles, the violated rule, and the permitted correction appropriate to that rule. The exact type, text and failure boundary MUST be tested.
- **FR-014**: An ownership/ownership refusal MUST state that both endpoints carry ownership roles and that the reverse of an ownership endpoint must be `AssociationOne` or `AssociationMany`; it MUST NOT claim all Many relationships are prohibited. A specialization/ordinary-role refusal MUST explain that `Specialization` and `Generalization` pair exclusively with each other.
- **FR-015**: Newly refused ownership/ownership pairs MUST be treated as an explicit migration: the refusal MUST show which endpoint to change to `AssociationOne` or `AssociationMany` according to the intended domain meaning, and MUST NOT silently rewrite declarations or invent database cascades, ownership uniqueness or storage constraints.
- **FR-016**: The dictionary-specific rule accepting only `AssociationOne[D]` with `NoInverse` MUST be removed. All six ordinary containers MUST be available for dictionary targets under the same full-declaration and endpoint-pair rules as other targets, including `AssociationMany[D]` and `Aggregate`/`Composite` dictionary targets that are not rejected merely because the target is `Enum`.
- **FR-017**: To-one dictionary containers MUST resolve an identifier to the canonical declared member; to-many containers MUST resolve every identifier in input order and retain the declared container class; unknown, blank or incorrectly typed codes and foreign, fabricated or mismatched supplied members MUST be refused with item paths where applicable; results MUST normalize into immutable containers without mutating the caller's input.
- **FR-018**: Empty selections, explicit absence, omission and loaded/unloaded states for dictionary fields MUST be specified and tested distinctly. The to-one transport contract MUST be preserved, and the equivalent documented to-many input/export contract and both schema modes MUST be implemented. Custom property serializers and typed exported-property schemas MUST be retained, and no unsupported uniqueness or cardinality restriction MAY be added.
- **FR-019**: Graph exports and consumers MUST preserve the declared role family, cardinality, endpoint direction, description and dictionary hint. A dictionary relationship MUST NOT be forced into association/one and MUST NOT emit duplicate relationship arrows. Historical graph import support MUST be preserved independently of the source declaration rule.
- **FR-020**: The public relationship reference MUST be updated with: definitions of all eight roles and the distinction between ownership meaning and cardinality; the complete symmetric 8×8 matrix and all twelve permitted unordered combinations; the three compatibility rules covering every prohibited family; both endpoints of each illustrated pair with complete `Annotated` declarations; reciprocal `Inverse` versus intentionally unpaired `NoInverse`, including the complete NoInverse table, two independent one-way fields and the prohibition on `NoInverse` for `Specialization`/`Generalization`; the model-assembly failure boundary, exact diagnostics and migration; dictionary targets using One/Many and association/aggregation/composition without the obsolete `AssociationOne`-only restriction; and links to the runnable scenarios and their executed notebooks.
- **FR-021**: Affected how-to pages and tutorials MUST be updated alongside the reference table, removing the former dictionary single-selection-only rule and the former claim that ordinary ownership/ownership pairs are all permitted. Historical changelog entries MUST remain identifiable as historical behaviour; current guidance MUST state the matrix.
- **FR-022**: Teaching scenarios MUST use coherent learning topics rather than one file per matrix cell. Each numbered script MUST have a matching notebook, a main function, clear assertions, expected-error handling and real output, and MUST be executed in a fresh process so a deliberately invalid declaration cannot contaminate another example's model discovery.
- **FR-023**: The five required scenario topics MUST be covered: (1) plain associations, (2) aggregation, (3) composition, (4) specialization and generalization, (5) dictionary endpoints. Notebooks MUST be executed with retained actual outputs and execution counts, script and notebook results MUST agree, documentation code MUST be copied into clean files and executed, and local links and section anchors MUST be checked.
- **FR-024**: Verification MUST test all sixty-four directed role combinations — exactly twenty-two accepted and forty-two refused — and MUST assert symmetry while retaining individual endpoint roles and One/Many values when records are reversed. Compatibility fixtures MUST reach the role-pair check rather than failing on a missing marker, unresolved type or absent reverse endpoint.
- **FR-025**: Verification MUST exercise actual reciprocal declarations through public model assembly in addition to isolated matrix checks, covering every permitted family and every prohibited family, and including a valid `Specialization`/`Generalization` case with its classifier/alternative requirements.
- **FR-026**: Verification MUST cover `NoInverse` on each of the six ordinary roles including dictionary targets, two opposite-direction `NoInverse` fields accepted as independent relationships, an `Inverse` targeting a `NoInverse` field refused in both inspection orders, `NoInverse` on `Specialization` and on `Generalization` refused with a valid reciprocal control, one-sided inverse refusal, cross-module rebuilding, hidden-edge and excluded-host checks, and all six ordinary dictionary containers across runtime values, empty/nullable cases, input/export, both schema modes, graph projection and affected consumers.
- **FR-027**: Verification MUST include isolated adversarial regressions — admit an ownership/ownership pair, admit an invalid specialized pair, reject a permitted Many pair, restore `AssociationOne`-only dictionary acceptance, and bypass member validation — each of which MUST fail its intended check while valid neighbouring controls pass.
- **FR-028**: Planning MUST reserve exactly three closing tasks in this order and no other task may absorb them: the scoped check run taken to zero, the documentation with its executed examples, and the changelog as one article.
- **FR-029**: The scope of this feature MUST exclude editing the constitution, touching Russian documents/drafts or the excluded package, and — until separately authorized — committing, pushing, opening a pull request or merging. Existing changes and staging MUST be preserved.

### Key Entities

- **Endpoint role**: One of the eight public containers a field declares — the role family (association, aggregate, composite, specialization, generalization) together with cardinality (One/Many) where applicable.
- **Reciprocal relationship**: Two endpoints whose fields each declare `Inverse` naming the other, forming the single pair the compatibility matrix validates.
- **One-way relationship**: A single field declared with `NoInverse` and no reverse field — intentionally unpaired and outside the reciprocal matrix.
- **Compatibility matrix**: The symmetric 8×8 table that states, for every unordered role pair, whether the pair is permitted or refused.
- **Ownership role**: `AggregateOne`, `AggregateMany`, `CompositeOne` or `CompositeMany` — a role whose reverse endpoint must be an association role.
- **Declaration error**: The single public exception a prohibited pair raises, naming both endpoints, both roles, the violated rule and the correction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All sixty-four directed role combinations are exercised through the compatibility rule and produce exactly twenty-two acceptances and forty-two refusals; the same sixty-four pairs, inspected in reverse, produce the identical verdicts with the roles and One/Many values retained.
- **SC-002**: Every permitted unordered combination assembles and publishes through a public model-assembly entry point, and every prohibited unordered combination is refused before graph publication — not merely in isolated matrix tests.
- **SC-003**: Each distinct refusal family produces a declaration error that names both owner classes and fields, both resolved roles, the violated rule and the permitted correction, with the exact exception type, text and failure boundary pinned by a test.
- **SC-004**: The NoInverse table is exercised end to end: one unpaired `NoInverse` field accepted, two mutually resolving `Inverse` markers accepted, an `Inverse` targeting a `NoInverse` field refused in both orders, and two `NoInverse` fields accepted as independent relationships with no inverse metadata.
- **SC-005**: All six ordinary dictionary containers pass runtime values, empty/nullable cases, input/export in both schema modes, graph projection and affected consumers; a search of the code finds no remaining `AssociationOne`-only dictionary restriction.
- **SC-006**: Every illustrated pair in the reference shows both endpoints with complete `Annotated` declarations, and no affected page, tutorial section or reference table states the former dictionary single-selection-only rule or the former claim that all ownership/ownership pairs are permitted.
- **SC-007**: Each numbered teaching script and its matching notebook executes in a fresh process, prints real output, and agrees with the page's recorded output; documentation code executes from clean copied files and all local links and section anchors resolve.
- **SC-008**: Each required adversarial mutation — admit ownership/ownership, admit an invalid specialized pair, reject a permitted Many pair, restore `AssociationOne`-only dictionary acceptance, bypass member validation — fails its targeted check while its valid neighbouring control passes.
- **SC-009**: `bash scripts/run_checks_with_log.sh` is green, with only the two accepted remarks the constitution names.

## Assumptions

- Issue #261 is the authoritative feature source, and its matrix is the complete role-pair policy; no additional pair restriction is inferred from entity stereotypes or cardinality, and this specification supersedes the earlier ordinary-pairs-all-permitted wording and the dictionary-specific restrictions of #259.
- Public role names, the matrix, the `Inverse`/`NoInverse` contract, the exception contract and the transport/export contract are product contracts in this specification, so they are named explicitly despite the generic template's preference for omitting implementation detail. No module layout, algorithm or internal naming is prescribed.
- `State`'s `Lifecycle` contract is already specified elsewhere and is preserved unchanged; it is not re-specified here.
- The closing check run's two known remarks — the Vite chunk-size advisory and LangGraph's pending-deprecation warning — remain accepted and are not acted on.
- This phase writes the specification and its quality checklist only. It does not claim implementation, executed examples or a passing check run.
- The constitution, the maintainer's existing changes and the staging area remain untouched. Commits, pushes, pull requests and merges require a separate explicit instruction.
