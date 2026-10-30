# VersionPicker


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The mockup's card under the version button, not modal, following the button: the service's name, its count of versions, Live and open pull requests, an "i" for the track's legend, the mode switch (One; Diff and Side by side greyed, "comes later"), the track, and the chosen version's message; a bottom sheet on a phone. (spec 037)

## Files

| File | Responsibility |
|------|----------------|
| `VersionPicker.tsx` | An MUI `Popper` with a click-away that lets the sidebar's clicks through, holding `VersionTrack`; a `Drawer` on a phone. |
| `TrackLegend.tsx` | The legend behind the "i": one row per kind of point in track order, then size, flag, the chosen point. |
