// src/lib/topCentre.ts
/**
 * The room a page keeps at the top centre of its canvas (spec 055): the events explorer's mode pill stands there, so
 * a banner that would cover it stands below it instead, as far from it as the pill is from the top.
 */
import { useEffect, useSyncExternalStore } from "react";

let reserved = 0;
const listeners = new Set<() => void>();

function set(px: number): void {
  reserved = px;
  for (const listener of listeners) listener();
}

/** Keep ``px`` at the top centre while the calling component is on screen. */
export function useReserveTopCentre(px: number): void {
  useEffect(() => {
    set(px);
    return () => set(0);
  }, [px]);
}

/** The room kept at the top centre now: 0 when nothing stands there. */
export function useTopCentreReserved(): number {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => reserved,
  );
}
