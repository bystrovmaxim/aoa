# Research: where the dictionary rule binds, and what it measures

**Feature**: `specs/018-dictionary-reference` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md)

Every decision below was taken against the merged baseline `d1f28968` and confirmed with a runnable probe, not by reading the issue. The probe lives in `evidence/baseline_probe.py`; it is re-run, not re-read, whenever a phase begins.

## Measured baseline

| Measurement | Probe block | Result |
| --- | --- | --- |
| Bare dictionary field | `bare D` | accepted by the rule |
| Optional dictionary field | `D \| None` | accepted |
| Relation container around a dictionary | `container around D` | accepted by the rule, and the graph gains an `entity_relation` edge to the dictionary |
| Bare structural entity | `bare structural` | refused, with the two legal forms |
| `NoRelation` on a dictionary | `marker on D` | refused: "the marker applies only to a Core, Assoc, Detail or Spec entity" |
| Graph rows | `graph rows and edges` | `region` carries `reference_qualname`; `regions` carries none; edges are `['domain', 'entity_field']` |
| Empty catalogue | `empty catalogue` | refused by the graph edge, not by the declaration boundary |
| Union of two structural entities | `union` | refused as "a collection of an entity", offering `AssociationMany` |
| Heterogeneous collection | `heterogeneous tuple` | refused as "a collection", naming only the first entity |
| Mapping | `mapping` | refused as "a collection", offering `AssociationMany` |

### Reproduced at `d1f28968`

The block below is the probe's output abridged at the long refusal texts, which are elided with
`...`; the exhaustive run is the probe itself, and T001 pastes its full output here before the
work starts.

```text
== the rule sees no dictionary ==
bare D: accepted
D | None: accepted
container around D: accepted
bare structural: REFUSED the field's type is an entity (TargetCoreEntity), so the field cannot be a scalar. Declare it as a relation (Annotated[AssociationOne[TargetCoreEntity], Inverse(...)]) or as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).
marker on D: REFUSED NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec entity; this field's type is RegionEnumEntity.
== graph rows and edges ==
row id       type=str                                reference_qualname=None
row region   type=RegionEnumEntity                   reference_qualname=RegionEnumEntity
row regions  type=tuple[RegionEnumEntity, Ellipsis]  reference_qualname=None
edges: ['domain', 'entity_field']
== container around a dictionary ==
edges: ['domain', 'entity_field', 'entity_relation']
relation target: RegionEnumEntity
== empty catalogue ==
graph build: ValueError: EmptyDictionaryCoreEntity.region: EmptyDictionaryEnumEntity declares no values; type the field with a concrete dictionary.
== refusal wording ==
union: REFUSED the field's type is a collection of an entity (TargetCoreEntity | BaseSpecEntity); a collection is not a relation. Declare the many relation (Annotated[AssociationMany[TargetCoreEntity], Inverse(...)]) ...
heterogeneous tuple: REFUSED the field's type is a collection of an entity (tuple); ... (Annotated[AssociationMany[TargetCoreEntity], ...])
mapping: REFUSED the field's type is a collection of an entity (dict); ... (Annotated[AssociationMany[TargetCoreEntity], ...])
```

Two facts the table above does not show. First, `AssociationOne[RegionEnumEntity]` already produces an `entity_relation` edge today, so a dictionary reference currently has two representations that disagree: the bare type is a column, the container is a relation. Second, the empty-catalogue refusal happens after the declaration boundary, so an author who types a field with an empty dictionary hears about it from the graph edge, not from the rule.

## D1 — The bare dictionary type is the declared reference, and the rule accepts it

**Decision**: `D` and `D | None` are legal. The rule judges the field, accepts the reference, and refuses only the forms that declare nothing or declare the wrong thing.

**Rationale**: #241 decided the form ("the dictionary type itself, not `str`, not `Literal`, not a marker"). The structural bare type is ambiguous and #249 refuses it because the author must say which of two things was meant; a dictionary bare type has one meaning. Requiring a wrapper would restate the type and migrate 60 declarations without adding information.

**Alternatives considered**: a new `Reference[D]` container (rejected for now — no information added, 60 declarations migrated; recorded as the alternative in spec D-1); refusing the bare type and allowing `AssociationOne[D]` (rejected — it calls a shared value an association, and the baseline already shows that form produces a relation edge the model never declared).

## D2 — The kind is detected by its base class, in the same classifier

**Decision**: `_ENTITY_BASES` gains `(BaseEnumEntity, "Enum")`, and `_kind_of` returns `"Enum"` for a dictionary. Nothing else in the classifier changes.

**Rationale**: each kind already has its own base class and each base enforces its naming suffix, so kind membership is a class relationship, not a string test. One classifier means a future kind is added in one place, which FR-009 asks for.

**Alternatives considered**: a separate walker for dictionaries (rejected — two walks over `model_fields` would drift); matching the `…EnumEntity` suffix (rejected — the suffix is a naming rule, not the type system).

## D3 — A collection of dictionary values is refused

**Decision**: `tuple[D, ...]`, `list[D]`, `Sequence[D]`, `set[D]`, `frozenset[D]` and `dict[K, D]` are refused with the dictionary form table, and the message offers no relation container.

