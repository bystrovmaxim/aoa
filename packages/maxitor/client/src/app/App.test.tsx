// src/app/App.test.tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "@/app/App";
import { setActiveSource } from "@/api/client";

// The real diagram engines pull G6 and the Graphviz wasm at import time. The full-graph viewer is
// replaced by a stand-in that still performs its read, so the test sees the first diagram request.
vi.mock("@/components/diagrams/FullGraphViewer", async () => {
  const { useEffect } = await import("react");
  const { fullGraph } = await import("@/api/fullGraph");
  return {
    FullGraphViewer: () => {
      useEffect(() => {
        void fullGraph().catch(() => undefined);
      }, []);
      return null;
    },
  };
});
vi.mock("@/components/diagrams/ErdViewer", () => ({ ErdViewer: () => null }));
vi.mock("@/components/diagrams/LifecycleFsmViewer", () => ({ LifecycleFsmViewer: () => null }));
vi.mock("@/components/diagrams/UseCaseDiagramViewer", () => ({ UseCaseDiagramViewer: () => null }));

const SOURCE = "https://service.test/graph-json";
const EMPTY_SIDEBAR = { level1_nodes: [], level2_diagrams: [], level2_nodes: [], level3_diagrams: [] };
const FULL_GRAPH = { payload: { nodes: [], edges: [], node_type_map: {}, domain_color_map: {} } };

type Call = { url: string; method: string };

let calls: Call[] = [];
let lastBody: string | null = null;
let replies: { load: () => Response; sidebar: () => Response; fullGraph: () => Response };

function json(body: unknown, status = 200): Response {
  return {
    ok: status < 400,
    status,
    headers: new Headers(),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function busy(seconds = 5): Response {
  return {
    ok: false,
    status: 503,
    headers: new Headers({ "Retry-After": String(seconds) }),
    json: async () => ({ detail: "Maxitor is busy building other graphs; try again shortly." }),
    text: async () => "busy",
  } as unknown as Response;
}

function deepLink(url = `/?source=${encodeURIComponent(SOURCE)}&view=full-graph`) {
  window.history.replaceState({}, "", url);
}

beforeEach(() => {
  calls = [];
  setActiveSource(null);
  replies = {
    load: () => json({ status: "ok" }),
    sidebar: () => json(EMPTY_SIDEBAR),
    fullGraph: () => json(FULL_GRAPH),
  };
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    calls.push({ url, method });
    if (method === "POST") lastBody = String(init?.body ?? "");
    if (url.startsWith("/api/load")) return replies.load();
    if (url.startsWith("/api/sidebar")) return replies.sidebar();
    if (url.startsWith("/api/v1/full-graph")) return replies.fullGraph();
    return json({});
  });
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

function sidebarCalls(): Call[] {
  return calls.filter((c) => c.url.startsWith("/api/sidebar"));
}

function postCalls(): Call[] {
  return calls.filter((c) => c.method === "POST" && c.url.startsWith("/api/load"));
}

describe("a deep link", () => {
  it("reads without reloading, and every read names the link's source", async () => {
    deepLink();

    render(<App />);

    await waitFor(() => expect(calls.some((c) => c.url.startsWith("/api/v1/full-graph"))).toBe(true));

    expect(postCalls()).toHaveLength(0);
    expect(calls[0].method).toBe("GET");
    // Every graph read; ``/api/meta/app-info`` asks which Maxitor runs and needs no source.
    for (const read of calls.filter((c) => c.method === "GET" && !c.url.startsWith("/api/meta/"))) {
      expect(new URL(read.url, "http://localhost").searchParams.get("source")).toBe(SOURCE);
    }
  });

  it("falls back to the prompt when the source cannot be built", async () => {
    replies.sidebar = () => json({ detail: "service is down" }, 422);

    render(<App />);

    await waitFor(() => expect(screen.getByText("AOA Service URL")).toBeTruthy());
    expect(screen.queryByLabelText("Reload from service")).toBeNull();
  });

  it("treats a busy server as a retry, never as a bad source", async () => {
    replies.sidebar = () => busy(60);
    deepLink();

    render(<App />);

    await waitFor(() => expect(screen.getByText(/busy/i)).toBeTruthy());
    expect(screen.queryByText("AOA Service URL")).toBeNull();
  });
});

describe("a typed source", () => {
  it("sends exactly one POST /api/load, then reads its sidebar", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: SOURCE } });
    fireEvent.click(screen.getByRole("button", { name: "Load graph" }));

    await waitFor(() => expect(postCalls()).toHaveLength(1));
    await waitFor(() => expect(sidebarCalls()).toHaveLength(1));
    expect(postCalls()[0].url).toBe("/api/load");
    expect(new URL(sidebarCalls()[0].url, "http://localhost").searchParams.get("source")).toBe(SOURCE);
  });
});

describe("the reload button", () => {
  it("sends one reload for the open source, then reads the sidebar again and keeps the URL", async () => {
    deepLink();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reload from service" })).toBeTruthy());
    const urlBefore = window.location.search;

    fireEvent.click(screen.getByRole("button", { name: "Reload from service" }));

    await waitFor(() => expect(postCalls()).toHaveLength(1));
    await waitFor(() => expect(sidebarCalls()).toHaveLength(2));
    expect(lastBody && JSON.parse(lastBody).service_url).toBe(SOURCE);
    expect(window.location.search).toBe(urlBefore);
    expect(postCalls()).toHaveLength(1);
  });

  it("reports a busy reload without retrying it and keeps the source", async () => {
    replies.load = () => busy(5);
    deepLink();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Reload from service" })).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: "Reload from service" }));

    await waitFor(() => expect(screen.getByText(/Reload failed/)).toBeTruthy());
    expect(postCalls()).toHaveLength(1);
    expect(sidebarCalls()).toHaveLength(1);  // the failed reload reads nothing again
    expect(screen.queryByText("AOA Service URL")).toBeNull();
  });
});

describe("leaving a source", () => {
  it("sends nothing", async () => {
    deepLink();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Load a different service" })).toBeTruthy());
    const sentBefore = calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Load a different service" }));
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(calls).toHaveLength(sentBefore);
  });
});
