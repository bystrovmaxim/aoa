# DiffCard


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The card of a changed table or row in Diff: every property that changed, by its path, before and after — values as text, never markup —; for an added or removed element one line, "Added in 0.9.0" / "Removed in 0.9.0". It reads `GET /api/v1/compare-element` for each graph element the click stands for (`@/lib/erdDiffCard`); a click outside or Escape closes it. An action changed inside lists its changed parts by group, from the target it is given. (spec 038, FR-028, FR-029; spec 041, FR-012)

## Files

| File | Responsibility |
|------|----------------|
| `DiffCard.tsx` | The card, its reads and `shownValue`. |
