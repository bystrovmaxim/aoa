// src/lib/stepKeys.ts
/**
 * Shift + ← → step the version shown, anywhere on the page (spec 038): one step older or newer, as the version button's
 * arrows do. Shift + ↑ ↓ step through a comparison's changes, as the arrows of the control beside it do (spec 040). Not
 * while one types, nor on a track's handle, whose keys move that handle.
 */

type StepKey = Pick<KeyboardEvent, "key" | "shiftKey" | "altKey" | "ctrlKey" | "metaKey" | "target">;

/** The step a press asks for between two keys, or ``null`` when it asks for none. */
function stepBetween(event: StepKey, back: string, on: string): -1 | 1 | null {
  if (!event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return null;
  if (event.key !== back && event.key !== on) return null;
  const target = event.target as Element | null;
  if (target?.closest?.('input, textarea, select, [contenteditable="true"], [role="slider"]')) return null;
  return event.key === back ? -1 : 1;
}

/** The step through versions a key press asks for, or ``null`` when it asks for none. */
export function stepOfKey(event: StepKey): -1 | 1 | null {
  return stepBetween(event, "ArrowLeft", "ArrowRight");
}

/** The step through changes a key press asks for, or ``null`` when it asks for none. */
export function changeStepOfKey(event: StepKey): -1 | 1 | null {
  return stepBetween(event, "ArrowUp", "ArrowDown");
}
