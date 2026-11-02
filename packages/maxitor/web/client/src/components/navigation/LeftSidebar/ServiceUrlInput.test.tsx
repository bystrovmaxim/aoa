// src/components/navigation/LeftSidebar/ServiceUrlInput.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { KEY_DOTS } from "@/lib/historyAddress";
import { getRecent, pushRecent } from "@/lib/serviceUrlHistory";
import { ServiceUrlInput } from "./ServiceUrlInput";

const NAME = "https://repo-graph-port.aoa.run/api/v1/history/orders";
const KEY = "a-key-of-forty-three-characters-0123456789";
const OPENED = { name: NAME, title: "orders", host: "github", repository: "owner/service", live: "https://orders.example", versions: [], count: 12, room_ticket: "t" };

let sent: { url: string; headers: Record<string, string> }[] = [];

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  sent = [];
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    sent.push({ url: String(input), headers: (init?.headers ?? {}) as Record<string, string> });
    return { ok: true, status: 200, json: async () => OPENED, headers: new Headers() } as Response;
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function field(): HTMLInputElement {
  return screen.getByLabelText("Service or history address") as HTMLInputElement;
}

describe("the address field", () => {
  it("shows a key as eight dots while not edited, and the eye shows and hides it", () => {
    render(<ServiceUrlInput onLoaded={() => undefined} />);
    fireEvent.focus(field());
    fireEvent.change(field(), { target: { value: `${NAME}#key=${KEY}` } });
    expect(field().value).toContain(KEY);
    fireEvent.blur(field());
    expect(field().value).toBe(`${NAME}#key=${KEY_DOTS}`);
    fireEvent.click(screen.getByRole("button", { name: "Show the key" }));
    expect(field().value).toContain(KEY);
    fireEvent.click(screen.getByRole("button", { name: "Hide the key" }));
    expect(field().value).not.toContain(KEY);
  });

  it("hides a revealed key again when the field loses focus", () => {
    render(<ServiceUrlInput onLoaded={() => undefined} />);
    fireEvent.change(field(), { target: { value: `${NAME}#key=${KEY}` } });
    fireEvent.click(screen.getByRole("button", { name: "Show the key" }));
    expect(field().value).toContain(KEY);
    fireEvent.focus(field());
    fireEvent.blur(field());
    expect(field().value).not.toContain(KEY);
  });

  it("opens a history with its key in a header only, and records what it turned out to be", async () => {
    const opened = vi.fn();
    render(<ServiceUrlInput onLoaded={() => undefined} onHistoryOpened={opened} />);
    fireEvent.change(field(), { target: { value: `${NAME}#key=${KEY}` } });
    fireEvent.keyDown(field(), { key: "Enter" });
    await vi.waitFor(() => expect(opened).toHaveBeenCalled());
    expect(sent[0].url).not.toContain(KEY);
    expect(sent[0].headers["X-Maxitor-History-Key"]).toBe(KEY);
    expect(getRecent()[0]).toMatchObject({ kind: "history", name: "orders", versions: 12, live: true });
  });
});

describe("Recent", () => {
  it("shows each address with its key as dots and says what it was", () => {
    pushRecent({ address: "http://127.0.0.1:8001", kind: "service" });
    pushRecent({ address: `${NAME}#key=${KEY}`, kind: "history", name: "orders", versions: 12, live: true });
    render(<ServiceUrlInput onLoaded={() => undefined} />);
    expect(screen.queryByText(new RegExp(KEY))).toBeNull();
    expect(screen.getByText(`${NAME}#key=${KEY_DOTS}`)).toBeTruthy();
    expect(screen.getByText("History · orders · 12 versions and Live")).toBeTruthy();
    expect(screen.getByText("Live service · one graph")).toBeTruthy();
  });

  it("removes a record, and its key with it", () => {
    pushRecent({ address: `${NAME}#key=${KEY}`, kind: "history", name: "orders", versions: 1 });
    render(<ServiceUrlInput onLoaded={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Remove from Recent" }));
    expect(getRecent()).toEqual([]);
    expect(localStorage.getItem("maxitor:serviceUrlHistory") ?? "").not.toContain(KEY);
    expect(screen.queryByText(`${NAME}#key=${KEY_DOTS}`)).toBeNull();
  });

  it("reads records written before histories as services", () => {
    localStorage.setItem("maxitor:serviceUrlHistory", JSON.stringify(["http://127.0.0.1:8001"]));
    expect(getRecent()).toEqual([{ address: "http://127.0.0.1:8001", kind: "service" }]);
  });
});
