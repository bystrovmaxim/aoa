# Contract: what the screen shows

The look is the mockup's (`specs/030-graph-history/mockup/index.html`), with the spec's three corrections (message, release, no index).

## Modes

Every screen and every test is specified for each mode. A mode is derived from what was opened; it can change while a history is open (a first version is merged: M6 → M5, M7 → M3; a second one: M3 → M2, M5 → M4).

| | M1 Live only | M2 History, several, no Live | M3 History, one, no Live | M4 Live and several | M5 Live and one | M6 Live, no version yet | M7 History, nothing yet |
|---|---|---|---|---|---|---|---|
| Opened | a running service, a graph-json address | history, ≥ 2 versions, no `live` | history, 1 version, no `live` | history, ≥ 2 versions, `live` | history, 1 version, `live` | history, 0 versions, `live` | history, 0 versions, no `live` |
| Version button | none | `◷ <newest> ▾` (`◷ 0.11.0 · #147 ▾`, `◷ #147 ▾`, `◷ #57 ▾`) | `◷ <it> ▾` | `◷ Live ▾` | `◷ Live ▾` | `◷ Live ▾` | none |
| Opens on | the graph | newest version | the version | Live | Live | Live | — |
| Picker subtitle | — | "12 versions" | "1 version" | "12 versions and Live" | "1 version and Live" | "0 versions and Live" | — |
| Track | — | points | one point | points ┆ Live | one point ┆ Live | Live alone | — |
| ← → | — | step | nothing | step, Live last | between the point and Live | nothing | — |
| Home / End | — | oldest / newest | nothing | oldest / Live | the point / Live | nothing | — |
| Message | — | the version's | the version's | the version's, or Live's closing line | the version's, or Live's closing line | Live's closing line | — |
| Workspace | the graph | the version's graph | the version's graph | Live's or the version's graph | Live's or the version's graph | Live's graph | "This history has no version yet." |
| Freshness | the graph, as today | the list | the list | the list and Live | the list and Live | the list and Live | the list |
| Recent says | "Live service · one graph" | "History · <name> · 12 versions" | "History · <name> · 1 version" | "History · <name> · 12 versions and Live" | "History · <name> · 1 version and Live" | "History · <name> · 0 versions and Live" | "History · <name> · no version yet" |

In every history mode (M2–M7): the key is eight dots in the field, Recent and the room link; the browser's address bar carries `history`, `b` (absent in M7) and the key after `#key=`, so copying it opens the same history at the same version; the room's link adds `#key=` too.

Inside M2–M5, a **refused** version stays on the track, drawn hollow (a refused release keeps its name, a refused merge its dot); its tooltip ends with "refused: <reason>"; choosing it shows the reason in the workspace instead of a diagram, and the button names it. Without Live, a history opens on its newest version that is not refused; when every version is refused, on its newest, showing its reason.

Live **unreachable** (M4–M6), at opening or later: the history still opens on Live; the button still says `◷ Live ▾`; the workspace shows the unreachable state a running service shows today, with the notice "Live cannot be reached; pick a version"; the versions open as usual; in M6 there is nothing else to show. In a room everyone on Live sees the same state.

**Moves** while a history is open: `live` removed while someone is on Live → they go to the newest version, told "Live is no longer part of this history"; the version someone is on disappears from the list → they go to the default version, told "<name> is no longer in the history"; a room moves as one. A page the new version lacks falls back as a link to a missing page does today; in a room, as on joining.

## The version button

Desktop: in the 38 px row above the workspace, at the left (the mockup's pill: the history's clock, the version's name in bold, a chevron); a click toggles the picker. Phone: in the 44 px phone bar. `aria-haspopup="dialog"`, `aria-expanded`.

## The picker

The mockup's 760 px card under the button, following it as the sidebar opens or closes; starts closed; not modal: a click on the sidebar does what it is for and leaves the picker open, a click on the diagram or Escape closes it; choosing a version leaves it open. Head: the service's name and the subtitle ("12 versions and Live · 2 open pull requests") at the left; at the right an "i" that opens the track's legend, then the mode switch — One active; Diff and Side by side greyed, `aria-disabled="true"`, tooltip "comes later". No copy button: the address bar is the link. Then the track, then the message. Phone: a sheet from the bottom with the same parts.

The legend: one row per kind of point in track order — Direct push, Merged, Review required, Approved, Changes requested, Live — each its point and line in its colour, a name and one line; then Size, Flag, The chosen point.

## The track

- Time axis: oldest left; then the open pull requests that change the graph; Live always last. What is not in the history yet — open pull requests and Live — follows a dashed line.
- One colour per kind of point, the same on the track, in the card and the legend: a direct push grey `#8c959f`, a merged pull request purple `#8250df`, an open one its review state's — review required `#9a6700`, approved `#1a7f37`, changes requested `#d1242f` — Live hollow grey. Each stretch of line takes the colour of the point it leads to, lighter.
- A point that starts a version — its own version-number tag — is larger; a point inside a version smaller. A flag above a point marks a release: a GitHub Release, or a tag named `release…`.
- When Live runs exactly the newest version's graph, the two are one point: Live, carrying that version's card and message.
- Points `max(24 px, width / count)` apart; phone touch targets ≥ 44 px.
- Scroll as the browser scrolls: a sideways swipe with momentum, the vertical wheel turned sideways, a drag; no scrollbar, nothing faded; the right edge says "N newer ›", N counting every point out of view there, Live included.
- The chosen point: smaller than the mockup's knob, in its own colour (Live hollow), its chip in the same colour — `0.11.0 · #147`, or `#147`, `#57`. Click a point, ← → Home End. Scrolled out of view, it is pinned to its edge; a click scrolls back to it.
- Names under the track: a version's own point by its number, and Live; nothing else, no dates; none under the chosen chip; they thin out where they would collide.
- The card (tooltip) under the track, never over a point: Merged, Direct push or the open pull request's state; the version and Release chips; its number and when; its title (two lines at most); author → merger, with a picture where the host gives one, else initials; lines and files; what it did to the graph — nodes by kind, nodes changed, links. One card for the track: it stays put while the track scrolls under a still pointer, then shows the point now under it, the track gliding the last pixels to stand it under the pointer.
- Opens with the chosen version in view.

## The message

`white-space: pre-wrap`; words wrap; nothing above the text; 180 px of text (about nine lines), then it scrolls inside with a thin visible scrollbar, nothing faded; selectable. Only `http(s)` addresses and `#<n>` of a GitHub history are links (new tab, `rel="noopener noreferrer"`). Live: "Live · checked 12 s ago · newest version <name>, <date>"; in M6 the last part is absent; while Live cannot be reached, "Live · cannot be reached since <time>". Every other link shown for a history (the Live service, the repository, a pull request) opens the same way.

## The address field

One field for every kind. While not edited, a key shows as `••••••••` with an eye button that reveals it until it is clicked again or the field is left. Recent lists records with what each turned out to be (table above), marked by a history's clock or a service's waves, keys as dots, each with copy and remove buttons that never cover the text. The page's title is `<name> · <version name> — Maxitor`.
