# VersionButton


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The one button at the left of the top row that names the version shown — `◷ 0.11.0 · #147 ▾`, `◷ #57 ▾`, `◷ Live ▾` — and opens or closes the picker; only while a history has something to pick (M2–M6). (spec 037) In Diff (spec 038) it names both versions and carries the diagram's counts in their colours — `◷ A 0.8.0 → B 0.9.0  +15 −1 ~3 ▾` — or "no changes"; on a phone the short names (`A #128 → B #129`), the name cut with an ellipsis before the counts are (FR-033).

## Files

| File | Responsibility |
|------|----------------|
| `VersionButton.tsx` | MUI `ButtonBase`, `aria-haspopup="dialog"`, `aria-expanded`. |
