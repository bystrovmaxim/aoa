# MapViewer

**Role:** The full graph as a map (spec 040): named domains far away, what they hold closer, read from the server in parts. Sigma.js draws with WebGL; it loads lazily, so no other diagram carries its weight.

## Public exports

**`index.ts`** exports **`MapViewer`** only.

## Files

| File | Responsibility |
|---|---|
| `MapViewer.tsx` | The layers, the first read and its waiting state, the zoom toolbar, the layout hash. |
| `mapEngine.ts` | Sigma, the areas and tags on their canvases, levels, reading detail and letting it go, hover, flying to a domain, the room's surface. |
