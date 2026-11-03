// src/lib/sanitizeGraphvizSvgOverlays.ts
/**
 * Graphviz WASM SVG post-pass: drop canvas backdrops and fix arrowheads that use an
 * opaque light fill (notably ``open`` / ``empty`` heads), which would otherwise hide
 * the dotted diagram background under the arrow tip.
 */

const LIGHT_OPAQUE_FILLS = new Set([
  "#ffffff",
  "#fff",
  "white",
  "#f8fafc",
  "#f4f5f7",
  "lightgray",
  "lightgrey",
]);

function isBackdropFill(fill: string): boolean {
  const f = fill.toLowerCase().trim();
  return (
    f === "#f8fafc" ||
    f === "#f4f5f7" ||
    f === "#ffffff" ||
    f === "#fff" ||
    f === "white" ||
    f === "lightgray" ||
    f === "lightgrey"
  );
}

/** Remove the first full-canvas ``polygon`` Graphviz paints when bgcolor is a solid light pad. */
export function removeGraphvizCanvasBackdropPolygon(svg: SVGSVGElement): void {
  const gg = svg.querySelector("g.graph");
  const bgPoly = gg?.querySelector("polygon");
  if (!bgPoly) return;
  const fill = String(bgPoly.getAttribute("fill") || "");
  if (isBackdropFill(fill)) bgPoly.remove();
}

/** Turn light-filled edge arrow polygons/paths into hollow outlines so the grid shows through. */
export function clearGraphvizEdgeArrowOpaqueFills(svg: SVGSVGElement): void {
  for (const g of svg.querySelectorAll("g.edge")) {
    for (const poly of g.querySelectorAll("polygon")) {
      const f = String(poly.getAttribute("fill") || "").toLowerCase().trim();
      if (LIGHT_OPAQUE_FILLS.has(f)) {
        poly.setAttribute("fill", "none");
      }
    }
    for (const path of g.querySelectorAll("path")) {
      const f = String(path.getAttribute("fill") || "").toLowerCase().trim();
      if (f && LIGHT_OPAQUE_FILLS.has(f)) {
        path.setAttribute("fill", "none");
      }
    }
  }
}

/** Run both passes after injecting Graphviz SVG into the DOM. */
export function postProcessGraphvizSvgDom(svg: SVGSVGElement): void {
  removeGraphvizCanvasBackdropPolygon(svg);
  clearGraphvizEdgeArrowOpaqueFills(svg);
}
