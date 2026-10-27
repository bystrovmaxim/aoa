// src/rooms/follow.ts
/**
 * Following someone (spec 028, FR-051 … FR-057): your screen goes where theirs goes — their active
 * page, centred on the centre of their screen — at your own zoom. It changes nothing for them.
 *
 * Who follows whom is the server's: **Follow** sends ``follow``, the room answers ``follows``, and the
 * tab follows while the links say so. It stops on your own pan (a drag; zooming does not stop it),
 * your own navigation, **Stop**, Esc, or their leaving, which the server turns into new links.
 *
 * While following, the follower also sees what the followed person sees — their hover, tooltip,
 * selection and open panels (spec 029, FR-010) — through ``focusStore``; every tab in a room sends what
 * it shows as ``focus``, at most ten times a second, and the server passes it to its followers only.
 */
import { useCallback, useEffect } from "react";
import type { DiagramViewport, Point } from "@/rooms/coordinates";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { focusToSend, sameFocus, setFollowTarget, subscribeFocus, type FocusState } from "@/rooms/focusStore";
import { subscribePointers, viewportOfParticipant } from "@/rooms/pointerStore";
import type { ClientMessage, Participant } from "@/rooms/protocol";
import type { RoomState } from "@/rooms/roomStore";
import { throttle } from "@/rooms/throttle";

/** Messages a second a focus may send (spec 029, contracts/room-protocol.md). */
export const FOCUS_RATE = 10;

/** The person this tab follows, or ``null``. */
export function followedBy(room: RoomState | null): Participant | null {
  if (!room) return null;
  const target = room.follows[room.youId];
  return target ? (room.participants.find((p) => p.id === target) ?? null) : null;
}

/** A page change following makes: their page, replacing the history entry (FR-057). */
export type FollowNavigation = { page: string; replace: true };

/** Where following takes this tab now: another page to open, or ``null`` when it is already there. */
export function followNavigation(target: Participant, page: string | null): FollowNavigation | null {
  if (!target.page || target.page === page) return null;
  return { page: target.page, replace: true };
}

/** The point following centres on: the centre of their screen, never its size as a zoom (FR-051). */
export function followCentre(viewport: DiagramViewport | undefined): Point | null {
  return viewport ? { x: viewport.cx, y: viewport.cy } : null;
}

/** Distance a pointer travels with its button down before it counts as a pan, in pixels. */
const PAN_THRESHOLD_PX = 4;

/**
 * Call ``onPan`` when the person drags the diagram with one pointer. A wheel or a two-finger pinch
 * zooms and is not a pan, so it never calls it. Returns the call that stops watching.
 */
export function watchOwnPan(element: HTMLElement, onPan: () => void): () => void {
  const down = new Map<number, { x: number; y: number }>();
  const onDown = (event: PointerEvent) => {
    if (event.button === 0) down.set(event.pointerId, { x: event.clientX, y: event.clientY });
  };
  const onMove = (event: PointerEvent) => {
    const start = down.get(event.pointerId);
    if (!start || down.size !== 1) return;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) >= PAN_THRESHOLD_PX) {
      down.clear();
      onPan();
    }
  };
  const onUp = (event: PointerEvent) => {
    down.delete(event.pointerId);
  };
  element.addEventListener("pointerdown", onDown);
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
  window.addEventListener("pointercancel", onUp);
  return () => {
    element.removeEventListener("pointerdown", onDown);
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    window.removeEventListener("pointercancel", onUp);
  };
}

export type FollowOptions = {
  room: RoomState | null;
  send: (message: ClientMessage) => void;
  surface: DiagramSurface | null;
  page: string | null;
  /** Open a page; following always replaces the history entry. */
  navigate: (page: string, options: { replace: boolean }) => void;
};

/** Follow, switch and stop; while following, keep this tab on the followed person's page and centre. */
export function useFollow({ room, send, surface, page, navigate }: FollowOptions) {
  const target = followedBy(room);
  const targetId = target?.id ?? null;
  const targetPage = target?.page ?? null;

  /** **Follow**, or **Follow <name> instead**: one message, the server switches in one step (FR-053). */
  const follow = useCallback((participant: string) => send({ type: "follow", target: participant }), [send]);
  const stop = useCallback(() => send({ type: "stop_following" }), [send]);

  // Their page.
  useEffect(() => {
    if (!target) return;
    const next = followNavigation(target, page);
    if (next) navigate(next.page, { replace: next.replace });
    // ``target`` changes identity with every presence; its id and page are what matter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetId, targetPage, page, navigate]);

  // Their screen's centre, on every new surface and every screen they report.
  useEffect(() => {
    if (!targetId || !surface || page !== targetPage) return undefined;
    const centre = () => {
      const point = followCentre(viewportOfParticipant(targetId));
      if (point) surface.centreOn(point);
    };
    centre();
    return subscribePointers(centre);
  }, [targetId, targetPage, surface, page]);

  // What the followed person sees shows here; the viewers then ignore this tab's own mouse.
  useEffect(() => {
    setFollowTarget(targetId);
    return () => setFollowTarget(null);
  }, [targetId]);

  // What this tab shows goes to the people who follow it.
  const inRoom = room !== null;
  useEffect(() => {
    if (!inRoom || page === null) return undefined;
    const sender = throttle<FocusState>(FOCUS_RATE, (focus) => send({ type: "focus", ...focus }), sameFocus);
    const offer = () => sender.push(focusToSend(page));
    offer();
    const unsubscribe = subscribeFocus(offer);
    return () => {
      unsubscribe();
      sender.cancel();
    };
  }, [inRoom, page, send]);

  // Your own pan stops it; zooming does not.
  useEffect(() => {
    if (!targetId || !surface) return undefined;
    return watchOwnPan(surface.element, stop);
  }, [targetId, surface, stop]);

  // Esc stops it.
  useEffect(() => {
    if (!targetId) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") stop();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [targetId, stop]);

  return { following: target, follow, stop };
}
