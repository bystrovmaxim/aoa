// src/rooms/closeCodes.ts
/**
 * What a closed room connection means for the page: the sentence it shows and whether to try again
 * (contracts/room-protocol.md, "Opening").
 */

/** Refusals that another try would only repeat: the page leaves the room and says why. */
const FINAL: Record<number, string> = {
  4401: "This page is not allowed to join rooms.",
  4403: "This page cannot join the room.",
  4404: "This room has ended. You are looking at the diagram on your own.",
  4409: "Can't join: this room already has 20 people.",
  4422: "Names are 1 to 40 characters.",
  4502: "The service's graph cannot be built now, so the room cannot open. Try again later.",
  4503: "Too many rooms are open on this server; try again later.",
};

/** Limits of one connection: the page says so and connects again. */
const LIMITS: Record<number, string> = {
  4413: "message too large",
  4429: "too many messages",
  4008: "this tab fell behind",
};

/** Whether a connection closed with ``code`` must not be opened again. */
export function isFinalClose(code: number): boolean {
  return code in FINAL;
}

/** The sentence for a close, or ``null`` when it needs none (a lost network, a normal close). */
export function closeSentence(code: number): string | null {
  if (code in FINAL) return FINAL[code];
  if (code in LIMITS) return `The connection was closed: ${LIMITS[code]}.`;
  return null;
}
