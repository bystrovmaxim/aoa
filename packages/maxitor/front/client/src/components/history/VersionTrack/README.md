# VersionTrack


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** One time axis of a history: a point per version, releases named, merges as dots, flags, refused versions hollow, Live after a dashed gap; the handle is a slider (← → Home End). (spec 037)

## Files

| File | Responsibility |
|------|----------------|
| `VersionTrack.tsx` | SVG drawing; `role="slider"` handle with `aria-valuetext`. |
| `thinLabels.ts` | Which names stay under the track: the chosen, the oldest, the newest and Live always; releases newest first where they overlap none. |
