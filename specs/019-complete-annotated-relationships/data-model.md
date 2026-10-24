# Data Model: Complete Annotated Relationships

## Resolved relationship declaration

This is an internal build-local view of existing user declarations, not a new public object the model author must construct.

| Attribute | Meaning / invariant |
| --- | --- |
| effective_host | Actual declared entity class being checked/projected, including graph-excluded hosts for completeness |
| declaring_owner | Class introducing the effective field declaration; unchanged inheritance retains this identity, explicit/semantic overrides create a new endpoint |
| field_name | Name from completed model_fields |
| target(s) | Resolved class identity; alternatives are allowed only by existing specialization grammar |
| container_kind | Existing association/aggregation/composition/specialization/generalization kind |
| cardinality | Existing one/many or dedicated specialization semantics |
| nullable / default | None only when declared; omission only with a permitted explicit default |
| metadata | Completed field metadata; direction marker count is exactly one |
| inverse target / field | Inferred or concrete checked target and named reverse field |
| description / deprecated | Existing field metadata; description is nonblank |
| omit_graph_edge | Presentation setting; cannot skip declaration/inverse validation |

State/Lifecycle and scalar fields are classified outside this descriptor's ordinary entity-relationship validation. Unsupported entity-bearing shapes and unresolved target names are refused rather than classified as scalars.

## Inverse endpoint index

Key: `(declaring_owner_class_identity, field_name)`. Value: normalized relationship descriptor. Resolve the effective declaration on a host before canonicalizing its endpoint. The index exists for one assembly operation; it is not a persistent registry.

For each Inverse endpoint, resolve the reverse field on the container target and its declaring owner. The reverse marker must resolve back to the canonical originating endpoint. An unchanged inherited field shares its declaring endpoint; an explicit override or a target-changing generic substitution creates a new endpoint. Explicit marker classes must still match their own resolved container targets by identity. A NoInverse endpoint cannot be a claimed reverse. Apply normal effective-field/MRO selection for multiple inheritance, and keep specialization classifier/target restrictions. See [the endpoint rules and acceptance table](contracts/complete-declarations.md#inherited-and-overridden-inverse-endpoints).

No ownership pair matrix or instance ownership store is added.

## Dictionary association value

The existing AssociationOne wrapper carries `id` and `entity`. For dictionary D:

1. Before insertion into a host, an explicit wrapper may contain only its id.
2. Host validation looks up the code in D's catalogue.
3. A supplied member must be the identical declared member matching that code.
4. The validated field receives a new immutable wrapper with canonical entity and matching id.
5. Python access keeps the wrapper; JSON field output is the canonical member's reference object.

No input wrapper is mutated. No raw Python code/member/reference is wrapped implicitly. JSON has the explicit container shape documented in [the runtime contract](contracts/dictionary-association.md). Optional absence is None; it does not change declaration-level cardinality.

## Graph projection

One graph-visible dictionary association produces:

- One ordinary `entity_relation` edge from host to dictionary.
- One `entity_field` row with `reference_qualname` naming that dictionary.
- No newly generated `entity_reference` edge.

The field row id and ordinary relation properties retain existing identity conventions. No inverse ids are emitted for NoInverse. NoGraphEdge retains existing supported suppression semantics after full validation.

Diagram field aggregation uses `(entity_id, field_name)` as the dictionary-row identity: enrich the retained row with the matching ordinary association's FK marker, preserving field_id/type/ordinal/reference_qualname and suppressing its synthesized FK duplicate. Ordinary structural fallback rows and historical reference payloads retain their existing behavior. See [the payload row contract](contracts/graph-and-diagrams.md#one-dictionary-field-row-in-the-diagram-payload).

Historical special-reference JSON can populate the legacy DuckDB edge table. New ordinary edges populate the existing relation table. Consumers must never duplicate an arrow by synthesizing a second relationship from reference_qualname.

## Boundaries and transitions

Declaration lifecycle: loaded class → resolved field → normalized descriptor → completeness and reciprocal validation → existing compatibility checks → graph publication.

Dictionary value lifecycle: explicit input wrapper → canonical code/member validation → normalized frozen wrapper → JSON reference export.

An error aborts the corresponding construction/assembly before a successful result is published. No business lifecycle or database state transition is added.
