# VersionsBetween


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** In Diff, under the two messages: one line, "N versions between", absent when A and B are neighbours on the track; it opens the history's versions strictly between them, newest first — open pull requests are not on the way from A to B —, each closed row its name and its message's first line, a click on a row opening its whole message through `VersionMessage`. (spec 038, FR-031)

## Files

| File | Responsibility |
|------|----------------|
| `VersionsBetween.tsx` | `versionsBetween` — the track's points strictly between A and B, newest first — and the line with its list. |
