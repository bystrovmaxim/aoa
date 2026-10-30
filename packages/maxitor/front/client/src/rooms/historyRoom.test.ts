// src/rooms/historyRoom.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RoomConnection } from "./connection";
import type { ServerEvent } from "./protocol";

/** A WebSocket stand-in that remembers its address and lets the test send it events. */
class FakeSocket {
  static instances: FakeSocket[] = [];
  static OPEN = 1;
  readyState = 1;
  onmessage: ((message: { data: string }) => void) | null = null;
  onclose: ((closed: { code: number; reason: string }) => void) | null = null;
  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }
  send() {}
  close() {
    this.readyState = 3;
  }
  serverSends(event: ServerEvent) {
    this.onmessage?.({ data: JSON.stringify(event) });
  }
}

const NAME = "https://port/api/v1/history/orders";

beforeEach(() => {
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});

afterEach(() => vi.unstubAllGlobals());

describe("a room on a private history", () => {
  it("opens with the history, its version and a fresh ticket — never the key, never a source", async () => {
    const tickets = ["ticket-1", "ticket-2"];
    const connection = new RoomConnection({
      room: "new",
      history: { name: NAME, version: "abcdefabcdef" },
      ticket: async () => tickets.shift() ?? null,
      name: "Anna",
      page: "view=full-graph",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    connection.open();
    await vi.waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
    const query = new URL(FakeSocket.instances[0].url).searchParams;
    expect([query.get("history"), query.get("version"), query.get("ticket"), query.get("source")]).toEqual([NAME, "abcdefabcdef", "ticket-1", null]);
    expect(FakeSocket.instances[0].url).not.toContain("key");
    connection.open();
    await vi.waitFor(() => expect(FakeSocket.instances).toHaveLength(2));
    expect(new URL(FakeSocket.instances[1].url).searchParams.get("ticket")).toBe("ticket-2");
  });

  it("hands the room's version events to the page", async () => {
    const events: ServerEvent[] = [];
    const connection = new RoomConnection({ room: "r1", history: { name: NAME, version: null }, name: "Anna", page: "", onEvent: (event) => events.push(event), onState: () => undefined });
    connection.open();
    FakeSocket.instances[0].serverSends({ type: "version", b: "abcdefabcdef", by: "boris" });
    FakeSocket.instances[0].serverSends({ type: "history_changed" });
    expect(events.map((event) => event.type)).toEqual(["version", "history_changed"]);
  });
});
