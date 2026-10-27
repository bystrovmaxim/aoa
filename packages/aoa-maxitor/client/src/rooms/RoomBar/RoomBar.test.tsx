// src/rooms/RoomBar/RoomBar.test.tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RoomBar } from "@/rooms/RoomBar";
import type { RoomState } from "@/rooms/roomStore";
import type { RoomSession } from "@/rooms/useRoomSession";

const room: RoomState = {
  roomId: "q8VZ0kR3b1xT9mWc4LhY2A",
  source: "https://svc/graph-json",
  youId: "anna",
  createdBy: "anna",
  participants: [
    { id: "anna", name: "Anna", colour: "#2563eb", page: "view=domain-erd", visible: true, away: false },
    { id: "boris", name: "Boris Petrov", colour: "#dc2626", page: "view=full-graph", visible: false, away: false },
  ],
  settings: {},
  follows: { anna: null, boris: "anna" },
  serverBuild: "",
  fallbackPage: null,
  notices: [],
  graphVersion: 0,
};

function session(overrides: Partial<RoomSession> = {}): RoomSession {
  return {
    room,
    connection: { kind: "open" },
    dialog: null,
    banner: null,
    pageNotice: null,
    inviteOpen: false,
    hidePointers: false,
    toggleHidePointers: vi.fn(),
    pointersOff: false,
    roomId: room.roomId,
    inRoom: true,
    requestOpen: vi.fn(),
    requestRename: vi.fn(),
    cancelDialog: vi.fn(),
    confirmName: vi.fn(),
    leave: vi.fn(),
    send: vi.fn(),
    closeInvite: vi.fn(),
    openInvite: vi.fn(),
    dismissBanner: vi.fn(),
    setPageSetting: vi.fn(),
    dismissPageNotice: vi.fn(),
    ...overrides,
  };
}

let writeText: ReturnType<typeof vi.fn>;

beforeEach(() => {
  writeText = vi.fn(async () => undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
});

afterEach(() => cleanup());

describe("RoomBar", () => {
  it("offers Open room outside a room", () => {
    const requestOpen = vi.fn();
    render(<RoomBar session={session({ room: null, inRoom: false, requestOpen })} page={null} pageLabel={() => ""} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Open room" }));
    expect(requestOpen).toHaveBeenCalled();
  });

  it("copies the page being looked at, not the one the room was opened on", async () => {
    window.history.replaceState(null, "", "/?source=https%3A%2F%2Fsvc%2Fgraph-json&view=domain-erd&room=q8VZ0kR3b1xT9mWc4LhY2A");
    const { rerender } = render(<RoomBar session={session()} page="view=domain-erd" pageLabel={() => ""} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    window.history.replaceState(null, "", "/?source=https%3A%2F%2Fsvc%2Fgraph-json&view=use-case&domain=players&room=q8VZ0kR3b1xT9mWc4LhY2A");
    rerender(<RoomBar session={session()} page="view=use-case&domain=players" pageLabel={() => ""} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    const copied = new URL(writeText.mock.calls[0][0] as string);
    expect(copied.searchParams.get("view")).toBe("use-case");
    expect(copied.searchParams.get("domain")).toBe("players");
    expect(copied.searchParams.get("room")).toBe(room.roomId);
  });

  it("labels every circle with the full name and page, yours first", () => {
    render(<RoomBar session={session()} page="view=domain-erd" pageLabel={(page) => `page ${page}`} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    const circles = screen.getAllByRole("button", { name: / — page / });
    expect(circles.map((c) => c.getAttribute("aria-label"))).toEqual([
      "Anna (you) — page view=domain-erd",
      "Boris Petrov — page view=full-graph",
    ]);
    expect(screen.getByLabelText("1 following you")).toBeTruthy();
  });

  it("opens a circle's card with Enter and closes it with Esc", async () => {
    render(<RoomBar session={session()} page="view=domain-erd" pageLabel={() => "Full graph"} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    const boris = screen.getByRole("button", { name: /Boris Petrov/ });
    boris.focus();
    fireEvent.click(boris);
    expect(await screen.findByRole("dialog", { name: "Boris Petrov" })).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Boris Petrov" })).toBeNull());
  });

  it("shows three circles on a phone and folds the rest into +N", () => {
    const many = ["a", "b", "c", "d", "e"].map((id) => ({ ...room.participants[0], id, name: id.toUpperCase() }));
    render(
      <RoomBar session={session({ room: { ...room, youId: "a", participants: many } })} page={null} pageLabel={() => "Full graph"} canOpen compact onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "3 more in this room" })).toBeTruthy();
    expect(screen.getAllByRole("button", { name: / — / })).toHaveLength(2);
  });

  it("leaves with Leave room", () => {
    const leave = vi.fn();
    render(<RoomBar session={session({ leave })} page={null} pageLabel={() => ""} canOpen compact={false} onGoTo={vi.fn()} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Leave room" }));
    expect(leave).toHaveBeenCalled();
  });

  it("goes to someone on a click of their circle, and from their card", async () => {
    const onGoTo = vi.fn();
    render(<RoomBar session={session()} page="view=domain-erd" pageLabel={() => "Full graph"} canOpen compact={false} onGoTo={onGoTo} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    const boris = screen.getByRole("button", { name: /Boris Petrov/ });
    fireEvent.click(boris, { detail: 1 });
    expect(onGoTo).toHaveBeenCalledWith("boris", "view=full-graph");
    fireEvent.click(boris, { detail: 0 });
    fireEvent.click(await screen.findByRole("button", { name: "Go to Boris" }));
    expect(onGoTo).toHaveBeenCalledTimes(2);
  });

  it("opens your own card, not a go-to, on a click of your circle", async () => {
    const onGoTo = vi.fn();
    render(<RoomBar session={session()} page="view=domain-erd" pageLabel={() => "ERD"} canOpen compact={false} onGoTo={onGoTo} onFollow={vi.fn()} onStopFollowing={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Anna \(you\)/ }), { detail: 1 });
    expect(await screen.findByRole("button", { name: "Change name" })).toBeTruthy();
    expect(onGoTo).not.toHaveBeenCalled();
  });
});
