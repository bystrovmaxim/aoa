// src/lib/useHoverCard.ts
/**
 * When a card opens and closes (spec 043, FR-002, FR-003): it waits until the pointer has rested, and stays a moment after
 * the pointer has left, so moving from an element onto its card does not lose it. A person's hover and a followed
 * person's arrive here the same way.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useHoverCardsOn } from "@/lib/hoverCardsOn";
import { useMirroredFocus } from "@/rooms/focusStore";

/** How long the pointer rests before a card opens. */
export const CARD_REST_MS = 300;
/** How long a card outlives the pointer, to reach it. */
export const CARD_STAY_MS = 200;

/** ``key`` tells one subject from another. */
export function useHoverCard<T extends { key: string }>(standing: boolean) {
  // The switch is the person's own: following shows all the followed person sees, whatever it says.
  const switchedOn = useHoverCardsOn();
  const following = useMirroredFocus() !== null;
  const paused = standing || !(switchedOn || following);
  const [shown, setShown] = useState<T | null>(null);
  const shownRef = useRef<T | null>(null);
  const opening = useRef<{ key: string; timer: ReturnType<typeof setTimeout> } | null>(null);
  const closing = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** The pointer is on the card: what happens on the diagram, even a moment late, leaves it alone. */
  const held = useRef(false);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  const put = useCallback((next: T | null) => {
    shownRef.current = next;
    setShown(next);
  }, []);
  const stopOpening = useCallback(() => {
    if (opening.current) clearTimeout(opening.current.timer);
    opening.current = null;
  }, []);
  const keep = useCallback(() => {
    if (closing.current !== null) clearTimeout(closing.current);
    closing.current = null;
  }, []);
  /** The pointer came onto the card. */
  const hold = useCallback(() => {
    held.current = true;
    stopOpening();
    keep();
  }, [keep, stopOpening]);
  const leaveSoon = useCallback(() => {
    if (!shownRef.current || closing.current !== null) return;
    closing.current = setTimeout(() => {
      closing.current = null;
      put(null);
    }, CARD_STAY_MS);
  }, [put]);
  /** Close at once: a press, a wheel, Escape. */
  const close = useCallback(() => {
    held.current = false;
    stopOpening();
    keep();
    put(null);
  }, [keep, put, stopOpening]);
  /** The pointer left the card. */
  const release = useCallback(() => {
    held.current = false;
    leaveSoon();
  }, [leaveSoon]);
  /** The pointer is on ``next``, or on nothing that has a card. */
  const want = useCallback(
    (next: T | null) => {
      if (pausedRef.current || held.current) return;
      if (next === null) {
        stopOpening();
        leaveSoon();
        return;
      }
      if (next.key === shownRef.current?.key) {
        stopOpening();
        keep();
        return;
      }
      if (next.key === opening.current?.key) return;
      stopOpening();
      // The open card stands until the next one takes its place, so moving along a table never blinks.
      keep();
      opening.current = {
        key: next.key,
        timer: setTimeout(() => {
          opening.current = null;
          keep();
          put(next);
        }, CARD_REST_MS),
      };
    },
    [keep, leaveSoon, put, stopOpening],
  );
  /** Open now: a tap does not rest. */
  const wantNow = useCallback(
    (next: T) => {
      if (pausedRef.current) return;
      held.current = false;
      stopOpening();
      keep();
      put(next);
    },
    [keep, put, stopOpening],
  );

  useEffect(() => {
    if (paused) close();
  }, [paused, close]);
  useEffect(() => close, [close]);

  return { shown, want, wantNow, hold, release, close };
}
