# DiagramShell


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Viewport chrome for diagram viewers: loading overlay, error strip, flex shell around children; **`index.ts`** also exports **`useDiagramLoader`** for async loads with cancellation.

## Files

| File | Responsibility |
|------|----------------|
| `DiagramShell.tsx` | Layout + spinner + error UI. |
| `hooks/useDiagramLoader.ts` | Cancelling async loader hook used by viewers. |
