// src/rooms/follow.ts
/**
 * Following someone (spec 028, FR-051 … FR-057): your screen goes where theirs goes — their active
 * page, centred on the centre of their screen, at their zoom: you see what they see, on a screen of another size
 * at least all of it (spec 038). It changes nothing for them.
 *
 * Who follows whom is the server's: **Follow** sends ``follow``, the room answers ``follows``, and the
 * tab follows while the links say so. It stops on your own pan (a drag; zooming does not stop it),
 * your own navigation, **Stop**, Esc, or their leaving, which the server turns into new links.
 *
 * The follower's screen glides: each new centre is reached over the time since the previous one, from
 * wherever the screen is now, and the glide ends exactly on it (spec 029, FR-014).
 *
 * While following, the follower also sees what the followed person sees — their hover, tooltip,
 * selection and open panels (spec 029, FR-010) — through ``focusStore``; every tab in a room sends what
 * it shows as ``focus``, at most ten times a second, and the server passes it to its followers only.
 */
import { useCallback, useEffect } from "react";
import { isZoomWheel } from "@/lib/wheelGesture";
import { viewportOf, type DiagramViewport, type Point } from "@/rooms/coordinates";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { focusToSend, sameFocus, setFollowTarget, subscribeFocus, type FocusState } from "@/rooms/focusStore";
import { subscribePointers, viewportOfParticipant } from "@/rooms/pointerStore";
import type { ClientMessage, Participant } from "@/rooms/protocol";
import type { RoomState } from "@/rooms/roomStore";
import { throttle } from "@/rooms/throttle";

/** Messages a second a focus may send (spec 029, contracts/room-protocol.md). */
export const FOCUS_RATE = 10;

/** The shortest and the longest glide to a new centre, in milliseconds. */
export const GLIDE_MIN_MS = 30;
export const GLIDE_MAX_MS = 200;

/**
 * The follower's centre between the screens it is told: a glide from where it is to each new centre,
 * as long as the time since the previous one (``GLIDE_MIN_MS`` … ``GLIDE_MAX_MS``), ending exactly on it.
 */
export type Glide = {
  /** A new centre arrived at ``now``. */
  push(target: Point, now: number): void;
  /** Where the screen is at ``now``, and whether it has arrived. */
  at(now: number): { point: Point; arrived: boolean };
  /** Stand at ``point`` at once (a new picture, or the first centre). */
  jump(point: Point, now: number): void;
};

export function createGlide(): Glide {
  let from: Point | null = null;
  let to: Point | null = null;
  let start = 0;
  let duration = GLIDE_MIN_MS;
  let lastPush = -Infinity;

  const at = (now: number) => {
    if (!to) return { point: { x: 0, y: 0 }, arrived: true };
    if (!from || now >= start + duration) return { point: to, arrived: true };
    const k = Math.max(0, (now - start) / duration);
    return { point: { x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k }, arrived: false };
  };

  return {
    push(target, now) {
      from = to ? at(now).point : target;
      to = target;
      start = now;
      duration = Math.min(GLIDE_MAX_MS, Math.max(GLIDE_MIN_MS, now - lastPush));
      lastPush = now;
    },
    at,
    jump(point, now) {
      from = point;
      to = point;
      start = now;
      lastPush = now;
    },
  };
}

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

/** The point following centres on: the centre of their screen. */
export function followCentre(viewport: DiagramViewport | undefined): Point | null {
  return viewport ? { x: viewport.cx, y: viewport.cy } : null;
}

/** How far apart two zooms may be before following changes yours: a hair's difference is left alone. */
const ZOOM_TOLERANCE = 0.01;

/**
 * The zoom that shows what they see (spec 038): yours, times what fits their screen's area into yours — the same zoom
 * on a screen of the same size, all of their area on another; ``null`` when yours already is it.
 */
export function followZoom(yours: DiagramViewport, theirs: DiagramViewport, zoom: number): number | null {
  if (!(theirs.w > 0 && theirs.h > 0 && yours.w > 0 && yours.h > 0 && zoom > 0)) return null;
  const next = zoom * Math.min(yours.w / theirs.w, yours.h / theirs.h);
  return Math.abs(next - zoom) / zoom > ZOOM_TOLERANCE ? next : null;
}

/** Distance a pointer travels with its button down before it counts as a pan, in pixels. */
const PAN_THRESHOLD_PX = 4;

/**
 * Call ``onPan`` when the person moves the diagram: a drag with one pointer, or a wheel that moves
 * (a trackpad swipe, a plain mouse wheel). A pinch, Ctrl / ⌘ + wheel or a two-finger touch pinch
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
  const onWheel = (event: WheelEvent) => {
    if (!isZoomWheel(event) && (event.deltaX !== 0 || event.deltaY !== 0)) onPan();
  };
  element.addEventListener("pointerdown", onDown);
  element.addEventListener("wheel", onWheel, { passive: true });
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
  window.addEventListener("pointercancel", onUp);
  return () => {
    element.removeEventListener("pointerdown", onDown);
    element.removeEventListener("wheel", onWheel);
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

  // Their screen's centre: at once on every new surface, then gliding to every screen they report.
  useEffect(() => {
    if (!targetId || !surface || page !== targetPage) return undefined;
    const glide = createGlide();
    let frame: number | null = null;
    let last: Point | null = null;
    let lastSize: { w: number; h: number } | null = null;
    const step = () => {
      frame = null;
      const { point, arrived } = glide.at(performance.now());
      surface.centreOn(point);
      if (!arrived) frame = requestAnimationFrame(step);
    };
    // Their zoom: when their area differs from yours, yours changes at once, on their centre.
    const matchZoom = (theirs: DiagramViewport): boolean => {
      lastSize = { w: theirs.w, h: theirs.h };
      const yours = viewportOf(surface.element.getBoundingClientRect(), surface.toDiagram);
      const zoom = surface.view()?.zoom;
      const next = yours && zoom ? followZoom(yours, theirs, zoom) : null;
      if (next === null) return false;
      surface.restore({ x: theirs.cx, y: theirs.cy, zoom: next });
      return true;
    };
    const onScreen = () => {
      const theirs = viewportOfParticipant(targetId);
      const point = followCentre(theirs);
      if (!theirs || !point) return;
      const resized = !lastSize || lastSize.w !== theirs.w || lastSize.h !== theirs.h;
      if (resized && matchZoom(theirs)) {
        last = point;
        glide.jump(point, performance.now());
        return;
      }
      if (last && point.x === last.x && point.y === last.y) return;
      if (!last) {
        // The first centre they report: nothing to glide from yet.
        last = point;
        glide.jump(point, performance.now());
        surface.centreOn(point);
        return;
      }
      last = point;
      glide.push(point, performance.now());
      if (frame === null) frame = requestAnimationFrame(step);
    };
    const firstScreen = viewportOfParticipant(targetId);
    const first = followCentre(firstScreen);
    if (firstScreen && first) {
      last = first;
      glide.jump(first, performance.now());
      if (!matchZoom(firstScreen)) surface.centreOn(first);
    }
    const unsubscribe = subscribePointers(onScreen);
    return () => {
      unsubscribe();
      if (frame !== null) cancelAnimationFrame(frame);
    };
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
