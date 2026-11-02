# RoomBar


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The room controls above the workspace (spec 028, mockup screens 1, 3, 5, 18, 19). Outside a room: **Open room**. Inside: the circles, **Copy link** and **Leave room** in the 38 px desktop row; on a phone the circles and one ⋮ menu with **Copy room link** and **Leave room** in words.

## Files

| File | Responsibility |
|------|----------------|
| `RoomBar.tsx` | The row's controls, the invite card after opening a room, *Reconnecting…* and the fading *joined* / *left* line. |
| `RoomBanner.tsx` | The sentence across the workspace when the tab could not stay in a room: ended (with **Open room**), full, refused. |
| `LeaveForServiceDialog.tsx` | *Leave the room and open another service?* before *Load a different service* inside a room. |
| `RoomBar.test.tsx` | Open room, the copied address is the current page, circle labels, Enter/Esc on a card, +N on a phone, Leave room. |
