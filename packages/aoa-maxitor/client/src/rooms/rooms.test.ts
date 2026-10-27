// src/rooms/rooms.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { roomLink } from "@/lib/urlState";
import { closeSentence, isFinalClose } from "@/rooms/closeCodes";
import { RECONNECT_DELAYS, RoomConnection, type ConnectionState } from "@/rooms/connection";
import { pageKeyOf, pageLabel, selectionOfPageKey } from "@/rooms/pageKey";
import type { Participant, ServerEvent, WelcomeEvent } from "@/rooms/protocol";
import { followerCount, reduceRoom, youFirst, type RoomState } from "@/rooms/roomStore";
import { nameIsValid } from "@/rooms/useRoomSession";

const anna: Participant = { id: "anna", name: "Anna", colour: "#2563eb", page: "view=full-graph", visible: true, away: false };
const boris: Participant = { id: "boris", name: "Boris", colour: "#dc2626", page: "view=domain-erd", visible: true, away: false };

const welcome: WelcomeEvent = {
  type: "welcome",
  you: { id: "boris", colour: boris.colour },
  room: { id: "r1", source: "https://svc/graph-json", created_by: "anna", participants: [anna, boris], settings: {}, follows: { anna: null, boris: null } },
  server_build: "b1",
  fallback_page: null,
};

function run(...events: ServerEvent[]): RoomState {
  const state = events.reduce<RoomState | null>((current, event) => reduceRoom(current, event), null);
  if (!state) throw new Error("no room");
  return state;
}

describe("the room store", () => {
  it("ignores events before the welcome", () => {
    expect(reduceRoom(null, { type: "joined", participant: anna })).toBeNull();
  });

  it("takes the whole room from the welcome, you first in the row", () => {
    const state = run(welcome);
    expect(state.roomId).toBe("r1");
    expect(youFirst(state).map((p) => p.id)).toEqual(["boris", "anna"]);
  });

  it("tells who joined and who left", () => {
    const vera: Participant = { ...anna, id: "vera", name: "Vera" };
    const state = run(welcome, { type: "joined", participant: vera }, { type: "left", participant: anna });
    expect(state.participants.map((p) => p.id)).toEqual(["boris", "vera"]);
    expect(state.notices.map((n) => n.text)).toEqual(["Vera joined", "Anna left"]);
  });

  it("says nothing when someone returns within two minutes", () => {
    const state = run(welcome, { type: "presence", ...anna, away: true }, { type: "presence", ...anna, away: false });
    expect(state.notices).toEqual([]);
    expect(state.participants.find((p) => p.id === "anna")?.away).toBe(false);
  });

  it("follows a participant to their new page and name", () => {
    const state = run(welcome, { type: "presence", ...anna, page: "view=domain-erd" }, { type: "renamed", participant: "anna", name: "Anna K" });
    expect(state.participants.find((p) => p.id === "anna")).toMatchObject({ page: "view=domain-erd", name: "Anna K" });
  });

  it("keeps the last value of a setting", () => {
    const state = run(
      welcome,
      { type: "setting", page: "view=domain-erd", name: "layout", value: "gv-neato", by: "anna" },
      { type: "setting", page: "view=domain-erd", name: "layout", value: "gv-circo", by: "boris" },
      { type: "setting", page: "view=domain-erd", name: "one_hop", value: true, by: "boris" },
    );
    expect(state.settings).toEqual({ "view=domain-erd": { layout: "gv-circo", one_hop: true } });
  });

  it("counts followers and shows a refusal once", () => {
    const state = run(
      welcome,
      { type: "follows", follows: { anna: "boris", boris: null } },
      { type: "follow_refused", target: "anna", reason: "they already follow you, directly or through others" },
    );
    expect(followerCount(state, "boris")).toBe(1);
    expect(state.notices.at(-1)?.text).toBe("they already follow you, directly or through others");
  });

  it("counts every rebuild of the room's graph", () => {
    expect(run(welcome, { type: "graph_changed", fingerprint: "f2" }).graphVersion).toBe(1);
  });
});

describe("close codes", () => {
  it("turns every refusal into its sentence and never retries it", () => {
    expect(closeSentence(4404)).toBe("This room has ended. You are looking at the diagram on your own.");
    expect(closeSentence(4409)).toBe("Can't join: this room already has 20 people.");
    expect(closeSentence(4403)).toBe("This page cannot join the room.");
    for (const code of [4403, 4404, 4409, 4422, 4502, 4503]) expect(isFinalClose(code)).toBe(true);
  });

  it("names the adapter's limits and connects again after them", () => {
    expect(closeSentence(4429)).toBe("The connection was closed: too many messages.");
    expect(isFinalClose(4429)).toBe(false);
    expect(closeSentence(1006)).toBeNull();
  });
});

