# DiagramShell

**Role:** Viewport chrome for diagram viewers: loading overlay, error strip, flex shell around children; **`index.ts`** also exports **`useDiagramLoader`** for async loads with cancellation.

## Files

| File | Responsibility |
|------|----------------|
| `DiagramShell.tsx` | Layout + spinner + error UI. |
| `hooks/useDiagramLoader.ts` | Cancelling async loader hook used by viewers. |
