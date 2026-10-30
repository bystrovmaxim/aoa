// src/rooms/coordinates.ts
/**
 * Diagram coordinates ⇄ screen coordinates.
 *
 * A pointer travels in the coordinates of the diagram itself, which every participant's picture
 * shares to the bit (spec 028, FR-006): the user space of the Graphviz SVG, or G6's canvas space for
 * the full graph. Each tab maps them to its own screen with its own zoom and pan (FR-040).
 */

export type Point = { x: number; y: number };

/** The parts of an SVG element the maps use: its screen transform. */
export type ScreenTransformed = { getScreenCTM(): DOMMatrixReadOnly | SVGMatrix | null };

/** Client pixels → the SVG's user space; ``null`` while the SVG is not laid out. */
export function svgClientToDiagram(svg: ScreenTransformed, client: Point): Point | null {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const det = ctm.a * ctm.d - ctm.b * ctm.c;
  if (!Number.isFinite(det) || det === 0) return null;
  const dx = client.x - ctm.e;
  const dy = client.y - ctm.f;
  return { x: (ctm.d * dx - ctm.c * dy) / det, y: (ctm.a * dy - ctm.b * dx) / det };
}

/** The SVG's user space → client pixels; ``null`` while the SVG is not laid out. */
export function svgDiagramToClient(svg: ScreenTransformed, point: Point): Point | null {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  return { x: ctm.a * point.x + ctm.c * point.y + ctm.e, y: ctm.b * point.x + ctm.d * point.y + ctm.f };
}

/** The parts of a G6 graph the maps use. */
export type CanvasMapped = {
  getCanvasByClient(point: [number, number]): ArrayLike<number>;
  getClientByCanvas(point: [number, number]): ArrayLike<number>;
};

/** Client pixels → G6's canvas space. */
export function g6ClientToDiagram(graph: CanvasMapped, client: Point): Point | null {
  const [x, y] = Array.from(graph.getCanvasByClient([client.x, client.y]));
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
}

/** G6's canvas space → client pixels. */
export function g6DiagramToClient(graph: CanvasMapped, point: Point): Point | null {
  const [x, y] = Array.from(graph.getClientByCanvas([point.x, point.y]));
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
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