describe("the copied address", () => {
  it("is the page being looked at, with the room", () => {
    const current = "https://maxitor.test/?source=https%3A%2F%2Fsvc%2Fgraph-json&view=domain-erd&domain=players";
    const link = new URL(roomLink(current, "q8VZ0kR3b1xT9mWc4LhY2A"));
    expect(link.searchParams.get("view")).toBe("domain-erd");
    expect(link.searchParams.get("domain")).toBe("players");
    expect(link.searchParams.get("source")).toBe("https://svc/graph-json");
    expect(link.searchParams.get("room")).toBe("q8VZ0kR3b1xT9mWc4LhY2A");
  });
});

describe("page keys", () => {
  it("are the server's keys, in the fixed parameter order", () => {
    expect(pageKeyOf({ kind: "interchange_graph" })).toBe("view=full-graph");
    expect(pageKeyOf({ kind: "erd", qualifier: "d 1" })).toBe("view=domain-erd&domain=d+1");
    expect(pageKeyOf({ kind: "lifecycle_fsm", lifecycle_graph_node_id: "n", host_entity_interchange_id: "h" })).toBe("view=lifecycle-fsm&node=n&host=h");
    expect(selectionOfPageKey("view=use-case&domain=x")).toEqual({ kind: "use_case", domain_qualifier: "x" });
  });

  it("read as words", () => {
    expect(pageLabel("view=domain-erd", null)).toBe("ERD · all domains");
    expect(pageLabel("view=full-graph", null)).toBe("Full graph");
  });
});

describe("names", () => {
  it("are 1 to 40 characters after trimming", () => {
    expect(nameIsValid("  Anna ")).toBe(true);
    expect(nameIsValid("   ")).toBe(false);
    expect(nameIsValid("x".repeat(40))).toBe(true);
    expect(nameIsValid("x".repeat(41))).toBe(false);
  });
});

/** A WebSocket stand-in the test closes and feeds by hand. */
class FakeSocket {
  static instances: FakeSocket[] = [];
  static OPEN = 1;
  readyState = 1;
  sent: string[] = [];
  onmessage: ((message: { data: string }) => void) | null = null;
  onclose: ((closed: { code: number; reason: string }) => void) | null = null;
  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
  }
  serverCloses(code: number, reason = "") {
    this.onclose?.({ code, reason });
  }
  serverSends(event: ServerEvent) {
    this.onmessage?.({ data: JSON.stringify(event) });
  }
}

describe("the room connection", () => {
  let states: ConnectionState[];

  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
    states = [];
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function connect(room: string, source?: string): RoomConnection {
    const connection = new RoomConnection({ room, source, name: "Anna", page: "view=full-graph", onEvent: () => undefined, onState: (s) => states.push(s) });
    connection.open();
    return connection;
  }

  it("opens a new room with the source, then reconnects to the room's own id", () => {
    connect("new", "https://svc/graph-json");
    const first = new URL(FakeSocket.instances[0].url);
    expect(first.pathname).toBe("/api/v1/rooms/new/live");
    expect(first.searchParams.get("source")).toBe("https://svc/graph-json");
    expect(first.searchParams.get("participant_name")).toBe("Anna");
    expect(first.searchParams.get("start_page")).toBe("view=full-graph");
    FakeSocket.instances[0].serverSends({ ...welcome, room: { ...welcome.room, id: "r9" } });
    FakeSocket.instances[0].serverCloses(1006);
    vi.advanceTimersByTime(RECONNECT_DELAYS[0] * 1000);
    const second = new URL(FakeSocket.instances[1].url);
    expect(second.pathname).toBe("/api/v1/rooms/r9/live");
    expect(second.searchParams.get("participant")).toBe(first.searchParams.get("participant"));
  });

  it("waits longer after each lost connection, up to fifteen seconds", () => {
    connect("r1");
    for (const delay of [1, 2, 4, 8, 15, 15]) {
      FakeSocket.instances.at(-1)!.serverCloses(1006);
      const count = FakeSocket.instances.length;
      vi.advanceTimersByTime(delay * 1000 - 1);
      expect(FakeSocket.instances.length).toBe(count);
      vi.advanceTimersByTime(1);
      expect(FakeSocket.instances.length).toBe(count + 1);
    }
    expect(states).toContainEqual({ kind: "reconnecting" });
  });

  it("never reconnects after a refusal or after leaving", () => {
    connect("r1");
    FakeSocket.instances[0].serverCloses(4404, "room ended");
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.instances).toHaveLength(1);
    expect(states.at(-1)).toEqual({ kind: "closed", code: 4404, reason: "room ended" });

    connect("r2");
    FakeSocket.instances[1].serverCloses(1000, "left the room");
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.instances).toHaveLength(2);
  });
});
