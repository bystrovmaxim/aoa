// src/rooms/seed.ts
/**
 * The messages a tab sends right after the welcome of a room it opened: its own value of every page
 * setting, one setting per message (spec 029, FR-001). One per setting keeps every message far below
 * the room's size limit; a single value too large to send — a very long list — is left out, and that
 * setting starts at its default rather than closing the connection with 4413.
 */
import { MAX_MESSAGE_BYTES, type ClientMessage } from "@/rooms/protocol";

const encoder = new TextEncoder();

export function seedMessages(own: Record<string, Record<string, unknown>>): ClientMessage[] {
  const messages: ClientMessage[] = [];
  for (const [page, values] of Object.entries(own)) {
    for (const [name, value] of Object.entries(values)) {
      const message: ClientMessage = { type: "seed", page, settings: { [name]: value } };
      if (encoder.encode(JSON.stringify(message)).length <= MAX_MESSAGE_BYTES) messages.push(message);
    }
  }
  return messages;
}
