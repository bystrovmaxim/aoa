// src/rooms/follow.ts
/**
 * Following someone (spec 028, FR-051 … FR-057): your screen goes where theirs goes — their active
 * page, at their zoom and with their top-left corner on yours — one to one, so the diagram stands where it stands for
 * them against the panels fixed to that corner, and a pointer over the diagram and over a panel agree (spec 038). It
 * changes nothing for them.
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
import { useCallback, useEffect, useRef } from "react";
import { isZoomWheel } from "@/lib/wheelGesture";
import { viewportOf, type DiagramViewport, type Point } from "@/rooms/coordinates";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { focusToSend, followedParticipant, sameFocus, setFollowTarget, subscribeFocus, type FocusState } from "@/rooms/focusStore";
import { screenOfParticipant, subscribePointers, viewportOfParticipant } from "@/rooms/pointerStore";
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

/**
 * Whom this tab takes the view from: the end of the chain it follows. Following Ваня while Ваня follows Лёша, the
 * camera, the hover and the panels come from Лёша directly — the same picture Ваня shows, without the second glide
 * and delay; once Ваня stops following, the chain ends at Ваня (spec 038). ``null`` while following nobody.
 */
export function followHead(room: RoomState | null): Participant | null {
  const target = followedBy(room);
  if (!room || !target) return null;
  let id = target.id;
  const seen = new Set([room.youId, id]);
  for (let next = room.follows[id]; next && !seen.has(next); next = room.follows[id]) {
    seen.add(next);
    id = next;
  }
  return room.participants.find((p) => p.id === id) ?? target;
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

/**
 * Where following puts your screen (spec 038). When they tell their screen's size in pixels: one to one — their zoom,
 * and their top-left corner on yours, so the diagram stands where it stands for them against the panels fixed to that
 * corner; a smaller screen then shows less on the right and below, a bigger one more. Without it: their centre, at the
 * zoom that shows all of their area. ``zoom`` in the answer is ``null`` when yours already is it.
 */
export function followTarget(yourPixels: { w: number; h: number }, yours: DiagramViewport, theirs: DiagramViewport, zoom: number): { centre: Point; zoom: number | null } {
  const { pw, ph } = theirs;
  if (pw && ph && pw > 0 && ph > 0 && theirs.w > 0 && yours.w > 0 && yourPixels.w > 0 && zoom > 0) {
    const scale = pw / theirs.w;
    const next = (zoom * scale) / (yourPixels.w / yours.w);
    return {
      centre: { x: theirs.cx - theirs.w / 2 + yourPixels.w / scale / 2, y: theirs.cy - theirs.h / 2 + yourPixels.h / scale / 2 },
      zoom: Math.abs(next - zoom) / zoom > ZOOM_TOLERANCE ? next : null,
    };
  }
  return { centre: { x: theirs.cx, y: theirs.cy }, zoom: followZoom(yours, theirs, zoom) };
}

/**
 * The size in pixels of the screen of the person this tab follows, when they tell it; ``null`` otherwise. A follower
 * fits a new drawing to it, not to its own screen: following one to one, that is the very view the person followed
 * fits it to, so a new filter or paint shows in one frame, not first fitted here and then moved there (spec 038).
 */
export function followedScreen(): { w: number; h: number } | null {
  const id = followedParticipant();
  return (id && screenOfParticipant(id)) || null;
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
  const following = followedBy(room);
  // The view comes from the end of the chain; whom you follow stays whom you chose.
  const target = followHead(room);
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
  const placedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!targetId) placedFor.current = null;
  }, [targetId]);
  useEffect(() => {
    if (!targetId || !surface || page !== targetPage) return undefined;
    // A new surface on the same page is a refit of a new drawing — new filters, a new layout mode. This tab fitted it
    // to their screen, which is their very view, so the screen they reported before their own refit is stale: it is
    // not put back, and only a screen they report after it is followed (spec 038).
    const refit = placedFor.current === `${targetId}|${page}`;
    placedFor.current = `${targetId}|${page}`;
    const stale = refit ? viewportOfParticipant(targetId) : undefined;
    const glide = createGlide();
    // Their zoom glides like their centre: ``x`` is the zoom, so a zoom they make arrives as smoothly as a pan.
    const zoomGlide = createGlide();
    let zooming = false;
    let frame: number | null = null;
    let last: Point | null = null;
    const step = () => {
      frame = null;
      const now = performance.now();
      const { point, arrived } = glide.at(now);
      const zoom = zooming ? zoomGlide.at(now) : null;
      if (zoom) surface.restore({ x: point.x, y: point.y, zoom: zoom.point.x });
      else surface.centreOn(point);
      if (zoom?.arrived) zooming = false;
      if (!arrived || (zoom && !zoom.arrived)) frame = requestAnimationFrame(step);
    };
    const schedule = () => {
      if (frame === null) frame = requestAnimationFrame(step);
    };
    /** Where your screen goes for their screen: its centre, and a new zoom or ``null``. */
    const targetFor = (theirs: DiagramViewport): { centre: Point; zoom: number | null } | null => {
      const rect = surface.element.getBoundingClientRect();
      const yours = viewportOf(rect, surface.toDiagram);
      const zoom = surface.view()?.zoom;
      return yours && zoom ? followTarget({ w: rect.width, h: rect.height }, yours, theirs, zoom) : null;
    };
    const onScreen = () => {
      const theirs = viewportOfParticipant(targetId);
      if (!theirs || theirs === stale) return;
      const target = targetFor(theirs);
      const point = target?.centre ?? followCentre(theirs);
      if (!point) return;
      const now = performance.now();
      const next = target?.zoom ?? null;
      if (next !== null) {
        const current = surface.view()?.zoom ?? next;
        if (!zooming) zoomGlide.jump({ x: current, y: 0 }, now);
        zoomGlide.push({ x: next, y: 0 }, now);
        zooming = true;
      }
      if (last && Math.abs(point.x - last.x) < 1e-6 && Math.abs(point.y - last.y) < 1e-6 && next === null) return;
      if (!last) {
        // The first centre they report: nothing to glide from yet.
        last = point;
        glide.jump(point, now);
        if (next === null) surface.centreOn(point);
        else schedule();
        return;
      }
      last = point;
      glide.push(point, now);
      schedule();
    };
    const firstScreen = refit ? undefined : viewportOfParticipant(targetId);
    const firstTarget = firstScreen ? targetFor(firstScreen) : null;
    const first = firstTarget?.centre ?? followCentre(firstScreen);
    if (first) {
      last = first;
      glide.jump(first, performance.now());
      // The first picture takes their view at once: there is nothing on screen yet to glide from.
      if (firstTarget?.zoom) surface.restore({ x: first.x, y: first.y, zoom: firstTarget.zoom });
      else surface.centreOn(first);
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

  return { following, lead: target, follow, stop };
}
