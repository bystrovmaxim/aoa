// src/lib/sidebarMemory.ts
/**
 * What the left panel holds open, kept in this browser so that a reload finds it as it was (spec 044): the open
 * branches and the switch to what changed. In ``localStorage``, not a cookie: a hundred open domains by their full
 * names do not fit in one, and nothing here is for the server. It may be empty or refused; the panel then opens closed.
 */

const KEY = "maxitor.left-panel";

export type SidebarMemory = { open: string[]; changedOnly: boolean };

const RAIL_KEY = "maxitor.left-panel-rail";

/** Whether the panel stood as the narrow rail. */
export function readSidebarRail(): boolean {
  try {
    return localStorage.getItem(RAIL_KEY) === "1";
  } catch {
    return false;
  }
}

/** Keep whether the panel stands as the narrow rail. */
export function writeSidebarRail(collapsed: boolean): void {
  try {
    localStorage.setItem(RAIL_KEY, collapsed ? "1" : "0");
  } catch {
    // A browser that refuses simply forgets.
  }
}

/** What this browser kept. */
export function readSidebarMemory(): SidebarMemory {
  try {
    const kept = JSON.parse(localStorage.getItem(KEY) ?? "null") as Partial<SidebarMemory> | null;
    const open = Array.isArray(kept?.open) ? kept.open.filter((id): id is string => typeof id === "string") : [];
    return { open, changedOnly: kept?.changedOnly === true };
  } catch {
    return { open: [], changedOnly: false };
  }
}

/** Keep the panel's state; a browser that refuses simply forgets. */
export function writeSidebarMemory(memory: SidebarMemory): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(memory));
  } catch {
    // Private windows and cleared site data refuse: the panel works without it.
  }
}
