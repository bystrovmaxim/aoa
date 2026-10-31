// src/rooms/diagramSurface.ts
/**
 * The diagram on screen, as the room sees it.
 *
 * The workspace shows one diagram at a time. Its viewer registers a surface — the element it draws
 * in, the coordinate maps, a way to hear about every pan and zoom, and a way to centre and restore
 * the view — and the room's pointer layer, pointer sender and page check work through it, the same
 * way for the three Graphviz viewers and for the map.
 */
import { useEffect, useSyncExternalStore, type RefObject } from "react";
import { svgClientToDiagram, svgDiagramToClient, type Point } from "@/rooms/coordinates";

/** Zoom and centre of a view, for restoring it after Maxitor reloads itself (FR-090). */
export type SavedView = { x: number; y: number; zoom: number };

export type DiagramSurface = {
  /** The viewer's element: it carries ``data-layout-hash`` and holds the pointer overlay. */
  element: HTMLElement;
  toDiagram(client: Point): Point | null;
  toClient(point: Point): Point | null;
  /** Subscribe to every pan, zoom and redraw; returns the unsubscribe. */
  subscribe(listener: () => void): () => void;
  /** Centre the view on a diagram point; the zoom stays. */
  centreOn(point: Point): void;
  view(): SavedView | null;
  restore(view: SavedView): void;
  /** How far zooms may differ before following moves yours, where a surface zooms finer than the default leaves alone. */
  zoomTolerance?: number;
};

let current: DiagramSurface | null = null;
const listeners = new Set<() => void>();

function publish(next: DiagramSurface | null): void {
  current = next;
  for (const listener of listeners) listener();
}

/** Make ``surface`` the diagram on screen; returns the call that takes it away again. */
export function registerDiagramSurface(surface: DiagramSurface): () => void {
  publish(surface);
  return () => {
    if (current === surface) publish(null);
  };
}

/** The diagram on screen, or ``null`` while none is drawn. */
export function useDiagramSurface(): DiagramSurface | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    () => current,
  );
}

/** Centre of ``element`` in client pixels. */
function centreOf(element: HTMLElement): Point {
  const rect = element.getBoundingClientRect();
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

/** What the Graphviz viewers' pan-zoom hook offers the room. */
export type SvgPanZoomControls = {
  onTransform(listener: () => void): () => void;
  centreOnClient(x: number, y: number): void;
  getScale(): number;
  setScale(scale: number): void;
  /** Bumped by every fit; each fit gives a new surface, so a view placed from outside is placed again. */
  fitCount: number;
};

/**
 * Register a Graphviz viewer's surface while ``ready`` (its SVG is on screen and fitted once, so a
 * view the room places — going to someone, a restored view — is not undone by the fit). Diagram coordinates
 * are the SVG's user space, mapped through its screen transform, which includes the pan and zoom.
 */
export function useSvgDiagramSurface(
  elementRef: RefObject<HTMLElement | null>,
  controls: SvgPanZoomControls,
  ready: boolean,
): void {
  const { onTransform, centreOnClient, getScale, setScale, fitCount } = controls;
  useEffect(() => {
    const element = elementRef.current;
    if (!element || !ready) return undefined;
    const svg = () => element.querySelector("svg");
    const toDiagram = (client: Point) => {
      const target = svg();
      return target ? svgClientToDiagram(target, client) : null;
    };
    const toClient = (point: Point) => {
      const target = svg();
      return target ? svgDiagramToClient(target, point) : null;
    };
    const centreOn = (point: Point) => {
      const client = toClient(point);
      if (client) centreOnClient(client.x, client.y);
    };
    return registerDiagramSurface({
      element,
      toDiagram,
      toClient,
      subscribe: onTransform,
      centreOn,
      view: () => {
        const centre = toDiagram(centreOf(element));
        return centre ? { ...centre, zoom: getScale() } : null;
      },
      restore: (view) => {
        setScale(view.zoom);
        centreOn(view);
      },
    });
    // ``fitCount``: a refit (new data, a new size) undoes a placed view, so it is a new surface.
  }, [elementRef, ready, onTransform, centreOnClient, getScale, setScale, fitCount]);
}
