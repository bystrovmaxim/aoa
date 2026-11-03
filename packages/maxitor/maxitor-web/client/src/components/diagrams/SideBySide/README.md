# SideBySide

Two versions of one diagram: A on the left, B on the right, each in its own layout. A viewer is drawn once under each half and tells them apart with `useHalf` (`@/lib/half`).

- `SideBySide` stands the two halves, or on a phone one half with an A / B switch.
- `HalfNote` is what a half says of the selection.

One element across the halves lives in `@/lib/halfPicking`: hover, selection, tracking, one step for both.
