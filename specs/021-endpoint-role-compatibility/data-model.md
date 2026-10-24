# Data Model: Endpoint Role Compatibility

Design-time view of the domain the new validator reasons about. No storage is introduced.

## Endpoint role

One of the eight public containers a field declares. Identity is the container class; cardinality
(One/Many) is a separate attribute that never changes a compatibility verdict.

| Role | Family | Cardinality |
| --- | --- | --- |
| `AssociationOne` | association | one |
| `AssociationMany` | association | many |
| `AggregateOne` | aggregate (ownership) | one |
| `AggregateMany` | aggregate (ownership) | many |
| `CompositeOne` | composite (ownership) | one |
| `CompositeMany` | composite (ownership) | many |
| `Specialization` | specialization | — |
| `Generalization` | generalization | one |

## Reciprocal relationship

Two fields that each declare `Inverse` naming the other. The pair is the only unit the matrix
validates. Attributes: the two owner classes and field names, the two resolved roles, and the
One/Many value attached to each declaring endpoint.

## One-way relationship

A single field declared with `NoInverse` and no reverse field. It is intentionally unpaired and is
never matched by the matrix, and no other field's `Inverse` may target it.

## Compatibility matrix

The symmetric 8×8 table (see `contracts/role-pair-matrix.md`). Allowed means the role pair passes
the compatibility check; all other declaration, inverse and classifier checks still apply.

## Declaration error

The single public exception (`RoleCompatibilityError`) a refused pair raises. Payload: both owner
classes and field names, both resolved roles, the violated rule, and the permitted correction.
