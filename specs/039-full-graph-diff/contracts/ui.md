# Contract: the full graph in Diff

| Thing | What the user sees |
|---|---|
| Added node | green ring |
| Changed node | amber ring |
| Removed node | white disk, dashed red circle |
| Unchanged node | faded |
| Marked edge | green, amber, or red and dashed |
| Retargeted relation | amber solid to B's target, thin dashed to A's |
| Hover label | carries `+`, `−` or `~` |
| Button | `◷ A 0.8.0 → B 0.9.0  +23 −1 ~5 ▾` |
| Nothing drawn changed | "no changes", drawn as One |
| Only edges changed | `+0 −0 ~0`, edges marked |
| Click on a marked node | the card of spec 038 |
| Panel | Node types, Domains, and in Diff Changes; one section open; replaces the legend |
| Filter switched off | those nodes and their edges gone, nothing moves; button and fading follow |

The address and a room carry the filters as on the ERD. On a phone the panel is the "Filter" pill.
