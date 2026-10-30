// src/lib/erdCopy.ts
/**
 * Click a table or field name on the ERD to copy it.
 *
 * Names live in the cells ``buildDotSource`` makes addressable (``<g id="a_hn<i>">`` for a table name,
 * ``<g id="a_fn<i>_<n>">`` for a field name). A press counts as a click only when the pointer moved at
 * most 4 px before release, so panning the canvas by dragging never copies. When the browser refuses the
 * clipboard, the name is selected instead and the message says how to copy it by hand. In Diff (spec 038) a
 * name carries its sign (``+ region``): the bare name is copied, and a marked cell opens its card instead.
 */

const NAME_CELL = 'g[id^="a_hn"], g[id^="a_fn"]';
/** The farthest a pointer may move during a press that still counts as a click, in CSS px. */
export const COPY_CLICK_SLOP_PX = 4;

/** Select a node's text so the user can copy it with the keyboard. */
function selectText(node: Node): void {
  const selection = globalThis.getSelection?.();
  if (!selection) return;
  const range = document.createRange();
  range.selectNodeContents(node);
  selection.removeAllRanges();
  selection.addRange(range);
}

/** A name as copied: without the sign Diff writes before it. */
export function bareName(text: string): string {
  return text.trim().replace(/^[+−~] /, "");
}

/** Copy names clicked inside ``root``; ``report`` receives the message to show; a cell ``skip`` takes is left alone. */
export function bindNameCopy(root: HTMLElement, report: (message: string) => void, signal: AbortSignal, skip: (cell: Element) => boolean = () => false): void {
  let press: { x: number; y: number; cell: Element } | null = null;
  root.addEventListener(
    "pointerdown",
    (event) => {
      const cell = (event.target as Element | null)?.closest?.(NAME_CELL) ?? null;
      press = cell && !skip(cell) ? { x: event.clientX, y: event.clientY, cell } : null;
    },
    { signal },
  );
  root.addEventListener(
    "pointerup",
    (event) => {
      const started = press;
      press = null;
      if (!started) return;
      if (Math.hypot(event.clientX - started.x, event.clientY - started.y) > COPY_CLICK_SLOP_PX) return;
      const text = started.cell.querySelector("text");
      const name = text?.textContent ? bareName(text.textContent) : "";
      if (!text || !name) return;
      const refused = () => {
        selectText(text);
        report(`Selected ${name} — press Cmd/Ctrl+C`);
      };
      const clipboard = globalThis.navigator?.clipboard;
      if (!clipboard?.writeText) {
        refused();
        return;
      }
      clipboard.writeText(name).then(() => report(`Copied ${name}`), refused);
    },
    { signal },
  );
}
