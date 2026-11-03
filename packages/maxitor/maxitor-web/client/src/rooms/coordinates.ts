// src/rooms/coordinates.ts
/**
 * Diagram coordinates ⇄ screen coordinates.
 *
 * A pointer travels in the coordinates of the diagram itself, which every participant's picture
 * shares to the bit (spec 028, FR-006): the user space of the Graphviz SVG, or the map's own units for
 * the full graph. Each tab maps them to its own screen with its own zoom and pan (FR-040).
 */

export type Point = { x: number; y: number };

/** The parts of an SVG element the maps use: its box on the screen and its ``viewBox``, else its screen transform. */
export type ScreenTransformed = {
  getScreenCTM(): DOMMatrixReadOnly | SVGMatrix | null;
  getBoundingClientRect?(): DOMRectReadOnly;
  viewBox?: { baseVal: { x: number; y: number; width: number; height: number } | null };
};

type Linear = { a: number; b: number; c: number; d: number; e: number; f: number };

/**
 * The SVG's user space → client pixels, as a matrix. It is read from the SVG's box on the screen and its ``viewBox``
 * (centred, the whole box shown), not from ``getScreenCTM``: Safari leaves the CSS transform of an ancestor — the pan
 * and zoom — out of that, so a follower in Safari mapped the screen at the wrong zoom and shrank to nothing (spec 038).
 * Every browser puts that transform in the box. Without a ``viewBox`` the screen transform is all there is.
 */
function screenTransform(svg: ScreenTransformed): Linear | null {
  const box = svg.viewBox?.baseVal;
  const rect = svg.getBoundingClientRect?.();
  if (box && box.width > 0 && box.height > 0 && rect && rect.width > 0 && rect.height > 0) {
    const scale = Math.min(rect.width / box.width, rect.height / box.height);
    return {
      a: scale,
      b: 0,
      c: 0,
      d: scale,
      e: rect.left + (rect.width - box.width * scale) / 2 - box.x * scale,
      f: rect.top + (rect.height - box.height * scale) / 2 - box.y * scale,
    };
  }
  return svg.getScreenCTM();
}

/** Client pixels → the SVG's user space; ``null`` while the SVG is not laid out. */
export function svgClientToDiagram(svg: ScreenTransformed, client: Point): Point | null {
  const ctm = screenTransform(svg);
  if (!ctm) return null;
  const det = ctm.a * ctm.d - ctm.b * ctm.c;
  if (!Number.isFinite(det) || det === 0) return null;
  const dx = client.x - ctm.e;
  const dy = client.y - ctm.f;
  return { x: (ctm.d * dx - ctm.c * dy) / det, y: (ctm.a * dy - ctm.b * dx) / det };
}

/** The SVG's user space → client pixels; ``null`` while the SVG is not laid out. */
export function svgDiagramToClient(svg: ScreenTransformed, point: Point): Point | null {
  const ctm = screenTransform(svg);
  if (!ctm) return null;
  return { x: ctm.a * point.x + ctm.c * point.y + ctm.e, y: ctm.b * point.x + ctm.d * point.y + ctm.f };
}

/** What a tab sees of the diagram, in diagram coordinates: centre and size (the ``viewport`` message). */
/** What a screen shows, in diagram units; ``pw`` × ``ph`` its size in pixels, when the sender tells it (spec 038). */
export type DiagramViewport = { cx: number; cy: number; w: number; h: number; pw?: number; ph?: number };

/** The part of the diagram inside ``rect`` (the viewer on screen), through ``toDiagram``. */
export function viewportOf(rect: DOMRectReadOnly, toDiagram: (client: Point) => Point | null): DiagramViewport | null {
  const a = toDiagram({ x: rect.left, y: rect.top });
  const b = toDiagram({ x: rect.right, y: rect.bottom });
  if (!a || !b) return null;
  return { cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2, w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y) };
}
