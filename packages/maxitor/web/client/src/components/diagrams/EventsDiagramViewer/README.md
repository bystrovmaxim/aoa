# EventsDiagramViewer

**Role:** A domain's events (spec 053): actions, those of their methods that emit, and the events in bands by the domain's vocabulary, with Graphviz **dot**. Resting on an event opens the common card: its fields, every method producing it, its domains. In Diff it draws A and B together, marked, with the counts on the version button; Side by side draws each version's part.

## Public exports

**`index.ts`** exports **`EventsDiagramViewer`** and **`EventsDiagramViewerProps`**.

## Files

| File | Responsibility |
|---|---|
| `EventsDiagramViewer.tsx` | Read the diagram, its filters and direction, draw it, open a card. |
| `src/lib/eventsDiagram.ts` | The DOT text, and the marks of a comparison. |
