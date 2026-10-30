# VersionTrack


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** One time axis of a history, as the mockup draws it: a point per version in the colour of how it came (direct push, merged, an open pull request's review state, Live hollow), the line coloured by the point it leads to; a version's own point larger and named by its number, flags for releases; open pull requests before Live, which is last and one point with the newest version when they match; a card per point; scrolls as the browser scrolls; a slider (← → Home End). (spec 037)

## Files

| File | Responsibility |
|------|----------------|
| `VersionTrack.tsx` | SVG drawing in a natively scrolled box; `role="slider"` with `aria-valuetext`; one card for the track that stays under a still pointer while it scrolls. |
| `VersionTip.tsx` | A point's card: how it came, version and Release chips, title, author → merger, size, graph change; `whenOf`, `kindCount`, `changeOf`, `initialsOf`. |
| `proposalLook.ts` | The colours of each kind of point, GitHub's own: merged, direct push, open pull request states, Live. |
| `thinLabels.ts` | Which names stay under the track: Live and the oldest always; then the others newest first where they overlap none. |
