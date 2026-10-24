# Contract: Role-Pair Matrix

The single source of truth for endpoint role compatibility. Rows and columns are the roles declared
on the two endpoints. "Allowed" means the role pair passes the compatibility check; all other
declaration, inverse and classifier checks still apply.

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

There are 12 permitted unordered combinations and 24 prohibited unordered combinations, counting a
same-role pair once. Equivalently, the directed 8×8 matrix contains 22 permitted and 42 prohibited
cells.

## The three rules

1. **Specialization/generalization.** A paired inheritance relationship has exactly one
   `Specialization` and one `Generalization` endpoint. They pair only with each other; same-role pairs
   are prohibited, and neither pairs with the six ordinary roles.
2. **Ownership/ownership.** For a pair drawn from the six ordinary roles, at most one endpoint may be
   an ownership role (`Aggregate*`/`Composite*`); if one is ownership the other must be
   `AssociationOne`/`AssociationMany`; if neither is ownership both are association. Consequently
   aggregate/aggregate, composite/composite and aggregate/composite are prohibited.
3. **Cardinality.** One and Many describe cardinality only and never add or remove compatibility.
   Compatibility is symmetric: swapping the endpoints preserves acceptance or refusal.

## Permitted unordered combinations (12)

`AssociationOne↔AssociationOne`, `AssociationOne↔AssociationMany`, `AssociationMany↔AssociationMany`,
`AssociationOne↔AggregateOne`, `AssociationOne↔AggregateMany`, `AssociationMany↔AggregateOne`,
`AssociationMany↔AggregateMany`, `AssociationOne↔CompositeOne`, `AssociationOne↔CompositeMany`,
`AssociationMany↔CompositeOne`, `AssociationMany↔CompositeMany`, `Specialization↔Generalization`.

## Prohibited unordered combinations (24)

`AggregateOne↔AggregateOne`, `AggregateOne↔AggregateMany`, `AggregateOne↔CompositeOne`,
`AggregateOne↔CompositeMany`, `AggregateMany↔AggregateMany`, `AggregateMany↔CompositeOne`,
`AggregateMany↔CompositeMany`, `CompositeOne↔CompositeOne`, `CompositeOne↔CompositeMany`,
`CompositeMany↔CompositeMany`, `Specialization↔Specialization`, `Generalization↔Generalization`, and
each of `Specialization`/`Generalization` paired with each of the six ordinary roles (12 more).

## Diagnostics

A refused pair raises `RoleCompatibilityError` naming both owner classes and field names, both
resolved roles, the violated rule and the permitted correction:

- Ownership/ownership refusal: both endpoints carry ownership roles; the reverse of an ownership
  endpoint must be `AssociationOne`/`AssociationMany`. It names which endpoint to change, and never
  claims all Many relationships are prohibited.
- Specialization/ordinary-role refusal: `Specialization` and `Generalization` pair exclusively with
  each other.

If an earlier declaration check fires first (a missing marker, an unresolved type, an absent reverse
endpoint), that earlier check's exception and boundary are reported, not this one.
