// src/rooms/throttle.ts
/**
 * Send at most once per interval, the newest value, and only when it changed.
 *
 * A pointer may go out 20 times a second and a screen 10 times (FR-043); between two sends only the
 * newest value matters, so it is sent when the interval ends rather than queued.
 */

/** Messages a second a pointer may send. */
export const POINTER_RATE = 20;
/** Messages a second a screen position may send. */
export const VIEWPORT_RATE = 10;

export type Throttled<T> = {
  /** Offer a value; it goes out now, or as the newest one when the interval ends. */
  push(value: T): void;
  /** Drop a value waiting for its turn. */
  cancel(): void;
};

/**
 * Wrap ``send`` so it runs at most ``rate`` times a second, with the newest value, never twice
 * with an equal one (``same`` compares).
 */
export function throttle<T>(rate: number, send: (value: T) => void, same: (a: T, b: T) => boolean): Throttled<T> {
  const interval = 1000 / rate;
  let lastAt = -Infinity;
  let lastSent: T | undefined;
  let pending: T | undefined;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const flush = () => {
    timer = null;
    if (pending === undefined) return;
    const value = pending;
    pending = undefined;
    if (lastSent !== undefined && same(lastSent, value)) return;
    lastAt = Date.now();
    lastSent = value;
    send(value);
  };

  return {
    push(value) {
      pending = value;
      if (timer) return;
      const wait = lastAt + interval - Date.now();
      if (wait <= 0) flush();
      else timer = setTimeout(flush, wait);
    },
    cancel() {
      if (timer) clearTimeout(timer);
      timer = null;
      pending = undefined;
    },
  };
}
