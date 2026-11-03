// src/rooms/connection.ts
/**
 * One room connection per tab, to ``/api/v1/rooms/{id}/live``.
 *
 * It opens with the participant's id (kept per room in ``localStorage``, so every tab of one browser
 * is one participant), the tab's id (``sessionStorage``), the name and the page. A lost connection is
 * opened again after 1, 2, 4, 8 and then every 15 s; a refusal (contracts/room-protocol.md) is final.
 * Opening ``new`` with a source creates the room; every reconnect then goes to the room's own id.
 */
import { apiUrl } from "@/api/client";
import { isFinalClose } from "@/rooms/closeCodes";
import type { ClientMessage, ServerEvent } from "@/rooms/protocol";

export type ConnectionState =
  | { kind: "connecting" }
  | { kind: "open" }
  | { kind: "reconnecting" }
  | { kind: "closed"; code: number; reason: string };

export type RoomConnectionOptions = {
  /** The room's id, or ``"new"`` with ``source`` to open one. */
  room: string;
  source?: string;
  /** A room on a history (spec 037): its name and the version a new room opens on, never its key. */
  history?: { name: string; version: string | null; versionA?: string | null; view?: string };
  /** For a private history: a fresh one-use ticket before every connection, the key's stand-in on the socket. */
  ticket?: () => Promise<string | null>;
  name: string;
  page: string;
  onEvent: (event: ServerEvent) => void;
  onState: (state: ConnectionState) => void;
};

/** The pauses before each reconnect, in seconds; the last one repeats. */
export const RECONNECT_DELAYS = [1, 2, 4, 8, 15];

/** The reason the server closes a participant's tabs with when they leave (``RoomRegistry``). */
export const LEFT_REASON = "left the room";

const TAB_KEY = "maxitor.tab";
const participantKey = (room: string) => `maxitor.room.${room}.participant`;

function randomId(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function stored(storage: Storage, key: string): string {
  let value: string | null = null;
  try {
    value = storage.getItem(key);
  } catch {
    // Storage may be unavailable (a private window); a fresh id per page load still works.
  }
  if (value) return value;
  const fresh = randomId();
  try {
    storage.setItem(key, fresh);
  } catch {
    // Ignored for the same reason.
  }
  return fresh;
}

/** This tab's id, the same across reloads of the tab. */
export function tabId(): string {
  return stored(sessionStorage, TAB_KEY);
}

/** This browser's participant id in ``room``; ``new`` gets a fresh one, kept once the room has an id. */
export function participantId(room: string): string {
  return room === "new" ? randomId() : stored(localStorage, participantKey(room));
}

/** Remember the participant id a new room was opened with, under the room's id. */
export function rememberParticipant(room: string, participant: string): void {
  try {
    localStorage.setItem(participantKey(room), participant);
  } catch {
    // Without storage, another tab simply joins as another participant.
  }
}

/** The WebSocket address of ``path``: the API's own host, or this page's when the API is proxied. */
export function socketUrl(path: string, query: URLSearchParams): string {
  const http = new URL(apiUrl(path), window.location.href);
  http.protocol = http.protocol === "https:" ? "wss:" : "ws:";
  http.search = query.toString();
  return http.toString();
}

export class RoomConnection {
  private socket: WebSocket | null = null;
  private attempt = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private room: string;
  private readonly participant: string;
  private readonly options: RoomConnectionOptions;
  private page: string;

  constructor(options: RoomConnectionOptions) {
    this.options = options;
    this.room = options.room;
    this.page = options.page;
    this.participant = participantId(options.room);
  }

  /** The participant id this connection joins with. */
  get participantId(): string {
    return this.participant;
  }

  open(): void {
    this.stopped = false;
    this.options.onState({ kind: this.attempt === 0 ? "connecting" : "reconnecting" });
    if (this.options.ticket) {
      // A ticket is used up by one connection, so every connection, a reconnect included, asks for its own.
      void this.options.ticket().then(
        (ticket) => this.connect(ticket),
        () => this.connect(null),
      );
      return;
    }
    this.connect(null);
  }

  private connect(ticket: string | null): void {
    if (this.stopped) return;
    const query = new URLSearchParams({
      participant: this.participant,
      tab: tabId(),
      participant_name: this.options.name,
      start_page: this.page,
    });
    if (this.room === "new" && this.options.history) {
      query.set("history", this.options.history.name);
      if (this.options.history.version) query.set("version", this.options.history.version);
      if (this.options.history.version && this.options.history.versionA) query.set("version_a", this.options.history.versionA);
      if (this.options.history.view === "split") query.set("opening_view", "split");
    } else if (this.room === "new" && this.options.source) query.set("source", this.options.source);
    if (ticket) query.set("ticket", ticket);
    const socket = new WebSocket(socketUrl(`/api/v1/rooms/${encodeURIComponent(this.room)}/live`, query));
    this.socket = socket;
    socket.onmessage = (message) => this.receive(message.data);
    socket.onclose = (closed) => this.closed(socket, closed.code, closed.reason);
  }

  /** Send ``message`` when the connection is open; a message sent while reconnecting is dropped. */
  send(message: ClientMessage): void {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(message));
  }

  /** The page a reconnect starts on: the tab's current one. */
  setPage(page: string): void {
    this.page = page;
  }

  /** Close for good: after **Leave room**, a refusal, or the page going away. */
  close(): void {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.socket?.close(1000);
    this.socket = null;
  }

  private receive(data: unknown): void {
    if (typeof data !== "string") return;
    let event: ServerEvent;
    try {
      event = JSON.parse(data) as ServerEvent;
    } catch {
      return;
    }
    if (event.type === "welcome") {
      this.attempt = 0;
      if (this.room === "new") {
        this.room = event.room.id;
        rememberParticipant(this.room, this.participant);
      }
      this.options.onState({ kind: "open" });
    }
    this.options.onEvent(event);
  }

  private closed(socket: WebSocket, code: number, reason: string): void {
    if (socket !== this.socket) return;
    this.socket = null;
    if (this.stopped) return;
    // Another tab of this participant pressed Leave room: the server closes every tab of theirs.
    if (isFinalClose(code) || (code === 1000 && reason === LEFT_REASON)) {
      this.stopped = true;
      this.options.onState({ kind: "closed", code, reason });
      return;
    }
    this.options.onState({ kind: "reconnecting" });
    const delay = RECONNECT_DELAYS[Math.min(this.attempt, RECONNECT_DELAYS.length - 1)];
    this.attempt += 1;
    this.timer = setTimeout(() => this.open(), delay * 1000);
  }
}
