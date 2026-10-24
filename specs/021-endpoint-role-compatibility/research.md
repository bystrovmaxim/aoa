# Research: Endpoint Role Compatibility

Decisions recorded with the file and line that justified each, and the alternative rejected.

## D1 — Enforcement location

**Decision**: Add the role-pair check as a new validator called from `NodeGraphCoordinator.build()`
after `validate_entity_inverses()` and before `_gather_all_nodes(...)`, and from `entity_graph_node.py`
beside the existing per-node calls.

**Rationale**: `node_graph_coordinator.py:154-159` already runs the completeness pass
(`validate_entity_fields`) then the reciprocity pass (`validate_entity_inverses`) before gathering
nodes; `entity_graph_node.py:83-84` runs the same two passes per node. The matrix needs a resolved
reciprocal pair, so it runs after reciprocity; it must run before nodes are gathered so a refused
model never publishes.

**Alternative rejected**: Fold the matrix into `entity_inverse_validator.py`. Rejected because the
issue requires one distinct public exception for compatibility refusals, and a separate validator
keeps that boundary explicit (an earlier reciprocity failure still raises `EntityFieldDeclarationError`
and fires first).

## D2 — Role identification

**Decision**: Map each endpoint's `ResolvedEntityField.container` to one of the eight roles:
`AssociationOne`/`AssociationMany`/`AggregateOne`/`AggregateMany`/`CompositeOne`/`CompositeMany` from
the six container classes, and `Specialization`/`Generalization` from the specialization containers.

**Rationale**: `resolved_entity_fields.py:79-121` already normalizes `container`, `relation_kind`,
`cardinality`, `is_relation`, `is_specialization`, `is_generalization`. The six ordinary containers
set `relation_type` to `RelationType.ASSOCIATION`/`AGGREGATION`/`COMPOSITION`
(`relation_containers.py:209, 509-596`). Cardinality is orthogonal to compatibility, so the matrix is
a family-level lookup over the eight role names.

**Alternative rejected**: A new public role enum. Rejected — the containers already carry the role;
no new public surface is needed.

## D3 — Reciprocity resolution reuse

**Decision**: Resolve the reverse field the same way the inverse validator does — by
`(declaring_owner, field_name)` identity, using `_reverse_field` (`entity_inverse_validator.py:79-84`).

**Rationale**: `_check_reciprocal` (`entity_inverse_validator.py:87-146`) already proves the pair
names itself back. The matrix validator re-resolves the reverse field rather than re-proving
reciprocity, and `declaring_owner_of` (`resolved_entity_fields.py:415-434`) already compares inherited
endpoints by resolved identity, not short name.

**Alternative rejected**: Matching by short class name. Rejected — the issue forbids it (FR-009).

## D4 — Dictionary rule removal

**Decision**: Rewrite `_dictionary_container_refusal` and `_dictionary_inverse_refusal`, and remove
the `if resolved.container is not AssociationOne` branch in `entity_field_validator.py:281-295, 403`,
so any of the six ordinary containers is legal for a dictionary target.

**Rationale**: The issue removes the dictionary-specific `AssociationOne`-only rule; the general
full-declaration and endpoint-pair rules replace it.

**Alternative rejected**: Keep the rule and add a to-many exception. Rejected — the issue mandates
full removal, not a special case.

## D5 — Exception contract

**Decision**: One new public exception `RoleCompatibilityError` in `domain/exceptions.py` beside
`EntityFieldDeclarationError` (`exceptions.py:265`) and `SpecializationDeclarationError`
(`exceptions.py:231`). Existing types keep their checks; the new type is additive.

**Rationale**: The issue requires "one consistent public exception contract" with a tested exact
type, text and failure boundary. The maintainer confirmed this as the answer to the clarification
question.

**Alternative rejected**: Reusing `EntityFieldDeclarationError`/`SpecializationDeclarationError`.
Rejected — that would leave two different contracts for one rule.

## D6 — Matrix encoding

**Decision**: Encode the matrix as a module-level constant keyed by role family, so One/Many never
changes a verdict, and the directed 8×8 counts (22 permitted / 42 refused) fall out of the same
lookup.

**Rationale**: The issue states One and Many "do not add or remove compatibility between role
families" (FR-006) and that the 8×8 matrix is the source of truth (FR-007).

## D7 — Specialization/generalization boundary

**Decision**: The matrix validator checks the spec/gen pairing boundary
(`Specialization ↔ Generalization` allowed; same-role and ordinary-role pairings refused), and does
not duplicate the classifier/alternative/closure/cycle checks that
`entity_specialization_validator.py` already performs.

**Rationale**: `entity_specialization_validator.py` already validates the axis structure; the matrix
only adds the role-pair boundary the issue requires.
