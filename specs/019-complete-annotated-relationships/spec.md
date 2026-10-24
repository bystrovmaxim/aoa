# Feature Specification: Complete Annotated Relationships

**Feature Branch**: `feature/issue-259-complete-annotated-relationships`

**Created**: 2026-10-24

**Status**: Draft — clarification complete; ready for planning; implementation not started

**Input**: Maintainer instruction to run `/speckit-specify` for [issue #259](https://github.com/bystrovmaxim/aoa/issues/259), following the discussion about mandatory complete declarations for every entity stereotype except State.

## Clarifications

### Session 2026-10-24

- Q: Should this feature introduce the new runtime relationship-pair compatibility matrix from issue #259? → A: No (option B). Remove the new matrix from this feature. Require complete declarations while preserving existing compatibility checks.

- Q: Must both fields of a reciprocal relationship explicitly name each other through Inverse, while NoInverse remains available for one-way relationships? → A: Yes (option A). Both endpoints require reciprocal Inverse markers. NoInverse remains valid for an intentionally unpaired relationship with no reverse field.

- Q: Should an explicit dictionary association use an ordinary association edge or retain the special dictionary-reference edge? → A: Ordinary association (option A). Generate one entity_relation edge with relation_type association, cardinality one and has_inverse false; retain the field reference_qualname and generate no entity_reference edge for new declarations. Consumers migrate to ordinary association handling.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare every entity relationship explicitly (Priority: P1)

A model author chooses the relationship kind, cardinality and inverse direction explicitly for every entity-valued field. Core, Assoc, Detail, Spec and Enum use the same complete declaration structure. A dictionary cannot silently become an ordinary column or an implicit reference.

**Why this priority**: This is the maintainer's central requirement. No stereotype-specific omission may bypass it.

**Independent Test**: For each non-State stereotype as an owner and target wherever otherwise permitted, assemble a model with a complete field and then with each incomplete alternative. Complete declarations pass; incomplete declarations prevent publication of the model.

**Acceptance Scenarios**:

1. **Given** a permitted relationship on Core, Assoc, Detail, Spec or Enum, **When** its field has a relationship container inside `Annotated`, exactly one `Inverse` or `NoInverse` marker, and a nonblank assignment-side `Field`, **Then** declaration completeness passes.
2. **Given** a bare or nullable bare entity field, a raw collection/mapping of entities, or `Annotated` containing a bare entity, **When** the model is assembled, **Then** it is refused with the owner, field, target and a complete supported correction.
3. **Given** `NoRelation` on an entity-valued field, **When** the model is assembled, **Then** the former embedded-value alternative is refused.
4. **Given** a valid State/Lifecycle declaration, **When** the model is assembled, **Then** existing behavior is preserved; a previously forbidden bare State field remains forbidden.
5. **Given** a graph-hidden or graph-excluded declaration, **When** its relationship is incomplete, **Then** presentation/exclusion does not waive completeness validation.

### User Story 2 - Declare reciprocal relationships across modules (Priority: P1)

An author puts related classes in separate modules without importing each class from the other module at runtime. Each field still explicitly names its reverse field.

**Why this priority**: Mandatory reciprocal markers must be expressible without circular imports.

**Independent Test**: Import a two-module relationship model in both orders, resolve its forward annotations in a composition root and assemble it. Repeat with an unresolved target, missing reverse field, mismatched concrete target and nonreciprocal reverse marker.

**Acceptance Scenarios**:

1. **Given** resolved relationship target types and `Inverse(field_name="...")` on both endpoints, **When** the model is assembled, **Then** each inverse resolves from its own container target and the pair is checked.
2. **Given** `Inverse(Target, "field")`, **When** Target differs from the resolved container target, **Then** the declaration fails.
3. **Given** one endpoint with `Inverse` and another with no direction marker or `NoInverse`, **When** assembly runs, **Then** the pair fails and the migration is explained.
4. **Given** two reciprocal markers, **When** the reverse field names a different originating field or targets a different entity, **Then** assembly fails.
5. **Given** an unresolved target, **When** assembly runs, **Then** the unresolved declaration blocks publication rather than being classified as scalar or unpaired.
6. **Given** a valid Base.items / Item.owner pair, **When** Child inherits items unchanged, **Then** completeness is checked on Child but reciprocity uses Base.items as the declaring endpoint; the base pair remains valid and Child projects its own edge.
7. **Given** Child explicitly overrides items or changes its resolved relationship target through generic substitution, **When** its claimed reverse resolves only to Base.items, **Then** the new Child endpoint is refused until it has its own valid reciprocal declaration. Multiple inheritance uses the effective field selected by normal MRO/model resolution.

### User Story 3 - Select and export a dictionary value explicitly (Priority: P1)

An author declares one selected dictionary value as an explicit unpaired association, constructs its relationship value and exports the same descriptive dictionary reference that consumers understand.

**Why this priority**: Enum must obey the full declaration without losing canonical catalogue identity or producing ambiguous graph projections.

**Independent Test**: Construct required and nullable selections with valid, unknown, foreign, fabricated and mismatched values; inspect runtime identity, JSON, both schema modes and the exported model/diagram.

**Acceptance Scenarios**:

1. **Given** `Annotated[AssociationOne[D], NoInverse()]`, **When** a host receives an identifier-only container with a declared code, **Then** host-field validation resolves the canonical member and the stored container has `id == entity.code`.
2. **Given** a supplied entity, **When** it is not the identical canonical member of D matching the identifier, **Then** validation fails. Unknown codes fail too.
3. **Given** raw members, bare codes or bare reference objects, **When** supplied as the relationship field value, **Then** they are refused rather than silently wrapped.
4. **Given** a valid dictionary association, **When** the host is serialized to JSON, **Then** the field emits the member's `to_reference()` representation; an absent nullable value emits null.
5. **Given** the required or nullable declaration, **When** the model graph is exported, **Then** one ordinary `entity_relation` association edge and one retained field row describe the field; no `entity_reference` edge or duplicate relation edge is generated.
6. **Given** a dictionary used only as specialization vocabulary, **When** the enclosing fully declared specialization is checked, **Then** the vocabulary parameter is not treated as a second relationship field.
7. **Given** a retained dictionary field row and its ordinary association edge, **When** Maxitor builds fields, **Then** it returns exactly one row for that host/field, preserving field identity/type/order/reference_qualname and enriching it with foreign_key=true instead of appending a second synthesized FK row. Two fields targeting the same dictionary remain distinct.

### User Story 4 - Preserve existing relationship compatibility (Priority: P2)

A project author migrates to complete relationship declarations without acquiring an additional ownership or container-pair policy. Existing compatibility checks remain in force.

**Why this priority**: Declaration completeness must not silently introduce the new pair matrix previously proposed in issue #259. The maintainer explicitly excluded that matrix during clarification.

**Independent Test**: Compare representative complete declarations against the existing compatibility checks. Apart from the separately specified declaration, inverse and dictionary changes, preserve existing acceptance/refusal outcomes without adding matrix-based restrictions.

**Acceptance Scenarios**:

1. **Given** a complete declaration accepted by existing compatibility checks, **When** assembly runs, **Then** it is not rejected solely by a newly introduced container-pair or ownership matrix.
2. **Given** a declaration rejected by an existing compatibility check, **When** assembly runs, **Then** the check is retained rather than weakened.
3. **Given** specialization/generalization endpoints, **When** assembly runs, **Then** existing classifier and compatibility rules remain in force, subject to the separately specified declaration and inverse requirements.

### User Story 5 - Migrate an existing model without implicit fallbacks (Priority: P2)

An author replaces bare dictionary fields, embedded entity declarations and one-sided inverse pairs using explicit examples and diagnostics.

**Why this priority**: The new contract intentionally rejects previously accepted declarations.

**Independent Test**: Take each documented before/after declaration and verify the old form fails while the replacement passes. Execute all shipped examples and notebooks with actual output.

**Acceptance Scenarios**:

1. **Given** a formerly accepted bare dictionary declaration, **When** the author migrates it to the specified association and supplies its container value, **Then** it builds and retains descriptive reference export.
2. **Given** an old one-sided inverse pair, **When** the second endpoint gains its reciprocal marker, **Then** inverse completeness passes, subject to existing compatibility checks.
3. **Given** an existing complete pair, **When** migration is verified, **Then** no new matrix-based ownership failure is introduced; existing compatibility failures remain enforced.

### Edge Cases

- Nullable relationship types still need the full declaration; nullability alone does not permit omission.
- Inherited fields, overridden fields, aliases, nested annotations, collections and mappings cannot hide entity-valued content. Unchanged inherited relationships retain their declaring-owner endpoint identity; explicit or target-changing semantic overrides must independently pair. Diamond inheritance does not duplicate an unchanged endpoint or a field projection.
- Same-named classes in different modules must resolve by actual target identity, not a short-name guess.
- A missing/blank description, duplicate or conflicting direction markers and a bare container are invalid.
- Empty, undecorated or graph-excluded dictionary targets retain their catalogue/availability refusals.
- `AssociationMany[D]`, composition, aggregation and generalization targeting dictionary values are refused; use a separate link entity for multiple selections.
- An entity-valued dictionary property otherwise prohibited remains prohibited, rather than becoming an exception to completeness.
- `NoGraphEdge` changes only supported presentation behavior after successful declaration validation; it cannot legalize an incomplete field.
- Old graph exports remain historical inputs; rebuilding cannot re-enable bare source declarations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every non-State entity-valued field MUST have the complete semantic declaration: relationship kind/cardinality, `Annotated` metadata, exactly one direction marker and a nonblank field description. Source examples and static checks MUST enforce one assignment-side `Field(...)`.
- **FR-002**: Core MUST obey FR-001 independently as owner and target; it MUST NOT accept bare, nullable bare, raw collection or embedded-marker alternatives.
- **FR-003**: Assoc MUST obey FR-001 independently as owner and target; technical-link endpoints MUST NOT be exempt.
- **FR-004**: Detail MUST obey FR-001 independently as owner and target, including explicit ownership/reverse fields.
- **FR-005**: Spec MUST obey FR-001 independently as owner and target, preserving classifier membership/coverage and specialization/generalization contracts.
- **FR-006**: Enum MUST obey FR-001. A dictionary selection MUST use `AssociationOne[D]` or its nullable form inside `Annotated`, with `NoInverse()`. Dictionary-target `Inverse` and unsupported containers MUST fail.
- **FR-007**: State alone MUST retain its existing Lifecycle/status contract; this MUST NOT legalize bare State fields. Scalars MUST remain outside the entity-relationship rule.
- **FR-008**: Field-only `Inverse(field_name=...)` MUST work for every otherwise supported relationship container. Its target MUST come from the resolved container type; concrete-class markers MUST match that type. This feature MUST NOT introduce string target classes in the marker.
- **FR-009**: Paired endpoints MUST both declare reciprocal `Inverse` markers. Missing markers, a mismatched reverse endpoint and `Inverse` paired with `NoInverse` MUST fail. `NoInverse` MUST explicitly denote an unpaired field. `NoInverse()` MUST remain supported for one-way relationships and MUST NOT be removed. A field marked `NoInverse()` MUST NOT serve as the reverse endpoint of another field's `Inverse`. Existing one-sided pairs MUST migrate both endpoints; this is an intentional breaking change. Reciprocity MUST compare canonical `(declaring_owner_class_identity, field_name)` endpoints. Unchanged inherited fields retain the declaring owner while completeness and graph projection still use the effective host. Explicit overrides and generic substitutions changing the relationship target/signature MUST be checked as new endpoints; no blanket subclass-target match is allowed.
- **FR-010**: This feature MUST preserve existing relationship compatibility checks and MUST NOT introduce the new ownership/container-pair matrix proposed in issue #259. The separately specified declaration, inverse and dictionary changes remain in scope; adding matrix-based runtime refusals does not.
- **FR-011**: Dictionary host-field validation MUST accept an explicit relationship container, resolve identifier-only containers to the canonical member and reject unknown codes and foreign/fabricated/mismatched supplied members. It MUST reject automatic conversion of raw members, codes and reference objects into containers.
- **FR-012**: A successfully validated dictionary container MUST expose the canonical member through `entity` and its code through `id`. Nullable absence MUST be allowed only by the declared type; omission MUST require an explicit allowed default.
- **FR-013**: Dictionary-association JSON output MUST be the canonical member's existing `to_reference()` representation, or null. The validation schema MUST describe explicit container input; the serialization schema MUST describe the emitted reference.
- **FR-014**: Dictionary fields MUST produce the ordinary `entity_relation` association contract below, retain the field row and its `reference_qualname`, and generate no `entity_reference` edge or duplicate relation edge. Consumers MUST handle the field through the ordinary association path, identifying dictionary targets by their entity stereotype. The diagram fields list MUST contain exactly one row per dictionary host/field: preserve the retained field_id/type/order/reference_qualname, enrich its FK flag from the matching ordinary edge and suppress the corresponding synthesized FK row. Distinct fields sharing a dictionary MUST remain distinct.
- **FR-015**: Invalid/unresolved declarations MUST prevent successful model assembly before graph publication through every supported public build entry point. Graph exclusion, hidden fields and metadata wrappers MUST NOT waive validation.
- **FR-016**: Errors MUST identify the owner/field, target type/stereotype, missing part or incompatible pair and a complete supported correction. Dictionary corrections MUST NOT recommend bare D.
- **FR-017**: Migration guidance MUST explicitly cover bare dictionaries, container access, removal of `NoRelation`, reciprocal inverse migration and dictionary-edge migration from `entity_reference` to ordinary `entity_relation` associations. No compatibility flag or warning-only fallback MAY preserve incomplete declarations.
- **FR-018**: Each stereotype MUST have its own positive/negative acceptance coverage and teaching example. Cross-module teaching material MUST include both declaration modules and the resolving composition root, exercised in both import orders.
- **FR-019**: Verification MUST include isolated adversarial mutations for bare Enum acceptance, `NoRelation`, missing direction markers, nonreciprocal pairs and wrong dictionary edge type, with valid neighboring controls.
- **FR-020**: Implementation planning MUST reserve exactly three closing tasks in order: scoped checks, documentation/examples, changelog. Changed scripts/notebooks and documentation blocks MUST execute with recorded actual results before delivery.

### Public declaration examples by stereotype

These are field excerpts defining the required public contract, not claims that the current implementation already accepts them. Shipped teaching scenarios must supply complete models and imports.

**Core**, on Region, paired with `Offer.regions`:

```python
offer: Annotated[
    AssociationOne[OfferCoreEntity],
    Inverse(field_name="regions"),
] = Field(description="Associated offer")
```

**Assoc**, an explicitly unpaired endpoint on a technical link:

```python
offer: Annotated[
    AssociationOne[OfferCoreEntity],
    NoInverse(),
] = Field(description="Offer participating in this link")
```

**Detail**, ownership field on Offer and reverse field on its Detail:

```python
# On OfferCoreEntity:
details: Annotated[
    CompositeMany[OfferDetailEntity],
    Inverse(field_name="offer"),
] = Field(description="Details owned by this offer")

# On OfferDetailEntity:
offer: Annotated[
    AssociationOne[OfferCoreEntity],
    Inverse(field_name="details"),
] = Field(description="Offer owning this detail")
```

**Spec**, specialization head and one reverse alternative; the complete model must include a reverse alternative for every declared dictionary choice:

```python
# On OfferCoreEntity:
details: Annotated[
    Specialization[
        RetailOfferSpecEntity | WholesaleOfferSpecEntity,
        OfferKindEnumEntity,
    ],
    Inverse(field_name="offer"),
] = Field(description="Details selected by offer kind")

# On RetailOfferSpecEntity:
offer: Annotated[
    Generalization[OfferCoreEntity],
    Classifier(variant=OfferKindEnumEntity.RETAIL),
    Inverse(field_name="details"),
] = Field(description="Offer described by these retail details")
```

**Enum**, required selection, optional selection, and canonical runtime construction:

```python
region: Annotated[
    AssociationOne[RegionEnumEntity],
    NoInverse(),
] = Field(description="Selected region")

optional_region: Annotated[
    AssociationOne[RegionEnumEntity] | None,
    NoInverse(),
] = Field(default=None, description="Optional selected region")

selected_region = AssociationOne[RegionEnumEntity](
    id=RegionEnumEntity.EU.code,
    entity=RegionEnumEntity.EU,
)
```

**State**, the unchanged separate form using a valid declared lifecycle:

```python
lifecycle: OfferLifecycle = Field(description="Offer lifecycle")
```

### Existing relationship compatibility

Preserve existing checks and their established acceptance/refusal outcomes. Do not introduce additional restrictions for Composite/Composite, Composite/AssociationMany, Aggregate/Aggregate or Composite/Aggregate pairs merely because the superseded issue matrix listed them as refused. This statement does not make a pair legal if an existing check already rejects it.

The complete-declaration, inverse and dictionary contracts are specified separately. Existing specialization/classifier checks remain in force. No new instance-level ownership uniqueness, database constraints or cascades are introduced.

### Dictionary graph and consumer contract

A validated, graph-visible dictionary selection uses the same ordinary association projection as other `AssociationOne` fields. It MUST NOT generate a special `entity_reference` edge. Existing supported `NoGraphEdge` behavior remains a presentation choice after declaration validation, with no dictionary-specific bypass.

| Export item | Required result |
| --- | --- |
| Edge source / target | Host identifier / dictionary identifier |
| Edge `type` | `entity_relation` |
| Edge `relationship` | Ordinary association relationship value used by structural association edges |
| Edge `is_dag` | false |
| `properties.field_name` | Declared field name |
| `properties.relation_type` | association |
| `properties.cardinality` | one, for required and nullable forms |
| `properties.description` | Declared field description, following the ordinary relation contract |
| `properties.has_inverse` | false |
| `properties.deprecated` | Existing ordinary relation deprecation behavior; false when not deprecated |
| `properties.inverse_entity_id` / `properties.inverse_field` | Omitted for NoInverse |
| Retained `entity_field` row | Present; `reference_qualname` equals the target dictionary identifier |
| Special `entity_reference` edge | Not generated for new declarations |
| Duplicate ordinary relation edge | Absent |
| Diagram source / target | Host / dictionary identifiers |
| Diagram `relationship_kind` | association |
| Diagram label | Ordinary association label identifying the declared field and its cardinality |
| Diagram field row count | Exactly one per dictionary `(entity_id, field_name)`; enrich the retained row, suppress its synthesized FK duplicate |
| Diagram field identity / type / order / hint | Preserve retained field_id/type/ordinal/reference_qualname; set foreign_key=true from a matching ordinary association |
| Diagram source / target multiplicity | zero_many / one |

Generated edges must validate against the ordinary `entity_relation` schema, including all its mandatory properties. Instance-level null does not remove a declaration-level edge. Diagram host multiplicity does not imply a reverse field. Keep the dictionary type hint and catalogue card, identifying a dictionary by its target stereotype; emit one ordinary association arrow.

For row-merging and inheritance details, the corresponding public acceptance rules are specified in [the declaration contract](contracts/complete-declarations.md#inherited-and-overridden-inverse-endpoints) and [the graph/diagram contract](contracts/graph-and-diagrams.md#one-dictionary-field-row-in-the-diagram-payload).

Consumers and graph/diagram snapshots must migrate from special reference-edge handling for newly generated declarations. Existing exported graphs remain historical inputs; this feature does not require deleting the legacy edge schema or removing legacy-import support. No legacy import path may legalize bare source declarations or generate duplicate arrows.

### Key Entities

- **Entity stereotype**: Core, Assoc, Detail, Spec, Enum or State; determines independent acceptance coverage without waiving the universal non-State contract.
- **Relationship declaration**: Owner, field, target, kind, cardinality, direction marker, description and optionality.
- **Inverse pair**: Two resolved, mutually naming canonical declaring-owner endpoints checked at model assembly; unchanged inherited copies share endpoint identity while effective hosts retain independent graph projections.
- **Dictionary selection**: An explicit single association identifying one canonical catalogue member by code.
- **Model projection**: Published field/edge description and its diagram representation, independently verifiable from the runtime field value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five non-State stereotypes have independently passing complete-declaration cases and failing incomplete-declaration cases; no permitted owner/target category silently avoids the rule.
- **SC-002**: Every supported public assembly entry point refuses the specified invalid-declaration corpus before publishing a model; all valid neighboring controls pass.
- **SC-003**: Both import orders of the cross-module reciprocal example assemble successfully; every unresolved or nonreciprocal control fails with an actionable diagnosis. Unchanged inherited Base/Child pairs pass, overrides must resolve their own reciprocal endpoint, and diamond inheritance produces no duplicate endpoint or field per effective host.
- **SC-004**: Every existing compatibility rule selected for regression verification retains its outcome on complete declarations, except where a separately specified declaration, inverse or dictionary change applies; zero additional failures originate from a new ownership/container-pair matrix.
- **SC-005**: Each valid dictionary selection resolves to the identical declared member and yields one ordinary association edge and one diagram arrow with matching target/field identity, retains `reference_qualname` and generates no special reference edge; all specified invalid values fail. Each selected dictionary field has exactly one enriched diagram field row with its retained field identity/type/order/hint, including cross-domain slicing and two fields sharing one dictionary.
- **SC-006**: Every documented migration has an executed before/after verification, and every changed teaching script and notebook completes with matching recorded output.
- **SC-007**: Each required adversarial mutation is detected by its targeted regression while valid neighboring controls pass.
- **SC-008**: Existing State/Lifecycle acceptance and refusal controls retain their results.

## Assumptions

- The published issue #259 is the starting feature source. The maintainer clarification recorded above supersedes its new pair-matrix requirement: that matrix is excluded. Reciprocal inverse markers are explicitly confirmed by the maintainer, with NoInverse retained for one-way relationships. The maintainer also confirmed ordinary entity_relation association edges for dictionary selections, superseding the special entity_reference projection in the issue. These local clarifications govern planning; they do not assert that the GitHub issue text has been updated.
- This phase writes the specification and its quality checklist only. It does not claim implementation, executed examples or passing runtime regressions.
- Public declaration syntax and graph interchange names are product contracts here. They are retained despite the generic template's preference to omit implementation details; no implementation module layout or algorithms are prescribed.
- The demo package and Russian/draft documents are outside the authorized work. Do not read, execute, check, modify or document them. Future verification must use scoped commands respecting these exclusions.
- The constitution, existing user changes and staging must remain untouched. Commits, pushes, PRs and merges require separate explicit authorization.
- No data migration, automatic storage loading, instance-level ownership uniqueness or storage cascades are introduced.
- Existing dictionary catalogues, relation containers, specialization/classifier contracts and graph consumers are dependencies. This feature deliberately changes the public declaration/validation behavior described above; old export files do not authorize old source forms.
