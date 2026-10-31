# Contract: the map on screen

| Thing | What the user sees |
|---|---|
| Overview | named areas, sized by what they hold, with bundled links |
| Level 2 | entities, operations, roles and resources inside the areas in view |
| Level 3 | their fields, states and other parts |
| Zoom | things fade in and out; nothing moves |
| Folded domain with changes | `+3 −1 ~2` on it, not faded |
| Folded domain without changes in Diff | faded |
| Marked node | green or amber ring, or a dashed red circle |
| Marked link | its status's colour, red and dashed when removed |
| Retargeted relation | amber solid to B's target, thin dashed to A's |
| Bundle holding a change | marked; hover says how many |
| Click on a folded domain | the map flies to it |
| Click on a marked node | the card of spec 038 |
| Click on a folded domain's count | the map flies to its first change, card open |
| Change arrows beside the button | `‹ 3 of 12 ›`: next or previous change, wrapping around |
| Button | `◷ A 0.8.0 → B 0.9.0  +23 −1 ~5 ▾`, whatever the zoom |
| A version being laid out | the page says so and stays alive |
| No WebGL | the page says so and offers the ERD |

## The filter panel, on every diagram with it

| Action | Result |
|---|---|
| Move the gear shift to a section | that section opens, the others fold, the diagram repaints |
| Open a section by hand | the paint stays |
| Fold the open section | the paint stays |
| The diagram opens | the painting section is open |

On the full graph the sections are Domains, Node types and, in Diff, Changes. One starts painted by Domains, Diff by Changes.

## Filters on the map

Switching a filter off hides those elements and their links; nothing else moves. Each domain's outline closes around what is left, its name stands there, and it reads `45 of 394 left`. A domain with nothing left goes. A bundle thins with its links.

## The look

Soft coloured domain areas with name tags, disks with their type's icon, the hover label with its stripe, arrows on links, the dotted background: as today (FR-009a).