**Rationale**: a column holds one code, and a many-reference would silently invent a join table the model does not declare. Refusing states that the shape has no declared form; a later issue can add one deliberately. It also removes the baseline's worst case — a column that is not even recognizable as a reference.

**Alternatives considered**: accepting a collection and giving it a many-edge (rejected — the edge would claim a cardinality the storage does not have); accepting it as a scalar column (rejected — that is the silent column the issue removes).

## D4 — The reference is a new `entity_reference` edge, not an `entity_relation`

**Decision**: a new `EntityReferenceGraphEdge` (`AssociationGraphEdge`, `edge_name` `entity_reference`, properties `field_name` and `cardinality`) is emitted per accepted reference; the graph JSON schema declares it; the Maxitor gets an `entity_reference_edges` table.

**Rationale**: `entity_relation` means "a relation field declared with a container" and carries inverse, description and deprecation semantics a reference does not have. Reusing it would also duplicate the field row in the ERD, because the `fk` CTE turns every `entity_relation_edges` row into a second row beside the `entity_field` row. A distinct type keeps the two statements distinct (D-5 of the spec) and gives tests something exact to assert.

**Alternatives considered**: reusing `entity_relation` with `relation_type="reference"` (rejected — claims a relation and duplicates the row); no edge at all, only `reference_qualname` (rejected — that is exactly the graph that lies, FR-010).

**The Maxitor constraint that couples the phases**: `DuckDBGraphResource.build_from_json()` raises `KeyError("Unknown edge graph type(s)")` for an edge type it does not know, and the demo graph already carries dictionary references. The new edge and the resource registration therefore ship in one phase.

## D5 — The declaration pass runs before the wiring pass

**Decision**: `validate_entity_fields()` moves to the start of `NodeGraphCoordinator.build()`, ahead of `_gather_all_nodes`, `_expand_and_collect` and `_single_pass_validate_and_wire`.

**Rationale**: the reference edge is emitted while the entity node is constructed, and a reference to a dictionary outside the graph would be a dangling target that `_single_pass_validate_and_wire` reports as `InvalidGraphError`. FR-014 asks for the field and the dictionary to be named; running the rule first makes the rule the only author of that refusal.

**Alternatives considered**: emitting the edge only when the target is a graph model and refusing in the validator (rejected — the exclusion test would live in two places); keeping the order and catching `InvalidGraphError` to re-raise (rejected — a second error path to maintain).

## D6 — The empty catalogue is refused by the rule, in every form

**Decision**: `EntityFieldGraphEdge._refuse_empty_dictionary` is deleted and the check moves into the validator. A dictionary whose catalogue is empty is refused whatever shape the field has.

**Rationale**: one rule, one boundary (FR-006). The graph edge sees only the bare and optional forms, and it sees them after the declaration boundary, so today a collection of an empty dictionary is not refused at all.

**Alternatives considered**: keeping both checks (rejected — two copies drift, as the two `_field_description_hint()` copies did); keeping only the graph check and extending it to collections (rejected — the declaration boundary is where every other form is refused).

## D7 — The ERD reads the new table and draws a `reference` relation

**Decision**: `relation_sql` gains a `UNION ALL` over `entity_reference_edges` with `relationship_kind` `"reference"` and the field name as the label; `neighbor_clause` unions the same table so a dictionary in another domain joins the slice. The renderer is unchanged: its relation loop draws any non-specialization kind with its label.

**Rationale**: the payload's `relations` list is the ERD's one source of edges. A second mechanism in the renderer — deriving arrows from `reference_qualname` — would split that source. `relationship_kind` is a free string in the payload schema, so no schema change is needed.

**Alternatives considered**: deriving the arrow in the renderer from `reference_qualname` (rejected — a second edge source, and the cross-domain inclusion still needs a query); drawing the reference as an `FK` row (rejected — the field row already exists and would be duplicated).

## D8 — The three diagnostics come from one shape classifier

**Decision**: the validator classifies the shape it is looking at — a bare entity, an optional entity, a union of entities, a homogeneous collection, a heterogeneous collection, a mapping — and derives the message from that classification. The refusal keeps naming the owner and the field.

**Rationale**: today every shape reaches `_collection_refusal`, which calls a union a collection and offers `AssociationMany` for a mapping. One classifier makes the message follow the shape without adding an accepted form.

**Alternatives considered**: three special cases in `_check_field` (rejected — the next shape repeats the bug); accepting unions (rejected — the spec forbids inferring intent from structure).

## D9 — Names fixed by this plan

| Name | Meaning |
| --- | --- |
| `entity_reference` | the graph edge type, emitted per accepted dictionary reference |
| `entity_reference_edges` | the Maxitor DuckDB table holding those edges |
| `references` | the `EntityGraphNode` attribute holding the edges |
| `relationship_kind: "reference"` | the payload relation kind the ERD renders |
| label of a reference relation | the field name, as a relation edge labels itself with its field |
| properties | `field_name`, `cardinality` (`one` for every accepted form) |

The edge carries no description, inverse or deprecation: a reference has none of those. The field's description is already on the field itself and is not copied to the edge.
