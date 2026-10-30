// src/lib/erdPaint.ts
/**
 * which filter section paints the ERD's headers — Domains, Kinds or, in Diff, Changes —
 * chosen by the gear shift at the foot of the filter panel. The ERD says which sections it offers and reads the choice. One and Diff keep their own choice: Diff starts painted by Changes, One by Domains.
 */
import { useSyncExternalStore } from "react";

/** A filter section that can paint the diagram. */
export type PaintSection = "domains" | "kinds" | "changes";

type State = { sections: readonly PaintSection[]; diff: boolean; one: PaintSection; inDiff: PaintSection };

let state: State = { sections: [], diff: false, one: "domains", inDiff: "changes" };
const listeners = new Set<() => void>();

function update(next: Partial<State>): void {
  state = { ...state, ...next };
  for (const listener of listeners) listener();
}

/** The ERD on screen says which sections it offers, in the filter's order, and whether it compares two versions. */
export function setPaintSections(sections: readonly PaintSection[], diff: boolean): void {
  if (diff === state.diff && sections.join() === state.sections.join()) return;
  update({ sections, diff });
}

/** Hand the colours to ``section``. */
export function setPaintSource(section: PaintSection): void {
  update(state.diff ? { inDiff: section } : { one: section });
}

/** Take ``section`` as the choice of One or of Diff — the paint an address names, read when the page opens. */
export function presetPaint(diff: boolean, section: PaintSection): void {
  update(diff ? { inDiff: section } : { one: section });
}

/** The section that paints: the mode's choice when the diagram offers it, else its first section. */
function sourceOf(current: State): PaintSection {
  const wanted = current.diff ? current.inDiff : current.one;
  return current.sections.includes(wanted) ? wanted : (current.sections[0] ?? "domains");
}

/** What paints now and what can, followed as it changes. */
export function useErdPaint(): { sections: readonly PaintSection[]; source: PaintSection; diff: boolean; one: PaintSection; inDiff: PaintSection } {
  const current = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => state,
  );
  return { sections: current.sections, source: sourceOf(current), diff: current.diff, one: current.one, inDiff: current.inDiff };
}
