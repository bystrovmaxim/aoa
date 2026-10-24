# Contract: Explicit Single Dictionary Association

**Source**: [Specification](../spec.md), FR-006, FR-011–014.

## Declaration

Required: `Annotated[AssociationOne[D], NoInverse()] = Field(description=...)`.
Nullable: `Annotated[AssociationOne[D] | None, NoInverse()] = Field(default=None, description=...)` when omission is intended.

D is a concrete nonempty declared dictionary with an available graph target. Bare D/D|None, NoRelation, Inverse to a catalogue, AssociationMany[D] and dictionary-target ownership/generalization containers are refused. The vocabulary parameter of a valid specialization is not an ordinary target field.

## Python input

Require an explicit AssociationOne instance at the host-field boundary. Its code must be a declared string code of D; booleans/numbers are not string-code shortcuts. The constructor's ordinary non-null-id check still happens where currently defined.

- Id only: resolve the canonical member with D.by_code.
- Id and entity: the supplied object must be that identical member, not a copy or a foreign/mismatched value.
- Normalize successful host input into a new frozen wrapper with that canonical member.
- Reject raw member objects, strings, bare reference mappings and Python mappings as implicit container conversions.
- Ordinary structural AssociationOne targets keep their existing id-only/hydrated behavior.

## JSON input

The transport container is an object with exactly one required key, `id`, whose value is a string code from D. Additional keys are refused. This transport branch reconstructs an explicit wrapper and applies canonical lookup; it does not accept a bare reference object containing code/display_name/properties.

Example transport field values (JSON, not Python constructor examples):

```json
{"id": "eu"}
```

A nullable absent value is null. JSON object parsing is confined to the JSON validation branch; Python host input still requires the wrapper instance. This makes the schema's explicit container input meaningful without silently accepting old dictionary-reference input.

## Runtime and serialization

After host validation, `field.entity is D.by_code(field.id)` and `field.id == field.entity.code`. Standalone id-only wrapper construction does not pretend this host validation has already happened.

Python field access keeps the wrapper. JSON serialization returns exactly the member's existing to_reference() result (code, display_name, serialized properties); nullable absence returns null. Preserve declared property serializers and definition references in schema generation. Serialized output is intentionally not the accepted container input shape, so direct output-to-input round-tripping is not promised; reconstruct the explicit id container when importing output.

## Schemas and refusals

Validation JSON schema describes the explicit id object and nullable union where applicable. Serialization schema describes the emitted dictionary reference, using existing handler-managed dictionary output definitions. Unknown id, wrong id type and foreign/fabricated/mismatched entity inputs produce validation errors at the host field. Bare input errors and canonical-lookup errors must name the field path. Exact diagnostics are tested during implementation.

Standalone dictionary APIs and reference-schema behavior remain unchanged outside this new relation container path.
