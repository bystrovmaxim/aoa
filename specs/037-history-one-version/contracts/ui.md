# Contract: what the screen shows

The look is the mockup's (`specs/030-graph-history/mockup/index.html`), with the spec's three corrections (message, release, no index).

## Modes

Every screen and every test is specified for each mode. A mode is derived from what was opened; it can change while a history is open (a first version is merged: M6 → M5, M7 → M3; a second one: M3 → M2, M5 → M4).

| | M1 Live only | M2 History, several, no Live | M3 History, one, no Live | M4 Live and several | M5 Live and one | M6 Live, no version yet | M7 History, nothing yet |
|---|---|---|---|---|---|---|---|
| Opened | a running service, a graph-json address | history, ≥ 2 versions, no `live` | history, 1 version, no `live` | history, ≥ 2 versions, `live` | history, 1 version, `live` | history, 0 versions, `live` | history, 0 versions, no `live` |
| Version button | none | `◷ <newest> ▾` | `◷ <it> ▾` | `◷ Live ▾` | `◷ Live ▾` | `◷ Live ▾` | none |
| Opens on | the graph | newest version | the version | Live | Live | Live | — |
| Picker subtitle | — | "12 versions" | "1 version" | "12 versions and Live" | "1 version and Live" | "0 versions and Live" | — |
| Track | — | points | one point | points ┆ Live | one point ┆ Live | Live alone | — |
| ← → | — | step | nothing | step, Live last | between the point and Live | nothing | — |
| Home / End | — | oldest / newest | nothing | oldest / Live | the point / Live | nothing | — |
| Message | — | the version's | the version's | the version's, or Live's closing line | the version's, or Live's closing line | Live's closing line | — |
| Workspace | the graph | the version's graph | the version's graph | Live's or the version's graph | Live's or the version's graph | Live's graph | "This history has no version yet." |
| Freshness | the graph, as today | the list | the list | the list and Live | the list and Live | the list and Live | the list |
| Recent says | "Live service · one graph" | "History · <name> · 12 versions" | "History · <name> · 1 version" | "History · <name> · 12 versions and Live" | "History · <name> · 1 version and Live" | "History · <name> · 0 versions and Live" | "History · <name> · no version yet" |

In every history mode (M2–M7): the key is eight dots in the field, Recent and the room link; the browser's address bar carries `history` and `b` (absent in M7) but never the key; **Copy link** and the room's link add `#key=`.

Inside M2–M5, a **refused** version stays on the track, drawn hollow (a refused release keeps its name, a refused merge its dot); its tooltip ends with "refused: <reason>"; choosing it shows the reason in the workspace instead of a diagram, and the button names it. Without Live, a history opens on its newest version that is not refused; when every version is refused, on its newest, showing its reason.

Live **unreachable** (M4–M6), at opening or later: the history still opens on Live; the button still says `◷ Live ▾`; the workspace shows the unreachable state a running service shows today, with the notice "Live cannot be reached; pick a version"; the versions open as usual; in M6 there is nothing else to show. In a room everyone on Live sees the same state.

**Moves** while a history is open: `live` removed while someone is on Live → they go to the newest version, told "Live is no longer part of this history"; the version someone is on disappears from the list → they go to the default version, told "<name> is no longer in the history"; a room moves as one. A page the new version lacks falls back as a link to a missing page does today; in a room, as on joining.

## The version button

Desktop: in the 38 px row above the workspace, at the right. Phone: in the 44 px phone bar. `aria-haspopup="dialog"`, `aria-expanded`.

## The picker

Over the diagram, anchored under the button; starts closed; closed by a click outside or Escape; choosing a version leaves it open. Head: the service's name, the subtitle above, **Copy link** (copies `?history=…&b=…#key=…` for the shown version; "Link copied" confirms), the mode switch — One active; Diff and Side by side greyed, `aria-disabled="true"`, tooltip "comes later" on hover, focus or touch, a click does nothing. Then the track, then the message. Phone: a sheet from the bottom with the same parts.

## The track

- Time axis: oldest left; Live after a dashed gap at the right end.
- A point per version; releases named by their tag, larger; merges small dots; flags above for other tags.
- Points `max(24 px, width / count)` apart; phone touch targets ≥ 44 px.
- Scroll: horizontal wheel or swipe, vertical wheel over the track, drag on empty track; no scrollbar; edges fade where more is hidden; the right edge says "N newer ›", N counting every point hidden there, Live included (as the mockup shows it).
- The handle: drag, click a point, ← → Home End. Scrolled out of view, it is pinned to its edge; a click scrolls back to it.
- Labels: the oldest point, releases and Live, none under the chosen chip; the merges between are dots only; the oldest and Live never thin out; then releases newest first, each kept only when it does not overlap one kept before.
- Opens with the chosen version in view.

## The message

`white-space: pre-wrap`; words wrap; nothing above the text; at most nine lines, then it scrolls inside with a thin visible scrollbar and a fade on the lower edge while more is below; selectable. Only `http(s)` addresses and `#<n>` of a GitHub history are links (new tab, `rel="noopener noreferrer"`). Live: "Live · checked 12 s ago · newest version <name>, <date>"; in M6 the last part is absent; while Live cannot be reached, "Live · cannot be reached since <time>". Every other link shown for a history (the Live service, the repository, a pull request) opens the same way.

## The address field

One field for every kind. While not edited, a key shows as `••••••••` with an eye button that reveals it until it is clicked again or the field is left. Recent lists records with what each turned out to be (table above), keys as dots, each with a remove button. The page's title is `<name> · <version name> — Maxitor`.
