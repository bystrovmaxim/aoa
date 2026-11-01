// src/lib/cardFieldsOpen.ts
/**
 * Whether a table's card shows its fields (spec 043, FR-006c): hidden at first, and the person's last choice from then on,
 * for every table. A convenience of this browser: it lives here, and a browser that refuses storage simply starts hidden.
 */
const KEY = "maxitor:cardFieldsOpen";

export function cardFieldsOpen(): boolean {
  try {
    return globalThis.localStorage?.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function rememberCardFieldsOpen(open: boolean): void {
  try {
    globalThis.localStorage?.setItem(KEY, open ? "1" : "0");
  } catch {
    // Nowhere to keep it: the choice lasts as long as the card.
  }
}
