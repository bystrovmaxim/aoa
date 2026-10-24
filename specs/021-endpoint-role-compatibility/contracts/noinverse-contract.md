# Contract: NoInverse

`NoInverse` means the field has no reverse field constituting the other endpoint of the same
relationship. It is a declaration of absence, not a marker for skipping one endpoint of a reciprocal
pair. `NoInverse` is permitted on each of the six ordinary containers and is refused on
`Specialization` and `Generalization`.

| Declaration | Required result |
| --- | --- |
| One ordinary field with `NoInverse` and no paired reverse field | Accepted as an intentionally one-way relationship |
| Two fields with mutually resolving `Inverse` markers | Accepted only if reciprocal endpoints and the role matrix are valid |
| An `Inverse` points at a field marked `NoInverse` | Refused; an unpaired field cannot be the reverse endpoint of a paired field (either inspection order) |
| Two fields marked `NoInverse`, including fields referring to each other's entity types | Accepted as two independent relationships, not as two endpoints of one reciprocal relationship |
| `Specialization` or `Generalization` marked `NoInverse` | Refused; these roles require a reciprocal `Specialization`/`Generalization` pair with `Inverse` on both endpoints |

## Invariants

- Reciprocal pairing is declared explicitly through `Inverse`; it is never inferred from two fields
  targeting each other's entity types, sharing names, or containing matching instance identifiers.
- A `NoInverse` declaration must not be targeted by any other field's `Inverse`.
- The role-pair matrix applies only to the two endpoints of an explicitly paired relationship; it
  never compares unrelated one-way fields or invents a second endpoint for `NoInverse`.
- `Specialization`/`Generalization` always require each other and reciprocal `Inverse` markers;
  `NoInverse` cannot replace either direction of that pair.
