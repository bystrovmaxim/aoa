# Research: The version track shows where the graph changed

## R1. How a public address carries the version file

- **Decision**: `https://github.com/<owner>/<repo>/blob/<branch>/<path>?version_link=<url>&version_key=<key>`, on the client and the server alike. Only these two parameters are accepted, `version_key=` only beside `version_link=`, and the history's name always writes them in this order. A version's source carries them too.
- **Rationale**: the name identifies a held history, so one graph joined with two files must be two histories. The port decides whether the link is usable and answers with `version_problem`.
- **Alternatives**: keeping them apart from the name would make two joined histories share one entry.

## R2. How the gateway receives them

- **Decision**: `describe` and `versions` gain keywords `version_link` and `version_key`, defaulting to none. The entry keeps both.
- **Rationale**: a change to every caller of `link` adds nothing.

## R3. Where a history's version facts come from

- **Decision**: from the port's description, read at opening and at every check, also on a `304`. A change to `version_problem` or `version_file` counts as a change of the history, like Live, and goes into the tag Maxitor gives a polling tab.
- **Rationale**: a fix to a file can leave the list of versions alone.

## R4. How the client knows numbers come from a file

- **Decision**: an explicit `versionFile` on the opened history; `numbersOf` and `shownNameOf` take it as an argument.
- **Rationale**: guessing from the points would show tags for a named file that cannot be read, which says the wrong thing.

## R5. What hiding does

- **Decision**: `layOut` builds every point first, so names and numbers keep their places, then drops points with `graph_changed === false` unless they are chosen, an end of the range, or the end being dragged by the person followed. Live and pull requests are never hidden. The newest version merged into Live stays, as Live. Keys step over what is on the track. A missing `graph_changed` counts as true.
- **Rationale**: the choice lives outside the track, so a filter inside it cannot move the choice. That is what the adversarial break tests.
- **Accepted limit**: a follower with another setting has other positions, so the scroll passed in a room lands elsewhere; the chosen versions and the hovered one are named by id and stay right.

## R6. Flags of hidden points

- **Decision**: a hidden point's flags move to the nearest drawn version before it, or the earliest drawn one when there is none. `Point` gains `carried`, and `VersionTip` lists them under the point's own.

## R7. Two points with the same graph

- **Decision**: `sameGraph(versions, a, b)` is true when no point after the older, up to the newer, has `graph_changed !== false`. Neither end may be Live or a pull request. The picker says "Both versions have the same graph", and the version button's counts read the same.
- **Rationale**: the diagrams already draw such a pair as one version; what is missing is the sentence. Otherwise equal graphs at a distance stay with the existing "no changes".

## R8. Where a version problem stands

- **Decision**: at the foot of the picker, in grey text saying what the track shows and why, plus a scarlet dot there and on the version button, with the same text in its tooltip.
- **Rationale**: the picker is closed most of the time, and the problem must not cover the graph. The colours of the track already mean how a point came, so the dot takes none of them.

## R9. The icon's memory

- **Decision**: `lib/smallPointsShown.ts`, the same shape as `lib/hoverCardsOn.ts`: one key, default shown, guarded reads and writes. Not in the address, not in `Panels`.
