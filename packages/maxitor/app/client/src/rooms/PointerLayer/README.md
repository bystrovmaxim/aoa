# PointerLayer


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** Everyone else's pointer over the diagram on screen, at the diagram point it marks, re-projected on every pan and zoom (spec 028, FR-040 … FR-045; mockup screens 6 and 8). A mouse is an arrow with a name tag in the person's colour; a touch is a ring that fades after about a second; a mouse pointer stays for as long as its person is in the room and on this page, however long it stands still (spec 029). A pointer outside the view is an arrow at the edge with the person's initials; a click on it centres the view there at the same zoom. Rendered into the viewer's own element through a portal, so the viewer's frame clips it.

## Files

| File | Responsibility |
|------|----------------|
| `PointerLayer.tsx` | The overlay, `place` (inside or at the edge) and `pointerVisible` (a mouse always, a touch for a moment). |
| `PointerLayer.test.tsx` | Which pointers show: a still mouse pointer after ten minutes, a tap only for a moment. |
