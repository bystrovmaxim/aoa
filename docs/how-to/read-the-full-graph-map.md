# Read the full graph as a map

The full graph is a map: far away it shows named domains and what links them, closer the entities and operations of a domain, closest their fields and states. Zooming only reveals things; nothing ever moves. It holds graphs of about a hundred thousand nodes, because the browser reads an overview first and then only the detail of what it looks at.

[18_the_full_graph_as_a_map.py](../../examples/step_26_maxitor/18_the_full_graph_as_a_map.py) ([notebook](../../examples/step_26_maxitor/18_the_full_graph_as_a_map.ipynb)) runs the reads below against a small service in three versions.

## Move around

As on every other diagram:

| To | Do |
|---|---|
| pan | a plain wheel or a two-finger swipe; Shift turns the wheel sideways; or drag |
| zoom around the pointer | a pinch, or Ctrl / ⌘ with the wheel |
| fly to a domain | click it while it is folded |
| see the whole map | the fit button |

On a phone, drag and pinch; a tap reads a node.

## What shows at each distance

| Distance | What you see |
|---|---|
| far | each domain as an outlined area with its name, what it holds, and bundles of links to other domains |
| middle | entities, actions, resources and roles, with their links |
| close | fields, states, aspects and everything else |

What belongs to no domain stands in its own area, *Outside domains*.

## Filter

The filter panel has **Domains**, **Node types** and, in Diff, **Changes**. A filter takes things off the picture and moves nothing else: the outline closes around what is left, the name stands with it, and the area reads how much is left, such as `45 of 394 left`. This works at every distance.

A hidden node takes everything below it: `Application → Domain → Entity, Action, Resource → fields, aspects, lifecycle → states`. So switching off a domain takes its entities and actions with all they hold; switching off the type Domain leaves only what is outside domains. A node in several domains goes when all of them are off.

Whether a row is on stays yours. A row that is on but has nothing left on the screen, because something above it is off, dims and carries a small mark. Hover or tap the mark: a card shows what is off above it, and one button switches that on.

The address keeps the filters and the paint, so a link opens the same picture.

## Paint

The gear shift at the foot of the panel chooses what paints the picture: domains, node types or, in Diff, changes. Moving it opens that section and folds the others. A section that does not paint shows grey disks.

## Compare two versions

[Pick two versions](compare-two-versions.md) in the version picker. Nodes stay where they stand in B; what only A has stands beside them.

| What | Looks |
|---|---|
| added, changed | a green or an amber ring |
| removed | a dashed red circle; a removed link is dashed red |
| a relation that points elsewhere now | one amber link, and a thin dashed line to its target in A |
| a domain where nothing changed, neither a node nor a link | grey and dim |
| a folded domain with changes | its count by status, such as `+3 −1 ~2` |

Switch off **Unchanged** to take the grey domains off the map. Fading and grey domains belong to painting by changes; rings stay under any paint.

The version button counts every change drawn, nodes and links, whatever the zoom. Beside it the stepper walks through them: the arrows or Shift + ↑ ↓ go to the next and the previous, and a click on its middle opens the list, where any change can be picked directly. A step flies to the change, marks it with a halo and opens its card. A click on a domain's count goes to its first change. All of it follows the filters, and with no change left the button says "no changes" and nothing fades.

## In a room

Everyone sees one picture: the filters, the paint, the version. Someone following you sees your hover, your stepper and its list as you scroll it, your pointer on the same row, and the card of a hidden row.

## What runs where

Each version is laid out once on the server, by [Graphviz](https://graphviz.org), domain by domain, and kept on disk under `MAXITOR_MAP_CACHE` (by default `~/.cache/maxitor/map`). A domain whose content did not change keeps its layout, and every domain keeps its place across versions, so a change in one moves nothing in the others. The first opening of a new version says it is laying out.

The Docker image includes Graphviz. To run Maxitor locally, install it:

```bash
brew install graphviz
```

A browser with no WebGL says so and offers the ERD.

On a graph of 96 361 nodes and 146 010 links, measured with `scripts/measure-map.ts` on a production build: the overview on screen in 417 ms, a domain read in 24 ms, zoom with no frame over 50 ms, a filter in 54–61 ms.
