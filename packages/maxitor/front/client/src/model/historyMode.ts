// src/model/historyMode.ts
/**
 * The seven modes of what is open (spec 037, FR-009a): whether there is a history, whether it has
 * Live, and how many versions it lists. The mode is read from the list itself, never from a count
 * a description gave, so a list that just changed changes the mode with it.
 */

/** M1 a service; M2/M3 a history without Live; M4–M6 with Live; M7 a history with nothing. */
export type HistoryMode = "M1" | "M2" | "M3" | "M4" | "M5" | "M6" | "M7";

/** The mode of what is open: ``null`` history is a running service (M1). */
export function modeOf(history: { versions: readonly unknown[]; live: string | null } | null): HistoryMode {
  if (!history) return "M1";
  const count = history.versions.length;
  if (history.live) return count >= 2 ? "M4" : count === 1 ? "M5" : "M6";
  return count >= 2 ? "M2" : count === 1 ? "M3" : "M7";
}

/** Whether the mode has a version button and a picker. */
export function hasPicker(mode: HistoryMode): boolean {
  return mode !== "M1" && mode !== "M7";
}

/** The picker's subtitle: "12 versions", "1 version and Live", "0 versions and Live". */
export function pickerSubtitle(count: number, live: boolean): string {
  return `${count} ${count === 1 ? "version" : "versions"}${live ? " and Live" : ""}`;
}
