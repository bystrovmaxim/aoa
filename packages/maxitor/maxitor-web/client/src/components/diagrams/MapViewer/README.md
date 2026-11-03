# MapViewer

**Role:** The full graph as a map (spec 040): named domains far away, what they hold closer, read from the server in parts. Sigma.js draws with WebGL; it loads lazily, so no other diagram carries its weight.

## Public exports

**`index.ts`** exports **`MapViewer`** only; **`ChangeStepper.tsx`** is imported on its own by the page's top row.

## Files

| File | Responsibility |
|---|---|
| `MapViewer.tsx` | The layers, the first read and its waiting state, the zoom toolbar, the layout hash. |
| `mapEngine.ts` | Sigma, the areas and tags on their canvases, levels, reading detail and letting it go, hover, flying to a domain, the room's surface. In Diff: rings, dashed removals, grey domains, counts, the steps through changes. |
| `src/lib/mapVisibility.ts` | What the filters leave at every zoom: a hidden node takes what stands below it, and each row is measured on its own axis. |
| `src/lib/mapFilterRows.ts` | The panel's rows: disks by what paints, dimmed rows and what keeps them hidden. |
| `ChangeStepper.tsx` | Next and previous through a comparison's changes, beside the version button. |

## Mouse and trackpad

As on every other diagram: a plain wheel or a two-finger swipe pans, Shift turns it sideways, a pinch or Ctrl / ⌘ with the wheel zooms around the pointer, a drag pans and stops where it is let go, and a double click does nothing.

## Filters

The filters and the paint are page settings, as on the ERD: a room shares them and the address carries them (`off_types`, `off_domains`, `off_changes`, `paint`, `paint_diff`). Applying them moves nothing. Outlines are redrawn around what is left a few at a time, after the picture has answered.

A browser without WebGL says so and offers the ERD.
