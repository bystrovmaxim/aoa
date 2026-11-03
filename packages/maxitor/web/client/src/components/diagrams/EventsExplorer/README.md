# EventsExplorer

**Role:** The events explorer (spec 055), shown for the Events pages of all domains and of one domain. The screen starts with one layer — every domain, every event or every action that emits, as the mode pill says — and the reader opens the graph link by link through ports. Graphviz `dot` places the nodes; the explorer draws its own nodes and lines at those places, and moves and zooms with ERD's pan and zoom.

## Public exports

**`index.ts`** exports **`EventsExplorer`** and **`EventsExplorerProps`**.

## Files

| File | Responsibility |
|---|---|
| `EventsExplorer.tsx` | Read the events graph, keep the page's settings, lay the screen out, draw lines, cards and the toolbar. |
| `ExplorerNode.tsx` | A node's body by kind and paint, and a port's pill. |
| `ModePill.tsx` | The pill of the three modes. |
| `explorerLook.ts` | Colours and icons. |
| `src/lib/eventsExplorer.ts` | Every rule of the screen: the graph, layers, ports, lines, filters, the DOT text and reading Graphviz's answer. |
