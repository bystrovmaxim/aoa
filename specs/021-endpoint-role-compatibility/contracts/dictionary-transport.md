# Contract: Dictionary Transport

A dictionary target accepts all six ordinary containers under the same full-declaration and
endpoint-pair rules as any other target. The former `AssociationOne[D]`-only rule is removed.

## Value resolution

- **To-one**: resolve one identifier to the canonical declared member.
- **To-many**: resolve every identifier in input order, retaining the declared container class.
- **Refusals**: unknown, blank or incorrectly typed codes, and foreign, fabricated or mismatched
  supplied members, are refused with item paths where applicable.
- **Normalization**: results normalize into immutable containers without mutating the caller's input.
- **States**: empty selection, explicit absence, omission, and loaded/unloaded states are each
  distinct and tested separately.

## Transport and export

- Preserve the to-one transport contract; implement the equivalent to-many input/export contract and
  both schema modes.
- Retain custom property serializers and typed exported-property schemas.
- Do not add unsupported uniqueness or cardinality restrictions.

## Graph projection

- Preserve the declared role family, cardinality, endpoint direction, description and dictionary
  hint.
- Do not force a dictionary relationship into association/one and do not emit duplicate relationship
  arrows.
- Preserve historical graph import support independently of the source declaration rule.
- A dictionary used as a specialization classifier is distinct from a relationship endpoint and keeps
  classifier semantics.
