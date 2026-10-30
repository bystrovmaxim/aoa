// src/lib/stepKeys.ts
/**
 * Shift + ← → step the version shown, anywhere on the page (spec 038): one step older or newer, as the version button's
 * arrows do. Not while one types, nor on a track's handle, whose keys move that handle.
 */

/** The step a key press asks for, or ``null`` when it asks for none. */
export function stepOfKey(event: Pick<KeyboardEvent, "key" | "shiftKey" | "altKey" | "ctrlKey" | "metaKey" | "target">): -1 | 1 | null {
  if (!event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return null;
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return null;
  const target = event.target as Element | null;
  if (target?.closest?.('input, textarea, select, [contenteditable="true"], [role="slider"]')) return null;
  return event.key === "ArrowLeft" ? -1 : 1;
}
