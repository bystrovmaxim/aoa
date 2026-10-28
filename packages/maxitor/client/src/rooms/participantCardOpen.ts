// src/rooms/participantCardOpen.ts
/**
 * Whether a participant's card (or the list of the rest) is open in the room bar.
 *
 * The card drops from the circles over the top of the workspace, where the *Following <name>* pill
 * stands; while a card is open the pill steps aside, so the two never overlap — switching whom you
 * follow happens in the card, which says the same thing (spec 029, FR-052).
 */
import { useSyncExternalStore } from "react";

let open = false;
const listeners = new Set<() => void>();

export function setParticipantCardOpen(next: boolean): void {
  if (open === next) return;
  open = next;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useParticipantCardOpen(): boolean {
  return useSyncExternalStore(subscribe, () => open);
}
