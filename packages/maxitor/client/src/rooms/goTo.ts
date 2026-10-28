// src/rooms/goTo.ts
/**
 * Going to someone (spec 028, FR-050): their active page, centred on their pointer — or on the centre
 * of their screen when they have none, as a phone between touches — at your own zoom.
 *
 * Their pointer and screen reach this tab only while it is on their page, and the server brings the
 * last ones the moment it arrives there. So going to someone on another page first navigates, then
 * centres as soon as the new diagram is drawn and their position is known; it gives up after a few
 * seconds and leaves the page fitted.
 */
import { useCallback, useEffect, useRef } from "react";
import type { DiagramViewport, Point } from "@/rooms/coordinates";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { currentPointers, subscribePointers, viewportOfParticipant, type RemotePointer } from "@/rooms/pointerStore";

/** How long going to someone waits for the diagram and their position. */
export const GO_TO_WAIT_MS = 5000;

/** Where to centre: their pointer, else the centre of their screen, else nowhere. */
export function goToPoint(pointer: RemotePointer | undefined, viewport: DiagramViewport | undefined): Point | null {
  if (pointer) return { x: pointer.x, y: pointer.y };
  if (viewport) return { x: viewport.cx, y: viewport.cy };
  return null;
}

/** Centre ``surface`` on where ``participant`` is, keeping the zoom; whether it could. */
export function centreOnParticipant(surface: DiagramSurface, participant: string): boolean {
  const point = goToPoint(currentPointers().get(participant), viewportOfParticipant(participant));
  if (!point) return false;
  surface.centreOn(point);
  return true;
}

/**
 * A go-to in progress. ``leaving`` is the surface of the page left, never the target; ``centred`` the
 * surface it already centred. A viewer may draw its diagram twice on arrival (a second batch of data
 * remounts it), so each new surface of the target page within the wait is centred once.
 */
type Pending = {
  participant: string;
  page: string;
  until: number;
  leaving: DiagramSurface | null;
  centred: DiagramSurface | null;
};

export type GoToOptions = {
  surface: DiagramSurface | null;
  /** The page on screen. */
  page: string | null;
  /** Open ``page`` as a navigation: the left panel and the address follow, Back returns. */
  navigate: (page: string) => void;
};

/** The call that goes to a participant on ``page``. */
export function useGoTo({ surface, page, navigate }: GoToOptions): (participant: string, theirPage: string | null) => void {
  const pending = useRef<Pending | null>(null);

  const settle = useCallback(() => {
    const target = pending.current;
    if (!target) return;
    if (Date.now() > target.until) {
      pending.current = null;
      return;
    }
    if (!surface || surface === target.leaving || surface === target.centred || page !== target.page) return;
    if (centreOnParticipant(surface, target.participant)) target.centred = surface;
  }, [surface, page]);

  // A new diagram, or their position arriving, may complete a pending go-to.
  useEffect(() => {
    settle();
    return subscribePointers(settle);
  }, [settle]);

  return useCallback(
    (participant: string, theirPage: string | null) => {
      if (!theirPage) return;
      const elsewhere = theirPage !== page;
      pending.current = {
        participant,
        page: theirPage,
        until: Date.now() + GO_TO_WAIT_MS,
        leaving: elsewhere ? surface : null,
        centred: null,
      };
      if (elsewhere) navigate(theirPage);
      else settle();
    },
    [page, surface, navigate, settle],
  );
}
